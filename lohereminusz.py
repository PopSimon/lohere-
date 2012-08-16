#!/usr/bin/env python
# -*- coding: utf-8 -*-

# deps: flask (werkzeug, jinja2), python-mysql, flask-wtf, flask-uploads, postmarkup (for bbcode)
# TODO: better security, admin panel, quotes/links, passwords/post deletion

PYGMENTS_ENABLED = False

from flask import Flask, g, render_template, url_for, redirect
from flask.ext.uploads import UploadSet, IMAGES, UploadNotAllowed
#from flask.ext.wtf.file import file_allowed, file_required
from flask.helpers import flash
from flask_wtf.file import file_allowed, file_required
from flaskext.uploads import configure_uploads
from sqlalchemy import create_engine
from flask_wtf import Form, StringField, validators, TextAreaField, FileField
from flask_wtf import Required
from flask.globals import request
import time, datetime, flask_wtf, os
from werkzeug.utils import secure_filename
from PIL import Image
import helpers
from postmarkup import render_bbcode
import postmarkup
if PYGMENTS_ENABLED:
    import pygments

markup_engine = postmarkup.create(exclude=['img'], use_pygments=PYGMENTS_ENABLED)

DATABASE_NAME = 'pytest'
DEBUG = True
SECRET_KEY = '\xd5\x01\xc8\x7f\xcb^,B\xe8zE\xc7\n\xa1\\4\x98\x93\xe1"\x9d\xf2\xd0@'
DATABASE_USER = 'pytest'
DATABASE_PASSWORD = 'test'
DATABASE_HOST = 'localhost'
UPLOADED_FILES_DEST = r'C:\Users\Andor\PycharmProjects\lohere-\static\images'
UPLOADS_DEFAULT_DEST = r'C:\Users\Andor\PycharmProjects\lohere-\static\images'
NOKO_STRING = 'noko'
SAGE_STRING = 'sage'

app = Flask(__name__)
app.config.from_object(__name__)

def resize(image, maxSize, method = 3):
    imAspect = float(image.size[0])/float(image.size[1])
    outAspect = float(maxSize[0])/float(maxSize[1])
 
    if imAspect >= outAspect:
        return image.resize((maxSize[0], int((float(maxSize[0])/imAspect) + 0.5)), method)
    else:
        return image.resize((int((float(maxSize[1])*imAspect) + 0.5), maxSize[1]), method)

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

img = UploadSet('image', IMAGES)

# sauce: http://stackoverflow.com/questions/8463209/how-to-make-a-field-conditionally-optional-in-wtforms
# MODIFIED for own needs, assumed public domain
class RequiredIfNot(Required):
    def __init__(self, other_field_name, *args, **kwargs):
        self.other_field_name = other_field_name
        super(RequiredIfNot, self).__init__(*args, **kwargs)

    def __call__(self, form, field):
        other_field = form._fields.get(self.other_field_name)
        if other_field is None:
            raise Exception('no field named "%s" in form' % self.other_field_name)
        if not bool(other_field.data) and not ((type(other_field) == FileField) and bool(request.files[other_field.name])):
            super(RequiredIfNot, self).__call__(form, field)

class PostForm(flask_wtf.Form):
    name = StringField('Namae wa')
    email = StringField('email')
    subject = StringField('Subject')
    file = FileField('File', validators=[file_allowed(img, 'images only')])
    message = TextAreaField('Message', validators=[RequiredIfNot('file')])

configure_uploads(app, (img,))

