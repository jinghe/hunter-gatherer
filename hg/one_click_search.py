import os
import sys
import re

from operator import itemgetter

from nugget_finder import load_ini, find_nuggets, do_search
from web_search import web_search

def query_web_search(query_str, ini):
    cache_folder = ini.get('cache_folder', ini.get('tmp_folder', './tmp') + "/cache")
    
    search_engine = ini.get('search_engine', 'Bing')
    search_count = int(ini.get('search_count', 200))

    return web_search(query_str, cache_folder, search_engine, search_count)
    
def score_passages(passages, scored_candidates):
    # for each passage, find each of the scored candidates in it
    sentences = list()
    for passage in passages:
        for sentence in passage[1].split(' .'):
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
    def same(text1, text2):
        #TODO implement ngram overlap
        return text1 == text2
    
    # while output is less than final length, accummulate
    output = ""
    idx = 0
    taken = list()
    while len(output) < final_length and idx < len(final_passages_scored):
        new = re.sub('\s+', ' ', final_passages_scored[idx][0][1])
        found = False
        for already in taken:
            if already == new:
                found = True
                break
        if not found:
            output = "%s %s" % (output, new)
            taken.append(new)
        idx += 1
    
    # shorten to fit
    while len(output) > final_length:
        output = re.sub('\s+[^\s]*$' , '', output)
    
    return output

if __name__ == '__main__':
    ####
    # input: ini file and query
    #
    ini_file = sys.argv[1]
    query_str = " ".join(sys.argv[2:])

    ini = load_ini(ini_file)

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
    for (final_length, output_type) in [ (1000, 'DESKTOP'), (140, 'MOBILE') ]:
        print "<%s>%s</%s>" % (output_type, assemble_output(final_passages_scored, final_length), output_type)

