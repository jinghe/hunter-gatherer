import sys
import subprocess
import re
import numpy as np

from IndriIndex import retrieve, Index
from Corpus import TRECWriter, Document

def get_type_features(candidate):
    features = [0,0,0]
    type_str = candidate[0]
    if type_str == 'NE':
        features[0] = 1
    elif type_str.startswith('wiki'):
        features[1] = 1
    else:
        features[2] = 1

def get_main_evidence_features(main_evidence):
    score = 1.0
    for entry in main_evidence.get('passages', []):
        score_line = entry[0]
        score += 100.0 + score_line['score']
    return [score, np.log(score)]
    
def get_evidence_features(evidence):
    score = 1.0
    for entry in evidence:
        score_line = entry[0]
        score += 100.0 + score_line['score']
    return [score, np.log(score)]

def get_idf_features(dumpindex_command, index_path, candidate):
    features = []
    tokens_string = ' '.join(candidate[1])
    search_patterns = [''"#1(%s)"'', ''"#urd8(%s)"'', ''"#band(%s)"'']
    for search_pattern in search_patterns:
        command = [dumpindex_command, index_path, 'dx', search_pattern % tokens_string]
        p = subprocess.Popen(command, stdout = subprocess.PIPE, stderr = subprocess.PIPE)
        line = p.stdout.readline().strip()
        pos = line.rfind(':')
        num = float(line[pos+1:])
        num += 1
        features += [num, np.log(num)]
    return features
        

def extract_candidate_features(candidate, evidence, main_evidence, query, dumpindex_command, term_stat_index):
    features = [];
    features = get_type_features(candidate) + get_main_evidence_features(main_evidence) + get_evidence_features(evidence) + get_idf_features(dumpindex_command, term_stat_index, candidate) 

class CandidateScorer:
    def __init__(ini): 
        self.dumpindex_command = ini.get('dumpindex_command', 'dumpindex')
        self.stat_index = ini.get('stat_index')
        self.score_model = self.load_model(ini.get('score_model'))

    def score(candidate, evidence, main_evidence, query):
        features = extract_candidate_features(candidate, evidence, main_evidence, query, self.dumpindex_command, self.stat_index)
        
        #TODO: add real score code


def expand_groudtruth(sample_dir, out_path):
    query_path = '%s/1C2-E-SAMPLE.tsv' % sample_dir
    query_ids = map(lambda line: line.strip().split()[0],  open(query_path).readlines())
    queries = map(lambda line: ' '.join(line.strip().split()[2:]),  open(query_path).readlines())
    writer = open(out_path, 'w')

    for i in xrange(len(query_ids)):
        writer.write('%s\ncate\nurl\n' % queries[i])
        iunit_path = '%s/1C2-E-SAMPLE.iUnits/%s.iUnits.tsv' % (sample_dir, query_ids[i])
        for line in open(iunit_path).readlines():
            if line.startswith('V'):
                line = ' '.join(filter(lambda token: not token.startswith('DEP'), line.split()[1:]))
                line = ''.join(map(lambda x: re.sub('[^A-Za-z0-9]',' ', x), line.strip()))
                tokens = line.split()
                writer.write('%s\n' % ' '.join(tokens))
        writer.write('\n')
    writer.close()

def read_groundtruth(path):
    records = []
    reader = open(path)
    more_line = True
    while True:
        if not more_line:
            break
        query = reader.readline().strip() 
        cate = reader.readline().strip()
        url = reader.readline().strip()
        content = ''
        while True:
            line = reader.readline()
            if not line:
                more_line = False
                break
            if len(line.strip()) == 0:
                break
            content += line
        records.append((query, content))
    return records

def do_get_train_html(groundtruth_path, index_path, html_folder):
    index = Index(index_path)
    records = read_groundtruth(groundtruth_path)
    for query, content in records:
        query_filename = '_'.join(query.split())
        trec_writer = TRECWriter('%s/%s' % (html_folder, query_filename))
        docnos = retrieve(query, index_path)
        count = 1
        for docno in docnos[:200]:
            html = index.get_doc_content(docno)
            trec_writer.write(Document('%s-%d' % (query_filename, count), html))
        trec_writer.close()

if __name__ == '__main__':
    option = sys.argv[1]    
    argv = sys.argv[2:]
    if option == '--test-idf':
        candidate = [0, argv[1:]]
        print get_idf_features('dumpindex', argv[0], candidate)
    elif option == '--expand-groundtruth':
        expand_groudtruth(*argv)
    elif option == '--get-train-html':
        do_get_train_html(*argv)



