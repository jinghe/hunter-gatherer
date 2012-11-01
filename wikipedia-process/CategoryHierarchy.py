from MyTriple import *
import sys
import time

#def flat_recurseChildren(query, ts):
    #c = filter(lambda x: x.object() == query.subject(), ts)
    #if len(c) == 0: return []
    #else:
        #ret = []
        #for i in c: 
            #print query,'->',i;
            #ret.append( (i, recurseChildren(i, ts)) )
        #return ret

def recurse_category_children(query, index_sink, children_set):
    if children_set.__contains__(query):
        return; 
    children_set.add(query)
    if not index_sink.has_key(query):
        return;
    else:
        triples = index_sink[query]
        for triple in triples:
            if triple.predicate().endswith('broader'): 
                next_query = triple.subject()
                print '%s->%s' % (query, next_query);
                recurse_category_children(next_query, index_sink, children_set)

def get_category_path(cate, ancestor_cate_set, cate_hierarchy, level):
    '''
        return list of paths to the ancestors from a specific cate
        cate: source category
        ancestor_cate_set: target category set
    '''
    results = []
    if not cate_hierarchy.has_key(cate) or level <= 0:
        return []
    parent_triples = filter(lambda triple: triple.predicate().endswith('broader'), cate_hierarchy[cate])
    for parent_triple in parent_triples:    
        parent_cate = parent_triple.object()
        if ancestor_cate_set.__contains__(parent_cate):
            results.append([parent_cate])
        else:
            results += map(lambda cate_path: cate_path + [parent_cate], get_category_path(parent_cate, ancestor_cate_set, cate_hierarchy, level - 1))
    return results

current_article = ''
current_results = []
def sink_get_category_path(s, p, o, ancestor_cate_set, cate_hierarchy, level, path_threshold):
    global current_article
    global current_results
    results = get_category_path(o, ancestor_cate_set, cate_hierarchy, level)
    if current_article <> s: 
        if len(current_results) >= path_threshold:
            print current_article, current_results[0][0], len(current_results)
        current_article = s
        current_results = results
    else:
        current_results += results
        
    
def do_get_descedants(xml_path, cate_name_path):
    cate_names = map(lambda line: line.strip(), open(cate_name_path).readlines())
    print 'loading.....'
    np = NTriplesParser(sink=IndexSink(False))
    sink = np.parse(open(xml_path))
    print 'recursing......'
    for cate_name in cate_names:
        children_set = set()
        print cate_name;
        recurseChildren(cate_name, sink, children_set)
        children = list(children_set)
        children.sort()
        #for child in children:
            #print child
        print '';

def do_get_ancestor_path(article_category_path, hierarchy_path, cate_name_path):
    ancestor_cate_set = set(map(lambda line: line.strip(), open(cate_name_path).readlines()))
    hierarchy_np = NTriplesParser(sink=IndexSink(True))
    cate_hierarchy = hierarchy_np.parse(open(hierarchy_path))

    article_np = NTriplesParser(sink=FuncSink(lambda s,p,o: sink_get_category_path(s,p,o,ancestor_cate_set,cate_hierarchy,5,8)))
    sink = article_np.parse(open(article_category_path)) 


def do_count(category_path):
    lines = map(lambda line: line.strip(), open(category_path).readlines())
    m = {}
    for line in lines:
        tokens = line.split()
        if len(tokens) >= 2:
            cate = tokens[1]
            if m.has_key(cate):
              m[cate] += 1  
            else:
              m[cate] = 1
    for key, value in m.items():
        print key, value

def do_sample(category_path, sample_size, out_path):
    import random
    lines = map(lambda line: line.strip(), open(category_path).readlines())
    sample_size = int(sample_size)
    m = {}
    for line in lines:
        tokens = line.split()
        if len(tokens) >= 2:
            cate = tokens[1]
            url = tokens[0]
            if m.has_key(cate):
              m[cate].append(url) 
            else:
              m[cate] = [url]
    writer = open(out_path, 'w')
    for cate, urls in m.items():
        print len(urls), sample_size
        if len(urls) > sample_size:
            urls = random.sample(urls, sample_size)
            print len(urls)
        print len(urls)
        print '-' * 10
        for url in urls:
            writer.write('%s %s\n' % (url, cate))
    writer.close()

def do_filter(sample_url_path, corpus_path, sample_corpus_path):
    import Corpus
    name_set = set(map(lambda line: line.strip().split()[0].split('/')[-1], open(sample_url_path).readlines()))
    trec_reader = Corpus.TRECReader()
    trec_reader.open(corpus_path)
    trec_writer = Corpus.TRECWriter(sample_corpus_path)
    doc = trec_reader.next()
    start_title_tag = '<title>'
    start_title_tag_len = len(start_title_tag)
    end_title_tag = '</title>'
    count = 0
    while doc:
        text = doc.text
        start = text.find(start_title_tag)
        end = text.find(end_title_tag)
        title = ''
        if start >= 0 and end >= 0:
            title = text[start + start_title_tag_len: end]
        if name_set.__contains__(title):
            trec_writer.write(doc)
            count += 1
            if count % 1000 == 0:
                print count
        doc = trec_reader.next()
    trec_reader.close()
    trec_writer.close()
    


if __name__ == '__main__':
    option = sys.argv[1]
    argv = sys.argv[2:]
    if option == '--get-ancestors':
        do_get_ancestor_path(*argv)
    elif option == '--count':
        do_count(*argv)
    elif option == '--sample':
        do_sample(*argv)
    elif option == '--sample-filter':
        do_filter(*argv)





