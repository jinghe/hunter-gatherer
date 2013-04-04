import os
import subprocess
import sys
import time
import socket


from data_process import *
import Corpus

traintest_program = 'MyTrainTest'
fs_program = 'MyFeatureSelection'
stanford_tag_program = 'ArticleParser'
class_path = 'mallet.jar:mallet-deps.jar:stanford-corenlp-2012-07-06-models.jar:stanford-corenlp-2012-07-09.jar:xom.jar:joda-time.jar'

def check_java_compile(lib_dir):
    for filename in os.listdir(lib_dir):
        if filename.endswith('.java'):
           filepath = '/'.join([lib_dir, filename])
           class_filepath = filepath.replace('.java', '.class')
           if not os.path.isfile(class_filepath) or os.path.getmtime(class_filepath) < os.path.getmtime(filepath):
               command = ['javac','-classpath', class_path, filepath]
               print ' '.join(command)
               subprocess.call(command)

def get_classpath(lib_dir):
    global class_path 
    class_path = ':'.join(map(lambda path: '/'.join([lib_dir, path]), class_path.split(':') ) + [lib_dir, './'] )
    return class_path

def prune_size(path, upper_bound, line_num):
    if os.path.getsize(path) > upper_bound:
        print 'heading %s......' % path
        tmp_path = path + '.tmp'
        subprocess.call(['head', '-n',str(line_num), path], stdout=open(tmp_path, 'w'))
        os.rename(tmp_path, path)

def prune_feature(path, feature_num):
    classify_path = '%s.classify' % path
    print 'converting %s to %s......' % (path, classify_path)
    do_crf2classify(path, classify_path)

    feature_path = '%s.feature' % path
    print 'feature selection for %s......' % feature_path
    command = ['java', '-Xms13G', '-Xmx13G', '-classpath', class_path, fs_program, '--input', classify_path,  '--prune-count', '3',  '--output-feature', feature_path, '--prune-infogain', str(feature_num)]
    print ' '.join(command)
    subprocess.call(command)

    pruned_path = '%s.prune' % path
    print 'pruning for %s......' % pruned_path
    do_prune(path, feature_path, pruned_path)

    os.remove(classify_path)
    return pruned_path

def parse_score(line):
    name_scores = line.strip().split()[1:]
    scores = []
    for name_score in name_scores:
        scores.append(name_score.split('=')[1])
    return scores

def do_train_test(path, model_path, feature_num, lib_dir):
    get_classpath(lib_dir)
    check_java_compile()
    prune_size(path, 2.2e9, 7000000)

    feature_num = int(feature_num)
    if feature_num > 0:
        path = prune_feature(path, feature_num)

    print 'partitioning %s......' % path
    train_path, test_path = do_partition(path, .5)

    print 'training......'
    command = ['java', '-Xms13G', '-Xmx13G', '-classpath', class_path, traintest_program, '--train-test', train_path, test_path, model_path]
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    train_scores = 0,0,0
    test_scores = 0,0,0
    for line in process.stderr.readlines():
        line = line.strip()
        if line.startswith('train precision'):
            train_scores = parse_score(line)
        elif line.startswith('test precision'):
            test_scores = parse_score(line)
    print 'train:', ' '.join(train_scores)
    print 'test:', ' '.join(test_scores)
    score_writer = open('%s.score' % path, 'w')
    score_writer.write('\n'.join([' '.join(train_scores), ' '.join(test_scores)]))
    score_writer.close()

    os.remove(train_path)
    os.remove(test_path)


def do_batch_train_test(dir_path, feature_num, lib_dir):
    get_classpath(lib_dir)
    check_java_compile()
    file_names =  os.listdir(dir_path)
    file_names.sort()
    for file_name in file_names:
        data_path = '/'.join([dir_path, file_name])
        if not os.path.isfile(data_path):
            continue
        model_path = '%s.model' % data_path
        do_train_test(data_path, model_path, feature_num)
        print '-' * 100

