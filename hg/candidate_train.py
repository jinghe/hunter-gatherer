import sys
import subprocess
import re
import os
import time
from shutil import copyfile, rmtree
from multiprocessing import Pool

import numpy as np
import pylab as pl
from nltk import word_tokenize
from sklearn.externals import joblib
from sklearn import ensemble

from IndriIndex import retrieve, Index
from Corpus import TRECWriter, Document
import nugget_finder
from web_search import web_search
from html_to_trec import detag_html_file
from parser import parse_into_chunks
import parser
from candidate_scorer import *

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
            count += 1
        trec_writer.close()

class TrainGenerator:
    def __init__(self, dumpindex_command, index_path):
        self.dumpindex_command = dumpindex_command
        self.index_path = index_path

    def __call__(self, instance):
        candidate, evidence, main_evidence, good_text = instance
        features = extract_candidate_features(candidate, evidence, main_evidence, self.dumpindex_command, self.index_path)
        is_good = all(map(lambda token: token.lower() in good_text, candidate.split()))
        return candidate, is_good, features


def gen_nugget_train(ini, htmls, query_str, good_text):
    from nugget_finder import load_ini, do_search, identify_candidates
    
    tmp_folder = ini.get('tmp_folder', './tmp')
    good_text = good_text.lower()

    ####
    # extract text from the HTML documents
    #
    sys.stderr.write("Extracting text...\n")
    path_to_corpus = "%s/to_index" % (tmp_folder,)
    if not os.path.exists(path_to_corpus):
        os.makedirs(path_to_corpus)
        
    html_count = 0
    for html in htmls:
        outfile = "%s/%s.txt" % (path_to_corpus, html_count)
        cached_detag = "%s.txt" % (html,)
        if os.path.exists(cached_detag):
            copyfile(cached_detag, outfile)
        else:
            detag_html_file(infile=html,outfile=outfile,id=html_count)
            copyfile(outfile, cached_detag)
        html_count += 1

    ####
    # build index
    #
    sys.stderr.write("Indexing...\n")
    path_to_index = "%s/index" % (tmp_folder,)
    if not os.path.exists(path_to_index):
        os.makedirs(path_to_index)
        
    config_template = file(ini.get('index_config_template', "./indexing.template")).read()
    config_filename = "%s/indexing.param" % (tmp_folder,)
    config_file = open(config_filename, "w")
    config_file.write(config_template.format(path_to_corpus=path_to_corpus,
                                             path_to_index=path_to_index))
    config_file.close()
    index_command = ini.get('index_command', 'IndriBuildIndex')

    retcode=subprocess.call([ index_command, config_filename ], stdout=sys.stderr, stderr=sys.stderr)
    assert retcode==0

    ####
    # generate query
    #
    parsed_query = parse_into_chunks(query_str)

    if bool(ini.get('condition_baseline', '')):
        print "baseline run."
        return ([], parsed_query, path_to_index)

    ####
    # main search
    #
    sys.stderr.write("Main search...\n")
    search_command = ini.get('search_command', './cpp/Search')    
    main_passages = do_search(parsed_query, search_command, path_to_index, 2000)
    #print 'passage num:', len(main_passages)

    ####
    # identify candidates
    #
    sys.stderr.write("Identifying candidates...\n")
    top_documents = int(ini.get('top_documents_for_candidate', '20'))
    candidates, main_evidence = identify_candidates(main_passages,
                                                    int(ini.get('main_search_passage_count', 3)),
                                                    top_documents)
    print 'candidate num:', len(candidates)

    ###
    # evidence search
    #
    sys.stderr.write("Evidence searching...\n")
    evidence = dict()
    t0 = time.time()
    searcher = Searcher(search_command, path_to_index,
                                      int(ini.get('evidence_search_passage_count', 10)))
    p = Pool(8)
    queries = map(lambda candidate: list(parsed_query) + [('NE', candidate[1] )], candidates)
    evidence_passages_list = p.map(searcher, queries, 50)
    p.close()
    print 'pool map evidence search:', time.time() - t0;
    for i in xrange(len(candidates)):
        candidate = candidates[i]
        evidence[candidate[0]] = filter(lambda passage: 
                                        all(map(lambda token: token.lower() in passage[1].lower(), candidate[1])), evidence_passages_list[i])

    ####
    # evaluate evidence
    #
    sys.stderr.write("Generating Training...\n")
    instances = []
    total = len(evidence)
    t0 = time.time()
    gen = TrainGenerator(ini.get('dumpindex_command', 'dumpindex'), ini.get('stat_index'))
    inputs = map(lambda candidate: (candidate, evidence[candidate], main_evidence[candidate], good_text), evidence.keys()) 
    p = Pool(8)
    instances = p.map(gen, inputs, 50)
    p.close()
    print 'pool map evaluating:', time.time() - t0

    ####
    # clean up
    #
    for i in xrange(0, html_count):
        try:
            os.unlink("%s/to_index/%s.txt" % (tmp_folder, i))
        except:
            pass

    return instances


