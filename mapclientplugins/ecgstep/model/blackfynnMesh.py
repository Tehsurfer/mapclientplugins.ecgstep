""" blackfynnMesh.py
blackfynn mesh uses the points defined in 'blackfynnECGgraphics.py' to create a 2d mesh

This file is modified from 'meshtype_2d_plate1.py' created by Richard Christie.

"""

from opencmiss.zinc.element import Element, Elementbasis
from opencmiss.zinc.field import Field
from opencmiss.zinc.node import Node
from opencmiss.zinc.glyph import Glyph
import opencmiss.zinc.scenecoordinatesystem as Scenecoordinatesystem

class Blackfynn_2d_plate(object):
    '''
    Blackfynn_2d_plate is the central point for generating the model for our mesh and drawing it
    '''


    def __init__(self, region, node_coordinate_list=[]):

        self.meshGroup = []
        ecg_region = region.findChildByName('ecg_plane')
        if ecg_region.isValid():
            region.removeChild(ecg_region)

        self._region = region.createChild('ecg_plane')
        self.node_coordinate_list = node_coordinate_list
        self.ECGcoloursMatrix = [[-5000,-4000,-3000],[-5000,-4000,-3000],]
        self.ECGtimes = [0,.5,1]



    def generateMesh(self):
        """
        :param region: Zinc region to define model in
        :param node_coordinate_list: an optional list that contains the 3d coordinates of our projected mesh
        :return: None
        """

        coordinateDimensions = 3
        self.number_points = len(self.node_coordinate_list)
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

        timeSequence = fm.getMatchingTimesequence(self.ECGtimes)
        nodetemplate.setTimesequence(colour, timeSequence)

        if self.node_coordinate_list == []:
            eegGrid = [[0.509204852009174, -0.5311370349544523, -0.0034167299250837833], [0.5395357502061648, -0.510145753072639, -0.007247427797009046], [0.5672355599089255, -0.48703701801970584, -0.012153448140377348], [0.5930761300982424, -0.4624320001118838, -0.01781933727302615], [0.6170586979158605, -0.4363316949788206, -0.024244589576721227], [0.6392717903894952, -0.40880734759611354, -0.031393024169503986], [0.6589501649806984, -0.37924310439469183, -0.03957739468908057], [0.6778529320418958, -0.34905466606355257, -0.04807875500503394], [0.49396373463086385, -0.5400449928328186, -0.014184277651397386], [0.5219938148165804, -0.5213737210183256, -0.021750259354039705], [0.5482188338281995, -0.5012497681117525, -0.03005396722860377], [0.5727230851056093, -0.4797409719725964, -0.03906095065501156], [0.5958093078547447, -0.45709097172323354, -0.048647480510566325], [0.6171537637833796, -0.43303922855054927, -0.058945868217426825], [0.6368878167933374, -0.40769146178367166, -0.06990242551847924], [0.6551617261442496, -0.38116859739924286, -0.08145574164826357], [0.4786410423087401, -0.5488873006489237, -0.024985164951952504], [0.50436802158169, -0.5325342016632791, -0.03628736350420491], [0.5285382209611089, -0.5149282339392697, -0.048225815989487504], [0.551651512683225, -0.4964716857519103, -0.060596225270077624], [0.5729419991860405, -0.4765481763808414, -0.07371161269096038], [0.5929925504583491, -0.4556267892144881, -0.08733376004007136], [0.611855196905776, -0.43374939739684715, -0.101441402557791], [0.628049851147178, -0.4097248529579398, -0.1166394500463296], [0.4627839639692091, -0.5572995441134712, -0.03600445512804877], [0.4858847684155735, -0.5430046138234724, -0.05117491042147269], [0.5087232878400857, -0.5284986012181218, -0.0664525612647761], [0.5290170611193118, -0.5119446222266737, -0.08277024657295778], [0.5482419145839613, -0.49453039560159, -0.09952479802961961], [0.5647161909178123, -0.4749025534782857, -0.11740350680925657], [0.5816541775040608, -0.4556478971093079, -0.1350926978072854], [0.5975407272902518, -0.43554706312547753, -0.15321160966832706], [0.4464484414499953, -0.5653267442213643, -0.0472192848228165], [0.4657279848893067, -0.5521281985486189, -0.06674642703677909], [0.4846600254596423, -0.5386499887545416, -0.08641559322474326], [0.5023725554772778, -0.5241903385821979, -0.10658317180147975], [0.5189795695333729, -0.5088409888487717, -0.12720257332472276], [0.534585481775473, -0.4926859702010134, -0.14823112386714643], [0.5492640292455159, -0.47578462489731665, -0.1696386871948885], [0.5630515535836841, -0.4581662000426028, -0.19141041052651545], [0.4268650717727057, -0.5707401347674506, -0.059761505458842935], [0.4454436325574417, -0.5611491181705042, -0.08237008085827056], [0.4612393379431116, -0.5493185090997809, -0.10611600566725035], [0.4759003113625392, -0.5365746879476093, -0.13032569396614718], [0.4895610726118554, -0.5230259138506624, -0.15494416768791758], [0.5023511716655504, -0.5087764463216492, -0.17991847992520738], [0.5116971489677351, -0.49175521093288904, -0.2063004002767459], [0.5224816534081826, -0.47589167657065673, -0.23209439644369428], [0.40867053627951044, -0.5772712343353802, -0.0717361113565054], [0.42464095641280963, -0.5697529000171239, -0.09820557295299938], [0.43392364037198017, -0.5568523947074416, -0.12740830369148262], [0.4450283897241741, -0.5454182551824549, -0.15586635865571763], [0.45511547470455493, -0.5331651174915164, -0.1847403317351347], [0.46434139783432693, -0.5202189320770146, -0.21396626055132748], [0.4714867061677311, -0.505598304921725, -0.2440425339491858], [0.4781123574909273, -0.4905594670576076, -0.2743311904963546], [0.39000920810428935, -0.5834266674645039, -0.08390149482078654], [0.3989216649580346, -0.5743998774071594, -0.11605047937872888], [0.4075667400902677, -0.5651579033013279, -0.14830874250112308], [0.41509775595236764, -0.5550193541317798, -0.18102232020921832], [0.41802707930328564, -0.541177444766751, -0.21561660370687405], [0.42255639587899896, -0.528623181459634, -0.24955697203879074], [0.42812246280518906, -0.5169032763742534, -0.2830736218406812], [0.4258422580102747, -0.4988688315180695, -0.3197970327671987]]
        else:
            eegGrid = []
            for coord in self.node_coordinate_list:
                eegGrid.append(coord)

        firstNodeNumber = 1

        # create nodes
        cache = fm.createFieldcache()
        nodeIdentifier =  firstNodeNumber
        x = [ 0.0, 0.0, 0.0 ]
        dx_ds1 = [ 0, 0.0, 0.0 ]
        dx_ds2 = [ 0.0, 0, 0.0 ]
        zero = [ 0.0, 0.0, 0.0 ]
        i = 0
        for n2 in range(elementsCount2 + 1):
            for n1 in range(elementsCount1 + 1):

                node = nodes.createNode(nodeIdentifier, nodetemplate)
                cache.setNode(node)
                coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_VALUE, 1, eegGrid[i])
                coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_D_DS1, 1, dx_ds1)
                coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_D_DS2, 1, dx_ds2)
                if useCrossDerivatives:
                    coordinates.setNodeParameters(cache, -1, Node.VALUE_LABEL_D2_DS1DS2, 1, zero)

                # need to set time via cache

                for j, time in enumerate(self.ECGtimes):
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
                bni = e2*no2 + e1 + firstNodeNumber
                nodeIdentifiers = [ bni, bni + 1, bni + no2, bni + no2 + 1]
                result = element.setNodesByIdentifier(eft, nodeIdentifiers)
                result = element.setNodesByIdentifier(eftBilinear, nodeIdentifiers)
                elementIdentifier = elementIdentifier + 1

        # Set fields for later access
        self.meshGroup = meshGroup
        self.fieldElementGroup = fieldElementGroup
        self.coordinates = coordinates

        fm.endChange()

    def drawMesh(self):

        scene = self._region.getScene()
        fm = self._region.getFieldmodule()

        coordinates = self.coordinates
        coordinates = coordinates.castFiniteElement()

        materialModule = scene.getMaterialmodule()

        lines = scene.createGraphicsLines()
        lines.setCoordinateField(coordinates)
        lines.setName('displayLines2')
        lines.setMaterial(materialModule.findMaterialByName('blue'))

        nodePoints = scene.createGraphicsPoints()
        nodePoints.setFieldDomainType(Field.DOMAIN_TYPE_NODES)
        #nodePoints.setSubgroupField(self.fieldElementGroup)
        nodePoints.setCoordinateField(coordinates)
        nodePoints.setMaterial(materialModule.findMaterialByName('blue'))
        nodePoints.setVisibilityFlag(True)

        nodePointAttr = nodePoints.getGraphicspointattributes()
        nodePointAttr.setGlyphShapeType(Glyph.SHAPE_TYPE_SPHERE)
        nodePointAttr.setBaseSize([.02, .02, .02])

        surfaces = scene.createGraphicsSurfaces()
        surfaces.setCoordinateField(coordinates)
        surfaces.setVisibilityFlag(True)

        colour = fm.findFieldByName('colour2')
        colour = colour.castFiniteElement()

        # Add Spectrum
        spcmod = scene.getSpectrummodule()
        spec = spcmod.getDefaultSpectrum()
        spec.setName('eegColourSpectrum')

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


