__author__ = 'Andor'
from hashlib import md5
from flask import g
from lohereminusz import app
import os

def hashfile(afile, blocksize=65536):
    buf = afile.read(blocksize)
    hasher = md5()
    while len(buf) > 0:
        hasher.update(buf)
        buf = afile.read(blocksize)
    return hasher.digest()

def delete_thread(board_id, thread_id):
    """
    delete specified thread from specified board, along with posts AND files
    :param board_id the id of the board the thread resides in
    :param thread_id the id of the thread
    """
    # fetch file ids
    file_ids = g.db.execute('''select file_id from posts where board_id = %s and (id = %s or parent_id = %s)''', board_id, thread_id, thread_id).fetchall()
    # fetch file rows
    file_rows = g.db.execute('''select * from files where id in %s''', file_ids).fetchall()
    # del "physical" files
    for file in file_rows:
        os.remove(os.path.join(app.config['UPLOADS_DEFAULT_DEST'], 'image' ,file.filename))
        os.remove(os.path.join(app.config['UPLOADS_DEFAULT_DEST'], 'thumbs' ,file.filename))
    # delete file rows
    g.db.execute('''delete from files where id in %s''', file_ids)
    # delete post rows
    g.db.execute('''delete from posts where board_id = %s and (id = %s or parent_id = %s)''', board_id, thread_id, thread_id)