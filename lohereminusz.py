#!/usr/bin/env python
# -*- coding: utf-8 -*-

from flask import Flask, g, render_template, url_for, redirect
from flask.ext.uploads import UploadSet, IMAGES, UploadNotAllowed
#from flask.ext.wtf.file import file_allowed, file_required
from flask_wtf.file import file_allowed, file_required
from flaskext.uploads import configure_uploads
from sqlalchemy import create_engine
from flask_wtf import Form, StringField, validators, TextAreaField, FileField
from flask_wtf import Required
from flask.globals import request
import time, datetime, flask_wtf, os
from werkzeug.utils import secure_filename
from PIL import Image

DATABASE_NAME = 'pytest'
DEBUG = True
SECRET_KEY = '\xd5\x01\xc8\x7f\xcb^,B\xe8zE\xc7\n\xa1\\4\x98\x93\xe1"\x9d\xf2\xd0@'
DATABASE_USER = 'pytest'
DATABASE_PASSWORD = 'test'
DATABASE_HOST = 'localhost'
UPLOADED_FILES_DEST = r'C:\Users\Andor\PycharmProjects\lohere-\static\images'
UPLOADS_DEFAULT_DEST = r'C:\Users\Andor\PycharmProjects\lohere-\static\images'

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
class RequiredIf(Required):
    # a validator which makes a field required if
    # another field is set and has a truthy value

    def __init__(self, other_field_name, *args, **kwargs):
        self.other_field_name = other_field_name
        super(RequiredIf, self).__init__(*args, **kwargs)

    def __call__(self, form, field):
        other_field = form._fields.get(self.other_field_name)
        if other_field is None:
            raise Exception('no field named "%s" in form' % self.other_field_name)
        if bool(other_field.data):
            super(RequiredIf, self).__call__(form, field)

class RequiredIfNot(Required):
    def __init__(self, other_field_name, *args, **kwargs):
        self.other_field_name = other_field_name
        super(RequiredIfNot, self).__init__(*args, **kwargs)

    def __call__(self, form, field):
        other_field = form._fields.get(self.other_field_name)
        if other_field is None:
            raise Exception('no field named "%s" in form' % self.other_field_name)
        #app.logger.warning(str(other_field) + ' ' + str(type(other_field) == FileField) + ' ' + str(bool(request.files[other_field.name])) + ' ' + str(request.files[other_field.name]))
        app.logger.warning(str(not bool(other_field.data)) + ' ' + str(((type(other_field) == FileField) and bool(request.files[other_field.name]))))
        if not bool(other_field.data) and not ((type(other_field) == FileField) and bool(request.files[other_field.name])):
            super(RequiredIfNot, self).__call__(form, field)

class PostForm(flask_wtf.Form):
    name = StringField('Namae wa')
    email = StringField('email')
    subject = StringField('Subject')
    file = FileField('File', validators=[file_allowed(img, 'images only')])
    message = TextAreaField('Message', validators=[RequiredIfNot('file')])

configure_uploads(app, (img,))

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

    if form.validate_on_submit():
        board_id = g.db.execute('''select id from boards where name = %s''', board_name).first()[0]
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
            g.db.execute('''insert into files (filetype, filename, extension, original_filename, size, md5) values (%s, %s, %s, %s, %s, %s)''', 1, filename, ext, secure_filename(file.filename), file.content_length, file.content_type)
            file_id = g.db.execute('''select LAST_INSERT_ID()''').first()[0]


        # új poszt adatainak beillesztése
        g.db.execute('''insert into posts (board_id, parent_id, name, subject, message, date) values (%s, %s, %s, %s, %s, %s)''', board_id, int(thread_id), form.name.data, form.subject.data, form.message.data, datetime.datetime.now())
        # parent poszt bumpolása
        g.db.execute('''update posts set bumped = %s where id = %s and parent_id = 0 and board_id = %s''', datetime.datetime.now(), thread_id, board_id)

        if file:
            post_id = g.db.execute('''select LAST_INSERT_ID()''').first()[0]
            # poszt img-idjének frissítése
            g.db.execute('''update posts set file_id = %s where id = %s''', file_id, post_id)
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