@app.route('/boards/<name>/', methods=['GET', 'POST'])
def get_board(name):
    """
    /boards/ handler
    """
    form = PostForm(request.form)

    if form.validate_on_submit():
        board_id, is_board_locked, max_threads = g.db.execute('''select id, locked, max_threads from boards where name = %s''', name).first()
        if is_board_locked:
            flash('Board is locked!')
            return redirect(url_for('get_board', name=name))
        # select how many threads there already are
        nr_threads = g.db.execute('''select count(*) from posts where board_id = %s and parent_id = 0''', board_id).first()[0]
        # grab threads, oldest first
        # TODO: maybe spare sticked? revisit!
        thread_ids = g.db.execute('''select id from posts where board_id = %s and parent_id = 0 order by stickied asc, bumped asc''', board_id)
        if nr_threads >= max_threads:
            # this should hopefully only always be one, but delete as many as necessary to adjust to max threads
            for i in range(nr_threads - max_threads):
                helpers.delete_thread(board_id, thread_ids[i])
        # TODO: ezt a részt lehetne egy külön metódusba átvinni
        file = request.files['file']
        file_id = None
        if file:
            # fájl mentése, validálás, new
            filename = ''
            try:
                filename = img.save(request.files['file'], name=str(int(time.mktime(datetime.datetime.now().timetuple())))+'.')
                imagefile = Image.open(os.path.join(UPLOADED_FILES_DEST, 'image' , filename))

                outimg = resize(imagefile, (150, 150))
                outimg.save(os.path.join(UPLOADED_FILES_DEST, 'thumbs' , filename))
            except UploadNotAllowed:
                return 'NEM BAZMEG'

            ext = filename[filename.rfind('.'):]
            # TODO: fix, hashing broken
            file_h = open(os.path.join(UPLOADED_FILES_DEST, 'image' , filename), 'r')
            filehash = helpers.hashfile(file_h)
            file_h.close()
            filesize = os.path.getsize(os.path.join(UPLOADED_FILES_DEST, 'image' , filename))
            g.db.execute('''insert into files (filename, extension, original_filename, size, md5, content_type) values (%s, %s, %s, %s, %s, %s)''', filename, ext, secure_filename(file.filename), filesize, filehash, file.content_type)
            file_id = g.db.execute('''select LAST_INSERT_ID()''').first()[0]

        # új poszt adatainak beillesztése
        actual_email = form.email.data
        if form.email.data == app.config['NOKO_STRING']: # or form.email.data == app.config['SAGE_STRING']:
            actual_email = None
        date_now = datetime.datetime.now()
        g.db.execute('''insert into posts (board_id, parent_id, name, subject, message, date, email) values (%s, 0, %s, %s, %s, %s, %s)''', str(board_id), form.name.data, form.subject.data, markup_engine(form.message.data), date_now, actual_email)
        post_id = g.db.execute('''select LAST_INSERT_ID()''').first()[0]

        if file:
            # poszt img-idjének frissítése
            g.db.execute('''update posts set file_id = %s where id = %s''', file_id, post_id)

        # finally return user to their thread
        return redirect(url_for('get_thread', board_name=name, thread_id=post_id))

    board = g.db.execute('''select * from boards where name = %s''', str(name)).first()
    board_names = [x[0] for x in g.db.execute('''select name from boards''').fetchall()]

    op_posts = g.db.execute('''select * from posts where board_id = %s and parent_id = 0 order by stickied desc, bumped desc, date desc limit %s''',
        int(board['id']),
        int(board['threads_per_page'])).fetchall()

    threads = []
    for i in op_posts:
        op_post = dict(i)
        if op_post['file_id']:
            op_post['file'] = g.db.execute('''select * from files where id = %s''', op_post['file_id']).first()
        replies = []#[dict(x).__setitem__('file', g.db.execute('''select * from files where id = %s''', x['file_id']).first()) if x['file_id'] else dict(x) for x in g.db.execute('''select * from posts where board_id = %s and parent_id = %s order by date desc limit 5''', int(board['id']),int(i['id'])).fetchall()]
        replies_with_image = 0
        for k in g.db.execute('''select * from posts where board_id = %s and parent_id = %s order by date desc limit 5''', int(board['id']),int(i['id'])).fetchall():
            reply = dict(k)
            if reply['file_id']:
                replies_with_image += 1
                reply['file'] = g.db.execute('''select * from files where id = %s''', reply['file_id']).first()
            replies.append(reply)

        threads.append({
            'op_post': op_post,
            'replies': replies[::-1],
            'num_unshown_posts': g.db.execute('''select COUNT(*)-5 from posts where board_id = %s and parent_id = %s order by date asc''', int(board['id']), int(i['id'])).first()[0],
            # TODO: fix, inner join vagy valami faszság :(
            'num_unshown_files': g.db.execute('''select COUNT(*)-(select COUNT(*) from posts where board_id = %s and parent_id = %s and file_id != 0 order by date limit 5) from posts where board_id = %s and parent_id = %s and file_id != 0 order by date asc''', int(board['id']), int(i['id']), int(board['id']), int(i['id'])).first()[0]
        })

    return render_template('board.html', board_name=board['name'], board_title=board['title'], board_names=board_names,
        threads=threads, default_name=board['default_name'], force_default=board['force_default'], form=form, board_locked=board['locked'])