def do_gen_nugget_train(ini_path):
    from nugget_finder import load_ini, do_search, identify_candidates
    from one_click_search import query_web_search
    
    ini = load_ini(ini_path)
    nugget_finder.USE_PATTERNS = True
    if bool(ini.get('condition_no_cclparser', '')) or \
           bool(ini.get('condition_baseline', '')):
        parser.USE_CCLPARSER = False

    if bool(ini.get('condition_no_boilerplate', '')) or \
           bool(ini.get('condition_baseline', '')):
        html_to_trec.USE_BOILERPLATE = False

    records = read_groundtruth(ini.get('ground_truth'))
    writer = open(ini.get('train_path'), 'w')
    for query_str, good_text in records:
        tmp_folder = ini.get('tmp_folder', '/tmp')
        print 'query:', query_str
        (htmls, html_urls) = query_web_search(query_str, ini)
        print "found", len(htmls), "pages"
        instances = gen_nugget_train(ini, htmls, query_str, good_text)
        for candidate, is_good, features in instances:
            writer.write('%d,%s#%s\n' % (is_good, ','.join(map(lambda feature: str(feature), features)), '%s:%s' % (query_str, candidate)))
        writer.flush()
        try:
            rmtree(tmp_folder)
            os.mkdir(tmp_folder)
        except Exception as e:
            print e
    writer.close()

def do_adjust_train(groundtruth_path, train_path, new_train_path):
    print 'loading groundtruth......'
    groundtruth = read_groundtruth(groundtruth_path)
    groundtruth_dict = {}
    map(lambda query_text: groundtruth_dict.__setitem__(query_text[0], set(map(lambda token: token.lower(), word_tokenize(query_text[1])))), groundtruth)
    
    print 'adjusting......'
    values_list = []
    comment_list = []
    train = open(train_path)
    line = train.readline()
    while line:
        value, comment = line.strip().split('#')
        query, nugget = comment.split(':')
        termset = groundtruth_dict[query]
        values = map(float, value.split(','))
        is_good = 1 if all(map(lambda token: termset.__contains__(token.lower()), nugget.split())) else -1;
        values[0] = is_good
        values_list.append(values)
        comment_list.append(comment)
        line = train.readline()

    writer = open(new_train_path, 'w')
    for i in xrange(len(values_list)):
        writer.write('%s#%s\n' % (','.join(map(str, values_list[i])), comment_list[i]))
    writer.close()
    


def my_loss(y_test, y_pred):
    real_true = float(len(filter(lambda y: y> 0, y_test)))
    pred_true = float(len(filter(lambda y: y> 0, y_pred)))
    real_pred_true = len(filter(lambda y: y>0, map(lambda x,y: x and y, y_pred, y_test)))
    if not pred_true:
        p = 0.0
    else:
        p = real_pred_true / pred_true
    r = real_pred_true / real_true
    f = p*r/(p+r)
    return f

