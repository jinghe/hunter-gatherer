'''
An Interface for IndriIndex
'''

import os;
import sys;
import tempfile
import subprocess

class RawDataParser:
    def parse(self, lines):
        data = {};
        curr_area = ''; curr_key = '';
        for line in lines:
            line = line.strip();
            area = self._is_area_begin(line);
            if area:
                curr_area = area;
                continue;
            if curr_area == 'Metadata':
                key, value = self._parse_key_value(line);
                if key:
                    curr_key = key;
                existing_value = data.get(curr_key, None); 
                if existing_value:
                    value = existing_value + '\n' + value;
                data.set(key, value);
        return data;

    def _parse_key_value(self, line):
        key = '';
        pos = line.find(':');
        if pos < 0:
            value = line;
        if pos >= 0:
            key = line[:pos];
            value = line[pos+2:];
        return key,value;

    def _is_area_begin(self, line):
        if line.startswith('---'):
            area = line.replace('---', '').strip();
            return area;
        return 0;

class NotInIndexException(Exception):
    def __init__(self, msg):
        self.msg = msg;

class Index:
    def __init__(self, index_path):
        self.path = index_path;
        self.raw_data_parser = RawDataParser();

    def get_doc_content(self, docno):
        inner_id = self.get_doc_inner_id(docno);
        cmd = 'dumpindex %s dt %d' % (self.path, inner_id);
        print cmd;
        f = os.popen(cmd);
        lines = f.readlines();
        f.close();
        content = ''.join(lines);
        return content;

    def get_parsed_data(self, docno):
        inner_id = self.get_inner_id(docno);
        data = self._get_raw_data(inner_id);
        parsed_data = self.raw_data_parser.parse(data);
        return parsed_data;

    def get_URL(self, docno):
        parsed_data = self.get_parsed_data(docno);
        return parsed_data.get('url');

    def get_doc_inner_id(self, docno):
        return self.find_field('docno', docno);

    def find_field(self, field_name, field_val):
        cmd = 'dumpindex %s di %s "%s"' % (self.path, field_name, field_val);
        print cmd;
        sys.stdout.flush();
        f = os.popen(cmd);
        line = f.readline();
        f.close();
        if not line:
            return 0;
        else:
            return int(line.strip());

    def get_docno(self, inner_doc_id):
        cmd = 'dumpindex %s dn %d' % (self.path, inner_doc_id);
        print cmd;
        f = os.popen(cmd);
        line = f.readline();
        if not line:
            return '';
        else:
            line.strip();
            return line;

        
    def get_term(self, term_id):
        cmd = './IndexApp --term %s %d' % (self.path, term_id);
        print cmd;
        f = os.popen(cmd);
        term = f.readline().strip();
        return term;

    def get_term_id(self, term):
        cmd = './IndexApp --term-id %s %s' % (self.path, term);
        print cmd;
        try:
            f = os.popen(cmd);
            term_id = int(f.readline().strip());
        except Exception as e:
            print 'cannot exe term' + term;
            sys.exit(-1);
        return term_id;

    def is_index_term(self, term):
        term_id = self.get_term_id(term);
        if term_id <= 0:
            return False;
        return True;

    def _get_raw_data(self, docid):
        cmd = 'dumpindex %s dd %d' % (self.path, docid);
        f = os.popen(cmd);
        lines = f.readlines();
        f.close();
        return lines;

    def index_stats(self):
        cmd = 'dumpindex %s stats' % (self.path);
        f = os.popen(cmd);
        lines = f.readlines();
        f.close();
        df, tf, cf = map(lambda line:int(line.strip().split('\t')[-1]), lines[1:4]);
        return df, tf, cf;

    def df(self):
        return self.index_stats()[0];

    def cf(self):
        return self.index_stats()[2];

    def term_df(self, term_id):
        cmd = './IndexApp --term-df %s %d' % (self.path, term_id);
        print cmd;
        f = os.popen(cmd);
        lines = f.readlines();
        f.close();
        return int(lines[0].strip());

    def term_cf(self, term_id):
        cmd = './IndexApp --term-cf %s %d' % (self.path, term_id);
        print cmd;
        f = os.popen(cmd);
        lines = f.readlines();
        f.close();
        return int(lines[0].strip());

    def count(self, indri_query):
        cmd = 'dumpindex %s xcount "%s"' % (self.path, indri_query);
        print cmd;
        f = os.popen(cmd);
        line = f.readline().strip();
        pos = line.find(':');
        return float(line[pos+1:]);

    def match(self, indri_query):
        cmd = 'dumpindex %s e "%s"' % (self.path, indri_query);
        print cmd;
        f = os.popen(cmd);
        lines = f.readlines();
        match_records = [];
        for line in lines[1:]:
            doc_id, tf, start_pos, end_pos = map(int, line.split());
            match_records.append((doc_id, tf, start_pos, end_pos));
        return match_records;

    def doc_terms(self, doc_id):
        doc_id = int(doc_id);
        cmd = 'dumpindex %s dv "%d"' % (self.path, doc_id);
        print cmd;
        f = os.popen(cmd);
        lines = f.readlines();
        field_positions = {};
        term_lineno = 0;
        for i in xrange(1,len(lines)):
            line = lines[i].strip();
            if line.startswith('--- Terms'):
                term_lineno = i + 1;        
                break;
            tokens = line.split();
            field_name = tokens[0];
            start_pos, end_pos, field_id = map(int, tokens[1:]);
            field_positions[field_name] = (start_pos, end_pos);
        doc = Document();
        for field_name in field_positions.keys():
            start_pos, end_pos = field_positions[field_name];
            tokens = [];
            for pos in xrange(start_pos, end_pos):
                tokens.append(lines[term_lineno + pos].split()[-1]);
            doc.add_field(field_name, tokens);
        if len(field_positions.keys()) == 0:
            tokens = [];
            for pos in xrange(term_lineno, len(lines)):
                tokens.append(lines[pos].split()[-1]);
            doc.add_text(tokens);
        return doc;
            


