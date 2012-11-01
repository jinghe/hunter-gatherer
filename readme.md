# Dependencies
* indri 
* NLTK
* Numpy

# Usage
1. make Search in cpp directory
2. run query.py to get the search result
3. assemble a task an run it through nugget_finder.py

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

# nugget_finder.py
* python hg/nugget_finder.py <ini file> <htmls file> query ...
      (requires NLTK and CCLParser server running on local host, port 8852)
* output
    1. nugget
    2. rank
    3. score
    3. evidence (one document id per line, space, score and url if given)
    4. empty line

HTMLs file format:
path to one html file, one per line. An optional URL can be added after a tab

INI file format:
key value pairs, divided by '='. Each key value pair is trimmed.
Lines starting with '#' are ignored.

Keys:
tmp_folder, folder to store temporary files, required. Using full path is advisable.
index_config_template, see provided indexing.template, defaults to that filename in the current folder
index_command, path to IndriBuildIndex, defaults to IndriBuildIndex (in the PATH)
search_command, path to Search, defaults to ./cpp/Search
main_search_passage_count, number of passages to fetch for main search, defaults to 3
evidence_search_passage_count, number of passages to fetch for main search, defaults to 10