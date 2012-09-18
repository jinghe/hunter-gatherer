import sys;
import os;

mand_fold = '../data/1C2-E.MAND';
oral_fold = '../data/1C2-E.ORCL';
html_fold = '../data/1C2-E.HTML';

def parse_filename(name):
    qID = name[:10];
    pos = name.find('.');
    res = name[10:pos];
    return qID, res;


def load_ret_res(res_fold):
    ret_res = {};
    for root, dirs, files in os.walk(fold):
        for filename in files:
            qID, res = parse_filename(filename);
            filepath = os.path.join(root, filename);
            f = open(filepath);
            htmlfiles = map(str.strip, f.readlines());
            ret_res[qID] = htmlfiles;
    return ret_res;

def do_convert_trec(out_path):
    writer = open(out_path, 'w');
    for root, dirs, files in os.walk(html_fold):
        for filename in files:
            docno = filename.split('.')[0]
            filepath = os.path.join(root, filename);
            f = open(filepath);
            writer.write('<DOC>\n<DOCNO>%s</DOCNO>\n<DOCHDR>\n</DOCHDR>\n%s\n</DOC>\n' % (docno, f.read()));
            f.close();
    writer.close();

if __name__ == '__main__':
    option = sys.argv[1];
    argv = sys.argv[2:];
    if option == '--convert-trec':
        do_convert_trec(*argv);

