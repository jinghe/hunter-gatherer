
from nltk.tokenize import wordpunct_tokenize, sent_tokenize;
from nltk.stem.snowball import EnglishStemmer
import sys
import numpy as np



class Parser:
    def __init__(self, stop_path):
        self.stop_set = set(map(lambda line: line.strip(), open(stop_path).readlines()))

    def parse(self, text):
        stemmer = EnglishStemmer()
        text = text.decode('utf-8')
        tokens = filter(lambda token: not self.stop_set.__contains__(token), map(lambda token: stemmer.stem(token.lower()), wordpunct_tokenize(text)));
        return tokens

def parse_nugget(parser, nugget, shingle_len):
    tokens = parser.parse(nugget['text'])
    token_num = len(tokens)
    shingles = []
    shingle_len = min(shingle_len, token_num)
    for i in xrange(token_num - shingle_len + 1):
        shingle_tokens = set(tokens[i:i+shingle_len])
        shingles.append(shingle_tokens)
    nugget['shingles'] = shingles 
    return nugget

def build_term_pos(tokens):
    data = {}
    for i in xrange(len(tokens)):
        term = tokens[i]
        data[term] = data.get(term, []) + [i]
    return data

def score_shingle(shingle, term_pos_dict):
    shingle_len = len(shingle)
    sorted_term_positions = []
    for term in shingle:
        if not term_pos_dict.has_key(term):
            return 0
        sorted_term_positions += map(lambda pos: (term, pos), term_pos_dict[term])
    if shingle_len == 1:
        return 1.
    sorted_term_positions.sort(key = lambda x: x[1])
    position_num = len(sorted_term_positions)
    i, j = 0, 0   
    min_dist, min_first, min_last = sys.maxint, 0, 0
    term_counts = {sorted_term_positions[i][0]: 1}
    while True:
        if len(term_counts) < shingle_len:
            j += 1
            if j >= position_num:
                break
            term, position = sorted_term_positions[j]
            term_counts[term] = term_counts.get(term, 0) + 1
        else:
            dist = sorted_term_positions[j][1] - sorted_term_positions[i][1] + 1
            if dist < min_dist:
                min_dist = dist
                min_first = sorted_term_positions[i][1]
                min_last = sorted_term_positions[j][1]
            term = sorted_term_positions[i][0]
            count = term_counts[term]
            if count == 1:
                term_counts.__delitem__(term)
            else:
                term_counts[term] -= 1
            i += 1
    _lambda = .95
    score = _lambda ** (float(min_dist - shingle_len) / shingle_len)
    return score

def evaluate(parser, summ_text, nuggets):
    summ_tokens = parser.parse(summ_text)
    summ_term_pos = build_term_pos(summ_tokens)
    summ_score, summ_count = 0, 0
    for nugget in nuggets:
        shingle_scores = []
        for shingle in nugget['shingles']:
            if len(shingle) == 0:
                continue
            shingle_scores.append(score_shingle(shingle, summ_term_pos))
        if not len(shingle_scores):
            continue
        nugget_score = np.mean(shingle_scores)
        summ_score += nugget_score * nugget['weight']
        summ_count += nugget['weight']
    summ_score /= summ_count
    return summ_score

def read_summ(summ_path):
    summs = []
    for line in open(summ_path).readlines()[1:]:
        qno, tag, text = line.strip().split('\t')
        if tag == 'OUT':
            summs.append((qno, text))
    return summs

def read_vstring(vstring_path):
    vstrings = []
    for line in open(vstring_path).readlines()[1:]:
        vstring_id, weight, length, dep, text = line.strip().split('\t')
        vstrings.append({'text': text, 'weight': float(weight)})
    return vstrings

def do_evaluate(summ_path, vstring_dir, stop_path):
    scores = []
    parser = Parser(stop_path)
    k = 3
    for qno, summ_text in read_summ(summ_path):
        vstring_path = '%s/%s.vitalstrings.txt' % (vstring_dir, qno)
        nuggets = read_vstring(vstring_path)
        nuggets = map(lambda nugget: parse_nugget(parser, nugget, k), nuggets)
        score = evaluate(parser, summ_text, nuggets)
        print qno, score
        scores.append(score)
    print np.mean(scores)

if __name__ == '__main__':
    do_evaluate(*sys.argv[1:])