@app.route('/boards/<board_name>/<thread_id>/', methods=['GET', 'POST'])
def get_thread(board_name, thread_id):
    """
    /boards/thread/ handler
    """
    form = PostForm(request.form)

    if form.validate_on_submit():
        board_id, max_replies = g.db.execute('''select id, max_replies from boards where name = %s''', board_name).first()
        nr_replies = g.db.execute('''select count(id) from posts where parent_id = %s''', thread_id).first()[0]
        is_admin_unlocked, locked = g.db.execute('''select admin_unlocked, locked from posts where id = %s''', thread_id).first()
        # thread lockolva
        if locked:
            flash('thread locked')
            return redirect(url_for('get_board', name=board_name))

        # thread full, és admin nem unlockolta
        if nr_replies >= max_replies and not is_admin_unlocked:
            flash('thread full')
            return redirect(url_for('get_board', name=board_name))
        file = request.files['file']
        file_id = None
        if file:
            # fájl mentése, validálás, new
            filename = ''
            try:
                filename = img.save(request.files['file'], name=str(int(time.mktime(datetime.datetime.now().timetuple())))+'.')
                imagefile = Image.open(os.path.join(UPLOADED_FILES_DEST, 'image' , filename))

                outimg = resize(imagefile, (150, 150))
                outimg.save(os.path.join(UPLOADED_FILES_DEST, 'thumbs' , filename))
            except UploadNotAllowed:
                return 'NEM BAZMEG'

            ext = filename[filename.rfind('.'):]
            # TODO: fix, hashing broken
            file_h = open(os.path.join(UPLOADED_FILES_DEST, 'image' , filename), 'r')
            filehash = helpers.hashfile(file_h)
            file_h.close()
            filesize = os.path.getsize(os.path.join(UPLOADED_FILES_DEST, 'image' , filename))
            g.db.execute('''insert into files (filename, extension, original_filename, size, md5, content_type) values (%s, %s, %s, %s, %s, %s)''', filename, ext, secure_filename(file.filename), filesize, filehash, file.content_type)
            file_id = g.db.execute('''select LAST_INSERT_ID()''').first()[0]

        date_now = datetime.datetime.now()
        # új poszt adatainak beillesztése
        actual_email = form.email.data
        if form.email.data == app.config['NOKO_STRING']: # or form.email.data == app.config['SAGE_STRING']:
            actual_email = ''
        g.db.execute('''insert into posts (board_id, parent_id, name, subject, message, date, email) values (%s, %s, %s, %s, %s, %s, %s)''', str(board_id), str(thread_id), form.name.data, form.subject.data, markup_engine(form.message.data), date_now, actual_email)

        if file:
            post_id = g.db.execute('''select LAST_INSERT_ID()''').first()[0]
            # poszt img-idjének frissítése
            g.db.execute('''update posts set file_id = %s where id = %s''', file_id, post_id)

        # parent poszt bumpolása
        if form.email.data != app.config['SAGE_STRING']:
            g.db.execute('''update posts set bumped = %s where id = %s and parent_id = 0 and board_id = %s''', date_now, thread_id, board_id)

        # noko, vissza a thread-be
        if form.email.data == app.config['NOKO_STRING']:
            return redirect(url_for('get_thread', board_name=board_name, thread_id=thread_id))
        else:
            return redirect(url_for('get_board', name=board_name))
    # invalid poszt
    elif request.method == 'POST' and not form.validate():
        # sem kép, sem szöveg
        if form.errors.keys()[0] == 'message':
            return 'need image or msg, lul'
        else: return ':('

    board = g.db.execute('''select * from boards where name = %s''', str(board_name)).first()
    posts = [dict(x) for x in g.db.execute('''select * from posts where board_id = %s AND (parent_id = %s OR (parent_id = 0 AND id = %s)) order by date''', board['id'], thread_id, thread_id).fetchall()]
    for i in range(len(posts)):
        if posts[i]['file_id'] != 0:
            file_details = g.db.execute('''select * from files where id = %s''', posts[i]['file_id']).first()
            posts[i]['file'] = file_details
    thread = { 'op_post': posts[0], 'replies': posts[1:] }
    board_names = [x[0] for x in g.db.execute('''select name from boards''').fetchall()]
    return render_template('thread.html', board_name=board['name'], board_title=board['title'], board_names=board_names, 
                           thread=thread, default_name=board['default_name'], force_default=board['force_default'], form=form)

if __name__ == '__main__':
    app.run()