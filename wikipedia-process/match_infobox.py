import datetime
import time

def load_infobox(infobox_path):
    infobox = {}
    reader = open(infobox_path)
    infobox_line = reader.readline()
    while infobox_line:
        tokens = infobox_line.split('----')
        name, key, value = tokens[:3]
        name = name.split('/')[-1]
        if not infobox.has_key(name):
            infobox[name] = {}
            curr_infobox = infobox[name]
        key = key.split('/')[-1]
        value_tokens = value.split()
        value_type = ''
        if len(value_tokens) == 1:
            value = value_tokens[0].split('/')[-1]
        else:
            lang = value_tokens[0]
            value_type = value_tokens[1]
            value = ' '.join(value_tokens[2:])
        if curr_infobox.has_key(key):
            curr_infobox[key].append((value_type, value))
        else:
            curr_infobox[key] = [(value_type, value)]
        infobox_line = reader.readline()
    return infobox


class Sentence(list):
    def __init__(self, text):
        for token in text.split():
            pos = token.rfind('/')
            term = token[:pos]
            tags = token[pos+2:-1].split(',')
            self.append((term, tags))

    def __str__(self):
        text = ' '.join(map(lambda term_tags: '%s/[%s]' % (term_tags[0], ','.join(term_tags[1])), self))
        return text

class TextPattern:
    def __init__(self, text):
        pos = text.find('(')
        if pos > 0:
            text = text[:pos]
        pos = text.find(',')
        if pos > 0 and pos < len(text) - 1:
            if text[pos-1] <> ' ':
                text = text[:pos] + ' ' + text[pos:]
            if text[pos+1] <> ' ':
                text = text[:pos+1] + ' ' + text[pos+1:]
        self.tokens = map(lambda token: token.lower(), text.split())
        self.token_num = len(self.tokens)

    def match(self, sentence):
        if self.token_num > len(sentence):
            return []
        is_match = True
        for i in xrange(self.token_num):
            if self.tokens[i] <> sentence[i][0].lower():
                is_match = False
                break
        if is_match: return range(0, self.token_num)
        match_indecies = self.match(sentence[1:])
        if len(match_indecies) > 0:
            match_indecies = map(lambda index: index + 1, match_indecies)
        return match_indecies


daySuffixLookup = [ "th","st","nd","rd","th",
                           "th","th","th","th","th" ];
class DatePattern:
    def __init__(self, text):
        self._expand_match_sets(text)

    def _expand_match_sets(self, text):
        self.match_sets = [set(), set(), set()]
        year, month, day = text.split('-')
        self.match_sets[0] = set([year,year[2:]])
        month_date = datetime.datetime.strptime(month, '%m')
        self.match_sets[1] = set([month_date.strftime('%b').lower(),month_date.strftime('%B').lower(),month_date.strftime('%m'), str(int(month_date.month))])
        int_day = int(day)
        self.match_sets[2] = set([day, str(int_day), str(int_day) + daySuffixLookup[int_day % 10]])

    def match(self, sentence):
        indecies = []
        matches = [0,0,0]
        for i in xrange(len(sentence)):
            token = sentence[i][0].lower()
            for j in xrange(3):
                if self.match_sets[j].__contains__(token):
                    matches[j] = 1
                    if not i in indecies:
                        indecies.append(i)
        if all(matches):
            return indecies
        else:
            return []

class InfoBoxMatcher:
    def __init__(self):
        self.LENGTH_LIMIT = 500

    def match(self, infobox, sentence_lines):
        patterns = self._process_infobox(infobox)
        tagged_text = ''
        for sentence_line in sentence_lines:
            sentence = Sentence(sentence_line)
            tagged_text += self._match_sentence(patterns, sentence).__str__() + '\n'
        return tagged_text

    def _match_sentence(self, patterns, sentence):
        if len(sentence) > self.LENGTH_LIMIT:
            return sentence
        for name, pattern in patterns:
            tag_name = 'wiki:%s' % name
            try:
                match_indeces = pattern.match(sentence);
            except Exception as e:
                print len(sentences)
            for i in match_indeces:
                tags = sentence[i][1]
                if tags.count(tag_name) == 0:
                    tags.append(tag_name)
        return sentence

    def _process_infobox(self, entity_infobox):
        patterns = []
        for name, values in entity_infobox.items():
            for value_type, value in values:
                patterns.append((name, self._generate_pattern(value_type, value)))
        return patterns

    def _generate_pattern(self, value_type, value):
        text = value.replace('_', ' ')
        if value_type.endswith('date'):
            return DatePattern(text)
        else:
            return TextPattern(text)

def do_match(infobox_path, text_path, out_path):
    import Corpus
    import time

    print 'loading......'
    infobox = load_infobox(infobox_path)
    reader = Corpus.TRECReader()
    reader.open(text_path)
    writer = Corpus.TRECWriter(out_path)
    matcher = InfoBoxMatcher()

    t0 = time.time()
    count = 0
    doc = reader.next()
    while doc:
        text = doc.text
        lines = text.split('\n')
        newlines = lines[:3]

        title_line = lines[1]
        title_begin_index = title_line.find('>')
        title_end_index = title_line.find('<', title_begin_index + 1)
        title = ''
        if title_begin_index >= 0 and title_end_index >= 0:
            title = title_line[title_begin_index + 1: title_end_index].strip()
            if infobox.has_key(title):
                tagged_text = matcher.match(infobox[title], lines[3:])
                doc.text = '\n'.join(lines[:3]) + '\n'
                doc.text += tagged_text
                writer.write(doc)
        doc = reader.next()
        count += 1
        if count % 100 == 0:
            print count, time.time() - t0
    writer.close()

def do_stat(match_path):
    import Corpus
    counts = {}
    conflicts = set()
    reader = Corpus.TRECReader()
    reader.open(match_path)
    doc = reader.next()
    doc_count = 0
    t0 = time.time()
    total_count = 0
    while doc:
        for token in doc.text.split():
            pos = token.find('/')
            if pos > 0:
                tag_string = token[pos+1:]
                if tag_string.startswith('[') and tag_string.endswith(']'):
                    conflict_set = set()
                    for tag_token in tag_string[1:-1].split(','):
                        if tag_token.startswith('wiki:'):
                            conflict_set.add(tag_token)
                            total_count += 1
                            if counts.has_key(tag_token):
                                counts[tag_token] += 1
                            else:
                                counts[tag_token] = 1
                    if len(conflict_set) > 1:
                        conflicts.add(' '.join(list(conflict_set)))
        doc = reader.next()
        doc_count += 1
        if doc_count % 1000 == 0:
            print doc_count, time.time() - t0, total_count, len(counts), len(conflicts)
    count_array = map(lambda tag_count: (tag_count[1], tag_count[0]), counts.items()) 
    count_array.sort(reverse=True)
    for count, tag in count_array:
        print count, tag
    for conflict in conflicts:
        print conflict                        

def do_filter_tag(tag_count_path, lower_bound, tag_path):
    lower_bound = int(lower_bound)
    count_tags = map(lambda s: s.split(), open(tag_count_path).readlines())
    count_tags = filter(lambda count_tag: int(count_tag[0]) >= lower_bound, count_tags)
    tags = map(lambda count_tag: count_tag[1], count_tags)
    writer = open(tag_path, 'w')
    writer.write('\n'.join(tags))
    writer.close()

if __name__ == '__main__':
    import sys
    option = sys.argv[1]
    argv = sys.argv[2:]
    if option == '--match':
        do_match(*argv)
    elif option == '--stat':
        do_stat(*argv)
    elif option == '--filter-tag':
        do_filter_tag(*argv)


