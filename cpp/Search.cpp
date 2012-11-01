/*
 * Search.cpp
 *
 *  Created on: Sep 17, 2012
 *      Author: hejing
 */

#include "indri/QueryEnvironment.hpp"
#include "lemur/Exception.hpp"

using namespace indri::api;
using namespace lemur::api;
using namespace std;

int main(int argc, char** argv) {
	try {
		QueryEnvironment env;
		std::string configPath = argv[1];
		ifstream fin(configPath.c_str());

		// open an Indri repository
		string indexPath;
		getline(fin, indexPath);
		cout << "index:" << indexPath << endl;
		env.addIndex(indexPath);

		// run an Indri query, returning top results
		string queryStr;
		getline(fin, queryStr);
		int resNum;
		fin >> resNum;
		std::vector<ScoredExtentResult> results = env.runQuery(queryStr,
				resNum);
		cout << queryStr << endl;

		// parse and stem query terms
		vector<vector<string> > queryTerms;
		string line;
		getline(fin, line);
		while (getline(fin, line)) {
			vector<string> terms;
			int pos = 0;
			int nextPos = line.find(' ', pos);
			while (nextPos != -1) {
				string term = line.substr(pos, nextPos - pos);
				terms.push_back(env.stemTerm(term));
				pos = nextPos + 1;
				nextPos = line.find(' ', pos);
			}
			terms.push_back(line.substr(pos));
			queryTerms.push_back(terms);
		}

		std::vector<indri::api::ParsedDocument*> documents = env.documents(
				results);
		vector<string> names = env.documentMetadata(results, "docno");
		vector<int> docIDs = env.documentIDsFromMetadata("docno", names);
		std::vector<DocumentVector*> docVecs = env.documentVectors(docIDs);

		// print results for each documents
		for (int i = 0; i < results.size(); i++) {
			cout << names[i] << " " << results[i].score << " " << i + 1 << endl;

			//show passage content;
			cout << "passage-content:" << endl;
			int wordBegin = results[i].begin;
			int wordEnd = results[i].end;
			int byteBegin = documents[i]->positions[wordBegin].begin;
			int byteEnd = documents[i]->positions[wordEnd - 1].end;
			const char* textPtr = documents[i]->text + byteBegin;
			cout.write(textPtr, byteEnd - byteBegin);
			std::cout << std::endl << std::endl;
			cout << "----------" << std::endl;
			cout << "matched-terms:" << endl;

			// show matched terms

			for (int queryPhraseIndex = 0; queryPhraseIndex < queryTerms.size();
					queryPhraseIndex++) {
				vector<string>& queryPhrase = queryTerms[queryPhraseIndex];
				for (int queryTermIndex = 0;
						queryTermIndex < queryPhrase.size(); queryTermIndex++) {
					cout << queryPhrase[queryTermIndex];
					if(queryTermIndex < queryPhrase.size() - 1)
					  cout << ' ';
				}
				cout << ": ";

				for (int docIndex = wordBegin; docIndex < wordEnd; docIndex++) {
					bool matched = true;
					int docIndex0 = docIndex;
					for (int queryTermIndex = 0;
							queryTermIndex < queryPhrase.size();
							queryTermIndex++, docIndex0++) {
						string& queryTerm = queryPhrase[queryTermIndex];
						string& docTerm =
								docVecs[i]->stems()[docVecs[i]->positions()[docIndex0]];
						if (docIndex0 >= wordEnd
								|| queryTerm.compare(docTerm) != 0) {
							matched = false;
							break;
						}
					}
					if (matched) {
						cout
								<< documents[i]->positions[docIndex].begin
										- byteBegin << '-'
								<< documents[i]->positions[docIndex0 - 1].end
										- byteBegin << ' ';
					}
				}
				cout << endl;
			}
			cout << "==========" << std::endl;
		}

		env.close();
	} catch (Exception& e) {
		LEMUR_ABORT(e);
	}

	return 0;
}

