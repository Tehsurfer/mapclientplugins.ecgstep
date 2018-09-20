# threeWrapper.py is a file that collects parameters in python 3.6 to be sent via FilePipe
# to the python 2.7 API calls

import subprocess
import time
from mapclientplugins.meshgeneratorstep.model.file_pipe import FilePipe

class BlackfynnGet:

    def __init__(self):
        self.api_key = ''
        self.api_secret = ''
        self.cacheData = True
        self.database = []


    def set_api_key_login(self,api_key='62145a3b-ed98-4239-8485-3c2031061b95',api_secret='ec1c215f-41dd-4396-a794-141b953e3dad'):
        self.api_key = api_key
        self.api_secret = api_secret

    def set_params(self,dataset='Demo Data From Blackfynn',collection='Example EEG Dataset',channels='LG3',window_from_start=1,start=-1,end=-1):
        self.dataset = dataset
        self.collection = collection
        self.channels = channels
        self.window_from_start = window_from_start
        self.start = start
        self.end = end


    def get(self):

        dict = {
            'api_key': self.api_key,
            'api_secret': self.api_secret,
            'dataset': self.dataset,
            'collection': self.collection,
            'channels': self.channels,
            'window_from_start': self.window_from_start,
            'start': self.start,
            'end': self.end,
            'error': 'Have not received any communication from python 2.7. Try checking the blackfynn call',
            }

        fpipe = FilePipe()
        fpipe.send(dict)
        python2_command = 'C:\\Users\jkho021\Projects\SPARC\\venv_mapclient\Scripts\python.exe' + \
                          ' C:\\Users\jkho021\Projects\\test_space\\blackfynnData\\blackfynn_call.py'
        process = subprocess.Popen(python2_command.split(), stdout=subprocess.PIPE)
        output, error = process.communicate()
        data = fpipe.receive()
        fpipe.destroy()

        return data


# # For testing
#
# bf = BlackfynnGet()
# bf.set_api_key_login()
# bf.set_params()
# data = bf.get()
# print(data['cache'])




