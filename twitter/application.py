#!/usr/bin/python

#
# simple twitter api - stefan@arentz.ca - 2010-11-28
#
# INTRODUCTION
#
# This is a tiny web app that allows you to post status updates to
# twitter with a simple HTTP GET call. Like in the old pre-OAuth
# days.
#
# It does this by letting you sign in with your Twtter account through
# OAuth, all behind the scenes, and then making a simpler API available,
# doing all the OAuth work for you.
#
# This is great for little scripts and apps where you don't want to
# go through all the OAuth silliness but instead just do a simple
# request.
#
# SETUP INSTRUCTIONS
#
# Register a new application with twitter. Make sure you copy the
# token and secret to this app's configuration. Properly configure
# the OAuth callback url to point to this app's /callback route.
#
# CLIENT INSTRUCTIONS
#
# When you login, you are given a user_id and a secret. You can then
# make a call to /tweet like this in Python:
#
#    user_id = ...
#    secret = ...
#    message = "Hello"
#    signature = hashlib.sha1(secret + user_id + message).hexdigest()
#
#    parameters = {
#      'user_id': user_id,
#      'message': message,
#      'signature': signature
#    }
#
#    url = "https://your.site/tweet?%s" % urllib.urlencode(parameters)
#    response = urllib.urlopen(url).read()
#


import os
import site
site.addsitedir(os.path.dirname(__file__))


import bottle
from beaker.middleware import SessionMiddleware

import oauth2 as oauth
import time
import cgi
import json
import pickle
import hashlib
import random
import urllib


TWITTER_SITE_ROOT=
TWITTER_USERS_ROOT=
TWITTER_SESSIONS_ROOT=
TWITTER_TOKEN=
TWITTER_SECRET=


# Who needs a database if you have a fileysstem

def load_user(user_id):
    path = "%s/%s.json" % (TWITTER_USERS_ROOT, user_id)
    if os.path.isfile(path):
        return json.loads(open(path).read())

def delete_user(user):
    path = "%s/%s.json" % (TWITTER_USERS_ROOT, user['user_id'])
    if os.path.isfile(path):
        os.remove(path)

def save_user(user):
    path = "%s/%s.json" % (TWITTER_USERS_ROOT, user['user_id'])
    open(path, "w").write(json.dumps(user))


@bottle.route('/')
def home():

    s = bottle.request.environ.get('beaker.session')
    if not s.has_key('access_token'):
        bottle.redirect(TWITTER_SITE_ROOT + '/login')

    u = load_user(s['access_token']['user_id'])

    html = "<p>You are logged in.</p>"
    html += "<p>Your settings are:</p><ul><li>user_id: %s</li><li>secret: %s</li></ul></p>" % (u['user_id'], u['secret'])
    html += "<p>You can post to twitter like this:</p>"
    signature = hashlib.sha1(u['secret'] + u['user_id'] + 'Hello').hexdigest()
    html += "<pre>https://%s/twitter/tweet?userid=%s&message=Hello&signature=%s</pre>" % (bottle.request.environ.get('HTTP_HOST'), u['user_id'], signature)
    html += "The signature is <code>HEX(SHA1(secret + user_id + message))</code>."
    html += "<p><a href='%s/logout'>Log-out</a></p>" % TWITTER_SITE_ROOT
    return html


@bottle.route('/foo')
def foo():

    consumer = oauth.Consumer(TWITTER_TOKEN, TWITTER_SECRET)
    client = oauth.Client(consumer)

    response, content = client.request('http://twitter.com/oauth/request_token', "GET")
    if response['status'] != '200':
        raise Exception("Invalid response from Twitter.")

    request_token = dict(cgi.parse_qsl(content))
    s = bottle.request.environ.get('beaker.session')
    s['request_token'] = request_token
    
    # Redirect to the Twitter login page
    url = "%s?oauth_token=%s" % ('http://twitter.com/oauth/authenticate', request_token['oauth_token'])
    bottle.redirect(url)


@bottle.route('/login')
def login():
    s = bottle.request.environ.get('beaker.session')
    if not s.has_key('access_token'):
        return '<a href="/twitter/foo"><img src="http://a0.twimg.com/images/dev/buttons/sign-in-with-twitter-d.png"></h1>'
    else:
        bottle.redirect(TWITTER_SITE_ROOT + '/')


@bottle.route('/callback')
def callback():

    # Just make sure that we have a valid session
    s = bottle.request.environ.get('beaker.session')
    if not s.has_key('request_token'):
        bottle.redirect(TWITTER_SITE_ROOT + '/login')

    # Use the request token in the session to build a new client
    consumer = oauth.Consumer(TWITTER_TOKEN, TWITTER_SECRET)
    token = oauth.Token(s['request_token']['oauth_token'], s['request_token']['oauth_token_secret'])
    client = oauth.Client(consumer, token)

    # Request the authorized access token from Twitter
    resp, content = client.request('http://twitter.com/oauth/access_token', "GET")
    if resp['status'] != '200':
        #print content
        raise Exception("Invalid response from Twitter.")
    access_token = dict(cgi.parse_qsl(content))

    # Lookup the user or create them if they don't exist
    user = load_user(access_token['user_id'])
    if not user:
        user = dict(access_token)
        user['token'] = hashlib.sha1(str(user) + str(random.random()) + str(random.random())).hexdigest()
        user['secret'] = hashlib.sha1(str(user) + str(random.random()) + str(random.random())).hexdigest()
        save_user(user)

    # Store the user id in the session and go back to the home page
    s['access_token'] = access_token
    bottle.redirect(TWITTER_SITE_ROOT + '/')


@bottle.route('/logout')
def logout():
    s = bottle.request.environ.get('beaker.session')
    s.clear()
    bottle.redirect(TWITTER_SITE_ROOT + '/')


@bottle.route('/tweet')
def tweet():
    
    userid = bottle.request.GET.get('userid')
    message = bottle.request.GET.get('message')
    signature = bottle.request.GET.get('signature')
    if not message or not userid or not signature:
        return { 'status': 'error' }

    user = load_user(userid)    
    if not user:
        return { 'status': 'error' }

    correct_signature = hashlib.sha1(user['secret'] + user['user_id'] + message).hexdigest()

    if signature != correct_signature:
        return { 'status': 'error' }

    # Use the request token in the session to build a new client
    consumer = oauth.Consumer(TWITTER_TOKEN, TWITTER_SECRET)
    token = oauth.Token(user['oauth_token'], user['oauth_token_secret'])
    client = oauth.Client(consumer, token)

    # Request the authorized access token from Twitter
    headers = { 'Content-Type': 'application/x-www-form-urlencoded' }
    body = urllib.urlencode({ 'status': message })
    resp, content = client.request('http://api.twitter.com/1/statuses/update.json', "POST", headers=headers, body=body)

    return { 'status': 'success' }


application = bottle.default_app()
session_opts = {
    'session.type': 'file',
    'session.cookie_expires': 300,
    'session.data_dir': TWITTER_SESSIONS_ROOT,
    'session.auto': True
}
application = SessionMiddleware(application, session_opts)

bottle.debug(True)

if __name__ == "__main__":
    bottle.debug(True)
    bottle.run(app=application, host='0.0.0.0', port=8080)
