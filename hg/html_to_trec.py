from bs4 import BeautifulSoup, Tag, NavigableString
import codecs

import sys
#sys.setrecursionlimit(2500)

import collections

inline_tags = set([ "tt", "i", "b", "u", "s", "strike", "big", "small", "em", "string",
                "dfn", "code", "samp", "kbd", "var", "cite", "acronym", "a", "img",
                "applet", "object", "font", "basefont", "script", "map", "q", "sub",
                "sup", "span", "bdo", "iframe", "input", "select", "textarea", "label",
                "button" ])

def extract_para(node, f):
    nodes = collections.deque(node.contents)
    #nodes = collections.deque()
    #for c in node.contents:
    #    nodes.append(c)
    while len(nodes) > 0:
        c = nodes.popleft()
        if type(c) == Tag:
            if c.name in inline_tags:
                pass
            else:
                f.write(u' . \n')
            if not (c.name == 'script' or c.name == 'style'):
                f.write(u' ')
                for cc in reversed(c.contents):
                    nodes.appendleft(cc)
        elif type(c) == NavigableString:
            f.write(c.string.replace('\n', ' '))
        else:
            f.write(u' ')
            if 'contents' in dir(c):
                for cc in c.contents:
                    nodes.append(cc)

def detag_html_file(infile, outfile, id):
    from boilerpipe.extract import Extractor
    try:
        extractor = Extractor(extractor='ArticleExtractor', url="file://"+infile)
        extracted_text = extractor.getText()
        extracted_html = extractor.getHTML()

        soup = BeautifulSoup(extracted_html)
        output = codecs.open(outfile, encoding='utf-8', mode='w')
        output.write(u"<DOC>\n<DOCNO>" + unicode(id) + u"</DOCNO>\n<DOCHDR>\n</DOCHDR>\n");
        head = soup.find('head')
        if head:
            title_tag = head.find('title')
            if title_tag and title_tag.string:
                output.write(u"<TITLE>" + title_tag.string.replace('\n', ' ') + u"</TITLE>\n")

        extract_para(soup, output)
        output.write(u"</DOC>\n")
        output.close()
    except Exception, exc:
        return detag_html_file_bs(infile, outfile, id)

    

def detag_html_file_bs(infile, outfile, id):
    try:
        soup = BeautifulSoup(open(infile))
        output = codecs.open(outfile, encoding='utf-8', mode='w')
        output.write(u"<DOC>\n<DOCNO>" + unicode(id) + u"</DOCNO>\n<DOCHDR>\n</DOCHDR>\n");
        head = soup.find('head')
        if head:
            title_tag = head.find('title')
            if title_tag and title_tag.string:
                output.write(u"<TITLE>" + title_tag.string.replace('\n', ' ') + u"</TITLE>\n")

        extract_para(soup, output)
        output.write(u"</DOC>\n")
        output.close()
    except Exception, exc:
        print exc

