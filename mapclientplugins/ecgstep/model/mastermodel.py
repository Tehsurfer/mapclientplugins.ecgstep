import os
import json

from PySide import QtCore

from opencmiss.zinc.context import Context
from opencmiss.zinc.material import Material

from mapclientplugins.ecgstep.model.blackfynndatamodel import BlackfynnDataModel
from mapclientplugins.ecgstep.model.video import Video
from mapclientplugins.ecgstep.model.imageplanemodel import ImagePlaneModel
from mapclientplugins.ecgstep.model.imageplanescene import ImagePlaneScene
class MasterModel(object):

    def __init__(self, location, identifier, image_context_data):
        self._location = location
        self._identifier = identifier
        self._filenameStem = os.path.join(self._location, self._identifier)
        self._context = Context('ecg')
        self._timekeeper = self._context.getTimekeepermodule().getDefaultTimekeeper()
        self._timer = QtCore.QTimer()
        self._current_time = 0.0
        self._play_rate = 1
        self._timeValueUpdate = None
        self._frameIndexUpdate = None
        self._initialise()
        self._region = self._context.createRegion()
        self._blackfynn_data_model = BlackfynnDataModel()
        video_path = image_context_data.get_video_path()
        self._video_path = video_path
        fps = image_context_data.get_frames_per_second()
        self.video = Video(video_path, fps)
        self.set_max_time(self.video.videoLength)
        self._image_plane_model = ImagePlaneModel(self, video_path)
        self._image_plane_scene = ImagePlaneScene(self)

        self._settings = {
            'frames-per-second': 30,
            'time-loop': False
        }
        self._makeConnections()
        self.loadSettings()

    def printLog(self):
        logger = self._context.getLogger()
        for index in range(logger.getNumberOfMessages()):
            print(logger.getMessageTextAtIndex(index))

    def _initialise(self):
        self._filenameStem = os.path.join(self._location, self._identifier)
        tess = self._context.getTessellationmodule().getDefaultTessellation()
        tess.setRefinementFactors(12)
        self._tess = tess
        # set up standard materials and glyphs so we can use them elsewhere
        self._materialmodule = self._context.getMaterialmodule()
        self._materialmodule.defineStandardMaterials()
        solid_blue = self._materialmodule.createMaterial()
        solid_blue.setName('solid_blue')
        solid_blue.setManaged(True)
        solid_blue.setAttributeReal3(Material.ATTRIBUTE_AMBIENT, [ 0.0, 0.2, 0.6 ])
        solid_blue.setAttributeReal3(Material.ATTRIBUTE_DIFFUSE, [ 0.0, 0.7, 1.0 ])
        solid_blue.setAttributeReal3(Material.ATTRIBUTE_EMISSION, [ 0.0, 0.0, 0.0 ])
        solid_blue.setAttributeReal3(Material.ATTRIBUTE_SPECULAR, [ 0.1, 0.1, 0.1 ])
        solid_blue.setAttributeReal(Material.ATTRIBUTE_SHININESS , 0.2)
        trans_blue = self._materialmodule.createMaterial()
        trans_blue.setName('trans_blue')
        trans_blue.setManaged(True)
        trans_blue.setAttributeReal3(Material.ATTRIBUTE_AMBIENT, [ 0.0, 0.2, 0.6 ])
        trans_blue.setAttributeReal3(Material.ATTRIBUTE_DIFFUSE, [ 0.0, 0.7, 1.0 ])
        trans_blue.setAttributeReal3(Material.ATTRIBUTE_EMISSION, [ 0.0, 0.0, 0.0 ])
        trans_blue.setAttributeReal3(Material.ATTRIBUTE_SPECULAR, [ 0.1, 0.1, 0.1 ])
        trans_blue.setAttributeReal(Material.ATTRIBUTE_ALPHA , 0.3)
        trans_blue.setAttributeReal(Material.ATTRIBUTE_SHININESS , 0.2)
        glyphmodule = self._context.getGlyphmodule()
        glyphmodule.defineStandardGlyphs()

    def _makeConnections(self):
        self._timer.timeout.connect(self._timeout)

    def _timeout(self):
        self._current_time += 1000/self._settings['frames-per-second']/1000 * self._play_rate
        duration = self.video.numFrames / self._settings['frames-per-second']
        if self._settings['time-loop'] and self._current_time > duration:
            self._current_time -= duration
        self._timekeeper.setTime(self._current_time)
        self._timeValueUpdate(self._current_time)
        frame_index = self._image_plane_model.get_frame_index_for_time(self._current_time)

    def set_max_time(self, max_time):
        self._timekeeper.setMaximumTime(max_time)


    def _scaleCurrentTimeToTimekeeperTime(self):
        scaled_time = 0.0
        duration = self.video.numFrames / self._settings['frames-per-second']
        if duration > 0:
            scaled_time = self._current_time/duration

        return scaled_time

    def getVideoPath(self):
        return self._video_path

    def getIdentifier(self):
        return self._identifier

    def getOutputModelFilename(self):
        return self._filenameStem + '.ex2'

    def getBlackfynnDataModel(self):
        return self._blackfynn_data_model

    def get_region(self):
        return self._region

    def getScene(self):
        return self._region.getScene()

    def get_image_plane_scene(self):
        return self._image_plane_scene

    def get_image_plane_model(self):
        return self._image_plane_model

    def getContext(self):
        return self._context

    def get_context(self):
        return self._context

    def get_timekeeper(self):
        return self._timekeeper

    def setTessellation(self,refinement_value):
        self._tess.setRefinementFactors(refinement_value)

    def setPlayRate(self, play_rate):
        self._play_rate = play_rate

    def setFrameIndex(self, frame_index):
        frame_value = frame_index - 1
        self._timekeeper.setTime(self._scaleCurrentTimeToTimekeeperTime())
        self._timeValueUpdate(self._current_time)

    def setTimeValue(self, time):
        self._current_time = time
        self._timekeeper.setTime(self._scaleCurrentTimeToTimekeeperTime())
        #self._frameIndexUpdate(frame_index)

    def setFramesPerSecond(self, value):
        self._settings['frames-per-second'] = value

    def getFramesPerSecond(self):
        return self._settings['frames-per-second']

    def setTimeLoop(self, state):
        self._settings['time-loop'] = state

    def isTimeLoop(self):
        return self._settings['time-loop']

    def play(self):
        self._timer.start(1000/self._settings['frames-per-second'])

    def stop(self):
        self._timer.stop()

    def registerFrameIndexUpdateCallback(self, frameIndexUpdateCallback):
        self._frameIndexUpdate = frameIndexUpdateCallback

    def registerTimeValueUpdateCallback(self, timeValueUpdateCallback):
        self._timeValueUpdate = timeValueUpdateCallback

    def done(self):
        self._saveSettings()

    def _getSettings(self):
        settings = self._settings
        settings['blackfynn_settings'] = self._blackfynn_data_model.getSettings()
        return settings

    def loadSettings(self):
        try:
            settings = self._settings
            with open(self._filenameStem + '-settings.json', 'r') as f:
                settings.update(json.loads(f.read()))
            if 'blackfynn_settings' not in settings:
                settings.update({'blackfynn_settings': self._blackfynn_data_model.getSettings()})
        except:
            # no settings saved yet, following gets defaults
            settings = self._getSettings()
        self._blackfynn_data_model.setSettings(settings['blackfynn_settings'])

    def _saveSettings(self):
        settings = self._getSettings()
        with open(self._filenameStem + '-settings.json', 'w') as f:
            f.write(json.dumps(settings, default=lambda o: o.__dict__, sort_keys=True, indent=4))

