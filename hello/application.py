#!/usr/bin/python


import os
import site
site.addsitedir(os.path.dirname(__file__))


import bottle
from message import Message


@bottle.route('/hello')
def hello():
    message = Message()
    return message.generate()


application = bottle.default_app()

