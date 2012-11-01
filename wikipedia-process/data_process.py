import time
import os
import numpy as np
import subprocess

class MalletCRFFormat:
    def open_read(self, path):
        self.f = open(path)

    def open_write(self, path):
        self.f = open(path, 'w')

    def close(self):
        self.f.close()

    def next(self):
        instances = []
        while True:
            line = self.f.readline()
            while line and line <> '\n':
                tokens = line.strip().split()
                features = tokens[:-1]
                target = tokens[-1]
                instances.append((target, features))
                line = self.f.readline()
            if len(instances):
                return instances
            if not line and len(instances) == 0:
                return None

    def write(self, instances):
        for target, features in instances:
            self.f.write('%s %s\n' % (' '.join(features), target))
        self.f.write('\n')

class MalletClassifyFormat:
    def open_write(self, path):
        self.f = open(path, 'w')

    def open_read(self, path):
        self.f = open(path)
        
    def close(self):
        self.f.close()

    def next(self):
        line = self.f.readline()
        while True:
            if not line:
                return None
            line = line.strip()
            pos = line.find(' ')
            if pos > 0:
                label, feature_string = line[:pos], line[pos+1:]
                features = feature_string.split()
                return label, features

    def write(self, target_features):
        target, features = target_features
        self.f.write('%s %s\n' % (target, ' '.join(features)))

def get_format(format_name):
    if format_name == 'crf':
        return MalletCRFFormat()
    elif format_name == 'classify':
        return MalletClassifyFormat()
    else:
        return None


def do_crf2classify(in_path, out_path):
    '''
        convert mallet format file in crf to classify
    '''
    reader = MalletCRFFormat()
    reader.open_read(in_path)
    writer = MalletClassifyFormat()
    writer.open_write(out_path)

    instances = reader.next()
    while instances:
        for target, features in instances:
            writer.write((target, features))
        instances = reader.next()

    reader.close()
    writer.close()

def get_converter(converter_type):
    if converter_type == 'token':
        return TokenMalletConverter()
    elif converter_type == 'sentence':
        return SentenceMalletConverter()

class SentenceMalletConverter:
    def open(self, mallet_path):
        self.writer = MalletClassifyFormat()
        self.writer.open_write(mallet_path)

    def convert(self, labels, self_features):
        label_num = len(labels)
        sentence_label = 'O'
        for label in labels:
            if label <> 'O':
                sentence_label = label
                break
        feature_set = set()
        for self_feature in self_features:
            feature_set = feature_set.union(self_feature)
        features = list(feature_set)
        if len(features):
            self.writer.write(sentence_label, list(feature_set))

    def close(self):
        self.writer.close()


class TokenMalletConverter:
    def open(self, mallet_path):
        self.writer = MalletCRFFormat()
        self.writer.open_write(mallet_path)

    def convert(self, labels, self_features):
        label_num = len(labels)
        instances = []
        for i in xrange(label_num):
            features = []
            if i == 0:
                features.append('begin')
            if i == label_num - 1:
                features.append('end')
            for j in range(max(0, i-8), max(0,i-1)) + range(min(label_num-1, i+1), min(label_num-1, i+9)):
                if len(self_features[j]) > 0:
                    features.append('%s.word@urd8' % self_features[j][0])
            for j in range(max(0, i-2), min(label_num-1, i + 3)):
                if len(self_features[j]) > 0:
                    features.append('%s.word@%d' % (self_features[j][0], j -i))
                    for f in self_features[j][1:]:
                        features.append('%s@%d' % (f, j - i))
            instances.append((labels[i], features))
        self.writer.write(instances)

    def close(self):
        self.writer.close()

class TaggedText(list):
    def get_from_file(self, path):
        del self[0: len(self)]
        for line in open(path).readlines():
            self.parse_and_add(line)

    def get_from_string(self, text):
        del self[0: len(self)]
        lines = text.split('\n')
        for line in lines:
            self.parse_and_add(line)

    def parse_and_add(self, line): 
        sentence_data = []
        for token in line.strip().split():
            pos = token.find('/')
            if pos > 0:
                term = token[:pos]
                tags_string = token[pos+1:]
                if tags_string.startswith('[') and tags_string.endswith(']'):
                    tags = tags_string[1:-1].split(',')
                    sentence_data.append((term, tags))
        if len(sentence_data) > 0:
            self.append(sentence_data)

    def update_tag(self, tagged_text, ignore_set):
        assert(len(tagged_text) == len(self))
        for i in xrange(len(self)):
            sentence = tagged_text[i]
            self_sentence = self[i]
            assert(len(sentence) == len(self_sentence))
            for j in xrange(len(sentence)):
                for tag in sentence[j][1]: 
                    if ignore_set.__contains__(tag):
                        continue
                    self_sentence[j][1].append(tag)

    def __str__(self):
        return '\n'.join(map(lambda sentence: ' '.join(map(lambda term_tags: '%s/[%s]' % (term_tags[0], ','.join(term_tags[1])), sentence)), self))


def convert_mallet(tagged_text, mallet_converter, tag_set):
    for sentence in tagged_text:
        valid_sentence = False
        labels, self_features = [], [] 
        for word, tags in sentence:
            label = 'O'
            self_feature = [word.lower()]
            contain_wiki_tag = False
            for tag in tags:
                if tag.startswith('wiki:') and not contain_wiki_tag and tag_set.__contains__(tag):
                    label = tag
                    contain_wiki_tag = True
                elif not tag.startswith('wiki:'):
                    self_feature.append(tag)
            self_features.append(self_feature)
            labels.append(label)
        mallet_converter.convert(labels, self_features)
    mallet_converter.close()

