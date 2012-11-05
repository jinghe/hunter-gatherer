from sklearn.externals import joblib
import numpy as np
import subprocess


def get_type_features(type_str):
    features = [0,0,0]
    if not type_str:
        features[2] = 1
    elif type_str == 'NE':
        features[0] = 1
    elif type_str.startswith('wiki'):
        features[1] = 1
    else:
        features[2] = 1
    return features

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
    tokens = candidate.split()
    tokens_string = candidate
    search_patterns = [''"#1(%s)"'', ''"#urd8(%s)"'', ''"#band(%s)"'']
    for search_pattern in search_patterns:
        command = [dumpindex_command, index_path, 'xcount', search_pattern % tokens_string]
        p = subprocess.Popen(command, stdout = subprocess.PIPE, stderr = subprocess.PIPE)
        line = p.stdout.readline().strip()
        pos = line.rfind(':')
        num = float(line[pos+1:])
        num += 1
        features += [num, np.log(num)]
        if len(tokens) == 1:
            features += [num, np.log(num)]
            features += [num, np.log(num)]
            break
    return features
        

def extract_candidate_features(candidate, evidence, main_evidence, dumpindex_command, term_stat_index):
    features = [];
    candidate_type = main_evidence['type']
    features = get_type_features(candidate_type) + get_main_evidence_features(main_evidence) + get_evidence_features(evidence) + get_idf_features(dumpindex_command, term_stat_index, candidate) 
    return features


class Searcher:
    def __init__(self, search_command, index_path, ret_size):
        self.search_command = search_command
        self.index_path = index_path
        self.ret_size = ret_size

    def __call__(self, query):
        from nugget_finder import load_ini, do_search, identify_candidates
        
        return do_search(query, self.search_command, self.index_path, self.ret_size)


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



class CandidateScorer:
    def __init__(self, ini): 
        self.dumpindex_command = ini.get('dumpindex_command', 'dumpindex')
        self.stat_index = ini.get('stat_index')
        self.model = joblib.load(ini.get('score_model'))

    def score(self, candidate, evidence, main_evidence, query):
        features = extract_candidate_features(candidate, evidence, main_evidence, self.dumpindex_command, self.stat_index)

#        print candidate, features
#        if features[6] == 0.0:
#            return 0.0
#        return features[0] * 0.5 + features[1] * 0.5 + features[2] * 0.5 + \
#                 (features[3] + features[5]) / features[6] #((features[6] + features[7] + features[8]) / 3. + 0.000001) # evidence times IDF
        
        return self.model.predict(np.array(features))

