import os
import sys
import re
from shutil import copyfile


import web_search
from one_click_search import one_click_search
from nugget_finder import load_ini

def load_queries(query_file):
    queries = []

    for line in file(query_file):
        parts = line.strip().split('\t')
        if len(parts) == 3:
            queries.append({'id' : parts[0], 'query': parts[2] })
        elif len(parts) == 2:
            queries.append({'id' : parts[0], 'query': parts[1] })
        else:
            sys.exit("Bad number of tabs in query file, line '%s'" % (line,))

    return queries

def register_query_pages(query_id, query_str, cursor, ntcir_urls_folder, ntcir_htmls_folder, cache_folder):
    cache_files_folder = "%s/pages" % (cache_folder,)

    qid = web_search.add_query(cursor, query_str, 'NTCIR')
    rank = 0

    for file_name in file("%s/%s.MAND.tsv" % (ntcir_urls_folder, query_id,)):
        full_name = "%s/%s" % (ntcir_htmls_folder, file_name.strip())
        url = "file://%s" % (full_name,)
        rid = web_search.copy_existing_page(cursor, cache_files_folder, full_name, url)
        web_search.ensure_page_query_link(cursor, cache_files_folder, qid, rank, url)
        rank += 1

if __name__ == '__main__':
    ####
    # input: ini file and queries file
    #
    ini_file = sys.argv[1]
    query_file = sys.argv[2]
    run_number = int(sys.argv[3])

    ini = load_ini(ini_file)
    queries = load_queries(query_file)

    ini['search_engine'] = 'NTCIR'

    # these entries must be defined in the ini file
    system_description = ini['ntcir_system_description'] 
    team_name = ini['ntcir_team_name']
    ntcir_urls_folder = ini['ntcir_urls_folder']
    ntcir_htmls_folder = ini['ntcir_htmls_folder']

    base_tmp = ini.get('tmp_folder', './tmp')

    cache_folder = ini.get('cache_folder',  "%s/cache" % (base_tmp,))
    (conn, cursor) = web_search.open_db(cache_folder)

    output_file_desktop = "%s-E-D-MAND-%d.tsv" % (team_name, run_number)
    output_file_mobile = "%s-E-M-MAND-%d.tsv" % (team_name, (run_number+1))
    output_desktop = file(output_file_desktop, 'w')
    output_mobile = file(output_file_mobile, 'w')

    output_desktop.write('SYSDESC\t%s -- desktop\n' % (system_description,))
    output_mobile.write('SYSDESC\t%s -- mobile\n' % (system_description,))

    output_desktop.close()
    output_mobile.close()

    import time
    t0 = time.time()
    for query in queries:
        print query, time.time() - t0
        query_id = query['id']
        query_str = query['query']

        tmp = "%s/%s" % (base_tmp, query_id)
        os.mkdir(tmp)
        ini['tmp_folder'] = tmp

        if web_search.find_query(cursor, query_str, 'NTCIR') is None:
            register_query_pages(query_id, query_str, cursor, ntcir_urls_folder, ntcir_htmls_folder, cache_folder)
            conn.commit()

        (results, html_urls) = one_click_search(ini, query_str, [(1000, 'DESKTOP'), (280, 'MOBILE')])
        for (output_file, result) in [(output_file_desktop, results['DESKTOP']), (output_file_mobile, results['MOBILE'])]:
            output = file(output_file, 'a')
            output.write('%s\tOUT\t%s\n' % (query_id, re.sub('\n', ' ', result[0])))
            printed = set()
            for evidence in result[1]:
                #TODO evidence id to page
                if not evidence in printed:
                    url = html_urls[int(evidence)]
                    url = re.sub('.*/', '', url)
                    output.write('%s\tSOURCE\t%s\n' % (query_id, url))
                    printed.add(evidence)

            output.close()
