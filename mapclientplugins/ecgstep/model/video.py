import re
import time

import cv2



class Video :

    def __init__(self, videoFilename, frameRate):
        self.frameRate = frameRate
        self.frameCount = 0
        self.cap = None
        self.pw = None
        self.line = None
        self.datalen = 1
        self.numFrames = None
        self.videoLength = 0
        self.loadVideo(videoFilename)
        # self.playVideo()

    def playVideo(self):
        while(self.getNextFrame()):

            self.updatePlot()
            time.sleep(1 / self.frameRate)
        # inter = setInterval(1/self.frameRate,self.getNextFrame)
        # t = threading.Timer(18, inter.cancel())
        # t.start()
        # self.getNextFrame()
        # self.updatePlot()

    def updatePlot(self):
        self.line.setValue(self.frameCount / self.numFrames * self.datalen)

    def getNextFrame(self):
        flag, frameTemp = self.cap.read()
        if flag and self.frameCount != self.numFrames:
            frame = cv2.cvtColor(frameTemp, cv2.COLOR_BGR2RGB)
            if self.frameCount == 1:
                imageDimension = [frame.shape[1], frame.shape[0]]
            # posFrame = cap.get(cv2.cv2.CAP_PROP_POS_FRAMES)
            # imArray = Image.fromarray(frame)
            # image = saveFrameInMemory(imArray)
            # imageList.append(image)
            cv2.imshow('frame', frameTemp)
            # self.line.setValue(self.frameCount / self.numFrames * self.datalen)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                self.stopVideo()
                return False
            if self.frameCount == 60:
                pass
        else:
            self.stopVideo()
            return False
        self.frameCount += 1
        return True

    def loadVideo(self, filename):
        self.cap = cv2.VideoCapture(filename)
        self.numFrames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.videoLength = self.numFrames/self.frameRate
        imageList = list()
        while not self.cap.isOpened():
            selfcap = cv2.VideoCapture(filename)
            cv2.waitKey(1000)
            print("Wait for the header")
        posFrame = self.cap.get(cv2.cv2.CAP_PROP_POS_FRAMES)

    def stopVideo(self):
        self.cap.release()
        cv2.destroyAllWindows()

    def frameFromVideo(self, filename):
        global line, datalen
        cap = cv2.VideoCapture(filename)
        length = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        imageList = list()
        while not cap.isOpened():
            cap = cv2.VideoCapture(filename)
            cv2.waitKey(1000)
            print("Wait for the header")
        posFrame = cap.get(cv2.cv2.CAP_PROP_POS_FRAMES)
        count = 1
        while True:
            flag, frameTemp = cap.read()
            if flag and count != length:
                frame = cv2.cvtColor(frameTemp, cv2.COLOR_BGR2RGB)
                if count == 1:
                    imageDimension = [frame.shape[1], frame.shape[0]]
                # posFrame = cap.get(cv2.cv2.CAP_PROP_POS_FRAMES)
                # imArray = Image.fromarray(frame)
                # image = saveFrameInMemory(imArray)
                # imageList.append(image)
                cv2.imshow('frame', frameTemp)
                line.setValue(count/length*datalen)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
            else:
                break
            count+=1
        cap.release()
        cv2.destroyAllWindows()
        # imageList.pop()
        return imageList, imageDimension