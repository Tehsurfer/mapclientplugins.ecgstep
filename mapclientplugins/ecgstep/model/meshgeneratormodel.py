"""
Created on 9 Mar, 2018 from mapclientplugins.meshgeneratorstep.

@author: Richard Christie
"""

import string

from opencmiss.zinc.field import Field
from opencmiss.zinc.glyph import Glyph
from opencmiss.zinc.graphics import Graphics
from opencmiss.zinc.node import Node
from scaffoldmaker.scaffoldmaker import Scaffoldmaker
from scaffoldmaker.utils.zinc_utils import *
import numpy as np

from mapclientplugins.ecgstep.model.meshalignmentmodel import MeshAlignmentModel

STRING_FLOAT_FORMAT = '{:.8g}'


class MeshGeneratorModel(MeshAlignmentModel):
    """
    Framework for generating meshes of a number of types, with mesh type specific options
    """

    def __init__(self, region, material_module):
        super(MeshGeneratorModel, self).__init__()
        self._region_name = "generated_mesh"
        self._parent_region = region
        self._materialmodule = material_module
        self._region = None
        self._sceneChangeCallback = None
        self._deleteElementRanges = []
        self._scale = [ 1.0, 1.0, 1.0 ]
        self._settings = {
            'meshTypeName' : '',
            'meshTypeOptions' : { },
            'deleteElementRanges' : '',
            'scale' : '*'.join(STRING_FLOAT_FORMAT.format(value) for value in self._scale),
            'displayAxes' : True,
            'displayElementNumbers' : True,
            'displayLines' : True,
            'displayNodeDerivatives' : False,
            'displayNodeNumbers' : True,
            'displaySurfaces' : True,
            'displaySurfacesExterior' : True,
            'displaySurfacesTranslucent' : True,
            'displaySurfacesWireframe' : False,
            'displayXiAxes' : False
        }
        self._discoverAllMeshTypes()


    def getRegion(self):
        return self._region

    def _discoverAllMeshTypes(self):
        scaffoldmaker = Scaffoldmaker()
        self._meshTypes = scaffoldmaker.getMeshTypes()
        self._currentMeshType = scaffoldmaker.getDefaultMeshType()
        self._settings['meshTypeName'] = self._currentMeshType.getName()
        self._settings['meshTypeOptions'] = self._currentMeshType.getDefaultOptions()

    def getAllMeshTypeNames(self):
        meshTypeNames = []
        for meshType in self._meshTypes:
            meshTypeNames.append(meshType.getName())
        return meshTypeNames

    def getMeshTypeName(self):
        return self._settings['meshTypeName']

    def _getMeshTypeByName(self, name):
        for meshType in self._meshTypes:
            if meshType.getName() == name:
                return meshType
        return None

    def setMeshTypeByName(self, name):
        meshType = self._getMeshTypeByName(name)
        if meshType is not None:
            if meshType != self._currentMeshType:
                self._currentMeshType = meshType
                self._settings['meshTypeName'] = self._currentMeshType.getName()
                self._settings['meshTypeOptions'] = self._currentMeshType.getDefaultOptions()
                self._generateMesh()

    def getMeshTypeOrderedOptionNames(self):
        return self._currentMeshType.getOrderedOptionNames()

    def registerSceneChangeCallback(self, sceneChangeCallback):
        self._sceneChangeCallback = sceneChangeCallback

    def _getMesh(self):
        fm = self._region.getFieldmodule()
        for dimension in range(3,0,-1):
            mesh = fm.findMeshByDimension(dimension)
            if mesh.getSize() > 0:
                break
        if mesh.getSize() == 0:
            mesh = fm.findMeshByDimension(3)
        return mesh

    def getMeshDimension(self):
        return self._getMesh().getDimension()

    def getSettings(self):
        return self._settings

    def setSettings(self, settings):
        self._settings.update(settings)
        self._currentMeshType = self._getMeshTypeByName(self._settings['meshTypeName'])
        self._generateMesh()

    def needPerturbLines(self):
        """
        Return if solid surfaces are drawn with lines, requiring perturb lines to be activated.
        """
        if self._region is None:
            return False
        mesh2d = self._region.getFieldmodule().findMeshByDimension(2)
        if mesh2d.getSize() == 0:
            return False
        # return self.isDisplayLines() and self.isDisplaySurfaces() and not self.isDisplaySurfacesTranslucent()
        return True
    def _generateMesh(self):
        if self._region:
            self._parent_region.removeChild(self._region)
        self._region = self._parent_region.createChild(self._region_name)
        self._scene = self._region.getScene()
        fm = self._region.getFieldmodule()
        fm.beginChange()
        # logger = self._context.getLogger()
        annotationGroups = self._currentMeshType.generateMesh(self._region, self._settings['meshTypeOptions'])
        # loggerMessageCount = logger.getNumberOfMessages()
        # if loggerMessageCount > 0:
        #     for i in range(1, loggerMessageCount + 1):
        #         print(logger.getMessageTypeAtIndex(i), logger.getMessageTextAtIndex(i))
        #     logger.removeAllMessages()
        mesh = self._getMesh()
        # meshDimension = mesh.getDimension()
        nodes = fm.findNodesetByFieldDomainType(Field.DOMAIN_TYPE_NODES)
        if len(self._deleteElementRanges) > 0:
            deleteElementIdentifiers = []
            elementIter = mesh.createElementiterator()
            element = elementIter.next()
            while element.isValid():
                identifier = element.getIdentifier()
                for deleteElementRange in self._deleteElementRanges:
                    if (identifier >= deleteElementRange[0]) and (identifier <= deleteElementRange[1]):
                        deleteElementIdentifiers.append(identifier)
                element = elementIter.next()
            #print('delete elements ', deleteElementIdentifiers)
            for identifier in deleteElementIdentifiers:
                element = mesh.findElementByIdentifier(identifier)
                mesh.destroyElement(element)
            del element
            # destroy all orphaned nodes
            #size1 = nodes.getSize()
            nodes.destroyAllNodes()
            #size2 = nodes.getSize()
            #print('deleted', size1 - size2, 'nodes')
        fm.defineAllFaces()
        if annotationGroups is not None:
            for annotationGroup in annotationGroups:
                annotationGroup.addSubelements()
        if self._settings['scale'] != '1*1*1':
            coordinates = fm.findFieldByName('coordinates').castFiniteElement()
            scale = fm.createFieldConstant(self._scale)
            newCoordinates = fm.createFieldMultiply(coordinates, scale)
            fieldassignment = coordinates.createFieldassignment(newCoordinates)
            fieldassignment.assign()
            del newCoordinates
            del scale
        fm.endChange()
        self._createGraphics(self._region)
        if self._sceneChangeCallback is not None:
            self._sceneChangeCallback()

        name = mesh.getName()
        print(name)

    def deleteAll(self):
        self._scene = self._region.getScene()
        fm = self._region.getFieldmodule()
        fm.beginChange()
        # logger = self._context.getLogger()
        # annotationGroups = self._currentMeshType.generateMesh(self._region, self._settings['meshTypeOptions'])
        #         # loggerMessageCount = logger.getNumberOfMessages()
        # if loggerMessageCount > 0:
        #     for i in range(1, loggerMessageCount + 1):
        #         print(logger.getMessageTypeAtIndex(i), logger.getMessageTextAtIndex(i))
        #     logger.removeAllMessages()
        mesh = self._getMesh()
        # meshDimension = mesh.getDimension()
        nodes = fm.findNodesetByFieldDomainType(Field.DOMAIN_TYPE_NODES)
        if len(self._deleteElementRanges) > 0:
            deleteElementIdentifiers = []
            elementIter = mesh.createElementiterator()
            element = elementIter.next()
            while element.isValid():
                identifier = element.getIdentifier()
                for deleteElementRange in self._deleteElementRanges:
                    if (identifier >= deleteElementRange[0]) and (identifier <= deleteElementRange[1]):
                        deleteElementIdentifiers.append(identifier)
                element = elementIter.next()
            #print('delete elements ', deleteElementIdentifiers)
            for identifier in deleteElementIdentifiers:
                element = mesh.findElementByIdentifier(identifier)
                mesh.destroyElement(element)
            del element
            # destroy all orphaned nodes
            #size1 = nodes.getSize()
            nodes.destroyAllNodes()
            #size2 = nodes.getSize()
            #print('deleted', size1 - size2, 'nodes')
        fm.defineAllFaces()
        fm.endChange()

    def _createGraphics(self, region):
        # Node numbers are generated here
        fm = region.getFieldmodule()
        meshDimension = self.getMeshDimension()
        coordinates = fm.findFieldByName('coordinates')
        nodeDerivativeFields = [
            fm.createFieldNodeValue(coordinates, Node.VALUE_LABEL_D_DS1, 1),
            fm.createFieldNodeValue(coordinates, Node.VALUE_LABEL_D_DS2, 1),
            fm.createFieldNodeValue(coordinates, Node.VALUE_LABEL_D_DS3, 1),
        ]
        elementDerivativeFields = []
        for d in range(meshDimension):
            elementDerivativeFields.append(fm.createFieldDerivative(coordinates, d + 1))
        elementDerivativesField = fm.createFieldConcatenate(elementDerivativeFields)
        cmiss_number = fm.findFieldByName('cmiss_number')
        # make graphics
        scene = region.getScene()
        scene.beginChange()
        axes = scene.createGraphicsPoints()
        pointattr = axes.getGraphicspointattributes()
        pointattr.setGlyphShapeType(Glyph.SHAPE_TYPE_AXES_XYZ)
        pointattr.setBaseSize([1.0, 1.0, 1.0])
        axes.setMaterial(self._materialmodule.findMaterialByName('grey50'))
        axes.setName('displayAxes')
        axes.setVisibilityFlag(True)
        lines = scene.createGraphicsLines()
        lines.setCoordinateField(coordinates)
        lines.setName('displayLines')
        lines.setVisibilityFlag(True)

        nodeNumbers = scene.createGraphicsPoints()
        nodeNumbers.setFieldDomainType(Field.DOMAIN_TYPE_NODES)
        nodeNumbers.setCoordinateField(coordinates)
        pointattr = nodeNumbers.getGraphicspointattributes()
        pointattr.setLabelField(cmiss_number)
        # pointattr.setGlyphShapeType(Glyph.SHAPE_TYPE_SPHERE)
        # pointattr.setBaseSize([0.02,0.02,0.02])
        nodeNumbers.setVisibilityFlag(True)
        nodeNumbers.setMaterial(self._materialmodule.findMaterialByName('white'))
        nodeNumbers.setName('displayNodeNumbers')

        elementNumbers = scene.createGraphicsPoints()
        elementNumbers.setFieldDomainType(Field.DOMAIN_TYPE_MESH_HIGHEST_DIMENSION)
        elementNumbers.setCoordinateField(coordinates)
        pointattr = elementNumbers.getGraphicspointattributes()
        pointattr.setLabelField(cmiss_number)
        pointattr.setGlyphShapeType(Glyph.SHAPE_TYPE_NONE)
        elementNumbers.setMaterial(self._materialmodule.findMaterialByName('cyan'))
        elementNumbers.setName('displayElementNumbers')
        elementNumbers.setVisibilityFlag(True)
        surfaces = scene.createGraphicsSurfaces()
        surfaces.setCoordinateField(coordinates)
        # surfaces.setExterior(self.isDisplaySurfacesExterior() if (meshDimension == 3) else False)
        surfacesMaterial = self._materialmodule.findMaterialByName('trans_blue')
        surfaces.setMaterial(surfacesMaterial)

        colour = fm.findFieldByName('colour2')
        colour = colour.castFiniteElement()

        # Add Spectrum
        scene = region.getScene()
        spcmod = scene.getSpectrummodule()
        spec = spcmod.getDefaultSpectrum()
        spec.setName('eegColourSpectrum')

        spcc = spec.getFirstSpectrumcomponent()
        spcc.setRangeMaximum(1000)
        spcc.setRangeMinimum(-8000)


        # Set attributes for our mesh
        surfaces.setSpectrum(spec)
        surfaces.setDataField(colour)

        nodeNumbers.setSpectrum(spec)
        nodeNumbers.setDataField(colour)

        surfaces.setName('displaySurfaces')
        surfaces.setVisibilityFlag(True)

        # derivative arrow width is based on shortest non-zero side
        minScale = 1.0
        first = True
        for i in range(coordinates.getNumberOfComponents()):
            absScale = abs(self._scale[i])
            if absScale > 0.0:
                if first or (absScale < minScale):
                    minScale = absScale
                    first = False
        width = 0.01*minScale

        nodeDerivativeMaterialNames = [ 'gold', 'silver', 'green' ]
        for i in range(meshDimension):
            nodeDerivatives = scene.createGraphicsPoints()
            nodeDerivatives.setFieldDomainType(Field.DOMAIN_TYPE_NODES)
            nodeDerivatives.setCoordinateField(coordinates)
            pointattr = nodeDerivatives.getGraphicspointattributes()
            pointattr.setGlyphShapeType(Glyph.SHAPE_TYPE_ARROW_SOLID)
            pointattr.setOrientationScaleField(nodeDerivativeFields[i])
            pointattr.setBaseSize([0.0, width, width])
            pointattr.setScaleFactors([1.0, 0.0, 0.0])
            nodeDerivatives.setMaterial(self._materialmodule.findMaterialByName(nodeDerivativeMaterialNames[i]))
            nodeDerivatives.setName('displayNodeDerivatives')
            nodeDerivatives.setVisibilityFlag(False)

        xiAxes = scene.createGraphicsPoints()
        xiAxes.setFieldDomainType(Field.DOMAIN_TYPE_MESH_HIGHEST_DIMENSION)
        xiAxes.setCoordinateField(coordinates)
        pointattr = xiAxes.getGraphicspointattributes()
        pointattr.setGlyphShapeType(Glyph.SHAPE_TYPE_AXES_123)
        pointattr.setOrientationScaleField(elementDerivativesField)
        if meshDimension == 1:
            pointattr.setBaseSize([0.0, 2*width, 2*width])
            pointattr.setScaleFactors([0.25, 0.0, 0.0])
        elif meshDimension == 2:
            pointattr.setBaseSize([0.0, 0.0, 2*width])
            pointattr.setScaleFactors([0.25, 0.25, 0.0])
        else:
            pointattr.setBaseSize([0.0, 0.0, 0.0])
            pointattr.setScaleFactors([0.25, 0.25, 0.25])
        xiAxes.setMaterial(self._materialmodule.findMaterialByName('yellow'))
        xiAxes.setName('displayXiAxes')
        xiAxes.setVisibilityFlag(False)
        self.applyAlignment()
        scene.endChange()

    def writeModel(self, file_name):
        self._region.writeFile(file_name)
