#!/usr/bin/env python
# -*- coding: utf-8 -*-

from flask import Flask, g
from sqlalchemy import create_engine

DATABASE_NAME = 'pytest'
DEBUG = True
SECRET_KEY = '\xd5\x01\xc8\x7f\xcb^,B\xe8zE\xc7\n\xa1\\4\x98\x93\xe1"\x9d\xf2\xd0@'
DATABASE_USER = 'pytest'
DATABASE_PASSWORD = 'test'
DATABASE_HOST = 'localhost'

app = Flask(__name__)
app.config.from_object(__name__)

def connect_db():
    """
    DB kapcsolat kiépítése
    """
    engine = create_engine('mysql://%s:%s@%s/%s' % (app.config['DATABASE_USER'], app.config['DATABASE_PASSWORD'],
                                                    app.config['DATABASE_HOST'], app.config['DATABASE_NAME']))
    conn = engine.connect()

    return conn

@app.before_request
def before_request():
    """
    DB konnekt request előtt
    """
    g.db = connect_db()

@app.teardown_request
def teardown_request(exception):
    """
    DB konnekt lezárás request végén
    """
    if hasattr(g, 'db'):
        g.db.close()


@app.route('/')
def hello_world():
    return "ZIAZDOG"

@app.route('/boards/<name>/', methods=['GET'])
def get_board(name):
    board = g.db.execute('''select * from boards where name = %s''', str(name)).first()
    posts = g.db.execute('''select * from posts where board_id = %s''', board["id"])
    return ("<html><body>/%s/ - %s \n</br>%s" % (board["name"], board["title"], board["desc"])) + "\n</br>" + ' '.join([x["message"] + "</br>" for x in posts]) + "</body></html>"

@app.route('/boards/<board_name>/<id>/', methods=['GET', 'POST'])
def get_thread(board_name, id):
    board = g.db.execute('''select * from boards where name = %s''', str(board_name)).first()
    posts = g.db.execute('''select * from posts where board_id = %s AND (parent_id = %s OR id = %s)''', board["id"], id, id).fetchall()
    return '</br>\n'.join([x["message"] for x in posts])

if __name__ == '__main__':
    app.run()