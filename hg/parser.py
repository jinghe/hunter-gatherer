import socket
import nltk
from nltk.tree import Tree
import re
import sys

# from https://gist.github.com/240957

from string import whitespace

atom_end = set('()"\'') | set(whitespace)

def parse_sexpr(sexp):
    stack, i, length = [[]], 0, len(sexp)
    while i < length:
        c = sexp[i]

        #print c, stack
        reading = type(stack[-1])
        if reading == list:
            if c == '(': stack.append([])
            elif c == ')':
                stack[-2].append(stack.pop())
                if stack[-1][0] == ('quote',): stack[-2].append(stack.pop())
            #elif c == '"': stack.append('')
            #elif c == "'": stack.append([('quote',)])
            elif c in whitespace: pass
            else: stack.append((c,))
        elif reading == str:
            if c == '"':
                stack[-2].append(stack.pop())
                if stack[-1][0] == ('quote',): stack[-2].append(stack.pop())
            elif c == '\\':
                i += 1
                stack[-1] += sexp[i]
            else: stack[-1] += c
        elif reading == tuple:
            if c in atom_end:
                atom = stack.pop()
#                if atom[0][0].isdigit(): stack[-1].append(eval(atom[0]))
#                else: 
                stack[-1].append(atom)
                if stack[-1][0] == ('quote',): stack[-2].append(stack.pop())
                continue
            else: stack[-1] = ((stack[-1][0] + c),)
        i += 1
    return stack.pop()

def sexpr_to_brackets(sexpr):
    brackets = []
    current = []
    for l in sexpr:
        if type(l) == list:
            if len(current)>0:
                brackets.append(current)
                current = []
            brackets.extend(sexpr_to_brackets(l))
        elif type(l) == tuple:
            current.append(l[0])
    if len(current)>0:
        brackets.append(current)
    return brackets


def cclparse(to_parse):
    HOST = 'localhost'
    PORT = 8852
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((HOST, PORT))
    s.sendall(to_parse)
    s.shutdown(socket.SHUT_WR)
    result = ""
    while True:
        data = s.recv(1024)
        if not data: break
        result = result + data
    s.close()
    return result

def ne(tok_text):
    #sentences = nltk.sent_tokenize(text)
    #sentences = [nltk.word_tokenize(sent) for sent in sentences]
    #sentences = [nltk.pos_tag(sent) for sent in sentences]
    #result = [ nltk.ne_chunk(sent, binary=True) for sent in sentences]
    return nltk.ne_chunk(nltk.pos_tag(tok_text), binary=True)

def flatten(list):
    return [item for sublist in list for item in sublist]

