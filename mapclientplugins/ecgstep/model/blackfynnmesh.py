""" blackfynnMesh.py
blackfynn mesh takes an input of ECG points and renders it to apply our data from Blackfynn to it

This file is modified from 'meshtype_2d_plate1.py' created by Richard Christie.

"""
import numpy as np

from opencmiss.zinc.element import Element, Elementbasis
from opencmiss.zinc.field import Field
from opencmiss.zinc.node import Node
from opencmiss.zinc.glyph import Glyph
from mapclientplugins.ecgstep.model.meshalignmentmodel import MeshAlignmentModel


class BlackfynnMesh(MeshAlignmentModel):
    """
    BlackfynnMesh is the central point for generating the model for our mesh and drawing it
    """

    def __init__(self, region, time_based_node_description):
        super(BlackfynnMesh, self).__init__()
        self._mesh_group = []
        self._field_element_group = None
        self._coordinates = None
        self._data_time_sequence = []
        self._data = []

        ecg_region = region.findChildByName('ecg_plane')
        if ecg_region.isValid():
            region.removeChild(ecg_region)

        self._region = region.createChild('ecg_plane')
        self._time_based_node_description = time_based_node_description

        # Note that these are normally changed before generating the mesh

    def set_data_time_sequence(self, data_time_sequence):
        self._data_time_sequence = data_time_sequence

    def set_data(self, data):
        self._data = data

    def generate_mesh(self):
        """
        generateMesh: This is where all points, elements, and colour fields relating to them are defined
        """
        coordinate_dimensions = 3
        # self.number_points = len(self._node_coordinate_list)

        # We currently find the number of elements by taking the square root of the number of given points
        elements_count_across = 7
        elements_count_up = 7
        use_cross_derivatives = 0

        # Set up our coordinate field
        field_module = self._region.getFieldmodule()
        field_module.beginChange()
        coordinates = field_module.createFieldFiniteElement(coordinate_dimensions)
        coordinates.setName('coordinates')
        coordinates.setManaged(True)
        coordinates.setTypeCoordinate(True)
        coordinates.setCoordinateSystemType(Field.COORDINATE_SYSTEM_TYPE_RECTANGULAR_CARTESIAN)
        coordinates.setComponentName(1, 'x')
        coordinates.setComponentName(2, 'y')
        if coordinate_dimensions == 3:
            coordinates.setComponentName(3, 'z')

        # Set up our node template
        nodes = field_module.findNodesetByFieldDomainType(Field.DOMAIN_TYPE_NODES)
        node_template = nodes.createNodetemplate()
        node_template.defineField(coordinates)
        node_template.setValueNumberOfVersions(coordinates, -1, Node.VALUE_LABEL_VALUE, 1)
        node_template.setValueNumberOfVersions(coordinates, -1, Node.VALUE_LABEL_D_DS1, 1)
        node_template.setValueNumberOfVersions(coordinates, -1, Node.VALUE_LABEL_D_DS2, 1)
        if use_cross_derivatives:
            node_template.setValueNumberOfVersions(coordinates, -1, Node.VALUE_LABEL_D2_DS1DS2, 1)

        mesh = field_module.findMeshByDimension(2)

        # Create our mesh subgroup
        fieldGroup = field_module.createFieldGroup()
        fieldElementGroup = fieldGroup.createFieldElementGroup(mesh)
        fieldElementGroup.setManaged(True)
        meshGroup = fieldElementGroup.getMeshGroup()

        # Define our interpolation
        bicubicHermiteBasis = field_module.createElementbasis(2, Elementbasis.FUNCTION_TYPE_CUBIC_HERMITE)
        bilinearBasis = field_module.createElementbasis(2, Elementbasis.FUNCTION_TYPE_LINEAR_LAGRANGE)

        # Set up our element templates
        eft = meshGroup.createElementfieldtemplate(bicubicHermiteBasis)
        eft_bi_linear = meshGroup.createElementfieldtemplate(bilinearBasis)
        if not use_cross_derivatives:
            for n in range(4):
                eft.setFunctionNumberOfTerms(n*4 + 4, 0)
        element_template = meshGroup.createElementtemplate()
        element_template.setElementShapeType(Element.SHAPE_TYPE_SQUARE)
        element_template.defineField(coordinates, -1, eft)

        # Create our spectrum colour field
        colour = field_module.createFieldFiniteElement(1)
        colour.setName('colour2')
        colour.setManaged(True)

        # add time support for colour field

        # Create node and element templates for our spectrum colour field
        node_template.defineField(colour)
        node_template.setValueNumberOfVersions(colour, -1, Node.VALUE_LABEL_VALUE, 1)
        element_template.defineField(colour, -1, eft_bi_linear)

        node_time_sequence = self._time_based_node_description['time_array']
        zinc_node_time_sequence = field_module.getMatchingTimesequence(node_time_sequence)
        node_template.setTimesequence(coordinates, zinc_node_time_sequence)
        zinc_data_time_sequence = field_module.getMatchingTimesequence(self._data_time_sequence)
        node_template.setTimesequence(colour, zinc_data_time_sequence)

        first_node_number = 1

        # create nodes
        cache = field_module.createFieldcache()
        node_identifier = first_node_number
        x = [0.0, 0.0, 0.0]
        dx_ds1 = [0.0, 0.0, 0.0]
        dx_ds2 = [0.0, 0.0, 0.0]
        zero = [0.0, 0.0, 0.0]
        i = 0
        for n2 in range(elements_count_up + 1):
            for n1 in range(elements_count_across + 1):

                node = nodes.createNode(node_identifier, node_template)
                cache.setNode(node)

                node_locations = self._time_based_node_description['{0}'.format(node_identifier)]
                # Assign the new node its position
                for index, time in enumerate(node_time_sequence):
                    cache.setTime(time)
                    coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_VALUE, 1, node_locations[index])
                # coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_D_DS1, 1, dx_ds1)
                # coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_D_DS2, 1, dx_ds2)
                if use_cross_derivatives:
                    coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_D2_DS1DS2, 1, zero)

                # Assign the new node its colour for each time step
                for index, time in enumerate(self._data_time_sequence):
                    cache.setTime(time)
                    colour_value = self._data[i % len(self._data)][index]
                    colour.setNodeParameters(cache, -1, Node.VALUE_LABEL_VALUE, 1, colour_value)

                node_identifier = node_identifier + 1
                i += 1

        # create elements
        elementIdentifier = first_node_number
        no2 = (elements_count_across + 1)
        for e2 in range(elements_count_up):
            for e1 in range(elements_count_across):
                element = meshGroup.createElement(elementIdentifier, element_template)
                bni = e2 * no2 + e1 + first_node_number
                nodeIdentifiers = [bni, bni + 1, bni + no2, bni + no2 + 1]
                result = element.setNodesByIdentifier(eft, nodeIdentifiers)
                result = element.setNodesByIdentifier(eft_bi_linear, nodeIdentifiers)
                elementIdentifier = elementIdentifier + 1

        # Set fields for later access
        self._mesh_group = meshGroup
        self._field_element_group = fieldElementGroup
        self._coordinates = coordinates

        field_module.endChange()

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
        nodePointAttr.setBaseSize([.005, .005, .005])
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
        # nodePoints.setSpectrum(spec)
        # nodePoints.setDataField(colour)

        axes = scene.createGraphicsPoints()
        pointattr = axes.getGraphicspointattributes()
        pointattr.setGlyphShapeType(Glyph.SHAPE_TYPE_AXES_XYZ)
        axesScale = 50
        pointattr.setBaseSize([axesScale, axesScale, axesScale])

        # # Uncomment to be able to adjust tessellation
        # tessellationmodule = self._context.getTessellationmodule()
        # fineTessellation = tessellationmodule.createTessellation()
        # fineTessellation.setName('fine')  # name it so it can be found by name later
        # fineTessellation.setManaged(True)  # manage its lifetime so it is kept even if not being used
        # fineTessellation.setMinimumDivisions(8)  # divide element edges into 8 line segments
        # isosurfaces.setTessellation(fineTessellation)

        scene.endChange()

    def createSpectrumColourBar(self, spectrum):
        # Add a colour bar for the spectrum

        fm = self._region.getFieldmodule()
        scene = self._region.getScene()
        nodes = fm.findNodesetByFieldDomainType(Field.DOMAIN_TYPE_NODES)
        cache = fm.createFieldcache()
        check = nodes.findNodeByIdentifier(1000)
        if not check.isValid():
            screen_coords = fm.createFieldFiniteElement(2)
            spectrum_template = nodes.createNodetemplate()
            spectrum_template.defineField(screen_coords)
            spectrum_node = nodes.createNode(1000, spectrum_template)
            cache.setNode(spectrum_node)
            screen_coords.setNodeParameters(cache, -1, Node.VALUE_LABEL_VALUE, 1, [-.95, -.78])
            fng = fm.createFieldNodeGroup(nodes)
            spectrum_group = fng.getNodesetGroup()
            spectrum_group.addNode(spectrum_node)

            spectrum_graphics = scene.createGraphicsPoints()
            spectrum_graphics.setScenecoordinatesystem(
                Scenecoordinatesystem.SCENECOORDINATESYSTEM_NORMALISED_WINDOW_FIT_BOTTOM)
            spectrum_graphics.setFieldDomainType(Field.DOMAIN_TYPE_NODES)
            spectrum_graphics.setCoordinateField(screen_coords)
            spectrum_graphics.setSubgroupField(fng)
            spectrum_graphics.setSpectrum(spectrum)
            spectrum_point_attr = spectrum_graphics.getGraphicspointattributes()

            gm = scene.getGlyphmodule()
            colour_bar = gm.createGlyphColourBar(spectrum)
            colour_bar.setLabelDivisions(6)

            spectrum_point_attr.setGlyph(colour_bar)
            spectrum_point_attr.setBaseSize([.3, .4, ])





    def initialiseSpectrumFromDictionary(self, data):
        # min = data[next(iter(data))][0]
        # max = min
        # for key in data:
        #     row_max = np.max(data[key])
        #     row_min = np.min(data[key])
        #     if row_min < min:
        #         min = row_min
        #     if row_max > max:
        #         max = row_max
        #
        # max = int(max) # Fix bug where numpy int is having issues
        # min = int(min)
        # self._spectrum_component.setRangeMaximum(max)
        # self._spectrum_component.setRangeMinimum(min)

        scene = self._region.getScene()
        spectrummodule = scene.getSpectrummodule()
        spectrum = spectrummodule.getDefaultSpectrum()
        scenefiltermodule = scene.getScenefiltermodule()
        scenefilter = scenefiltermodule.getDefaultScenefilter()
        spectrum.autorange(scene, scenefilter)


def find_nearest(array, value):
    array = np.asarray(array)
    idx = (np.abs(array - value)).argmin()
    return array[idx]