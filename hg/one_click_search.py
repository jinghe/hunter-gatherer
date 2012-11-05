import os
import sys
import re
import nltk
import tempfile

from operator import itemgetter

from nugget_finder import load_ini, find_nuggets, do_search
from web_search import web_search

import parser
import html_to_trec
import nugget_finder

USE_ILP = True

def query_web_search(query_str, ini):
    cache_folder = ini.get('cache_folder', ini.get('tmp_folder', './tmp') + "/cache")
    
    search_engine = ini.get('search_engine', 'Bing')
    search_count = int(ini.get('search_count', 200))

    return web_search(query_str, cache_folder, search_engine, search_count)
    
def score_passages(passages, scored_candidates):
    # for each passage, find each of the scored candidates in it
    sentences = list()
    for passage in passages:
        for chunk in passage[1].split(' .'):
            chunk_sentences = nltk.sent_tokenize(chunk)
            for sentence in chunk_sentences:
                sentences.append( (passage[0], sentence, passage[1]) )
            
    final_passages = []
    for passage in sentences:
        passage_text = passage[1]
        passage_score = passage[0]['score']
        candidates_in_passage = []
        for scored_candidate in scored_candidates:
            candidate_text = scored_candidate[0]
            candidate_score = scored_candidate[1]
            
            # for a production system, all these candidates should
            # be conflated in an automaton
            if candidate_text in passage_text:
                # more interesting math should come here
                passage_score += candidate_score
                candidates_in_passage.append(scored_candidate[2])

        final_passages.append( (passage, passage_score, candidates_in_passage) )
            
    # sort by score
    final_passages.sort(key=itemgetter(1), reverse=True)

    return final_passages

def clean_passage_text(text):
    """Remove URLs and other extraneous texts."""
    text = re.sub('http\:\/\/[a-zA-Z0-9\/\.\-\&\_\%\+]+', '', text)
    text = re.sub('\s+', ' ', text)
    text = re.sub('\<\/TITLE\>', ' ', text)
    raw_tokens = text.split(' ')
    raw_tokens = filter(lambda token: len(token) < 26, raw_tokens)

    return (' '.join(raw_tokens)).strip()

def assemble_output_ilp(final_passages, scored_candidates, final_length):
    import glpk

    ####
    # Clean passage text and get final length per sentence.
    #
    sentences = list()
    seen = set()
    for passage in final_passages:
        for chunk in passage[1].split(' .'):
            chunk_sentences = nltk.sent_tokenize(chunk)
            
            for sentence in chunk_sentences:
                clean_text = clean_passage_text(sentence)
                if clean_text in seen:
                    continue
                if len(clean_text) > 20:
                    if not clean_text[-1] in [ '.', '!', '?' ]:
                        clean_text += '.'
                    sentences.append( ( clean_text, len(clean_text) + 1, passage[0]['document'] ) )
                    seen.add(clean_text)
                
    ####
    # Check which candidates appear in which sentences
    #
    candidate_per_sentence = set() # string '%d-%d' candidate-sentence
    candidate_scores = list()
    for cand_idx in xrange(len(scored_candidates)):
        candidate_text = scored_candidates[cand_idx][0]
        candidate_scores.append(scored_candidates[cand_idx][1])

        for sent_idx in xrange(len(sentences)):
            if candidate_text in sentences[sent_idx][0]:
                candidate_per_sentence.add( '%d-%d' % (cand_idx, sent_idx) )

    ####
    # Build ILP model
    #
    f = tempfile.NamedTemporaryFile(delete=False, suffix='.mod')
    f.write('param NS;\n')
    f.write('param NC;\n')
    f.write('param K;\n')
    f.write('param M{1..NS, 1..NC}, binary;\n')
    f.write('param L{1..NS}, integer;\n')
    f.write('param W{1..NC} ;\n')
    f.write('\n')
    
    f.write('var s{1..NS}, binary;\n')
    f.write('var e{1..NC}, binary;\n')
    f.write('\n')

    f.write('maximize z: sum { i in 1..NC } e[i]*W[i];\n');
    f.write('\n')
    
    f.write('subject to l:\n')
    f.write('  sum { i in 1..NS } L[i]*s[i] <= K;\n')
    f.write('\n')
    
    f.write('subject to m {j in 1..NC}:\n')
    f.write('  sum { i in 1..NS } M[i,j]*s[i] >= e[j];\n')
    f.write('\n')

    f.write('data;\n')
    f.write('param NS := %d;\n' % (len(sentences),))
    f.write('param NC := %d;\n' % (len(candidate_scores),))
    f.write('param K := %d;\n' % (final_length,))
    f.write('param L :=')
    for sent_idx in xrange(len(sentences)):
        if sent_idx > 0:
            f.write(',')
        f.write(' [%d] %d' % (sent_idx + 1, sentences[sent_idx][1]))
    f.write(';\n')
    
    f.write('param M :=')
    for sent_idx in xrange(len(sentences)):
        f.write('\n');
        for cand_idx in xrange(len(scored_candidates)):
            f.write('[%d,%d] ' % (sent_idx+1, cand_idx+1,))
            if '%d-%d' % (cand_idx, sent_idx) in candidate_per_sentence:
                f.write(' 1 ')
            else:
                f.write(' 0 ')
    f.write(';\n')

    f.write('param W :=')
    for cand_idx in xrange(len(scored_candidates)):
        f.write(' [%d] %f' % (cand_idx+1, candidate_scores[cand_idx]))
    f.write(';\n')
    f.write('end;\n')
    f.close()

    constraints = glpk.glpk(f.name)
    constraints.update()
    constraints.solve()
    #print constraints.solution()
    #print constraints.s

    # take selected sentences
    output = ""
    evidence = list()
    for sent_idx in xrange(len(sentences)):
        if constraints.s[sent_idx+1].value() == 1.0:
            output = "%s %s" % (output, sentences[sent_idx][0])
            evidence.append(sentences[sent_idx][2])

    output = output.strip()

    os.unlink(f.name)
    
    return (output, evidence)


