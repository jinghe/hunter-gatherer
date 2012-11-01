import sys
import os

import web_search

if __name__ == '__main__':
    cache_folder = sys.argv[1]
    search_engine = sys.argv[2]
    html_file = sys.argv[3]
    query_str = " ".join(sys.argv[4:])

    print "cache folder", cache_folder
    print "search engine", search_engine
    print "urls", html_file
    print "query", query_str

    (conn, cursor) = web_search.open_db(cache_folder)

    if web_search.find_query(cursor, query_str, search_engine) is not None:
        sys.exit("Query already in index")

    cache_files_folder = "%s/pages" % (cache_folder,)
    print "page cache folder", cache_files_folder
    try:
        os.mkdir(cache_files_folder)
        print "creating page cache folder", cache_files_folder
    except object as exc:
        print "(warning) problem creating", cache_files_folder, exc
    except OSError:
        pass    

    qid = web_search.add_query(cursor, query_str, search_engine)

    rank = 0
    found = set()
    for url in file(html_file):
        url = url.replace('\n', '')
        if url in found:
            continue
        found.add(url)
        web_search.ensure_page_query_link(cursor, cache_files_folder, qid,  rank, url)
        conn.commit()
        rank += 1    

    conn.close()
