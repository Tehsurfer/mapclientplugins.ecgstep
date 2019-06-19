from __future__ import division

from opencmiss.utils.maths.algorithms import calculate_line_plane_intersection
from opencmiss.zinc.context import Context
from opencmiss.utils.zinc import createFiniteElementField, createSquare2DFiniteElement, createMaterialUsingImageField
import cv2

class ImagePlaneModel(object):

    def __init__(self, master_model, video_path):
        self._master_model = master_model
        self._region = None
        self._frames_per_second = -1
        self._images_file_name_listing = []
        self._image_dimensions = [-1, -1]
        self._duration_field = None
        self._image_based_material = None
        self._scaled_coordinate_field = None
        self._time_sequence = []
        self._video_path = video_path

        self._initialise()

    def _initialise(self):
        child_region = self.create_model(self._master_model._region)
        self._region = self._master_model._region.findChildByName('images')
        self.cap = cv2.VideoCapture(self._video_path)
        self._length = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self._frames_per_second = self.cap.get(cv2.CAP_PROP_FPS)
        flag, frame = self.cap.read()
        self._image_dimensions = [frame.shape[1], frame.shape[0]]

        self.creatZincFields(self._region, self._length, self._frames_per_second, self._image_dimensions)

        field_module = self._region.getFieldmodule()
        self._scaled_coordinate_field = field_module.findFieldByName('scaled_coordinates')
        self._duration_field = field_module.findFieldByName('duration')
        self._image_field = field_module.findFieldByName('volume_image2')
        self._image_field = self._image_field.castImage()
        context = self._master_model.get_context()
        material_module = context.getMaterialmodule()
        self._image_based_material = material_module.findMaterialByName('images')
        self._images_file_name_listing = ['usused'] * self._length
        self.get_image_at(1)


    def create_model(self, parent_region):
        region = parent_region.createChild('images')
        coordinate_field = createFiniteElementField(region)
        field_module = region.getFieldmodule()
        scale_field = field_module.createFieldConstant([2, 3, 1])
        scale_field.setName('scale')
        duration_field = field_module.createFieldConstant(1.0)
        duration_field.setManaged(True)
        duration_field.setName('duration')
        offset_field = field_module.createFieldConstant([+0.5, +0.5, 0.0])
        scaled_coordinate_field = field_module.createFieldMultiply(scale_field, coordinate_field)
        scaled_coordinate_field = field_module.createFieldAdd(scaled_coordinate_field, offset_field)
        scaled_coordinate_field.setManaged(True)
        scaled_coordinate_field.setName('scaled_coordinates')
        createSquare2DFiniteElement(field_module, coordinate_field,
                                    [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 0.0, 1.77], [1.0, 0.0, 1.77]])

        return region

    def creatZincFields(self, region, num_frames, frames_per_second, image_dimension):
        image_dimensions = [-1, -1]
        field_module = region.getFieldmodule()
        frame_count = num_frames
        # Assume all images have the same dimensions.
        width, height = image_dimension
        scale = .001
        cache = field_module.createFieldcache()
        scale_field = field_module.findFieldByName('scale')
        scale_field.assignReal(cache, [width*scale, height*scale, 1.0])
        duration = frame_count / frames_per_second
        duration_field = field_module.findFieldByName('duration')
        duration_field.assignReal(cache, duration)
        image_dimensions = [width, height]
        image_field = createVolumeImageField(field_module, image_dimension, 'volume_image2')
        image_based_material = createMaterialUsingImageField(region, image_field)
        image_based_material.setName('images')  # this is where we will grab the material later
        image_based_material.setManaged(True)
        return image_dimensions, image_based_material

    def set_image_information(self):
        pass

    def get_coordinate_field(self):
        return self._scaled_coordinate_field

    def get_region(self):
        return self._region

    def get_material(self):
        return self._image_based_material

    def get_duration_field(self):
        return self._duration_field

    def get_frame_count(self):
        return len(self._images_file_name_listing)

    def get_frames_per_second(self):
        return self._frames_per_second

    def get_image_file_name_at(self, index):
        return self._images_file_name_listing[index]

    def get_image_at(self, index):
        self.cap.set(1, index)
        res, frame = self.cap.read()
        frame = cv2.flip(frame, 0)
        self._image_field.setBuffer(frame.tobytes())
        return frame

    def calculate_image_pixels_rectangle(self, top_left_mesh_location, bottom_right_mesh_location):
        """
        The origin for the rectangle in the image is the top left corner, the mesh locations are given from
        the bottom left corner.
        :param top_left_mesh_location:
        :param bottom_right_mesh_location:
        :return: Rectangle with origin at top left of image described by [x, y, width, height]
        """
        field_module = self._scaled_coordinate_field.getFieldmodule()
        field_module.beginChange()
        field_cache = field_module.createFieldcache()
        field_cache.setMeshLocation(top_left_mesh_location[0], top_left_mesh_location[1])

        _, top_left_values = self._scaled_coordinate_field.evaluateReal(field_cache, 3)
        field_cache.setMeshLocation(bottom_right_mesh_location[0], bottom_right_mesh_location[1])
        _, bottom_right_values = self._scaled_coordinate_field.evaluateReal(field_cache, 3)
        field_module.endChange()

        return (int(top_left_values[0] + 0.5),
                self._image_dimensions[1] - int(top_left_values[1] + 0.5),
                int(bottom_right_values[0] - top_left_values[0] + 0.5),
                int(top_left_values[1] - bottom_right_values[1] + 0.5))

    @staticmethod
    def get_intersection_point(ray):
        return calculate_line_plane_intersection(ray[0], ray[1], [0.0, 0.0, 0.0], [0.0, 0.0, 1.0])

    def _convert_point_coordinates(self, points):
        return [(point[0], self._image_dimensions[1] - point[1]) for point in points]

    def convert_to_model_coordinates(self, image_points):
        return self._convert_point_coordinates(image_points)

    def convert_to_image_coordinates(self, model_points):
        return self._convert_point_coordinates(model_points)

    def get_time_for_frame_index(self, index):
        frame_count = self.get_frame_count()
        duration = frame_count / self._frames_per_second
        frame_separation = 1 / frame_count
        initial_offset = frame_separation / 2
        return ((index - 1) * frame_separation + initial_offset) * duration

    def get_frame_index_for_time(self, time):
        frame_count = self._length
        duration = frame_count / self._frames_per_second
        frame_separation = 1 / frame_count
        initial_offset = frame_separation / 2

        frame_id = int((time / duration - initial_offset) / frame_separation + 0.5) + 1

        # self._image_field.setBuffer(self._images_file_name_listing[frame_id])
        self.cap.set(1, frame_id)
        res, frame = self.cap.read()
        frame = cv2.flip(frame, 0)
        self._image_field.setBuffer(frame.tobytes())
        return frame_id

def createVolumeImageField(fieldmodule, image_dims, field_name='volume_image'):
    """
    Create an image field using the given fieldmodule.  The image filename must exist and
    be a known image type.

    :param fieldmodule: The fieldmodule to create the field in.
    :param buffer: image buffers
    :param field_name: Optional name of the image field, defaults to 'volume_image'.
    :return: The image field created.
    """
    image_field = fieldmodule.createFieldImage()
    image_field.setName(field_name)
    image_field.setFilterMode(image_field.FILTER_MODE_LINEAR)
    image_field.setSizeInPixels([image_dims[0], image_dims[1], 1])
    image_field.setPixelFormat(image_field.PIXEL_FORMAT_BGR)

    return image_field