"""
Created on Aug 29, 2017

@author: Richard Christie
"""


import types


from PySide import QtGui, QtCore
from functools import partial
import webbrowser, os

from mapclient.view.utils import set_wait_cursor
from mapclientplugins.ecgstep.view.ecg_ui import Ui_MeshGeneratorWidget
from mapclientplugins.ecgstep.view.addprofile import AddProfileDialog
from mapclientplugins.ecgstep.model.blackfynnMesh import Blackfynn_2d_plate
from mapclientplugins.ecgstep.blackfynn_wrapper_package.threeWrapper import BlackfynnGet
from mapclientplugins.ecgstep.model.constants import NUMBER_OF_FRAMES

from opencmiss.zinc.node import Node

from opencmiss.utils.maths import vectorops
import time

# imports added for pop up graph
import pyqtgraph as pg

import numpy as np

class MeshGeneratorWidget(QtGui.QWidget):

    def __init__(self, model, parent=None, port_data=[]):
        super(MeshGeneratorWidget, self).__init__(parent)
        self._ui = Ui_MeshGeneratorWidget()

        self._generator_model = model.getGeneratorModel()
        self._model = model
        self._model.registerTimeValueUpdateCallback(self._updateTimeValue)
        self._model.registerFrameIndexUpdateCallback(self._updateFrameIndex)

        self._ui.setupUi(self)
        self._doneCallback = None
        self._marker_mode_active = False
        self._have_images = False
        self.x = 0
        self.y = 0
        self.time = 0
        self.pw = None
        self.node_coordinate_list = port_data


        self.blackfynn = BlackfynnGet()
        self._blackfynn_data_model = model.getBlackfynnDataModel()
        self._ui.sceneviewer_widget.setContext(model.getContext())
        self._ui.sceneviewer_widget.setModel(self._generator_model)
        self._ui.sceneviewer_widget.initializeGL()
        self._generator_model.enableAlignment()
        self._generator_model.setStateAlign(state=True)
        self._makeConnections()


    def _graphicsInitialized(self):
        """
        Callback for when SceneviewerWidget is initialised
        Set custom scene from model
        """
        sceneviewer = self._ui.sceneviewer_widget.getSceneviewer()
        if sceneviewer is not None:
            self._model.loadSettings()
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
            sceneviewer.setPerturbLinesFlag(self._generator_model.needPerturbLines())

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
        # self._ui.submitButton.clicked.connect(self._submitClicked)
        # self._ui.treeWidgetAnnotation.itemSelectionChanged.connect(self._annotationSelectionChanged)
        # self._ui.treeWidgetAnnotation.itemChanged.connect(self._annotationItemChanged)

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
        if self._have_images:
            frame_count = NUMBER_OF_FRAMES
            self._ui.numFramesValue_label.setText("{0}".format(frame_count))
            self._ui.frameIndex_spinBox.setMaximum(frame_count)
            self._ui.timeValue_doubleSpinBox.setMaximum(frame_count / self._model.getFramesPerSecond())
        else:
            self._generator_model.disableAlignment()
            self._plane_model.disableAlignment()
            self._ui.alignment_groupBox.setVisible(False)
            self._ui.fiducialMarkers_groupBox.setVisible(False)
            self._ui.video_groupBox.setVisible(False)
            self._ui.displayImagePlane_checkBox.setVisible(False)
            self._ui.displayFiducialMarkers_checkBox.setVisible(False)

    def setImageInfo(self, image_info):
        self._plane_model.setImageInfo(image_info)
        self._have_images = image_info is not None
        self._updateUi()

    def _doneButtonClicked(self):
        self._ui.dockWidget.setFloating(False)
        self._model.done()
        self._model = None
        self._doneCallback()


    def _updateTimeValue(self, value):
        self._ui.timeValue_doubleSpinBox.blockSignals(True)
        max_time_value = NUMBER_OF_FRAMES / self._ui.framesPerSecond_spinBox.value()
        self.time = self._model._current_time

        if value > max_time_value:
            self._ui.timeValue_doubleSpinBox.setValue(max_time_value)
            self._timePlayStopClicked()
        else:
            self._ui.timeValue_doubleSpinBox.setValue(value)
            if self.pw is not None:
                self.line.setValue(round(value, 3)) # adjust time marker
            # if self._ui.displayEEGAnimation_checkBox.isChecked() and self.data is not False:
            #     pass
                # use model to update colours
                #self.updateAllNodes(value)
            #self.updatePlate(value)
        self._ui.timeValue_doubleSpinBox.blockSignals(False)

    def scaleCacheData(self):
        tempDict = {}
        for i, key in enumerate(self.data['cache']):
            tempDict[str(i)] = self.scaleData(key)
        self.data['scaled'] = tempDict

    def scaleData(self, key):
        numFrames = NUMBER_OF_FRAMES
        y = np.array(self.data['cache'][key])
        x = np.linspace(0, 16, len(y))
        xterp = np.linspace(0, 16, numFrames)
        yterp = np.interp(xterp, x, y)
        return yterp

    def initialiseSpectrum(self, data):
        maximum = -1000000
        minimum = 1000000
        for key in data['cache']:
            array_max = max(data['cache'][key])
            array_min = min(data['cache'][key])
            maximum = max(array_max, maximum)
            minimum = min(array_min, minimum)
        scene = self._generator_model._region.findChildByName('ecg_plane').getScene()
        specMod = scene.getSpectrummodule()
        spectrum = specMod.findSpectrumByName('eegColourSpectrum2')
        spectrum_component = spectrum.getFirstSpectrumcomponent()
        spectrum_component.setRangeMaximum(maximum)
        spectrum_component.setRangeMinimum(minimum)

    def _renderECGMesh(self):

        pm = Blackfynn_2d_plate(self._generator_model._region, self.node_coordinate_list)

        if self.data:
            # prepare data
            self.scaleCacheData()
            self.initialiseSpectrum(self.data)
            ECGmatrix = []
            for key in self.data['cache']:
                ECGmatrix.append(self.data['cache'][key][0::10])
            for i in range(len(ECGmatrix)):
                ECGmatrix[i].append(ECGmatrix[i][-1])
            ECGtimes = np.linspace(0, 1, len(ECGmatrix[:][0]))
            pm.ECGtimes = ECGtimes.tolist()
            pm.ECGcoloursMatrix = ECGmatrix

            self._generator_model.initialiseSpectrumFromDictionary(self.data['cache'])

        pm.generateMesh()
        pm.drawMesh()



    def currentFrame(self, value):
        frame_vals = np.linspace(0, 16, NUMBER_OF_FRAMES)
        currentFrame = (np.abs(frame_vals - value)).argmin()
        return currentFrame

    def find_nearest(array, value):
        # fin_nearets() Find the index of the nearest value in an array
        idx = np.searchsorted(array, value, side="left")
        if idx > 0 and (idx == len(array) or math.fabs(value - array[idx - 1]) < math.fabs(value - array[idx])):
            return array[idx - 1]
        else:
            return array[idx]

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
        self._ui.timeValue_doubleSpinBox.setMaximum(NUMBER_OF_FRAMES/value)

    def _fixImagePlaneClicked(self):
        self._plane_model.setImagePlaneFixed(self._ui.fixImagePlane_checkBox.isChecked())

    def _submitClicked(self):
    # submitClicked initialises all the blackfynn functionality and updates login fields.
        if self._ui.api_key.displayText() != 'API Key' and self._ui.api_secret.text() != '***************************':
            self.pw = pg.plot(title='Blackfynn electrode graph',
                              labels={'left': f'EEG value of node', 'bottom': 'time in seconds'})
            self._ui.Login_groupBox.setTitle(QtGui.QApplication.translate("MeshGeneratorWidget", "Login details saved, click on a node to open graphs", None,
                                                                       QtGui.QApplication.UnicodeUTF8))
            self.initialiseBlackfynnData()
            self._ui.api_secret.setText('***************************')
            self.blackfynn.loaded = True


    def initialiseBlackfynnData(self):
        # self.blackfynn.api_key = self._ui.api_key.text()  <- commented so that we do not have to enter key each time
        # self.blackfynn.api_secret = self._ui.api_secret.text()
        self.blackfynn.set_api_key_login()
        self.blackfynn.set_params(channels='LG4', window_from_start=16) # need to add dataset selection
        self.data = self.blackfynn.get()
        self.updatePlot(4)
        self.scaleCacheData()
        self.initialiseSpectrum(self.data)

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
        self.data['cache'] = self._blackfynn_data_model.getTimeseriesData(self._ui.profiles_comboBox.currentText(),
                                                        self._ui.blackfynnDatasets_comboBox.currentText(),
                                                        self._ui.blackfynnTimeSeries_comboBox.currentText())
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

    def updatePlot(self, key):

        try:
            self.data['cache'][f'LG{key}']
        except KeyError:
            print('ERROR: selected data could not be found')
            self.pw.plot(title='Error in data collection')
            return
        self.pw.clear()

        self.pw.plot(self.data['x'],
                     self.data['cache'][f'LG{key}'],
                     pen='b',
                     title=f'EEG values from {key} LG{key}',
                     )
        self.pw.setTitle(f'EEG values from {key} (LG{key})')
        self.line = self.pw.addLine(x=self.time,
                                    pen='r')  # show current time


    def _displayImagePlaneClicked(self):
        self._plane_model.setImagePlaneVisible(self._ui.displayImagePlane_checkBox.isChecked())

    def _meshTypeChanged(self, index):
        meshTypeName = self._ui.meshType_comboBox.itemText(index)
        self._generator_model.setMeshTypeByName(meshTypeName)
        self._refreshMeshTypeOptions()
        #self._ecg_graphics.createGraphics()

    def _meshTypeOptionCheckBoxClicked(self, checkBox):
        self._generator_model.setMeshTypeOption(checkBox.objectName(), checkBox.isChecked())

    def _meshTypeOptionLineEditChanged(self, lineEdit):
        self._generator_model.setMeshTypeOption(lineEdit.objectName(), lineEdit.text())
        finalValue = self._generator_model.getMeshTypeOption(lineEdit.objectName())
        lineEdit.setText(str(finalValue))

    def _refreshMeshTypeOptions(self):
        pass

    def _refreshOptions(self):
        self._ui.framesPerSecond_spinBox.setValue(self._model.getFramesPerSecond())
        self._ui.timeLoop_checkBox.setChecked(self._model.isTimeLoop())
        self._refreshBlackfynnOptions()
        self._refreshMeshTypeOptions()

    def _deleteElementRangesLineEditChanged(self):
        self._generator_model.setDeleteElementsRangesText(self._ui.deleteElementsRanges_lineEdit.text())
        self._ui.deleteElementsRanges_lineEdit.setText(self._generator_model.getDeleteElementsRangesText())

    def _scaleLineEditChanged(self):
        self._generator_model.setScaleText(self._ui.scale_lineEdit.text())
        self._ui.scale_lineEdit.setText(self._generator_model.getScaleText())

    def converNodesToMesh(self):
        self._generator_model.setDisplayAxes(self._ui.displayAxes_checkBox.isChecked())
        # for testing, we delete our ecg nodes and reload the entire mesh
        self._ecg_graphics.deleteAll()
        self._meshTypeChanged(9)
        self._meshTypeChanged(10)

        # prepare data
        self.scaleCacheData()
        self._ecg_graphics.initialiseSpectrum(self.data)
        ECGmatrix = []
        for key in self.data['cache']:
            ECGmatrix.append(self.data['cache'][key][0::10])
        for i in range(len(ECGmatrix)):
            ECGmatrix[i].append(ECGmatrix[i][-1])
        ECGtimes = np.linspace(0, 1, len(ECGmatrix[:][0]))

        # clear all of the current mesh data by going to a mesh with nothing in it
        self._generator_model.deleteAll()
        # self._meshTypeChanged(3)

        # create our new mesh with the Blackfynn_2d_plate class
        pm = Blackfynn_2d_plate(self._generator_model._region, self._ecg_graphics.node_coordinate_list)
        pm.ECGtimes = ECGtimes.tolist()
        pm.ECGcoloursMatrix = ECGmatrix
        pm.generateMesh()
        pm.drawMesh()


    def _exportWebGLJson(self):
        '''
            Export graphics into JSON formats. Returns an array containing the
       string buffers for each export
            '''

        try:
            self.data
            ECGmatrix = []
            for key in self.data['cache']:
                ECGmatrix.append(self.data['cache'][key][0::10])
            for i in range(len(ECGmatrix)):
                ECGmatrix[i].append(ECGmatrix[i][-1])
            ECGtimes = np.linspace(0, 1, len(ECGmatrix[:][0]))

            ecg_region = self._generator_model._region.findChildByName('ecg_plane')
            scene = ecg_region.getScene()
            sceneSR = scene.createStreaminformationScene()
            sceneSR.setIOFormat(sceneSR.IO_FORMAT_THREEJS)
            sceneSR.setInitialTime(ECGtimes[0])
            sceneSR.setFinishTime(ECGtimes[-1])
            sceneSR.setNumberOfTimeSteps(len(ECGtimes))
            sceneSR.setOutputTimeDependentColours(1)

            # Get the total number of graphics in a scene/region that can be exported
            number = sceneSR.getNumberOfResourcesRequired()
            resources = []
            # Write out each graphics into a json file which can be rendered with our
            # WebGL script
            for i in range(number):
                resources.append(sceneSR.createStreamresourceMemory())
            scene.write(sceneSR)
            # Write out each resource into their own file

            buffer = [resources[i].getBuffer()[1] for i in range(number)]

            mpbPath = self._ui.exportDirectory_lineEdit.text()

            heartPath = mpbPath + '\simple_heart\models\organsViewerModels\cardiovascular\heart\\'
            htmlIndexPath = mpbPath + '\simple_heart\\index.html'
            for i, content in enumerate(buffer):
                if content is None:
                    break
                if (i + 1) is 2:
                    f2 = open(heartPath + 'picking_node_2.json', 'w')
                    f2.write(content)
                    f2.close()
                if (i + 1) is 3:
                    f2 = open(heartPath + 'picking_node_3.json', 'w')
                    f2.write(content)
                    f2.close()
                if (i + 1) is 4:
                    f2 = open(heartPath + 'ecgAnimation.json', 'w')
                    f2.write(content)
                    f2.close()
                f = open(f'webGLExport{i+1}.json', 'w')
                f.write(content)
            webbrowser.open(htmlIndexPath)
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
            self._ui.sceneviewer_widget._model = self._fiducial_marker_model
            self._original_mousePressEvent = self._ui.sceneviewer_widget.mousePressEvent
            self._ui.sceneviewer_widget.original_mousePressEvent = self._ui.sceneviewer_widget.mousePressEvent
            self._ui.sceneviewer_widget.plane_model_temp = self._plane_model

            self._ui.sceneviewer_widget._calculatePointOnPlane = types.MethodType(_calculatePointOnPlane, self._ui.sceneviewer_widget)
            self._ui.sceneviewer_widget.mousePressEvent = types.MethodType(mousePressEvent, self._ui.sceneviewer_widget)
            #self._ui.sceneviewer_widget.foundNode = False
            self._model.printLog()

    def keyReleaseEvent(self, event):
        if self._marker_mode_active:
            self._marker_mode_active = False
            self._ui.sceneviewer_widget._model = self._plane_model
            self._ui.sceneviewer_widget._calculatePointOnPlane = None
            self._ui.sceneviewer_widget.mousePressEvent = self._original_mousePressEvent
            if self._ui.sceneviewer_widget.foundNode and len(self._ui.sceneviewer_widget.grid) is 2:
                self.updatePlot(self._ui.sceneviewer_widget.nodeKey) # updates plot if a node is clicked
                if self._ui.sceneviewer_widget.nodeKey in self._ecg_graphics.node_corner_list:
                    self._ecg_graphics.updateGrid(self._ui.sceneviewer_widget.nodeKey,  self._ui.sceneviewer_widget.grid[1])
                self._ui.sceneviewer_widget.foundNode = False




