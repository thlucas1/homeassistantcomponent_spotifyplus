# """ Intent handlers namespace. """

# import all classes from the namespace.
from .spotifyplusplayermediapause_handler import SpotifyPlusPlayerMediaPause_Handler
from .spotifyplusplayermediaresume_handler import SpotifyPlusPlayerMediaResume_Handler
from .spotifyplusplayermediaskipnext_handler import SpotifyPlusPlayerMediaSkipNext_Handler
from .spotifyplusplayermediaskipprevious_handler import SpotifyPlusPlayerMediaSkipPrevious_Handler
from .spotifyplusplayermediaskipstart_handler import SpotifyPlusPlayerMediaSkipStart_Handler
from .spotifyplusplayersetrepeatmode_handler import SpotifyPlusPlayerSetRepeatMode_Handler
from .spotifyplusplayersetshufflemode_handler import SpotifyPlusPlayerSetShuffleMode_Handler
from .spotifyplusvolumesetstep_handler import SpotifyPlusVolumeSetStep_Handler

# all classes to import when "import *" is specified.
__all__ = [
    'SpotifyPlusPlayerMediaPause_Handler',
    'SpotifyPlusPlayerMediaResume_Handler',
    'SpotifyPlusPlayerMediaSkipNext_Handler',
    'SpotifyPlusPlayerMediaSkipPrevious_Handler',
    'SpotifyPlusPlayerMediaSkipStart_Handler',
    'SpotifyPlusPlayerSetRepeatMode_Handler',
    'SpotifyPlusPlayerSetShuffleMode_Handler',
    'SpotifyPlusVolumeSetStep_Handler',
]
