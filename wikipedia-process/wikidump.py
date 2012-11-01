import xml.sax

class WikiPageHandler(xml.sax.ContentHandler):
    def __init__(self, func):
        self.func = func 
        self.stack = []
        self.text = None
        self.title = None

    def startElement(self, name, attributes):
        #~ print "start", name
        if name == "page":
            assert self.stack == []
            self.text = None
            self.title = None
        elif name == "title":
            assert self.stack == ["page"]
            assert self.title is None
            self.title = ""
        elif name == "text":
            assert self.stack == ["page"]
            assert self.text is None
            self.text = ""
        else:
            assert len(self.stack) == 0 or self.stack[-1] == "page"
            return

        self.stack.append(name)

    def endElement(self, name):
        #~ print "end", name
        if len(self.stack) > 0 and name == self.stack[-1]:
            del self.stack[-1]
        if name == "text":
            # We have the complete article: write it out
            self.func(self.title, self.text)

    def characters(self, content):
        assert content is not None and len(content) > 0
        if len(self.stack) == 0:
            return

        if self.stack[-1] == "title":
            self.title += content
        elif self.stack[-1] == "text":
            assert self.title is not None
            self.text += content


class WikiFilter:
    def __init__(self, names, out_path):
        import Corpus
        self.name_set = set(names)
        self.writer = Corpus.TRECWriter(out_path)
        self.id = 1
        self.count = 0

    def process(self, title, text):
        import Corpus
        self.count += 1
        title = title.replace(' ', '_').encode('utf8')
        text = text.encode('utf8')
        if self.name_set.__contains__(title):
            self.writer.write(Corpus.Document(str(self.id), '<title>%s</title>\n%s' % (title, text)))
            print self.count, self.id, title
            self.id += 1



def do_filter_article(article_path, dump_path, out_path):
    names = map(lambda line:line.strip().split()[0].split('/')[-1], open(article_path).readlines())
    wiki_filter = WikiFilter(names, out_path)
    func = wiki_filter.process
    xml.sax.parse(dump_path, WikiPageHandler(func))

class DBPediaFilter:
    def __init__(self, names, out_path):
        self.name_set = set(names)
        self.writer = open(out_path, 'w')
        self.count = 0

    def process(self, s,p,o):
        if self.name_set.__contains__(s.split('/')[-1]):
            self.writer.write(('%s----%s----%s\n' % (s,p,o)).encode('utf8'))
            self.count += 1
            if self.count % 1000 == 0:
                print self.count


def do_filter_dbpedia(url_path, dbpedia_path, out_path):
    import MyTriple
    names = map(lambda line:line.strip().split()[0].split('/')[-1], open(url_path).readlines())
    dbpedia_filter = DBPediaFilter(names, out_path)
    filter_np = MyTriple.NTriplesParser(sink=MyTriple.FuncSink(lambda s,p,o: dbpedia_filter.process(s,p,o)))
    sink = filter_np.parse(open(dbpedia_path)) 

if __name__ == '__main__':
    import sys
    option = sys.argv[1]
    argv = sys.argv[2:]
    if option == '--filter-article':
        do_filter_article(*argv)
    elif option == '--filter-dbpedia':
        do_filter_dbpedia(*argv)
    

