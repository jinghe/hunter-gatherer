from data_process import *
import os
import subprocess
import sys
import Corpus

traintest_program = 'MyTrainTest'
fs_program = 'MyFeatureSelection'
stanford_tag_program = 'ArticleParser'
class_path = '.:depend/mallet.jar:depend/mallet-deps.jar:depend/stanford-corenlp-2012-07-06-models.jar:depend/stanford-corenlp-2012-07-09.jar:depend/xom.jar:depend/joda-time.jar'


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

def do_train_test(path, model_path, feature_num):
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


def do_batch_train_test(dir_path, feature_num):
    file_names =  os.listdir(dir_path)
    file_names.sort()
    for file_name in file_names:
        data_path = '/'.join([dir_path, file_name])
        if not os.path.isfile(data_path):
            continue
        model_path = '%s.model' % data_path
        do_train_test(data_path, model_path, feature_num)
        print '-' * 100


def base_tag(text):
    t = time.time()
    tmp_text_path = '%f.text.tmp' % t;
    tmp_tag_path = '%f.tag.tmp' % t

    writer = open(tmp_text_path, 'w')
    writer.write(text)
    writer.close()

    command = ['java', '-Xms13G', '-Xmx13G', '-classpath', class_path, stanford_tag_program, '--parse-text', tmp_text_path, tmp_tag_path]
    print ' '.join(command)
    subprocess.call(command)
    tagged_text = TaggedText()
    tagged_text.get_from_file(tmp_tag_path)
    os.remove(tmp_text_path)
    os.remove(tmp_tag_path)
    return tagged_text


def crf_label(mallet_path, labeled_mallet_path, model_path):
    command = ['java', '-Xms13G', '-Xmx13G', '-classpath', class_path, traintest_program, '--test', mallet_path, model_path, labeled_mallet_path]
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


def wiki_tag(mallet_path, model_path, feature_path):
    #1. prune the mallet path with features
    pruned_mallet_path = '%s.prune' % mallet_path
    do_prune(mallet_path, feature_path, pruned_mallet_path)

    #2. run CRF labelling program
    labeled_mallet_path = '%s.label' % mallet_path
    crf_label(pruned_mallet_path, labeled_mallet_path, model_path)

    #3. build a new tagged text object
    tagged_text = malletlabel_2_taggedtext(labeled_mallet_path)

    #4. clear
    os.remove(pruned_mallet_path)
    os.remove(labeled_mallet_path)

    return tagged_text

def apply_tag(text_path, tagged_text, model_dir):
    mallet_converter = TokenMalletConverter()
    mallet_path = '%s.mallet' % text_path
    mallet_converter.open(mallet_path)
    convert_mallet(tagged_text, mallet_converter, set())

    for filename in os.listdir(model_dir):
        if filename.endswith('model'):
            model_path = '/'.join([model_dir, filename])
            feature_path = '/'.join([model_dir, filename.replace('.model', '.feature')])

            wiki_tagged_text = wiki_tag(mallet_path, model_path, feature_path)
            tagged_text.update_tag(wiki_tagged_text, set(['O']))
    os.remove(mallet_path)
    return tagged_text

def do_apply(text_path, model_dir, out_path):
    print 'POS/NER tagging......'
    text = ''.join(open(text_path).readlines())
    tagged_text = base_tag(text)
    print 'extracting features......'
    tagged_text = apply_tag(text_path, tagged_text, model_dir)
    print 'writing......'
    writer = open(out_path, 'w')
    writer.write(tagged_text.__str__())
    writer.close()

def do_batch_apply(trec_path, model_dir, out_path):
    base_tag_trec_path = '%s.basetag' % trec_path
    command = ['java', '-Xms13G', '-Xmx13G', '-classpath', class_path, stanford_tag_program, '--batch-trec', trec_path, base_tag_trec_path]
    print ' '.join(command)
    subprocess.call(command)

    reader = Corpus.TRECReader()
    reader.open(base_tag_trec_path)
    writer = Corpus.TRECWriter(out_path)
    doc = reader.next()
    while doc:
        print doc.ID
        tagged_text = TaggedText()
        tagged_text.get_from_string('\n'.join(filter(lambda line:not line.startswith('<'), doc.text.split('\n'))))
        tagged_text = apply_tag(trec_path, tagged_text, model_dir)
        doc.text = tagged_text.__str__()
        writer.write(doc)
        doc = reader.next()
    reader.close()
    writer.close()

if __name__ == '__main__':
    option = sys.argv[1]    
    argv = sys.argv[2:]
    if option == '--train-test':
        do_train_test(*argv)
    elif option == '--batch-train-test':
        do_batch_train_test(*argv)
    elif option == '--apply':
        do_apply(*argv)
    elif option == '--batch-apply':
        do_batch_apply(*argv)
    else:
        print 'ERROR PARAM!'


