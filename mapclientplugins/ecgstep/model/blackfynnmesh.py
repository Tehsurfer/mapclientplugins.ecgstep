""" blackfynnMesh.py
blackfynn mesh takes an input of ECG points and renders it to apply our data from Blackfynn to it

This file is modified from 'meshtype_2d_plate1.py' created by Richard Christie.

"""
import numpy as np

from opencmiss.zinc.element import Element, Elementbasis
from opencmiss.zinc.field import Field
from opencmiss.zinc.node import Node
from opencmiss.zinc.glyph import Glyph


class BlackfynnMesh(object):
    """
    BlackfynnMesh is the central point for generating the model for our mesh and drawing it
    """

    def __init__(self, region, node_coordinate_list):
        super(BlackfynnMesh, self).__init__()
        self._mesh_group = []
        self._field_element_group = None
        self._coordinates = None
        self._time_sequence = []

        ecg_region = region.findChildByName('ecg_plane')
        if ecg_region.isValid():
            region.removeChild(ecg_region)

        self._region = region.createChild('ecg_plane')
        self._node_coordinate_list = node_coordinate_list

        # Note that these are normally changed before generating the mesh

    def generate_mesh(self):
        """
        generateMesh: This is where all points, elements, and colour fields relating to them are defined
        """
        coordinateDimensions = 3
        self.number_points = len(self._node_coordinate_list)

        # We currently find the number of elements by taking the square root of the number of given points
        elementsCount1 = int((self.number_points**.5) - 1)
        elementsCount2 = int((self.number_points**.5) - 1)
        useCrossDerivatives = 0

        # Set up our coordinate field
        fm = self._region.getFieldmodule()
        fm.beginChange()
        coordinates = fm.createFieldFiniteElement(coordinateDimensions)
        coordinates.setName('coordinates')
        coordinates.setManaged(True)
        coordinates.setTypeCoordinate(True)
        coordinates.setCoordinateSystemType(Field.COORDINATE_SYSTEM_TYPE_RECTANGULAR_CARTESIAN)
        coordinates.setComponentName(1, 'x')
        coordinates.setComponentName(2, 'y')
        if coordinateDimensions == 3:
            coordinates.setComponentName(3, 'z')

        # Set up our node template
        nodes = fm.findNodesetByFieldDomainType(Field.DOMAIN_TYPE_NODES)
        nodetemplate = nodes.createNodetemplate()
        nodetemplate.defineField(coordinates)
        nodetemplate.setValueNumberOfVersions(coordinates, -1, Node.VALUE_LABEL_VALUE, 1)
        nodetemplate.setValueNumberOfVersions(coordinates, -1, Node.VALUE_LABEL_D_DS1, 1)
        nodetemplate.setValueNumberOfVersions(coordinates, -1, Node.VALUE_LABEL_D_DS2, 1)
        if useCrossDerivatives:
            nodetemplate.setValueNumberOfVersions(coordinates, -1, Node.VALUE_LABEL_D2_DS1DS2, 1)

        mesh = fm.findMeshByDimension(2)

        # Create our mesh subgroup
        fieldGroup = fm.createFieldGroup()
        fieldElementGroup = fieldGroup.createFieldElementGroup(mesh)
        fieldElementGroup.setManaged(True)
        meshGroup = fieldElementGroup.getMeshGroup()

        # Define our interpolation
        bicubicHermiteBasis = fm.createElementbasis(2, Elementbasis.FUNCTION_TYPE_CUBIC_HERMITE)
        bilinearBasis = fm.createElementbasis(2, Elementbasis.FUNCTION_TYPE_LINEAR_LAGRANGE)

        # Set up our element templates
        eft = meshGroup.createElementfieldtemplate(bicubicHermiteBasis)
        eftBilinear = meshGroup.createElementfieldtemplate(bilinearBasis)
        if not useCrossDerivatives:
            for n in range(4):
                eft.setFunctionNumberOfTerms(n*4 + 4, 0)
        elementtemplate = meshGroup.createElementtemplate()
        elementtemplate.setElementShapeType(Element.SHAPE_TYPE_SQUARE)
        result = elementtemplate.defineField(coordinates, -1, eft)

        # Create our spectrum colour field
        colour = fm.createFieldFiniteElement(1)
        colour.setName('colour2')
        colour.setManaged(True)

        # add time support for colour field

        # Create node and element templates for our spectrum colour field
        nodetemplate.defineField(colour)
        nodetemplate.setValueNumberOfVersions(colour, -1, Node.VALUE_LABEL_VALUE, 1)
        result = elementtemplate.defineField(colour, -1, eftBilinear)

        timeSequence = fm.getMatchingTimesequence(self._time_sequence)
        nodetemplate.setTimesequence(colour, timeSequence)

        eegGrid = []
        for coord in self._node_coordinate_list:
            eegGrid.append(coord)

        firstNodeNumber = 1

        # create nodes
        cache = fm.createFieldcache()
        nodeIdentifier = firstNodeNumber
        x = [0.0, 0.0, 0.0]
        dx_ds1 = [0.0, 0.0, 0.0]
        dx_ds2 = [0.0, 0.0, 0.0]
        zero = [0.0, 0.0, 0.0]
        i = 0
        for n2 in range(elementsCount2 + 1):
            for n1 in range(elementsCount1 + 1):

                node = nodes.createNode(nodeIdentifier, nodetemplate)
                cache.setNode(node)

                # Assign the new node its position
                coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_VALUE, 1, eegGrid[i])
                coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_D_DS1, 1, dx_ds1)
                coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_D_DS2, 1, dx_ds2)
                if useCrossDerivatives:
                    coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_D2_DS1DS2, 1, zero)

                # Assign the new node its colour for each time step
                for j, time in enumerate(self._time_sequence):
                    cache.setTime(time)
                    colour_value = self.ECGcoloursMatrix[i % len(self.ECGcoloursMatrix)][j]
                    colour.setNodeParameters(cache, -1, Node.VALUE_LABEL_VALUE, 1, colour_value)

                nodeIdentifier = nodeIdentifier + 1
                i += 1

        # create elements
        elementIdentifier = firstNodeNumber
        no2 = (elementsCount1 + 1)
        for e2 in range(elementsCount2):
            for e1 in range(elementsCount1):
                element = meshGroup.createElement(elementIdentifier, elementtemplate)
                bni = e2 * no2 + e1 + firstNodeNumber
                nodeIdentifiers = [bni, bni + 1, bni + no2, bni + no2 + 1]
                result = element.setNodesByIdentifier(eft, nodeIdentifiers)
                result = element.setNodesByIdentifier(eftBilinear, nodeIdentifiers)
                elementIdentifier = elementIdentifier + 1

        # Set fields for later access
        self._mesh_group = meshGroup
        self._field_element_group = fieldElementGroup
        self._coordinates = coordinates

        fm.endChange()

    def drawMesh(self):

        scene = self._region.getScene()
        fm = self._region.getFieldmodule()

        coordinates = self._coordinates
        coordinates = coordinates.castFiniteElement()

        materialModule = scene.getMaterialmodule()

        lines = scene.createGraphicsLines()
        lines.setCoordinateField(coordinates)
        lines.setName('displayLines2')
        lines.setMaterial(materialModule.findMaterialByName('blue'))

        nodePoints = scene.createGraphicsPoints()
        nodePoints.setFieldDomainType(Field.DOMAIN_TYPE_NODES)
        nodePoints.setCoordinateField(coordinates)
        nodePoints.setMaterial(materialModule.findMaterialByName('blue'))
        nodePoints.setVisibilityFlag(True)

        nodePointAttr = nodePoints.getGraphicspointattributes()
        nodePointAttr.setGlyphShapeType(Glyph.SHAPE_TYPE_SPHERE)
        nodePointAttr.setBaseSize([.02, .02, .02])
        cmiss_number = fm.findFieldByName('cmiss_number')
        nodePointAttr.setLabelField(cmiss_number)

        surfaces = scene.createGraphicsSurfaces()
        surfaces.setCoordinateField(coordinates)
        surfaces.setVisibilityFlag(True)

        colour = fm.findFieldByName('colour2')
        colour = colour.castFiniteElement()

        # Add Spectrum
        spcmod = scene.getSpectrummodule()
        spec = spcmod.getDefaultSpectrum()
        spec.setName('eegColourSpectrum')
        spcc = spec.getFirstSpectrumcomponent()

        spcc.setRangeMaximum(1)
        spcc.setRangeMinimum(0)
        self._spectrum_component = spcc

        # Set attributes for our mesh
        surfaces.setSpectrum(spec)
        surfaces.setDataField(colour)
        nodePoints.setSpectrum(spec)
        nodePoints.setDataField(colour)

        # # Add a colour bar for the spectrum
        # nodes = fm.findNodesetByFieldDomainType(Field.DOMAIN_TYPE_NODES)
        # cache = fm.createFieldcache()
        # check = nodes.findNodeByIdentifier(1000)
        # if not check.isValid():
        #     screen_coords = fm.createFieldFiniteElement(2)
        #     spectrum_template = nodes.createNodetemplate()
        #     spectrum_template.defineField(screen_coords)
        #     spectrum_node = nodes.createNode(1000, spectrum_template)
        #     cache.setNode(spectrum_node)
        #     screen_coords.setNodeParameters(cache, -1, Node.VALUE_LABEL_VALUE, 1, [-.95, -.78])
        #     fng = fm.createFieldNodeGroup(nodes)
        #     spectrum_group = fng.getNodesetGroup()
        #     spectrum_group.addNode(spectrum_node)
        #
        #     spectrum_graphics = scene.createGraphicsPoints()
        #     spectrum_graphics.setScenecoordinatesystem(
        #         Scenecoordinatesystem.SCENECOORDINATESYSTEM_NORMALISED_WINDOW_FIT_BOTTOM)
        #     spectrum_graphics.setFieldDomainType(Field.DOMAIN_TYPE_NODES)
        #     spectrum_graphics.setCoordinateField(screen_coords)
        #     spectrum_graphics.setSubgroupField(fng)
        #     spectrum_graphics.setSpectrum(spec)
        #     spectrum_point_attr = spectrum_graphics.getGraphicspointattributes()
        #
        #     gm = scene.getGlyphmodule()
        #     colour_bar = gm.createGlyphColourBar(spec)
        #     colour_bar.setLabelDivisions(6)
        #
        #     spectrum_point_attr.setGlyph(colour_bar)
        #     spectrum_point_attr.setBaseSize([.3, .4, ])

        scene.endChange()

    def initialiseSpectrumFromDictionary(self, data):
        min = data[next(iter(data))][0]
        max = min
        for key in data:
            row_max = np.max(data[key])
            row_min = np.min(data[key])
            if row_min < min:
                min = row_min
            if row_max > max:
                max = row_max

        self._spectrum_component.setRangeMaximum(max)
        self._spectrum_component.setRangeMinimum(min)
