from sklearn.externals import joblib
from candidate_train import extract_candidate_features

class CandidateScorer:
    def __init__(self, ini): 
        self.dumpindex_command = ini.get('dumpindex_command', 'dumpindex')
        self.stat_index = ini.get('stat_index')
        self.model = joblib.load(ini.get('score_model'))

    def score(self, candidate, evidence, main_evidence, query):
        features = extract_candidate_features(candidate, evidence, main_evidence, query, self.dumpindex_command, self.stat_index)

#        print candidate, features
#        if features[6] == 0.0:
#            return 0.0
#        return features[0] * 0.5 + features[1] * 0.5 + features[2] * 0.5 + \
#                 (features[3] + features[5]) / features[6] #((features[6] + features[7] + features[8]) / 3. + 0.000001) # evidence times IDF
        
        return self.model.predict(np.array(features))

