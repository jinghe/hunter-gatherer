import os
import sys
import robotparser
import socket
import codecs
import urllib2
import urlparse
import httplib
import ssl
import sqlite3

HUNTER_GATHERER_USER_AGENT = "Hunter-Gatherer/0.1"

robotparser.URLopener.version = HUNTER_GATHERER_USER_AGENT

url_opener = urllib2.build_opener()
url_opener.addheaders = [('User-agent', HUNTER_GATHERER_USER_AGENT)]


urls_to_robotparser = dict() # url string for base site to robot parser instance

DB_SQL_INIT = '''
        CREATE TABLE query (
          id integer not null,
          query text not null,
          search_engine text not null,
          constraint pk_query primary key (id)
        );
        CREATE TABLE page (
          id integer not null,
          url text not null,
          file_name text null,
          constraint pk_page primary key (id)
        );
        CREATE TABLE query_page (
          id integer not null,
          query integer not null,
          page integer not null,
          ranked integer not null, --rank is reserved word
          constraint pk_query_page primary key (id),
          foreign key (query) references query (id),
          foreign key (page) references page (id) 
        );
        CREATE UNIQUE INDEX idx_query_se ON query (query, search_engine);
        CREATE INDEX idx_query ON query (query);
        CREATE UNIQUE INDEX idx_page_url ON page (url);
        CREATE INDEX idx_page_file ON page (file_name);
        CREATE UNIQUE INDEX idx_query_page ON query_page (query, page);
        CREATE INDEX idx_query_page_page ON query_page (page);
        CREATE INDEX idx_query_page_query ON query_page (query);
        CREATE INDEX idx_query_page_rank ON query_page (query, ranked);
        '''

def search_bing(query, count):
    # return list of urls
    pass

def fetch_page(url):
    # return the text of the page or None

    base_url = urlparse.urljoin(url, '/')
    # track robots.txt
    rp = urls_to_robotparser.get(base_url)
    if rp is None:
        print 'fetching robots for ', urlparse.urljoin(url, '/')
        rp = robotparser.RobotFileParser()
        rp.set_url(urlparse.urljoin(url, "/robots.txt"))
        try:
            rp.read()
        except object as exc:
            print "exception fetching robots", exc
            return None
        except IOError as exc:
            print "exception fetching robots", exc
            return None
        except:
            print "exception fetching robots (other)"
            return None
            
        urls_to_robotparser[base_url] = rp
    if not rp.can_fetch("*", url):
        print "robots.txt forbids ", url
        return None
    try:
        print "fetching ", url
        page = url_opener.open(url, None, 2) # timeout is in seconds
        bytes = page.read()
        page.close()
        print "success"
        return bytes
    except object as exc:
        print "exception fetching page", exc
        return None
    except urllib2.HTTPError as exc:
        print "exception fetching page", exc
        return None
    except httplib.IncompleteRead as exc:
        print "exception fetching page", exc
        return None

def open_db(cache_folder):
    cache_db = "%s/db.sqlite3" % (cache_folder,)
    exists = os.path.exists(cache_db)
    conn = sqlite3.connect(cache_db) # will create if it doesn't
    cursor = conn.cursor()
    if not exists:
        cursor.executescript(DB_SQL_INIT)
    return (conn, cursor)

def find_query(cursor, query, search_engine):
    row = cursor.execute('''SELECT id FROM query WHERE query = ? AND search_engine = ?''',
                         (query, search_engine)).fetchone()
    return None if row is None else row[0]

def add_query(cursor, query, search_engine):
    cursor.execute('''INSERT INTO query (id, query, search_engine) VALUES (?,?,?)''',
                   (None, query, search_engine))
    return cursor.lastrowid

def ensure_page_query_link(cursor, cache_files_folder, qid,  rank, url):
    """Fetch a page if necessary and record query / url link"""

    def write_to_disk(base_folder, num, bytes):
        num_str = str(num)
        if len(num_str) < 2:
            num_str = "0%s" % (num_str,)
        chars = list(num_str)
        chars.reverse()
        file_name = "%s/%s/%d" % (chars[0], chars[1], num)
        first = "%s/%s" % (base_folder, chars[0])
        second = "%s/%s" % (first, chars[1])
        def mkdirs(folder):
            if not os.path.exists(folder):
                os.mkdir(folder)
        mkdirs(first)
        mkdirs(second)
        output = open("%s/%s" % (base_folder, file_name), 'w')
        output.write(bytes)
        output.close()
        return file_name

    # in index?
    rid = cursor.execute('''SELECT id FROM page WHERE url = ?''',  (url,)).fetchone()
    if rid is None:
        print 'not in index', url
        file_name = None
        try:
            html_bytes = fetch_page(url)
            if not html_bytes is None:
                # write to disk
                file_number = cursor.execute('''SELECT id FROM page ORDER BY ID DESC LIMIT 1''').fetchone()
                file_number = 0 if file_number is None else file_number[0]
                file_name = write_to_disk(cache_files_folder, file_number, html_bytes)
                print 'fetched'
            else:
                print 'not fetched'
        except object as exc:
            print "error fetching page", url, exc
        except socket.timeout as exc:
            print "time out fetching page", url, exc
        except ssl.SSLError as exc:
            print "SSL error fetching page", url, exc
        except urllib2.URLError as exc:
            print "error fetching page", url, exc
            
        cursor.execute('''INSERT INTO page (id, url, file_name) VALUES (?,?,?)''', (None, url, file_name))
        rid = cursor.lastrowid
    else:
        print 'in index', url
        rid = rid[0]

    cursor.execute('''INSERT INTO query_page (id, query, page, ranked) VALUES (?,?,?,?)''', (None, qid, rid, rank))
    

def web_search(query_str, cache_folder='/tmp/cache', search_engine='Bing', search_count=200):

    cache_files_folder = "%s/pages" % (cache_folder)
    try:
        os.mkdir(cache_files_folder)
    except:
        pass

    # open search index
    (conn, cursor) = open_db(cache_folder)

    # query not in index? do search
    def search(query, search_engine):
        if search_engine == 'Bing':
            urls = search_bing(query, search_count)
        else:
            sys.exit("Unknown search engine: %s" % (search_engine,))

        qid = add_query(cursor, query, search_engine)
        
        # fetch pages
        rank = 0
        for url in urls:
            ensure_page_query_link(cursor, qid,  rank, url)
            rank += 1

    qid = find_query(cursor, query_str, search_engine)
    if qid is None:
        qid = search(query_str, search_engine)

    cursor.execute('''SELECT file_name, url FROM page
       INNER JOIN query_page ON page.id = query_page.page
       WHERE query_page.query = ?
       ORDER BY query_page.ranked''', (qid,))
    file_urls = filter(lambda x: x[0] is not None, map(lambda r:(r[0], r[1]), cursor))
    if len(file_urls) > search_count:
        file_urls = file_urls[0:search_count]

    conn.close()

    return (map(lambda p: "%s/%s" % (cache_files_folder, p[0]), file_urls),
            map(lambda p: p[1], file_urls))
