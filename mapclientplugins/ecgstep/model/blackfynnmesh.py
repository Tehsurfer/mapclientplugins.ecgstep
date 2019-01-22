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

        first_node_number = 0

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
        element_node_list = []
        elementIdentifier = first_node_number
        mesh_group_list = []
        no2 = (elements_count_across + 1)
        for e2 in range(elements_count_up):
            for e1 in range(elements_count_across):
                element_node_list.append([])
                element = meshGroup.createElement(elementIdentifier, element_template)
                bni = e2 * no2 + e1 + first_node_number
                nodeIdentifiers = [bni, bni + 1, bni + no2, bni + no2 + 1]
                element_node_list[e1+e2*elements_count_across] = nodeIdentifiers
                result = element.setNodesByIdentifier(eft, nodeIdentifiers)
                result = element.setNodesByIdentifier(eft_bi_linear, nodeIdentifiers)
                elementIdentifier = elementIdentifier + 1
                element_group = field_module.createFieldElementGroup(mesh)
                temp_mesh_group = element_group.getMeshGroup()
                temp_mesh_group.addElement(element)
                mesh_group_list.append(element_group)

        # Set fields for later access
        self._mesh_group = meshGroup
        self._field_element_group = fieldElementGroup
        self._coordinates = coordinates

        field_module.endChange()
        for i, mg in enumerate(mesh_group_list):
            strain = self.calculate_strains_on_element(element_node_list[i], 0)
            self.display_strains(strain, mg)


    def calculate_strains_on_element(self, element, timestep):
        strains = [0,0,0]
        nodes = self._time_based_node_description
        points = [nodes[str(element[0])][timestep], nodes[str(element[1])][timestep]]
        points_dash = [nodes[str(element[0])][timestep+1], nodes[str(element[1])][timestep+1]]
        strain_1 = self.calculate_strain(points, points_dash)

        points = [nodes[str(element[2])][timestep], nodes[str(element[3])][timestep]]
        points_dash = [nodes[str(element[2])][timestep + 1], nodes[str(element[3])][timestep + 1]]
        strain_2 = self.calculate_strain(points, points_dash)


        strain_av = ( np.array(strain_1) + np.array(strain_2) ) / 2

        return strain_av.tolist()

    def display_strains(self, strain, mesh_group):
        scene = self._region.getScene()
        fm = self._region.getFieldmodule()
        coordinates = self._coordinates
        coordinates = coordinates.castFiniteElement()
        strain_graphics = scene.createGraphicsPoints()
        strain_graphics.setFieldDomainType(Field.DOMAIN_TYPE_MESH_HIGHEST_DIMENSION)
        strain_graphics.setCoordinateField(coordinates)
        strain_graphics.setSubgroupField(mesh_group)
        pointattr = strain_graphics.getGraphicspointattributes()
        pointattr.setGlyphShapeType(Glyph.SHAPE_TYPE_AXES_123)
        meshDimension = 3
        if meshDimension == 1:
            pointattr.setBaseSize([0.0, 2 * width, 2 * width])
            pointattr.setScaleFactors([0.25, 0.0, 0.0])
        elif meshDimension == 2:
            pointattr.setBaseSize([0.0, 0.0, 2 * width])
            pointattr.setScaleFactors([0.25, 0.25, 0.0])
        else:
            pointattr.setBaseSize(strain)
        materialModule = scene.getMaterialmodule()
        strain_graphics.setMaterial(materialModule.findMaterialByName('yellow'))
        strain_graphics.setName('displayXiAxes')

    def convert_dict_to_array(self, dictionary):
        array = []
        for key in dictionary:
            if key is not 'time_array':
                array.append(dictionary[key])
        return array

    def create_strain_arrays(self, ecg_dict):
        strains = []
        for i, points_over_time in enumerate(ecg_dict[:-1]):
            strains.append([])
            for j, point in enumerate(points_over_time[:-1]):
                points = [ecg_dict[i][j], ecg_dict[i + 1][j]]
                points_dash = [ecg_dict[i][j + 1], ecg_dict[i + 1][j + 1]]
                strains[i].append(self.calculate_strain(points, points_dash))
        return strains

    def calculate_strain(self, points, points_dash):
        strain = [0, 0, 0]
        for dimension, value in enumerate(points):
            length1 = points_dash[1][dimension] - points_dash[0][dimension]
            length0 = points[1][dimension] - points[0][dimension]
            strain[dimension] = (length1 - length0) / length0
        return strain

    def calculate_strain_in_line_direction(self, points, points_dash):
        '''
        :param points: p1 and p2
        :param points_dash: p1' and p2'
        :return:

        note that we calculate in the direction of the line between two points by creating a weighting of line gradient
        then multiply our strains by this normalised line
        '''

        strain = self.calculate_strain(points, points_dash)
        total_delta = sum(np.array(points[1]) - np.array(points[0]))
        line_direction = np.array(points[1] - np.array(points[0])) / total_delta
        adjusted_strains = np.array(strain) * line_direction
        return [adjusted_strains, line_direction]

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
        nodePointAttr.setBaseSize([5, 5, 5])
        # cmiss_number = fm.findFieldByName('cmiss_number')
        # nodePointAttr.setLabelField(cmiss_number)

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
