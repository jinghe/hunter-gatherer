import os
import sys
import re
import nltk

from operator import itemgetter

from nugget_finder import load_ini, find_nuggets, do_search
from web_search import web_search

import parser
import html_to_trec

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

    def clean_text(text):
        """Remove URLs and other extraneous texts."""
        text = re.sub('http\:\/\/[a-zA-Z0-9\/\.\-\&]+', '', text)
        text = re.sub('\s+', ' ', text)
        text = re.sub('\<\/TITLE\>', ' ', text)
        return text
    
    # while output is less than final length, accummulate
    output = ""
    idx = 0
    taken = list()
    evidence = list()
    while len(output) < final_length and idx < len(final_passages_scored):
        passage_text = clean_text(final_passages_scored[idx][0][1])
        tokens = nltk.word_tokenize(passage_text)

        if len(tokens) == 0:
            idx += 1
            continue

        tokens = filter(lambda token: len(token) < 26, tokens)
        
        found = False
        for already in taken:
            if subsummed(already, passage_text, tokens):
                found = True
                break
        if not found:
            if not tokens[-1] in [ '.', '!', '?' ]:
                tokens.append('.')
            reassembled_passage = ' '.join(tokens)
            reassembled_passage = re.sub(" ([\.\,\.\'\;])", '\\1', reassembled_passage).strip()
            output = "%s %s" % (output, reassembled_passage)
            evidence.append(final_passages_scored[idx][0][0]['document'])
            taken.append(passage_text)
        idx += 1
    
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
    # score final passages
    #
    final_passages = do_search(parsed_query, ini.get('search_command', './cpp/Search'),
                               path_to_index, int(ini.get('main_search_passage_count', 3)))
    final_passages_scored = score_passages(final_passages, scored_candidates)
    
    ####
    # assemble final output
    #
    results = {}

    for (final_length, output_type) in outputs:
        results[output_type] = assemble_output(final_passages_scored, final_length)
    
    return results


if __name__ == '__main__':
    ####
    # input: ini file and query
    #
    ini_file = sys.argv[1]
    query_str = " ".join(sys.argv[2:])

    ini = load_ini(ini_file)

    results = one_click_search(ini, query_str, [ (1000, 'DESKTOP'), (140, 'TWITTER'), (280, 'MOBILE') ])

    tmp_folder = ini.get('tmp_folder', './tmp')
    output_file = "%s/out" % (tmp_folder,)
    output = file(output_file, 'w')

    for output_type in results:
        output_text = results[output_type][0]
        output.write("<%s>%s</%s>\n" % (output_type, output_text, output_type))

    output.close()