def mousePressEvent(self, event):
    if self._active_button != QtCore.Qt.NoButton:
        return

    if (event.modifiers() & QtCore.Qt.CTRL) and event.button() == QtCore.Qt.LeftButton:
        point_on_plane = self._calculatePointOnPlane(event.x(), event.y())
        print('Location of click (x,y): (' + str(event.x()) + ', ' + str(event.y()) +')')
        node = self.getNearestNode(event.x(), event.y())
        if node.isValid():
            print(f'node {node.getIdentifier()} was clicked')
            self.foundNode = True
            self.nodeKey = node.getIdentifier()
            self.node = node
            self.grid = []
        # return sceneviewers 'mouspressevent' function to its version for navigation

        self._model = self.plane_model_temp
        self._calculatePointOnPlane = None
        self.mousePressEvent = self.original_mousePressEvent

        if len(self.grid) > 2 and self.foundNode:
            self.grid = []
            self.foundNode = False
        self.grid.append(point_on_plane)

        if len(self.grid) > 4:
            self.grid = []

    return [event.x(), event.y()]




def _calculatePointOnPlane(self, x, y):
    from opencmiss.utils.maths.algorithms import calculateLinePlaneIntersection

    far_plane_point = self.unproject(x, -y, -1.0)
    near_plane_point = self.unproject(x, -y, 1.0)
    plane_point, plane_normal = self._model.getPlaneDescription()
    point_on_plane = calculateLinePlaneIntersection(near_plane_point, far_plane_point, plane_point, plane_normal)
    self.plane_normal = plane_normal
    print(point_on_plane)
    print(f'normal: {plane_normal}')
    return point_on_plane


