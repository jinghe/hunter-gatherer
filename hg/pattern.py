import sys

from crf import server_base_tag, server_apply_tag
from data_process import TaggedText

def parse_pattern_chunks(text):
    chunk_set = set()
    host = 'localhost'
    base_tag_port = '8854'
    crf_port = '8855'
    try:
        tagged_text = server_base_tag(text, host, base_tag_port)
        tagged_text = server_apply_tag('.tmp', tagged_text, host, crf_port)
    except Exception as e:
        tagged_text = TaggedText()
    #print tagged_text
    for sentence in tagged_text:
        waiting_chunks = {}
        for term, tags in sentence:
            for tag in tags:
                if tag.startswith('wiki'):
                    if waiting_chunks.has_key(tag):
                        waiting_chunks[tag].append(term.lower())
                    else:
                        waiting_chunks[tag] = [term.lower()]
            stop_tags = set(waiting_chunks.keys()).difference(tags)
            for stop_tag in stop_tags:
                chunk_set.add('%s----%s' % (' '.join(waiting_chunks[stop_tag]), stop_tag))
    chunks = []
    for chunk_str in chunk_set:  
        term_string, tag = chunk_str.split('----')
        chunks.append((tag, term_string.split()))
    if len(chunks) > 0:
        print '-' * 100
        print 'wiki chunks'
        print '\n'.join(map(lambda chunk: '%s----%s' % (chunk[0] , ' '.join(chunk[1])),chunks ))
        print '-' * 100
    return chunks

def test_parse_pattern_chunks(text_path):
    chunks = parse_pattern_chunks(open(text_path).read())
    for type_str, tokens in chunks:
        print '%s----%s' % (type_str, ' '.join(tokens))

if __name__ == '__main__':
    option = sys.argv[1]
    argv = sys.argv[2:]
    if option == '--test':
        test_parse_pattern_chunks(*argv)