def assemble_output(final_passages_scored, final_length):
    bigrams_cache = dict()
    
    def subsummed(old, new, tokens):
        if new == old:
            return True

        if len(new) < len(old) and new in old:
            return True

        if len(new) < len(old) * 1.2 and old in new:
            return True

        if not old in bigrams_cache:
            old_tokens =  nltk.model.NgramModel(2, nltk.word_tokenize(old))
            bigrams_cache[old] = old_tokens
        else:
            old_tokens = bigrams_cache[old]

        new_tokens = nltk.model.NgramModel(2, tokens)

        distance = nltk.metrics.jaccard_distance(new_tokens._ngrams, old_tokens._ngrams)

        if distance < 0.3:
            return True
        else:
            bigrams_cache[new] = new_tokens
            return False
    
    # while output is less than final length, accummulate
    output = ""
    idx = 0
    taken = list()
    evidence = list()
    while len(output) < final_length and idx < len(final_passages_scored):
        passage_text = clean_passage_text(final_passages_scored[idx][0][1])
        tokens = nltk.word_tokenize(passage_text)

        if len(tokens) == 0:
            idx += 1
            continue

        
        found = False
        for already in taken:
            if subsummed(already, passage_text, tokens):
                found = True
                break
        if not found:
            if not passage_text[-1] in [ '.', '!', '?' ]:
                passage_text += '.'
            output = "%s %s" % (output, passage_text)
            evidence.append(final_passages_scored[idx][0][0]['document'])
            taken.append(passage_text)
        idx += 1

    output = output.strip()
    
    # shorten to fit
    while len(output) > final_length:
        output = re.sub('\s+[^\s]*$' , '', output)
    
    return (output, evidence)

def one_click_search(ini, query_str, outputs):

    if bool(ini.get('condition_no_cclparser', '')) or \
           bool(ini.get('condition_baseline', '')):
        parser.USE_CCLPARSER = False

    if bool(ini.get('condition_no_boilerplate', '')) or \
           bool(ini.get('condition_baseline', '')):
        html_to_trec.USE_BOILERPLATE = False

    if bool(ini.get('condition_patterns', '')):
        nugget_finder.USE_PATTERNS = True

    if bool(ini.get('condition_candidate_scorer', '')):
        nugget_finder.USE_CANDIDATE_SCORER = True

    if bool(ini.get('condition_no_ilp', '')):
        USE_ILP = False
    else:
        USE_ILP = True

    ####
    # fetch results from Web search engine (or cache)
    #
    (htmls, html_urls) = query_web_search(query_str, ini)
    print "found", len(htmls), "pages"

    ####
    # extract relevant nuggets
    #
    (scored_candidates, parsed_query, path_to_index) = find_nuggets(ini, htmls, query_str)

    ####
    # final output
    #
    final_passages = do_search(parsed_query, ini.get('search_command', './cpp/Search'),
                               path_to_index, int(ini.get('main_search_passage_count', 3)))
    results = {}
    if USE_ILP:
        ####
        # assemble final output
        #
        for (final_length, output_type) in outputs:
            results[output_type] = assemble_output_ilp(final_passages, scored_candidates, final_length)
    else:
        ####
        # score final passages
        #
        final_passages_scored = score_passages(final_passages, scored_candidates)

        ####
        # assemble final output
        #
        for (final_length, output_type) in outputs:
            results[output_type] = assemble_output(final_passages_scored, final_length)
    
    return (results, html_urls)


if __name__ == '__main__':
    ####
    # input: ini file and query
    #
    ini_file = sys.argv[1]
    query_str = " ".join(sys.argv[2:])

    ini = load_ini(ini_file)

    (results, html_urls) = one_click_search(ini, query_str, [ (1000, 'DESKTOP'), (140, 'TWITTER'), (280, 'MOBILE') ])

    tmp_folder = ini.get('tmp_folder', './tmp')
    output_file = "%s/out" % (tmp_folder,)
    output = file(output_file, 'w')

    for output_type in results:
        output_text = results[output_type][0]
        output.write("<%s>%s</%s>\n" % (output_type, output_text, output_type))

    output.close()
