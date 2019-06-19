

class ImagePlaneScene(object):

    def __init__(self, master_model):
        self._master_model = master_model

    def create_graphics(self):
        image_plane_model = self._master_model.get_image_plane_model()
        region = image_plane_model.get_region()
        scene = region.getScene()
        coordinate_field = image_plane_model.get_coordinate_field()
        duration_field = image_plane_model.get_duration_field()

        scene.beginChange()
        scene.removeAllGraphics()
        field_module = region.getFieldmodule()
        xi = field_module.findFieldByName('xi')
        lines = scene.createGraphicsLines()
        lines.setExterior(True)
        lines.setName('plane-lines')
        lines.setCoordinateField(coordinate_field)
        surfaces = scene.createGraphicsSurfaces()
        surfaces.setName('plane-surfaces')
        surfaces.setCoordinateField(coordinate_field)
        temp1 = field_module.createFieldComponent(xi, [1, 2])
        temp2 = field_module.createFieldTimeValue(self._master_model.get_timekeeper())
        temp3 = field_module.createFieldDivide(temp2, duration_field)
        texture_field = field_module.createFieldConcatenate([temp1, temp3])
        surfaces.setTextureCoordinateField(texture_field)
        scene.endChange()

    def set_image_material(self):
        image_plane_model = self._master_model.get_image_plane_model()
        image_material = image_plane_model.get_material()
        scene = image_plane_model.get_region().getScene()
        surfaces = scene.findGraphicsByName('plane-surfaces')
        surfaces.setMaterial(image_material)
