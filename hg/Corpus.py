import os

class Document:
    def __init__(self, ID, text):
        self.ID = ID;
        self.text = text;

class TRECReader:
    def open(self, path):
        self.f = open(path);

    def next(self):
        line = self.f.readline();
        docno = 0
        text = ''
        start_doc = False
        start_text = False;
        while line:
            if line.startswith('<DOC>'):
                start_doc = True
            elif line.startswith('<DOCNO>') and start_doc:
                pos = line[7:].find('<')
                docno = line[7:7+pos].strip()
                start_text = True
            elif line.startswith('</DOC>'):
                return Document(docno, text)
            elif start_doc and start_text:
                text += line;
            line = self.f.readline();
        return 0

    def close(self):
        self.f.close();

class TRECWriter:
    def __init__(self, path):
        self.f = open(path, 'w');

    def close(self):
        self.f.close();

    def write(self, doc):
        self.f.write('<DOC>\n<DOCNO>%s</DOCNO>\n%s\n</DOC>\n' % (doc.ID, doc.text));

class PabloWikiReader:
    def __init__(self, path):
        self.f = open(path);
        self.ID = 1;

    def hasMore(self):
        line = self.f.readline();
        while line:
            doc_text = self.parseLine(line);
            if doc_text:
#print doc_text;
#sys.exit(-1);
                self.doc_text = doc_text;
                return True;
            line = self.f.readline();
        return False;

    def next(self):
        doc = Document(self.ID, self.doc_text);
        self.ID += 1;
        return doc;

    def parseLine(self, line):
        tokens = line.split('\t');
        doc_text = '';
        query = 0;
        if(len(tokens) >= 3):
            number, title, summary = tokens[-3:];
            title = title.strip();
            summary = summary.strip();
            if len(tokens) >= 4:
                query = tokens[-4];
                query = query.strip();
            if query:
                doc_text += '<QUERY>%s</QUERY>\n' % query;
            if title and summary:
                doc_text += '<TITLE>%s</TITLE>\n<SUMMARY>\n%s\n</SUMMARY>\n' % (title, summary);
        return doc_text;

    

def is_cluewebB(docno):
    if not docno.startswith('clueweb09'):
        return False;
    corpus_name, subcorpus_name, setno, docno = docno.split('-');
    pos = subcorpus_name.find('0');
    if pos < 0:
        return False;
    name = subcorpus_name[:pos];
    no = int(subcorpus_name[pos+1:]);
    if name == 'en' and no >= 0 and no <= 11:
        return True;
    elif name == 'enwp' and no >= 0 and no <= 3:
        return True;
    return False;

def filter_cluewebB_qrel(qrel_path, new_qrel_path):
    from QRelFile import QRelFile;
    qrel_file = QRelFile(qrel_path);
    docnos = qrel_file.key2s();
    print 'total docno:', len(docnos);
    docnos = set(filter(is_cluewebB, docnos));
    print 'valid docno:', len(docnos);
    qrel_file.filter_key2s(docnos);
    qrel_file.store(new_qrel_path);

def convert(pablo_input, trec_output):
    reader = PabloWikiReader (pablo_input);
    writer =TRECWriter (trec_output);
    c = 0;
    while reader.hasMore():
        doc = reader.next();
        writer.write(doc);
        c += 1;
        if c % 100000 == 0:
            print c;
    writer.close();

if __name__ == '__main__':
    import sys;
    option = sys.argv[1]
    argv = sys.argv[2:]
    if option == '--test-read':
        dir_name = argv[0]
        filepaths = []
        if not os.path.isdir(dir_name):
            filepaths.append(dir_name);
        else:
            for root, dirnames, filenames in os.walk(dir_name):
                for filename in filenames:
                    filepath = '%s/%s' % (root, filename)
                    filepaths.append(filepath)
            filepaths.sort()
        reader = TRECReader()
        for filepath in filepaths:
            print filepath
            reader.open(filepath)
            count = 0;
            doc = reader.next()
            while doc:
                #print len(doc.text),
                count += 1
                doc = reader.next()
            print count
    


