def traintest_model(train_path):
    print 'loading......'
    data = np.genfromtxt(train_path, delimiter = ',')
    y = data[:,0]
    X = data[:,1:]
    sample_size = len(y)
    train_size = int(sample_size * .95)

    X_train, X_test = X[:train_size], X[train_size:]
    y_train, y_test = y[:train_size], y[train_size:]

    original_params = {'n_estimators': 100, 'max_depth': 2, 'random_state': 1,
                       'min_samples_split': 5}

    pl.figure()

    for label, color, setting in [
                                  ('Shrink=0.05', 'orange',
                                   {'learn_rate': 0.05, 'subsample': 1.0}),
                                  ('Shrink=0.02', 'turquoise',
                                   {'learn_rate': 0.02, 'subsample': 1.0}),
                                  ('Shrink=0.05, Sample=0.5', 'gray',
                                   {'learn_rate': 0.05, 'subsample': 0.5}),
                                  ('Shrink=0.02, Sample=0.5', 'black',
                                   {'learn_rate': 0.02, 'subsample': 0.5})]:
        print label
        params = dict(original_params)
        params.update(setting)

        clf = ensemble.GradientBoostingClassifier(**params)
        clf.fit(X_train, y_train)

        # compute test set deviance
        test_deviance = np.zeros((params['n_estimators'],), dtype=np.float64)

        for i, y_pred in enumerate(clf.staged_decision_function(X_test)):
            #test_deviance[i] = clf.loss_(y_test, y_pred)
            test_deviance[i] = my_loss(y_test, y_pred)

        pl.plot(np.arange(test_deviance.shape[0]) + 1, test_deviance, '-',
                color=color, label=label)
    pl.show()


def test_feature(train_path):
    data = np.genfromtxt(train_path, delimiter = ',')
    y = data[:,0]
    X = data[:,1:]
    sample_size = len(y)
    train_size = int(sample_size * .95)

    params = {'n_estimators': 100, 'max_depth': 2, 'random_state': 1,
                       'min_samples_split': 5}
    params.update({'learn_rate': 0.02, 'subsample': 1.0})
    clf = ensemble.GradientBoostingClassifier(**params)
    clf.fit(X, y)

    pl.figure()
    feature_names = np.array(['type', 'type', 'type', 'main', 'log_main', 'evi', 'log_evi', 'df1', 'log_df1', 'dfu8', 'log_dfu8', 'dfband', 'log_dfband'])

    feature_importance = clf.feature_importances_
# make importances relative to max importance
    feature_importance = 100.0 * (feature_importance / feature_importance.max())
    sorted_idx = np.argsort(feature_importance)[-8:]
    pos = np.arange(sorted_idx.shape[0]) + .5
    pl.barh(pos, feature_importance[sorted_idx], align='center')
    pl.yticks(pos, feature_names[sorted_idx])
    pl.xlabel('Relative Importance')
    pl.title('Variable Importance')
    pl.show()

    

def do_learn_model(train_path, model_path):
    print 'loading......'
    data = np.genfromtxt(train_path, delimiter = ',')
    y = data[:,0]
    X = data[:,1:]
    params = {'n_estimators': 100, 'max_depth': 2, 'random_state': 1,
                       'min_samples_split': 5}
    
    params.update({'learn_rate': 0.05, 'subsample': 0.5})
    clf = ensemble.GradientBoostingClassifier(**params)
    clf.fit(X, y)
    joblib.dump(clf, model_path, 3)


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
    elif option == '--gen-nugget-train':
        do_gen_nugget_train(*argv)
    elif option == '--adjust-train':
        do_adjust_train(*argv)
    elif option == '--test-model':
        traintest_model(*argv)
    elif option == '--test-feature':
        test_feature(*argv)
    elif option == '--learn-model':
        do_learn_model(*argv)




