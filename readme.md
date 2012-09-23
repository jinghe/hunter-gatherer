# Dependencies
* indri 
* NLTK
* Numpy

# Usage
1. make Search in cpp directory
2. run query.py to get the search result;

# query.py
* command
    * python hg/query.py --search-from-parsed-query index-path search-exe-file query-str passage-length passage-step result-num
    * python hg/query.py --search index-path search-exe-file query-str passage-length passage-step result-num
      (requires NLTK and CCLParser server running on local host, port 8852)
* output
    1. index info
    2. query info
    3. docno score rank
    4. passage-content
    5. term/phrase character positions;
