# """ Intent handlers namespace. """

# import all classes from the namespace.
from .spotifyplusfavoriteartistadd_handler import SpotifyPlusFavoriteArtistAdd_Handler
from .spotifyplusfavoriteartistremove_handler import SpotifyPlusFavoriteArtistRemove_Handler
from .spotifyplusfavoritetrackadd_handler import SpotifyPlusFavoriteTrackAdd_Handler
from .spotifyplusfavoritetrackremove_handler import SpotifyPlusFavoriteTrackRemove_Handler
from .spotifyplusgetinfoartistbio_handler import SpotifyPlusGetInfoArtistBio_Handler
from .spotifyplusnowplayinginfoartistbio_handler import SpotifyPlusNowPlayingInfoArtistBio_Handler
from .spotifyplusnowplayinginfoaudiobook_handler import SpotifyPlusNowPlayingInfoAudiobook_Handler
from .spotifyplusnowplayinginfopodcast_handler import SpotifyPlusNowPlayingInfoPodcast_Handler
from .spotifyplusnowplayinginfotrack_handler import SpotifyPlusNowPlayingInfoTrack_Handler
from .spotifyplusplayermediapause_handler import SpotifyPlusPlayerMediaPause_Handler
from .spotifyplusplayermediaresume_handler import SpotifyPlusPlayerMediaResume_Handler
from .spotifyplusplayermediaskipnext_handler import SpotifyPlusPlayerMediaSkipNext_Handler
from .spotifyplusplayermediaskipprevious_handler import SpotifyPlusPlayerMediaSkipPrevious_Handler
from .spotifyplusplayermediaskipstart_handler import SpotifyPlusPlayerMediaSkipStart_Handler
from .spotifyplusplayersetrepeatmode_handler import SpotifyPlusPlayerSetRepeatMode_Handler
from .spotifyplusplayersetshufflemode_handler import SpotifyPlusPlayerSetShuffleMode_Handler
from .spotifyplusplayersetvolumelevel_handler import SpotifyPlusPlayerSetVolumeLevel_Handler
from .spotifyplusvolumedown_handler import SpotifyPlusVolumeDown_Handler
from .spotifyplusvolumemuteoff_handler import SpotifyPlusVolumeMuteOff_Handler
from .spotifyplusvolumemuteon_handler import SpotifyPlusVolumeMuteOn_Handler
from .spotifyplusvolumesetstep_handler import SpotifyPlusVolumeSetStep_Handler
from .spotifyplusvolumeup_handler import SpotifyPlusVolumeUp_Handler

# all classes to import when "import *" is specified.
__all__ = [
    'SpotifyPlusFavoriteArtistAdd_Handler',
    'SpotifyPlusFavoriteArtistRemove_Handler',
    'SpotifyPlusFavoriteTrackAdd_Handler',
    'SpotifyPlusFavoriteTrackRemove_Handler',
    'SpotifyPlusGetInfoArtistBio_Handler',
    'SpotifyPlusNowPlayingInfoArtistBio_Handler',
    'SpotifyPlusNowPlayingInfoAudiobook_Handler',
    'SpotifyPlusNowPlayingInfoPodcast_Handler',
    'SpotifyPlusNowPlayingInfoTrack_Handler',
    'SpotifyPlusPlayerMediaPause_Handler',
    'SpotifyPlusPlayerMediaResume_Handler',
    'SpotifyPlusPlayerMediaSkipNext_Handler',
    'SpotifyPlusPlayerMediaSkipPrevious_Handler',
    'SpotifyPlusPlayerMediaSkipStart_Handler',
    'SpotifyPlusPlayerSetRepeatMode_Handler',
    'SpotifyPlusPlayerSetShuffleMode_Handler',
    'SpotifyPlusPlayerSetVolumeLevel_Handler',
    'SpotifyPlusVolumeDown_Handler',
    'SpotifyPlusVolumeMuteOff_Handler',
    'SpotifyPlusVolumeMuteOn_Handler',
    'SpotifyPlusVolumeSetStep_Handler',
    'SpotifyPlusVolumeUp_Handler',
]
