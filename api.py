#!/usr/bin/env python
import os
import json
import argparse
import tempfile

from bottle import route, request, response, run
from bottle import HTTPError

from viper.common.objects import File
from viper.core.storage import store_sample
from viper.core.database import Database

db = Database()

def jsonize(data):
    return json.dumps(data, sort_keys=False, indent=4)

@route('/test', method='GET')
def test():
    return jsonize({'message' : 'test'})

@route('/file/add', method='POST')
def add_file():
    tags = request.forms.get('tags')
    upload = request.files.get('file')

    tf = tempfile.NamedTemporaryFile()
    tf.write(upload.file.read())
    tf_obj = File(tf.name)
    tf_obj.name = upload.filename

    new_path = store_sample(tf_obj)

    success = False
    if new_path:
        # Add file to the database.
        success = db.add(obj=tf_obj, tags=tags)

    if success:
        return jsonize({'message' : 'added'})
    else:
        return HTTPError(500, 'Unable to store file')

@route('/file/get/<sha256>', method='GET')
def get_file(sha256):
    path = get_sample_path(sha256)
    if not path:
        raise HTTPError(404, 'File not found')

    response.content_length = os.path.getsize(path)
    response.content_type = 'application/octet-stream; charset=UTF-8'
    data = open(path, 'rb').read()

    return data

@route('/file/find', method='POST')
def find_file():
    def details(row):
        tags = []
        for tag in row.tag:
            tags.append(tag.tag)

        entry = {
            'id' : row.id,
            'file_name' : row.file_name,
            'file_type' : row.file_type,
            'file_size' : row.file_size,
            'md5' : row.md5,
            'sha1' : row.sha1,
            'sha256' : row.sha256,
            'sha512' : row.sha512,
            'crc32' : row.crc32,
            'ssdeep': row.ssdeep,
            'created_at': row.created_at.__str__(),
            'tags' : tags
        }

        return entry

    md5 = request.forms.get('md5')
    sha256 = request.forms.get('sha256')
    ssdeep = request.forms.get('ssdeep')
    tag = request.forms.get('tag')
    date = request.forms.get('date')

    if md5:
        row = db.find_md5(md5)
        if row:
            return jsonize(details(row))
        else:
            raise HTTPError(404, 'File not found')
    elif sha256:
        row = db.find_sha256(sha256)
        if row:
            return jsonize(details(row))
        else:
            raise HTTPError(404, 'File not found')
    else:
        if ssdeep:
            rows = db.find_ssdeep(ssdeep)
        elif tag:
            rows = db.find_tag(tag)
        elif date:
            rows = db.find_date(date)
        else:
            return HTTPError(400, 'Invalid search term')

        if not rows:
            return HTTPError(404, 'File not found')

        results = []
        for row in rows:
            entry = details(row)
            results.append(entry)

        return jsonize(results)

@route('/tags/list', method='GET')
def list_tags():
    rows = db.list_tags()

    results = []
    for row in rows:
        results.append(row.tag)

    return jsonize(results)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-H', '--host', help='Host to bind the API server on', default='localhost', action='store', required=False)
    parser.add_argument('-p', '--port', help='Port to bind the API server on', default=8080, action='store', required=False)
    args = parser.parse_args()

    run(host=args.host, port=args.port)
