# """ Intent handlers namespace. """

# import all classes from the namespace.
from .spotifyplusfavoriteaddremove_handler import SpotifyPlusFavoriteAddRemove_Handler
from .spotifyplusgetinfoartistbio_handler import SpotifyPlusGetInfoArtistBio_Handler
from .spotifyplusgetnowplayinginfo_handler import SpotifyPlusGetNowPlayingInfo_Handler
from .spotifyplusplayerdeckcontrol_handler import SpotifyPlusPlayerDeckControl_Handler
from .spotifyplusplayersetrepeatmode_handler import SpotifyPlusPlayerSetRepeatMode_Handler
from .spotifyplusplayersetshufflemode_handler import SpotifyPlusPlayerSetShuffleMode_Handler
from .spotifyplusplayertransferplayback_handler import SpotifyPlusPlayerTransferPlayback_Handler
from .spotifyplusplayervolumecontrol_handler import SpotifyPlusPlayerVolumeControl_Handler
from .spotifyplusplaylistcreate_handler import SpotifyPlusPlaylistCreate_Handler
from .spotifyplussearchplaycontrol_handler import SpotifyPlusSearchPlayControl_Handler

# all classes to import when "import *" is specified.
__all__ = [
    'SpotifyPlusFavoriteAddRemove_Handler',
    'SpotifyPlusGetInfoArtistBio_Handler',
    'SpotifyPlusGetNowPlayingInfo_Handler',
    'SpotifyPlusPlayerDeckControl_Handler',
    'SpotifyPlusPlayerSetRepeatMode_Handler',
    'SpotifyPlusPlayerSetShuffleMode_Handler',
    'SpotifyPlusPlayerTransferPlayback_Handler',
    'SpotifyPlusPlayerVolumeControl_Handler',
    'SpotifyPlusPlaylistCreate_Handler',
    'SpotifyPlusSearchPlayControl_Handler',
]
