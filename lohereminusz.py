#!/usr/bin/env python
# -*- coding: utf-8 -*-

from flask import Flask, g, render_template
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
    """
    /boards/ handler
    """
    board = g.db.execute('''select * from boards where name = %s''', str(name)).first()
    board_names = [x[0] for x in g.db.execute('''select name from boards''').fetchall()]

    op_posts = g.db.execute('''select * from posts where board_id = %s and parent_id = 0 order by stickied desc, bumped desc, date desc limit %s''',
        int(board['id']),
        int(board['threads_per_page'])).fetchall()

    threads = []
    for i in op_posts:
        replies = g.db.execute('''select * from posts where board_id = %s and parent_id = %s order by date desc limit 5''',
            int(board['id']),
            int(i['id'])).fetchall()
        threads.append({'op_post': dict(i), 'replies' :replies[::-1]})

    return render_template('new_board.html', board_name=board['name'], board_title=board['title'], board_names=board_names,
        threads=threads, default_name=board['default_name'], force_default=board['force_default'])

@app.route('/boards/<board_name>/<thread_id>/', methods=['GET', 'POST'])
def get_thread(board_name, thread_id):
    board = g.db.execute('''select * from boards where name = %s''', str(board_name)).first()
    posts = g.db.execute('''select * from posts where board_id = %s AND (parent_id = %s OR thread_id = %s)''', board["thread_id"], thread_id, thread_id).fetchall()
    return '</br>\n'.join([x["message"] for x in posts])

if __name__ == '__main__':
    app.run()