def mix_brackets(brackets, ne):
    """Surgeon general's warning: reading this code will hurt your brain."""
    
    # align tokens
    def type_brackets(br):
        return map(lambda x:(None, x), br)

    def ne_to_typed_brackets(node):
        if type(node) == list:
            return flatten(map(ne_to_typed_brackets,node))
        elif type(node) == Tree:
            if node.node == 'NE':
                return [('NE', flatten(map(ne_to_typed_brackets,node)))]
            else: # 'S', etc
                rec = map(ne_to_typed_brackets, node)
                return flatten(rec)
        elif type(node) == tuple:
            return [ node[0] ]

    def number_tokens(l):
        def nt(l,n):
            if type(l) == str:
                return ( (l, n), n+1 )
            elif type(l) == tuple:
                (r, nn) = nt(l[1], n)
                return ( (l[0], r), nn )
            elif type(l) == list:
                r = list()
                for o in l:
                    (rec, nn) = nt(o, n)
                    n = nn
                    r.append(rec)
                return ( r, nn )
            else:
                raise Error("Unknown type: " + type(l))
        return nt(l,0)[0]

    def remove_numbering(nt):
        if type(nt) == list:
            return map(remove_numbering, nt)
        elif type(nt) == tuple:
            if type(nt[1]) == list:
                return (nt[0], map(remove_numbering, nt[1]))
            else:
                return nt[0]
            
    def extract_tokens(nt):
        if type(nt) == tuple:
            if type(nt[1]) == list:
                return extract_tokens(nt[1])
            else:
                return [ nt ]
        elif type(nt) == list:
            return flatten(map(extract_tokens,nt))
        else:
            raise Error("Unknown type: "+type(nt))

    def align(br,ne):
        b_to_n=[None for t in br]
        n_to_b=[None for t in ne]
        b_idx=0
        n_idx=0
        while b_idx<len(br) and n_idx<len(ne):
            if br[b_idx][0].lower() == ne[n_idx][0].lower():
                b_to_n[b_idx]=n_idx
                n_to_b[n_idx]=b_idx
                n_idx += 1
                b_idx += 1
            else:
                found=False
                s_n_idx = n_idx + 1
                while s_n_idx < len(ne):
                    if ne[s_n_idx][0].lower() == br[b_idx][0].lower():
                        found=True
                        break
                    s_n_idx += 1
                if found:
                    n_idx = s_n_idx
                    b_to_n[b_idx]=n_idx
                    n_to_b[n_idx]=b_idx
                    n_idx += 1
                    b_idx += 1
                else:
                    s_b_idx = b_idx + 1
                    while s_b_idx < len(br):
                        if ne[n_idx][0].lower() == br[s_b_idx][0].lower():
                            found=True
                            break
                        s_b_idx += 1
                    if found:
                        b_idx = s_b_idx
                        b_to_n[b_idx]=n_idx
                        n_to_b[n_idx]=b_idx
                    n_idx += 1
                    b_idx += 1
        return (b_to_n, n_to_b)

    nbr=number_tokens(type_brackets(brackets))
    nne=number_tokens(ne_to_typed_brackets(ne))

    (b_to_n, n_to_b) = align(extract_tokens(nbr), extract_tokens(nne))

    # go through the brackets, merging in the ne
    #print nbr
    #print nne

    for t in filter(lambda x:type(x[1]) == list and x[0] == 'NE', nne):
        start = t[1][0][1]
        end = t[1][-1][1]
        s_start = start
        b_start = n_to_b[s_start]
        while b_start is None and s_start < end:
            s_start += 1
            b_start = n_to_b[s_start]

        if b_start is None:
            continue # warning?
            
        s_end = end
        b_end = n_to_b[s_end]
        while b_end is None and s_end > start:
            s_end -= 1
            b_end = n_to_b[s_end]

        # repair nbr
        good=[ chunk for chunk in nbr if chunk[1][-1][1] < b_start ]
        problem=[ chunk for chunk in nbr if (chunk[1][0][1] <= b_start and b_start <= chunk[1][-1][1]) or
                  (b_start < chunk[1][0][1] and chunk[1][-1][1] < b_end) or
                  (chunk[1][0][1] <= b_end and b_end <= chunk[1][-1][1]) ]

        # fix
        fix = []
        if len(problem) == 1:
            chunk = problem[0]
            beginning = [ tok for tok in chunk[1] if tok[1] < b_start ]
            if len(beginning) > 0:
                fix.append( (None, beginning) )
            new_ne = [ tok for tok in chunk[1] if tok[1] >= b_start and tok[1] <= b_end ]
            fix.append( ('NE', new_ne) )
            ending = [ tok for tok in chunk[1] if tok[1] > b_end ]
            if len(ending) > 0:
                fix.append( (None, ending) )
        else:
            chunk = problem[0]
            beginning = [ tok for tok in chunk[1] if tok[1] < b_start ]
            if len(beginning) > 0:
                fix.append( (None, beginning) )
            new_ne = [ tok for tok in chunk[1] if tok[1] >= b_start and tok[1] <= b_end ]
            for chunk in problem[1:-1]:
                new_ne = new_ne + chunk[1]
            chunk = problem[-1]
            new_ne = new_ne + [ tok for tok in chunk[1] if tok[1] >= b_start and tok[1] <= b_end ]
            fix.append( ('NE', new_ne) )
            ending = [ tok for tok in chunk[1] if tok[1] > b_end ]
            if len(ending) > 0:
                fix.append( (None, ending) )

        nbr = good + fix + [ chunk for chunk in nbr if b_end < chunk[1][0][1] ]
        
    return remove_numbering(nbr)      
    
def parse_into_chunks(text):
    tok = nltk.word_tokenize(text)
    brackets = sexpr_to_brackets(parse_sexpr(cclparse(" ".join(tok))))
    named_entities = ne(tok)

    return map(lambda x: x if(len(x[1])==1 or x[0] is not None) else ('Non-NE', x[1]),
               mix_brackets(brackets, named_entities))

if __name__ == '__main__':
    for line in sys.stdin:
        sentences = nltk.sent_tokenize(line)
        for sent in sentences:
            tok = nltk.word_tokenize(sent)
            brackets = sexpr_to_brackets(parse_sexpr(cclparse(" ".join(tok))))
            named_entities = ne(tok)

            print "brackets", brackets
            print "ne", named_entities,"\n"

            print mix_brackets(brackets, named_entities)
