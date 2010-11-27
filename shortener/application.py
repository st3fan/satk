#!/usr/bin/python

#
# sqlite /var/local/shortener.db
# CREATE TABLE links (code integer primary key autoincrement, url);
#
# Apache Configuration:
#
# WSGIDaemonProcess shortener user=www-data group=www-data processes=1 threads=5
# WSGIScriptAlias /shortener /home/stefan/bottle/shortener/application.py
#
# <Directory /home/stefan/bottle/shortener/application.py>
#     WSGIProcessGroup shortener
#     WSGIApplicationGroup %{GLOBAL}
#     Order deny,allow
#     Allow from all
# </Directory>
#
# RewriteRule ^/([0-9]+)$ /shortener/redirect/$1 [R]
#

import os
import site
site.addsitedir(os.path.dirname(__file__))


import bottle
import sqlite3
import hashlib


def lookup_by_url(url):
    result = None
    conn = sqlite3.connect('/var/local/shortener.db')
    cursor = conn.cursor()
    cursor.execute('select code from links where url = ?', (url,))
    row = cursor.fetchone()
    if row:
        result = { 'code': row[0], 'url': url }
    conn.close()
    return result

def lookup_by_code(code):
    result = None
    conn = sqlite3.connect('/var/local/shortener.db')
    cursor = conn.cursor()
    cursor.execute('select url from links where code = ?', (code,))
    row = cursor.fetchone()
    if row:
        result = { 'url': row[0], 'code': code}
    conn.close()
    return result

def insert(url):
    code = hashlib.sha1(url).hexdigest()
    conn = sqlite3.connect('/var/local/shortener.db')
    cursor = conn.cursor()
    cursor.execute('insert into links (url) values (?)', (url,))
    conn.commit()
    result = { 'url': url, 'code': str(cursor.lastrowid)}
    conn.close()
    return result


@bottle.route('/shorten')
def shorten():
    url = bottle.request.GET.get('url')
    r = lookup_by_url(url)
    if not r:
        r = insert(url)
    return r['code']

@bottle.route('/redirect/:code')
def redirect(code):
    r = lookup_by_code(code)
    if r:
	bottle.redirect(r['url'])
    else:
        bottle.abort(404, "No cheese")
	

bottle.debug(True)
application = bottle.default_app()

