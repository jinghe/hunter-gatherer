/*
 * Search.cpp
 *
 *  Created on: Sep 17, 2012
 *      Author: hejing
 */

#include "indri/QueryEnvironment.hpp"
#include "lemur/Exception.hpp"

#include <sys/socket.h>
#include <stdlib.h>
#include <errno.h>

#include <ext/stdio_filebuf.h>
#include <netdb.h>
#include <unistd.h>
#include <string.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>


#include <iostream>
#include <fstream>
#include <string>

using namespace indri::api;
using namespace lemur::api;
using namespace std;

int main(int argc, char** argv) {

    // process queries through socket

    int sd;
    struct sockaddr_in clin;

    sd = socket(AF_INET, SOCK_STREAM, 0);
    if (sd < 0) {
      cout << "ERROR opening socket";
      exit(1);
    }
    struct sockaddr_in sin;
    struct hostent *host = gethostbyname("localhost");
	  
    memcpy(&sin.sin_addr.s_addr, host->h_addr, host->h_length);
    sin.sin_family = AF_INET;
    sin.sin_port = htons(8852);
    
    if (bind(sd, (struct sockaddr *) &sin, sizeof(sin)) < 0) {
      cout << "ERROR on binding";
      exit(1);
    }
    
    listen(sd,5);

    try{
      // open index on command line
      QueryEnvironment env;
      string indexPath = argv[1];
      cout << "index:" << indexPath << endl;
      env.addIndex(indexPath);

      while(1){
	socklen_t clilen=sizeof(clin);

	cout << "Waiting on port 8856\n";
	int clientsocketfd = accept(sd, (struct sockaddr *)&clin, &clilen);
	if (clientsocketfd < 0) {
          cout << "ERROR on accept";
	  exit(1);
	}
	cout << "connected.\n";


	__gnu_cxx::stdio_filebuf<char> filebuf(clientsocketfd, std::ios::in);
	istream fin(&filebuf);

	__gnu_cxx::stdio_filebuf<char> out_filebuf(clientsocketfd, std::ios::out);
	ostream fos(&out_filebuf);
  
	fos << "index:" << indexPath << endl;

	// run an Indri query, returning top results
	string queryStr;
	getline(fin, queryStr);
	if(queryStr.compare("HUNTER-GATHERER-STOP") == 0){
	  break;
	}
	int resNum;
	fin >> resNum;
	std::vector<ScoredExtentResult> results = env.runQuery(queryStr,resNum);
	  
	fos << queryStr << endl;
	
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
	
	std::vector<indri::api::ParsedDocument*> documents = env.documents(results);
	vector<string> names = env.documentMetadata(results, "docno");
	vector<int> docIDs = env.documentIDsFromMetadata("docno", names);
	std::vector<DocumentVector*> docVecs = env.documentVectors(docIDs);
	
	// print results for each documents
	for (int i = 0; i < results.size(); i++) {
	  fos << names[i] << " " << results[i].score << " " << i + 1 << endl;

	  //show passage content;
	  fos << "passage-content:" << endl;
	  int wordBegin = results[i].begin;
	  int wordEnd = results[i].end;
	  int byteBegin = documents[i]->positions[wordBegin].begin;
	  int byteEnd = documents[i]->positions[wordEnd - 1].end;
	  const char* textPtr = documents[i]->text + byteBegin;
	  fos.write(textPtr, byteEnd - byteBegin);
	  fos << std::endl << std::endl;
	  fos << "----------" << std::endl;
	  fos << "matched-terms:" << endl;
	  
	  // show matched terms
	  
	  for (int queryPhraseIndex = 0; queryPhraseIndex < queryTerms.size();
	       queryPhraseIndex++) {
	    vector<string>& queryPhrase = queryTerms[queryPhraseIndex];
	    for (int queryTermIndex = 0;
		 queryTermIndex < queryPhrase.size(); queryTermIndex++) {
	      fos << queryPhrase[queryTermIndex];
	      if(queryTermIndex < queryPhrase.size() - 1)
		fos << ' ';
	    }
	    fos << ": ";
	    
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
		fos
		  << documents[i]->positions[docIndex].begin
		  - byteBegin << '-'
		  << documents[i]->positions[docIndex0 - 1].end
		  - byteBegin << ' ';
	      }
	    }
	    fos << endl;
	  }
	  fos << "==========" << std::endl;
	}
	// fos closes as it goes out of scope here
      }
      env.close();
    } catch (Exception& e) {
	LEMUR_ABORT(e);
    }
      
    return 0;
}

