import json
import pyqtgraph as pg

class Plot:
    def __init__(self, data):
        self.line = None
        self.datalen = 1
        self.data = data
        self.plotData(data)

    def plotJson(self, filename):
        with open(str(filename), 'r') as fp:
            data = json.load(fp)
            self.original_data = data
            self.data = data

        self.pw = pg.plot(data['times'],
                     data['values']['1'],
                     pen='b')
        self.line = self.pw.addLine(x=0,pen='r')
        self.datalen = max(data['times'])

    def plotData(self, data):
        self.original_data = data
        self.data = data

        self.pw = pg.plot(data['times'],
                          data['cache'][next(iter(data['cache']))],
                          pen='b')
        self.line = self.pw.addLine(x=0, pen='r')
        self.datalen = max(data['times'])

    def adjustData(self, value):
        newTimes = []
        for i,val in enumerate(self.original_data['times']):
            newTimes.append(val+value)

        self.pw.clear()
        self.pw.plot(newTimes,
                          self.data['cache'][next(iter(self.data['cache']))],
                          pen='b')
        self.line = self.pw.addLine(x=0, pen='r')