def do_combine_train_test_scores(score_dir_path, out_path):
    '''
        score_dir_path: a directory contain the scores for different relations;
        out_path: relation with precision/recall/f1 scores
    '''
    writer = open(out_path, 'w')
    for filename in os.listdir(score_dir_path):
        if filename.endswith('.score'):
            pos = filename.find('.', 1)
            pattern_name = filename[:pos]
            filepath = '/'.join([score_dir_path, filename])
            test_score_line = open(filepath).readlines()[-1]
            writer.write('%s %s\n' % (pattern_name, test_score_line.strip()))
    writer.close()

def base_tag(text):
    t = time.time()
    tmp_text_path = '%f.text.tmp' % t;
    tmp_tag_path = '%f.tag.tmp' % t

    writer = open(tmp_text_path, 'w')
    writer.write(text)
    writer.close()

    command = ['java', '-classpath', class_path, stanford_tag_program, '--parse-text', tmp_text_path, tmp_tag_path]
    print ' '.join(command)
    subprocess.call(command)
    tagged_text = TaggedText()
    tagged_text.get_from_file(tmp_tag_path)
    os.remove(tmp_text_path)
    os.remove(tmp_tag_path)
    return tagged_text


def crf_label(mallet_path, labeled_mallet_path, model_path):
    command = ['java', '-classpath', class_path, traintest_program, '--test', mallet_path, model_path, labeled_mallet_path]
    print ' '.join(command)
    subprocess.call(command)

def malletlabel_2_taggedtext(mallet_path):
    tagged_text = TaggedText()
    reader = MalletCRFFormat()
    reader.open_read(mallet_path)
    instances = reader.next()
    while instances:
        sentence_data = []
        for label, features in instances:
            sentence_data.append(('', [label]))
        tagged_text.append(sentence_data)
        instances = reader.next()
    return tagged_text


prune_t = 0
label_t = 0

def wiki_tag(mallet_path, model_path, feature_path):
    global prune_t
    global label_t
    #1. prune the mallet path with features
    t = time.time()
    pruned_mallet_path = mallet_path
    #pruned_mallet_path = '%s.prune' % mallet_path
    #do_prune(mallet_path, feature_path, pruned_mallet_path)
    #prune_t += time.time() - t

    #2. run CRF labelling program
    t = time.time()
    labeled_mallet_path = '%s.label' % mallet_path
    crf_label(pruned_mallet_path, labeled_mallet_path, model_path)
    label_t += time.time() - t
    #print prune_t, label_t

    #3. build a new tagged text object
    tagged_text = malletlabel_2_taggedtext(labeled_mallet_path)

    #4. clear
    #os.remove(pruned_mallet_path)
    #os.remove(labeled_mallet_path)

    return tagged_text

def apply_tag(text_path, tagged_text, model_dir, pattern_set):
    mallet_converter = TokenMalletConverter()
    mallet_path = '%s.mallet' % text_path
    mallet_converter.open(mallet_path)
    convert_mallet(tagged_text, mallet_converter, set())

    for filename in os.listdir(model_dir):
        if filename.endswith('model'):
            pattern_name = filename[:-6]
            if not pattern_set.__contains__(pattern_name):
                continue
            print pattern_name
            model_path = '/'.join([model_dir, filename])
            feature_path = '/'.join([model_dir, filename.replace('.model', '.feature')])

            wiki_tagged_text = wiki_tag(mallet_path, model_path, feature_path)
            tagged_text.update_tag(wiki_tagged_text, set(['O']))
    #os.remove(mallet_path)
    return tagged_text

def do_apply(text_path, model_dir, pattern_path, out_path, lib_dir):
    get_classpath(lib_dir)
    check_java_compile(lib_dir)
    pattern_set = set(map(lambda line: line.split()[0], open(pattern_path).readlines()))
    print 'POS/NER tagging......'
    text = ''.join(open(text_path).readlines())
    tagged_text = base_tag(text)
    print 'extracting features......'
    tagged_text = apply_tag(text_path, tagged_text, model_dir, pattern_set)
    print 'writing......'
    writer = open(out_path, 'w')
    writer.write(tagged_text.__str__())
    writer.close()

