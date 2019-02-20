"""
Created on Aug 29, 2017

@author: Richard Christie
"""

import types


import json
import webbrowser
import numpy as np

from PySide import QtGui, QtCore

from mapclient.view.utils import set_wait_cursor
from mapclientplugins.ecgstep.view.ecg_ui import Ui_MeshGeneratorWidget
from mapclientplugins.ecgstep.view.addprofile import AddProfileDialog
from mapclientplugins.ecgstep.model.plot import Plot
from mapclientplugins.ecgstep.model.blackfynnmesh import BlackfynnMesh

class MeshGeneratorWidget(QtGui.QWidget):

    def __init__(self, model, node_coordinates_data, export_directory, parent=None):
        super(MeshGeneratorWidget, self).__init__(parent)
        self._ui = Ui_MeshGeneratorWidget()
        self._model = model
        self._model.registerTimeValueUpdateCallback(self._updateTimeValue)
        self._model.registerFrameIndexUpdateCallback(self._updateFrameIndex)

        self._ui.setupUi(self)
        self._export_directory = export_directory
        self._doneCallback = None
        self._marker_mode_active = False
        self._have_images = False

        self.time = 0
        self._electrode_mesh = None
        self._node_coordinates_data = node_coordinates_data
        self._time_sequence = node_coordinates_data['time_array']

        self._blackfynn_data_model = model.getBlackfynnDataModel()
        self._ui.sceneviewer_widget.setContext(model.getContext())
        self._ui.sceneviewer_widget.setModel(self._model)
        self._ui.sceneviewer_widget.initializeGL()
        self._makeConnections()

        self.plot = None
        self._ui.sceneviewer_widget.grid = []

    def _graphicsInitialized(self):
        """
        Callback for when SceneviewerWidget is initialised
        Set custom scene from model
        """
        sceneviewer = self._ui.sceneviewer_widget.getSceneviewer()
        if sceneviewer is not None:
            self._refreshOptions()
            scene = self._model.getScene()
            self._ui.sceneviewer_widget.setScene(scene)
            # self._ui.sceneviewer_widget.setSelectModeAll()
            sceneviewer.setLookatParametersNonSkew([2.0, -2.0, 1.0], [0.0, 0.0, 0.0], [0.0, 0.0, 1.0])
            sceneviewer.setTransparencyMode(sceneviewer.TRANSPARENCY_MODE_SLOW)
            self._autoPerturbLines()
            self._viewAll()

    def _sceneChanged(self):
        sceneviewer = self._ui.sceneviewer_widget.getSceneviewer()
        if sceneviewer is not None:
            if self._have_images:
                self._plane_model.setSceneviewer(sceneviewer)
            scene = self._model.getScene()
            self._ui.sceneviewer_widget.setScene(scene)
            self._autoPerturbLines()

    def _sceneAnimate(self):
        sceneviewer = self._ui.sceneviewer_widget.getSceneviewer()
        if sceneviewer is not None:
            self._model.loadSettings()
            scene = self._model.getScene()
            self._ui.sceneviewer_widget.setScene(scene)
            self._autoPerturbLines()
            self._viewAll()

    def _autoPerturbLines(self):
        """
        Enable scene viewer perturb lines iff solid surfaces are drawn with lines.
        Call whenever lines, surfaces or translucency changes
        """
        sceneviewer = self._ui.sceneviewer_widget.getSceneviewer()
        if sceneviewer is not None:
            #sceneviewer.setPerturbLinesFlag(self._generator_model.needPerturbLines())
            pass

    def _makeConnections(self):
        self._ui.sceneviewer_widget.graphicsInitialized.connect(self._graphicsInitialized)
        self._ui.done_button.clicked.connect(self._doneButtonClicked)
        self._ui.viewAll_button.clicked.connect(self._viewAll)
        self._ui.timeValue_doubleSpinBox.valueChanged.connect(self._timeValueChanged)
        self._ui.timePlayStop_pushButton.clicked.connect(self._timePlayStopClicked)
        self._ui.frameIndex_spinBox.valueChanged.connect(self._frameIndexValueChanged)
        self._ui.framesPerSecond_spinBox.valueChanged.connect(self._framesPerSecondValueChanged)
        self._ui.timeLoop_checkBox.clicked.connect(self._timeLoopClicked)
        self._ui.pushButton.clicked.connect(self._exportWebGLJson)
        self._ui.addProfile_pushButton.clicked.connect(self._addProfileClicked)
        self._ui.blackfynnDatasets_pushButton.clicked.connect(self._downloadDatasetsClicked)
        self._ui.blackfynnTimeSeries_pushButton.clicked.connect(self._downloadTimeSeriesClicked)
        self._ui.blackfynnDatasets_comboBox.currentIndexChanged.connect(self._blackfynnDatasetsChanged)
        self._ui.downloadData_button.clicked.connect(self._downloadBlackfynnData)
        # self._ui.UploadToBlackfynn_button.clicked.connect(self._exportWebGLJsonToBlackfynn)
        self._ui.viewVideo_button.clicked.connect(self._playVideo)
        self._ui.adjustData_Slider.valueChanged.connect(self._adjustData)
        self._ui.tessellation_spinBox.valueChanged.connect(self._setTesselation)

    def _createFMAItem(self, parent, text, fma_id):
        item = QtGui.QTreeWidgetItem(parent)
        item.setText(0, text)
        item.setData(0, QtCore.Qt.UserRole + 1, fma_id)
        item.setCheckState(0, QtCore.Qt.Unchecked)
        item.setFlags(QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsTristate)

        return item

    def getModel(self):
        return self._model

    def registerDoneExecution(self, doneCallback):
        self._doneCallback = doneCallback

    def _updateUi(self):
        pass

    def _doneButtonClicked(self):
        self._ui.dockWidget.setFloating(False)
        self._model.done()
        self._model = None
        self._doneCallback()


    def _updateTimeValue(self, value):
        self._ui.timeValue_doubleSpinBox.blockSignals(True)
        max_time_value = self._model.video.videoLength
        self.time = self._model._current_time

        if value > max_time_value:
            self._ui.timeValue_doubleSpinBox.setValue(max_time_value)
            self._timePlayStopClicked()
        else:
            self._ui.timeValue_doubleSpinBox.setValue(value)
            if self.plot.line is not None:
                self.plot.line.setValue(round(value, 3)) # adjust time marker

        self._ui.timeValue_doubleSpinBox.blockSignals(False)

    def initialiseSpectrum(self, data):
        # initialiseSpectrum modifies the scale of the spectrum to match a set of data

        maximum = -1000000
        minimum = 1000000
        for key in data['cache']:
            array_max = max(data['cache'][key])
            array_min = min(data['cache'][key])
            maximum = max(array_max, maximum)
            minimum = min(array_min, minimum)
        scene = self._model._region.findChildByName('ecg_plane').getScene()
        specMod = scene.getSpectrummodule()
        spectrum = specMod.findSpectrumByName('eegColourSpectrum2')
        spectrum_component = spectrum.getFirstSpectrumcomponent()
        spectrum_component.setRangeMaximum(maximum)
        spectrum_component.setRangeMinimum(minimum)

    def _renderECGMesh(self):

        self._electrode_mesh = BlackfynnMesh(self._model.get_region(), self._node_coordinates_data)

        if self.data:

            # prepare data
            self.initialiseSpectrum(self.data)
            ecg_mmatrix = []
            for key in self.data['cache']:
                if 'time' not in key:
                    # note that we downsample the data to get it to fit on web portal
                    ecg_mmatrix.append(self.data['cache'][key][0::24])
            for i in range(len(ecg_mmatrix)):
                ecg_mmatrix[i].append(ecg_mmatrix[i][-1])


            # pass the created data dictionaries to the mesh model
            self._electrode_mesh.set_data_time_sequence(self._time_sequence)
            self._electrode_mesh.set_data(ecg_mmatrix)

        self._electrode_mesh.generate_mesh()
        self._electrode_mesh.drawMesh()
        self._electrode_mesh.initialiseSpectrumFromDictionary(self.data['cache'])
        self._ui.sceneviewer_widget.setModel(self._electrode_mesh)

    def _setTesselation(self):
        self._model.setTessellation(self._ui.tessellation_spinBox.value())

    def _updateFrameIndex(self, value):
        self._ui.frameIndex_spinBox.blockSignals(True)
        self._ui.frameIndex_spinBox.setValue(value)
        self._ui.frameIndex_spinBox.blockSignals(False)

    def _timeValueChanged(self, value):
        self._model.setTimeValue(value)

    def _timeDurationChanged(self, value):
        self._model.setTimeDuration(value)

    def _timePlayStopClicked(self):
        play_text = 'Play'
        stop_text = 'Stop'
        current_text = self._ui.timePlayStop_pushButton.text()
        if current_text == play_text:
            self._ui.timePlayStop_pushButton.setText(stop_text)
            self._model.play()
        else:
            self._ui.timePlayStop_pushButton.setText(play_text)
            self._model.stop()

    def _timeLoopClicked(self):
        self._model.setTimeLoop(self._ui.timeLoop_checkBox.isChecked())

    def _frameIndexValueChanged(self, value):
        self._model.setFrameIndex(value)

    def _framesPerSecondValueChanged(self, value):
        self._model.setFramesPerSecond(value)
        self._ui.timeValue_doubleSpinBox.setMaximum(self._model.video.numFrames/value)

    def _addProfileClicked(self):
        dlg = AddProfileDialog(self, self._blackfynn_data_model.getExistingProfileNames())

        if dlg.exec_():
            profile = dlg.profile()
            self._blackfynn_data_model.addProfile(profile)
            self._refreshBlackfynnOptions()

    @set_wait_cursor
    def _retrieveDatasets(self):
        return self._blackfynn_data_model.getDatasets(self._ui.profiles_comboBox.currentText(), refresh=True)

    def _downloadDatasetsClicked(self):
        datasets = self._retrieveDatasets()
        self._ui.blackfynnDatasets_comboBox.clear()
        self._ui.blackfynnDatasets_comboBox.addItems([ds.name for ds in datasets])
        self._updateBlackfynnUi()

    @set_wait_cursor
    def _retrieveDataset(self):
        return self._blackfynn_data_model.getDataset(self._ui.profiles_comboBox.currentText(),
                                                self._ui.blackfynnDatasets_comboBox.currentText(), refresh=True)

    def _downloadTimeSeriesClicked(self):
        dataset = self._retrieveDataset()
        self._ui.blackfynnTimeSeries_comboBox.clear()
        self._ui.blackfynnTimeSeries_comboBox.addItems([ds.name for ds in dataset])
        self._updateBlackfynnUi()

    def _downloadBlackfynnData(self):
        self.data = {}
        blackfynnOutput = self._blackfynn_data_model.getTimeseriesData(self._ui.profiles_comboBox.currentText(),
                                                        self._ui.blackfynnDatasets_comboBox.currentText(),
                                                        self._ui.blackfynnTimeSeries_comboBox.currentText(),
                                                        self._model.video.videoLength)
        self.data['cache'] = blackfynnOutput[0]
        self.data['times'] = blackfynnOutput[1]
        self.plot = Plot(self.data)
        self._renderECGMesh()

    def _updateBlackfynnUi(self):
        valid_profiles = False
        if self._ui.profiles_comboBox.count() > 0:
            valid_profiles = True

        self._ui.blackfynnDatasets_comboBox.setEnabled(valid_profiles)
        self._ui.blackfynnTimeSeries_comboBox.setEnabled(valid_profiles)

        valid_datasets = False
        if self._ui.blackfynnDatasets_comboBox.count() > 0:
            valid_datasets = True

        self._ui.blackfynnTimeSeries_pushButton.setEnabled(valid_datasets)
        self._ui.blackfynnTimeSeries_pushButton.setEnabled(valid_datasets)

    def _refreshBlackfynnOptions(self):
        self._ui.profiles_comboBox.clear()
        self._ui.profiles_comboBox.addItems(self._blackfynn_data_model.getExistingProfileNames())
        self._updateBlackfynnUi()

    def _blackfynnDatasetsChanged(self, index):
        print(index)

    def _playVideo(self):
        if self.data:
            self._adjustData()
            self._model.video.line = self.plot.line
            self._model.video.datalen = self.plot.datalen
            self._model.video.playVideo()

    def _adjustData(self):
        newOffset = self._ui.adjustData_Slider.value()/100
        self.plot.adjustData(newOffset)
        self._model.video.line = self.plot.line
        self.data = self.plot.data

    def _refreshOptions(self):
        self._ui.framesPerSecond_spinBox.setValue(self._model.getFramesPerSecond())
        self._ui.timeLoop_checkBox.setChecked(self._model.isTimeLoop())
        self._refreshBlackfynnOptions()

    def _exportDataJson(self):
        export_data = {'values': {}}
        for key in self.data['cache']:
            export_data['values'][key] = self.data['cache'][key]
        export_data['times'] = self.data['times']
        with open('ecgDataFull.json', 'w') as fp:
            json.dump(export_data, fp)

    def _exportWebGLJson(self):
        """
        Export graphics into JSON formats. Returns an array containing the
        string buffers for each export
        """

        try:
            self.data

            # Scale down our data (every 10th value) for exporting
            ECGmatrix = []
            for key in self.data['cache']:
                ECGmatrix.append(self.data['cache'][key][0::100])
            for i in range(len(ECGmatrix)):
                ECGmatrix[i].append(ECGmatrix[i][-1])
            ECGtimes = np.linspace(self._time_sequence[0], self._time_sequence[-1], len(ECGmatrix[:][0]))

            # Set up our scene resource
            ecg_region = self._model._region.findChildByName('ecg_plane')
            scene = ecg_region.getScene()
            sceneSR = scene.createStreaminformationScene()
            sceneSR.setIOFormat(sceneSR.IO_FORMAT_THREEJS)
            sceneSR.setInitialTime(ECGtimes[0])
            sceneSR.setFinishTime(ECGtimes[-1])
            sceneSR.setNumberOfTimeSteps(len(ECGtimes))
            sceneSR.setOutputTimeDependentColours(1)
            sceneSR.setOutputTimeDependentVertices(1)

            # Get the total number of graphics in a scene/region that can be exported
            number = sceneSR.getNumberOfResourcesRequired()
            resources = []
            # Write out each graphics into a json file which can be rendered with our
            # WebGL script
            for i in range(number):
                resources.append(sceneSR.createStreamresourceMemory())
            scene.write(sceneSR)

            # Store all the resources in a buffer
            buffer = [resources[i].getBuffer()[1] for i in range(number)]

            mpbPath = self._export_directory

            # Write the files to directories for the MPB to read.
            # Find it at https://github.com/Tehsurfer/MPB
            heartPath = mpbPath
            htmlIndexPath = mpbPath + '\simple_heart\\index.html'
            for i, content in enumerate(buffer):
                if content is None:
                    break
                if (i + 1) is 4:
                    f2 = open(heartPath + 'picking_node_2.json', 'w')
                    f2.write(content)
                    f2.close()
                if (i + 1) is 2:
                    f2 = open(heartPath + 'ecgAnimation.json', 'w')
                    f2.write(content)
                    f2.close()
                if (i + 1) is 3:
                    f2 = open(heartPath + 'picking_node_3.json', 'w')
                    f2.write(content)
                    f2.close()
                f = open(heartPath + '\webGLExport'+ str(i+1) + '.json', 'w') # for debugging
                f.write(content)
            webbrowser.open(htmlIndexPath)
        except:
            pass

    def _exportWebGLJsonToBlackfynn(self):
        '''
        exportWebGLJsonToBlackfynn: Using the logged in Blackfynn user we upload all of the needed files for rendering
            the current model
            '''

        try:
            mpbPath = self._export_directory

            # Write the files to directories for the MPB to read.
            # Find it at https://github.com/Tehsurfer/MPB
            heartPath = mpbPath + '\simple_heart\models\organsViewerModels\cardiovascular\heart\\'
            htmlIndexPath = mpbPath + '\simple_heart\\index.html'

            self._blackfynn_data_model.uploadRender(heartPath + 'picking_node_2.json')
            self._blackfynn_data_model.uploadRender(heartPath + 'ecgAnimation.json')

        except:
            pass


    def _annotationItemChanged(self, item):
        print(item.text(0))
        print(item.data(0, QtCore.Qt.UserRole + 1))

    def _viewAll(self):
        """
        Ask sceneviewer to show all of scene.
        """
        if self._ui.sceneviewer_widget.getSceneviewer() is not None:
            self._ui.sceneviewer_widget.viewAll()

    def keyPressEvent(self, event):
        if event.modifiers() & QtCore.Qt.CTRL and QtGui.QApplication.mouseButtons() == QtCore.Qt.NoButton:
            self._marker_mode_active = True

            self._ui.sceneviewer_widget._calculatePointOnPlane = types.MethodType(_calculatePointOnPlane, self._ui.sceneviewer_widget)
            self._ui.sceneviewer_widget.mousePressEvent = types.MethodType(mousePressEvent, self._ui.sceneviewer_widget)
            self._model.printLog()

    def keyReleaseEvent(self, event):
        if self._marker_mode_active:
            self._marker_mode_active = False
            self._ui.sceneviewer_widget._calculatePointOnPlane = None
            self._ui.sceneviewer_widget.mousePressEvent = self._original_mousePressEvent


