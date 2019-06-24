import json
import pyqtgraph as pg

class Plot:
    def __init__(self, data):
        self.line = None
        self.time = 0
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
                          data['cache']['26'],
                          pen='b')
        self.line = self.pw.addLine(x=0, pen='r')
        self.datalen = max(data['times'])

    def nudgePlotStart(self, value):
        newTimes = []
        for i,val in enumerate(self.original_data['times']):
            newTimes.append(val+value)

        self.pw.clear()
        self.pw.plot(newTimes,
                          self.data['cache']['26'],
                          pen='b')
        self.line = self.pw.addLine(x=self.time, pen='r')

    def nudgeDataStart(self, value):
        newTimes = []
        for i,val in enumerate(self.original_data['times']):
            newTimes.append(val+value)
        self.data['times'] = newTimes
        return self.data

    def updateTimeMarker(self, value):
        self.time = value
        if self.line is not None:
            self.line.setValue(round(value,3))