def do_convert_mallet(match_path, mallet_path, tag_path, num):
    import Corpus
    reader = Corpus.TRECReader()
    reader.open(match_path)
    doc = reader.next()
    converter_type = 'token'
    converter = get_converter(converter_type)
    converter.open(mallet_path)
    tag_set = set(map(lambda s: s.strip(), open(tag_path).readlines()))
    num = int(num)

    doc_count = 0
    t0 = time.time()
    total_count = 0
    while doc:
        tagged_text = TaggedText()
        tagged_text.get_from_string(doc.text)
        convert_mallet(tagged_text, converter, tag_set) 
        doc = reader.next()
        doc_count += 1
        if doc_count % 10 == 0:
            print doc_count, time.time() - t0
        if doc_count > num:
            break
    converter.close()
    reader.close()


def count_tag(reader, positive_func):
    instances = reader.next()
    t0 = time.time()
    count = 0
    positive, negative = 0, 0
    while instances:
        if positive_func(instances):
            positive += 1
        else:
            negative += 1
        instances = reader.next()
        count += 1
        if count % 100000 == 0:
            print count, time.time() - t0, positive, negative
    print 'positive:%d negative:%d' % (positive, negative)
    return positive, negative

def sample_negative(reader, writer, sample_percent, convert_func = lambda a: a):
    t0 = time.time()
    count = 0
    instances = reader.next()
    while instances:
        if any(map(lambda instance: instance[0] <> 'O', instances)):
            writer.write(convert_func(instances))
        else:
            if np.random.binomial(1, sample_percent):
                writer.write(convert_func(instances))
        instances = reader.next()
        count += 1
        if count % 100000 == 0:
            print count, time.time() - t0

def do_sample_negative(in_path, k, out_path):
    '''
        sample some negative examples, so that the size of neg examples is k times of positive examples
    '''
    print '1st pass......'
    reader = MalletCRFFormat()
    reader.open_read(in_path)
    positive, negative = count_tag(reader, any(map(lambda instance: instance[0] <> 'O', instances)))
    reader.close()
    sample_percent = min(1, positive * float(k) / negative)

    print '2nd pass......'
    reader.open_read(in_path)
    writer = MalletCRFFormat()
    writer.open_write(out_path)
    sample_negative(reader, writer, sample_percent)
    writer.close()
    reader.close()

def remove_other_wikitags(instances, current_tag):
    new_instances = []
    for label, features in instances:
        if label <> current_tag:
            label = 'O'
        new_instances.append((label, features))
    return new_instances

def filter_sample(data_path, tag, negative_k, out_path):
    print '1st pass......'
    reader = MalletCRFFormat()
    reader.open_read(data_path)
    positive_func = lambda instances: any(map(lambda instance: instance[0] == tag, instances))
    positive, negative = count_tag(reader, positive_func)
    reader.close()
    sample_percent = min(1, positive * float(negative_k) / negative)

    print '2nd pass: writing to %s......' % out_path
    reader.open_read(data_path)
    writer = MalletCRFFormat()
    writer.open_write(out_path)
    sample_negative(reader, writer, sample_percent, lambda instances: remove_other_wikitags(instances, tag))
    writer.close()
    reader.close()

def do_filter_sample(data_path, tag_path, negative_k, out_path):
    '''
        filter only for a set of tags, and sample with parameter k
    '''
    tags = map(lambda s: s.strip(), open(tag_path).readlines())
    for tag in tags:
        print tag
        tag_out_path = '%s.%s' % (out_path, tag)
        filter_sample(data_path, tag, negative_k, tag_out_path)
        if os.path.getsize(tag_out_path) > 5e9:
            tmp_path = tag_out_path + '.tmp'
            subprocess.call(['head', '-n','15000000', tag_out_path], stdout=open(tmp_path, 'w'))
            os.rename(tmp_path, tag_out_path)
        

def do_prune(data_path, feature_path, out_path):
    reader, writer = MalletCRFFormat(), MalletCRFFormat()
    reader.open_read(data_path)
    writer.open_write(out_path)
    feature_set = set(map(lambda s: s.strip(), open(feature_path).readlines()))

    count = 0
    t0 = time.time()
    instances = reader.next()
    while instances:
        new_instances = []
        for target, features in instances:
            new_features = [] 
            for feature in features:
                if feature_set.__contains__(feature) or feature.find('word') < 0:
                    new_features.append(feature)
            new_instances.append((target, new_features))
        writer.write(new_instances)
        
        instances = reader.next()
        count += 1
        if count % 10000 == 0:
            print time.time() - t0, count

    reader.close()
    writer.close()

def do_partition(data_path, percent):
    '''
        partition crf mallet file into percent of training and 1-percent of test
    '''
    format_type = 'crf'
    reader, train_writer, test_writer = get_format(format_type), get_format(format_type), get_format(format_type)
    reader.open_read(data_path)
    train_path, test_path = data_path + '.train', data_path + '.test'
    train_writer.open_write(train_path)
    test_writer.open_write(test_path)
    percent = float(percent)

    instances = reader.next()
    while instances:
        if np.random.binomial(1, percent):
            train_writer.write(instances)
        else:
            test_writer.write(instances)
        instances = reader.next()

    train_writer.close()
    test_writer.close()
    reader.close()
    return train_path, test_path



if __name__ == '__main__':
    import sys
    option = sys.argv[1]
    argv = sys.argv[2:]
    if option == '--convert-mallet':
        do_convert_mallet(*argv)
    elif option == '--crf2classify':
        do_crf2classify(*argv)
    elif option == '--prune':
        do_prune(*argv)
    elif option == '--partition':
        do_partition(*argv)
    elif option == '--sample-negative':
        do_sample_negative(*argv)
    elif option == '--filter-sample':
        do_filter_sample(*argv)
    else:
        print 'error params'
           

