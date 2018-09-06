# file_pipe.py is a class that uses msgpack to a file to communicate between Python versions

import msgpack
import json


class FilePipe(object):

    def __init__(self):
        self.filename = 'file_pipe.msgpack'

    def send(self, params):

        content = json.dumps(params)
        with open(self.filename, 'wb') as outfile:
            msgpack.pack(content, outfile)

    def receive(self):
        with open(self.filename, 'rb') as data_file:
            content_loaded = msgpack.unpack(data_file)
            params = json.loads(content_loaded)
        return params

    def destroy(self):
        # overwrite data

        open(self.filename, 'w').close()
