# """ Intent handlers namespace. """

# import all classes from the namespace.
from .spotifyplusplayermediaskipnext_handler import SpotifyPlusPlayerMediaSkipNext_Handler
from .spotifyplusplayermediaskipprevious_handler import SpotifyPlusPlayerMediaSkipPrevious_Handler

# all classes to import when "import *" is specified.
__all__ = [
    'SpotifyPlusPlayerMediaSkipNext_Handler',
    'SpotifyPlusPlayerMediaSkipPrevious_Handler',
]
