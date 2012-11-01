from ntriples import *
import sys

class Triple:
    """
     A simplistic representation of a triple
    """
    def __init__(self, s, p, o):
        self._s = s
        self._p = p
        self._o = o
    def __repr__(self): return '%s, %s, %s' % (self._s, self._p, self._o)
    def subject(self): return self._s
    def predicate(self): return self._p
    def object(self): return self._o

class MySink:
    """
     This class stores the triples as they are parsed from the file
    """
    def __init__(self):
        self._triples = []

    def triple(self, s, p, o):
        self._triples.append( Triple(s,p,o) )
       
    def __len__(self): return len(self._triples)

    def getTriples(self): return self._triples

class IndexSink(dict):
    def __init__(self, is_direct_index):
        self._size = 0
        self._is_direct_index = is_direct_index

    def triple(self, s, p, o):
        if self._is_direct_index: key = s
        else: key = o
        if not self.has_key(key):
            self[key] = []
        self[key].append(Triple(s,p,o))
        self._size += 1

    def __len__(self): return self._size

class FuncSink:
    def __init__(self, func):
        self._size = 0
        self._func = func

    def triple(self, s, p, o):
        self._func(s,p,o)

    def __len__(self): return self._size


