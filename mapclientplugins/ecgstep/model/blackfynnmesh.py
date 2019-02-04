""" blackfynnMesh.py
blackfynn mesh takes an input of ECG points and renders it to apply our data from Blackfynn to it

This file is modified from 'meshtype_2d_plate1.py' created by Richard Christie.

"""
import numpy as np
import math
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
        self._mesh_group_list = mesh_group_list
        self._element_node_list = element_node_list
        self._field_element_group = fieldElementGroup
        self._coordinates = coordinates

        field_module.endChange()
        self._strain_graphics_point_attr = []
        for i, mg in enumerate(mesh_group_list):
            strain = self.calculate_strain_in_element_xi(element_node_list[i], 0)
            scaled_eigvectors = self.get_sized_eigvectors(strain)
            if np.iscomplex(scaled_eigvectors).any():
                x = 0
            self.create_display_strains(scaled_eigvectors, mg)

    def display_strains_at_given_time(self, time_step):
        fm = self._region.getFieldmodule()
        for i, mg in enumerate(self._mesh_group_list):
            strain = self.calculate_strains_on_element(self._element_node_list[i], time_step)
            scaled_eigvectors = self.get_sized_eigvectors(strain)
            ss = fm.createFieldConstant(np.array(scaled_eigvectors).flatten().tolist())
            self._strain_graphics_point_attr[i].setOrientationScaleField(ss)

    def display_strains_at_given_time_to_reference(self, time_step):
        fm = self._region.getFieldmodule()
        for i, mg in enumerate(self._mesh_group_list):
            strain = self.calculate_strains_from_element_reference(self._element_node_list[i], time_step)
            scaled_eigvectors = self.get_sized_eigvectors(strain)
            ss = fm.createFieldConstant(np.array(scaled_eigvectors).flatten().tolist())
            self._strain_graphics_point_attr[i].setOrientationScaleField(ss)

    def calculate_strains_on_element(self, element, timestep):

        nodes = self._time_based_node_description

        # points is the location of a line at timestep t. points_dash is the location of the line at timestep t+1
        points = [nodes[str(element[1])][timestep], nodes[str(element[2])][timestep],nodes[str(element[3])][timestep]]
        points_dash = [nodes[str(element[1])][timestep+1], nodes[str(element[2])][timestep+1],nodes[str(element[3])][timestep+1]]
        strain = self.calculate_strain(points, points_dash)

        return strain
    def calculate_strains_from_element_reference(self, element, timestep):

        nodes = self._time_based_node_description

        # points is the location of a line at timestep t. points_dash is the location of the line at timestep t+1
        points = [nodes[str(element[1])][self._frame_index], nodes[str(element[2])][self._frame_index],nodes[str(element[3])][self._frame_index]]
        points_dash = [nodes[str(element[1])][timestep], nodes[str(element[2])][timestep],nodes[str(element[3])][timestep]]
        strain = self.calculate_strain(points, points_dash)

        return strain
    def get_sized_eigvectors(self, E):

        e_vals, e_vecs = np.linalg.eig(E)
        sizedvectors = []
        for i, _ in enumerate(e_vals):
            sizedvectors.append(list(e_vals[i] * e_vecs[:, i]))
        return np.vstack(sizedvectors).tolist()

    def create_display_strains(self, strain, mesh_group):
        scene = self._region.getScene()
        fm = self._region.getFieldmodule()
        fm.beginChange()
        coordinates = self._coordinates
        coordinates = coordinates.castFiniteElement()
        strain_graphics = scene.createGraphicsPoints()
        strain_graphics.setFieldDomainType(Field.DOMAIN_TYPE_MESH_HIGHEST_DIMENSION)
        strain_graphics.setCoordinateField(coordinates)
        strain_graphics.setSubgroupField(mesh_group)
        pointattr = strain_graphics.getGraphicspointattributes()
        pointattr.setGlyphShapeType(Glyph.SHAPE_TYPE_DIAMOND )

        pointattr.setBaseSize([0.01,0.01,0.01])
        ss = fm.createFieldConstant(np.array(strain).flatten().tolist())
        pointattr.setOrientationScaleField(ss)
        materialModule = scene.getMaterialmodule()
        strain_graphics.setMaterial(materialModule.findMaterialByName('red'))
        strain_graphics.setName('displayStrains')

        # Create a point attribute arrray so that we can modify the size later easily
        self._strain_graphics_point_attr.append(pointattr)
        fm.endChange()

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
        F = np.linalg.solve(points, points_dash)
        C = F.T @ F
        E = .5 * (C - np.identity(3))
        return E

    def calculate_strain_in_element_xi(self, element, timestep):

        nodes = self._time_based_node_description

        # xl and yl are our un adjusted element directions. We will use these create a local 3D coordinates for the element

        # xl = point 2 of our element - point 1
        xl = np.array( nodes[str(element[1])][timestep] ) - np.array( nodes[str(element[0])][timestep] )
        yl = np.array( nodes[str(element[0])][timestep] ) - np.array( nodes[str(element[2])][timestep] )

        xi = xl / np.linalg.norm(xl)
        norm = np.cross(yl, xl)
        zi = norm / np.linalg.norm(norm)
        yi = np.cross(zi, xi)
        yi = yi / np.linalg.norm(yi)
        TT = np.vstack([xi, yi, zi]).T
        # Transormation Matrix TM will be used to convert between coordinate systems
        TM = np.eye(3)
        for i in range (0,3):
            for j in range(0,3):
                TM[i][j] = math.cos(angle_between_vectors(np.eye(3)[:,i],TT[:,j]))

        E = self.calculate_strains_on_element(element, timestep)

        Exi = TM @ E
        return Exi


    def set_strain_reference_frame(self, frame_index):
        self._frame_index = frame_index





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


def vector_norm(data, axis=None, out=None):
    data = np.array(data, dtype=np.float64, copy=True)
    if out is None:
        if data.ndim == 1:
            return math.sqrt(np.dot(data, data))
        data *= data
        out = np.atleast_1d(np.sum(data, axis=axis))
        np.sqrt(out, out)
        return out
    else:
        data *= data
        np.sum(data, axis=axis, out=out)
        np.sqrt(out, out)

def angle_between_vectors(v0, v1, directed=True, axis=0):

    v0 = np.array(v0, dtype=np.float64, copy=False)
    v1 = np.array(v1, dtype=np.float64, copy=False)
    dot = np.sum(v0 * v1, axis=axis)
    dot /= np.linalg.norm(v0, axis=axis) * vector_norm(v1, axis=axis)
    dot = np.clip(dot, -1.0, 1.0)
    return np.arccos(dot if directed else numpy.fabs(dot))