def do_batch_apply(trec_path, model_dir, pattern_path, out_path, lib_dir):
    get_classpath(lib_dir)
    check_java_compile(lib_dir)
    pattern_set = set(map(lambda line: line.split()[0], open(pattern_path).readlines()))
    base_tag_trec_path = '%s.basetag' % trec_path
    command = ['java', '-Xms13G', '-Xmx13G', '-classpath', class_path, stanford_tag_program, '--batch-trec', trec_path, base_tag_trec_path]
    print ' '.join(command)
    subprocess.call(command)

    t = time.time()
    reader = Corpus.TRECReader()
    reader.open(base_tag_trec_path)
    doc = reader.next()
    indecies = [0]
    ids = []
    all_tagged_text = None
    while doc:
        tagged_text = TaggedText()
        tagged_text.get_from_string('\n'.join(filter(lambda line:not line.startswith('<'), doc.text.split('\n'))))
        if all_tagged_text:
            all_tagged_text += tagged_text
        else:
            all_tagged_text = tagged_text
        indecies.append(len(all_tagged_text))
        tagged_text = apply_tag(trec_path, tagged_text, model_dir, pattern_set)
        ids.append(doc.ID)
        doc = reader.next()
    reader.close()
    os.remove(base_tag_trec_path)

    #tagged_text = apply_tag(trec_path, all_tagged_text, model_dir, pattern_set)
    print len(tagged_text)
    writer = Corpus.TRECWriter(out_path)
    for i in xrange(len(ids)):
        doc = Corpus.Document(ids[i], tagged_text[indecies[i]: indecies[i+1]].__str__())
        writer.write(doc)
    writer.close()
    global prune_t, label_t
    print time.time() - t, prune_t, label_t

def socket_communicate(message, host, port, timeout = 15.0):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    s.connect((host, int(port)))
    s.sendall(message)
    s.shutdown(socket.SHUT_WR)
    result = ""
    while True:
        data = s.recv(4096)
        if not data: break
        result = result + data
    s.close()
    return result


def server_base_tag(text, host, port):
    result = socket_communicate(text, host, port)
    tagged_text = TaggedText()
    tagged_text.get_from_string(result)
    return tagged_text

def server_apply_tag(text_path, tagged_text, host, port):
    mallet_converter = TokenMalletConverter()
    mallet_path = '%s.mallet' % text_path
    mallet_converter.open(mallet_path)
    convert_mallet(tagged_text, mallet_converter, set())
    
    mallet_content = open(mallet_path).read()
    result = ''
    t0 = time.time()
    result = socket_communicate(mallet_content, host, port)
    lines = result.split('\n')
    idx = 0
    for sentence_idx in xrange(len(tagged_text)):
        sentence_data = tagged_text[sentence_idx]
        for sentence_token_idx in xrange(len(sentence_data)):
            term, tags = sentence_data[sentence_token_idx]
            tag_set = set(tags)
            wiki_tags = lines[idx].strip().split()
            for wiki_tag in wiki_tags:
                if wiki_tag <> 'O':
                    tag_set.add(wiki_tag)
            sentence_data[sentence_token_idx] = term, list(tag_set)
            idx += 1
        idx += 1
    return tagged_text

def do_server_apply(text_path, out_path):
    host = 'localhost'
    base_tag_port = '8854'
    crf_port = '8855'
    text = ''.join(open(text_path).readlines())
    tagged_text = server_base_tag(text, host, base_tag_port)
    print 'extracting features......'
    tagged_text = server_apply_tag(text_path, tagged_text, host, crf_port)
    print 'writing......'
    writer = open(out_path, 'w')
    writer.write(tagged_text.__str__())
    writer.close()


if __name__ == '__main__':
    option = sys.argv[1]    
    argv = sys.argv[2:]
    if option == '--train-test':
        do_train_test(*argv)
    elif option == '--batch-train-test':
        do_batch_train_test(*argv)
    elif option == '--combine-score':
        do_combine_train_test_scores(*argv)
    elif option == '--apply':
        do_apply(*argv)
    elif option == '--batch-apply':
        do_batch_apply(*argv)
    elif option == '--server-apply':
        do_server_apply(*argv)
    else:
        print 'ERROR PARAM!'


