
"""
MAP Client Plugin
"""

__version__ = '1.0.0'
__author__ = 'Jesse Khorasanee'
__stepname__ = 'ecg'
__location__ = ''

# import class that derives itself from the step mountpoint.
from mapclientplugins.ecgstep import step

# Import the resource file when the module is loaded,
# this enables the framework to use the step icon.
from . import resources_rc