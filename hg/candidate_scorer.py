from sklearn.externals import joblib

class CandidateScorer:
    def __init__(self, ini): 
        self.dumpindex_command = ini.get('dumpindex_command', 'dumpindex')
        self.stat_index = ini.get('stat_index')
        self.model = joblib.load(ini.get('score_model'))

    def score(self, candidate, evidence, main_evidence, query):
        features = extract_candidate_features(candidate, evidence, main_evidence, query, self.dumpindex_command, self.stat_index)
        return self.model.predict(np.array(features))

