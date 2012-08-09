#!/usr/bin/env python
# -*- coding: utf-8 -*-

from flask import Flask, g, render_template, url_for, redirect
from sqlalchemy import create_engine
from wtforms import Form, StringField, validators, TextAreaField
from flask.globals import request
import time, datetime

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

class PostForm(Form):
    name = StringField('Namae wa')
    email = StringField('Ímél cím')
    subject = StringField('Subject')
    message = TextAreaField('Message', [validators.Required()])

@app.route('/boards/<name>/', methods=['GET'])
def get_board(name):
    """
    /boards/ handler
    """
    form = PostForm(request.form)
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

    return render_template('board.html', board_name=board['name'], board_title=board['title'], board_names=board_names,
        threads=threads, default_name=board['default_name'], force_default=board['force_default'], form=form)

@app.route('/boards/<board_name>/<thread_id>/', methods=['GET', 'POST'])
def get_thread(board_name, thread_id):
    form = PostForm(request.form)
    if request.method == 'POST' and form.validate():
        board_id = g.db.execute('''select id from boards where name = %s''', board_name).first()[0]
        g.db.execute('''insert into posts (board_id, parent_id, name, subject, message, date) values (%s, %s, %s, %s, %s, %s)''', board_id, int(thread_id), form.name.data, form.subject.data, form.message.data, datetime.datetime.now())
        
    board = g.db.execute('''select * from boards where name = %s''', str(board_name)).first()
    posts = g.db.execute('''select * from posts where board_id = %s AND (parent_id = %s OR (parent_id = 0 AND id = %s)) order by date''', board['id'], thread_id, thread_id).fetchall()
    thread = { 'op_post': posts[0], 'replies': posts[1:] }
    board_names = [x[0] for x in g.db.execute('''select name from boards''').fetchall()]
    return render_template('thread.html', board_name=board['name'], board_title=board['title'], board_names=board_names, 
                           thread=thread, default_name=board['default_name'], force_default=board['force_default'], form=form)

if __name__ == '__main__':
    app.run()