def mousePressEvent(self, event):
    if self._active_button != QtCore.Qt.NoButton:
        return

    if (event.modifiers() & QtCore.Qt.CTRL) and event.button() == QtCore.Qt.LeftButton:
        point_on_plane = self._calculatePointOnPlane(event.x(), event.y())
        print('Location of click (x,y): (' + str(event.x()) + ', ' + str(event.y()) +')')
        node = self.getNearestNode(event.x(), event.y())
        if node.isValid():
            print('node {0} was clicked'.format(node.getIdentifier()))
            self.foundNode = True
            self.nodeKey = node.getIdentifier()
            self.node = node
            self.grid = []

        # return sceneviewers 'mouspressevent' function to its version for navigation
        self._calculatePointOnPlane = None
        self.mousePressEvent = self.original_mousePressEvent

    return [event.x(), event.y()]


def _calculatePointOnPlane(self, x, y):
    from opencmiss.utils.maths.algorithms import calculateLinePlaneIntersection

    far_plane_point = self.unproject(x, -y, -1.0)
    near_plane_point = self.unproject(x, -y, 1.0)
    plane_point, plane_offset, plane_normal = self._model.getPlaneDescription()
    point_on_plane = calculateLinePlaneIntersection(near_plane_point, far_plane_point, plane_point, plane_normal)
    # if len(self.grid) < 4:
    #     self.grid.append(point_on_plane)
    # else:
    #     self.grid = []
    #     self.grid.append(point_on_plane)
    return point_on_plane