class Document:
    def __init__(self):
        self.data = {};
    def add_field(self, field_name, tokens):
        self.data[field_name] = tokens;
    def add_text(self, tokens):
        self.data[''] = tokens;
    def __str__(self):
        text = '';
        for field_name, tokens in self.data.items():
            if field_name:
                text += '%s:%s\n' % (field_name, ' '.join(tokens));
            else:
                text += ' '.join(tokens) + '\n';
        return text;

class FieldData(Index):
    def __init__(self, path, index_path):
        self.path = index_path;
        f = open(path);
        self.direct_data = {};
        self.invert_data = {};
        while True:
            line = f.readline();
            if not line:
                break;
            pos = line.find(' ');
            doc_id = int(line[:pos]);
            passages = line.split('|');
            doc = [];
            for passage in map(str.strip, passages):
                if not passage:
                    continue;
                term_ids = map(int, passage.split(' '));
                doc.append(term_ids);
            self._update_direct_data(doc_id, doc);
            self._update_invert_data(doc_id, doc);
            reporter.report();
        reporter.end();

    def term_df(self, term_id):
        return self.invert_data.get(term_id, (0,0))[0];

    def term_cf(self, term_id):
        return self.invert_data.get(term_id, (0,0))[1];

    def _update_invert_data(self, doc_id, doc):
        local_term_count = {};
        for term_ids in doc:
            for term_id in term_ids:
                local_term_count[term_id] = local_term_count.get(term_id,0) + 1;
        for term_id, count in local_term_count.items():
            df, cf = self.invert_data.get(term_id, (0,0));
            self.invert_data[term_id] = (df+1, cf+count);

    def _update_direct_data(self, doc_id, doc):
        pass;



def retrieve(query_string, index_path):
    param_file = tempfile.NamedTemporaryFile()
    param_file.write('<parameters><index>%s</index><retModel>kl</retModel><rule>method:dirichlet,mu:1000</rule><trecFormat>true</trecFormat><query><number>1</number><text>%s</text></query><count>200</count></parameters>' % (index_path, '#combine(%s)' % query_string))
    param_file.flush()
    command = ['IndriRunQuery', param_file.name];
    print ' '.join(command)
    p = subprocess.Popen(command, stderr = subprocess.PIPE, stdout = subprocess.PIPE)
    lines = p.stdout.readlines()
    docnos = map(lambda line: line.strip().split()[2], lines)
    param_file.close()
    return docnos
                
def test_index():
    #index = Index('~/data/dbpedia/disambiguation.index/');
    #doc = index.doc('1');
    #print doc;
    index = Index('~/data/dbpedia/title.index/');
    records = index.match('#1(horse hoove)');
    for doc_id, tf, start_pos, end_pos in records:
        print doc_id, tf, start_pos, end_pos;
        if start_pos == 0:
            doc = index.doc(doc_id);
            print doc;


if __name__ == '__main__':
    test_index();



