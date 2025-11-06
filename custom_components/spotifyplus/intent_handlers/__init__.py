# """ Intent handlers namespace. """

# import all classes from the namespace.
from .spotifyplusfavoriteaddremove_handler import SpotifyPlusFavoriteAddRemove_Handler
from .spotifyplusgetinfoartistbio_handler import SpotifyPlusGetInfoArtistBio_Handler
from .spotifyplusgetnowplayinginfo_handler import SpotifyPlusGetNowPlayingInfo_Handler
from .spotifyplusplayermediapause_handler import SpotifyPlusPlayerMediaPause_Handler
from .spotifyplusplayermediaresume_handler import SpotifyPlusPlayerMediaResume_Handler
from .spotifyplusplayermediaskipnext_handler import SpotifyPlusPlayerMediaSkipNext_Handler
from .spotifyplusplayermediaskipprevious_handler import SpotifyPlusPlayerMediaSkipPrevious_Handler
from .spotifyplusplayermediaskipstart_handler import SpotifyPlusPlayerMediaSkipStart_Handler
from .spotifyplusplayersetrepeatmode_handler import SpotifyPlusPlayerSetRepeatMode_Handler
from .spotifyplusplayersetshufflemode_handler import SpotifyPlusPlayerSetShuffleMode_Handler
from .spotifyplusplayersetvolumelevel_handler import SpotifyPlusPlayerSetVolumeLevel_Handler
from .spotifyplusplayertransferplayback_handler import SpotifyPlusPlayerTransferPlayback_Handler
from .spotifyplusplayfavoritetracks_handler import SpotifyPlusPlayFavoriteTracks_Handler
from .spotifyplusplaylistcreate_handler import SpotifyPlusPlaylistCreate_Handler
from .spotifyplussearchplayartistalbum_handler import SpotifyPlusSearchPlayArtistAlbum_Handler
from .spotifyplussearchplayartisttrack_handler import SpotifyPlusSearchPlayArtistTrack_Handler
from .spotifyplussearchplayaudiobook_handler import SpotifyPlusSearchPlayAudiobook_Handler
from .spotifyplussearchplayplaylist_handler import SpotifyPlusSearchPlayPlaylist_Handler
from .spotifyplussearchplaypodcast_handler import SpotifyPlusSearchPlayPodcast_Handler
from .spotifyplussearchplaypodcastepisode_handler import SpotifyPlusSearchPlayPodcastEpisode_Handler
from .spotifyplussearchplaytrack_handler import SpotifyPlusSearchPlayTrack_Handler
from .spotifyplusvolumedown_handler import SpotifyPlusVolumeDown_Handler
from .spotifyplusvolumemuteoff_handler import SpotifyPlusVolumeMuteOff_Handler
from .spotifyplusvolumemuteon_handler import SpotifyPlusVolumeMuteOn_Handler
from .spotifyplusvolumesetstep_handler import SpotifyPlusVolumeSetStep_Handler
from .spotifyplusvolumeup_handler import SpotifyPlusVolumeUp_Handler

# all classes to import when "import *" is specified.
__all__ = [
    'SpotifyPlusFavoriteAddRemove_Handler',
    'SpotifyPlusGetInfoArtistBio_Handler',
    'SpotifyPlusGetNowPlayingInfo_Handler',
    'SpotifyPlusPlayerMediaPause_Handler',
    'SpotifyPlusPlayerMediaResume_Handler',
    'SpotifyPlusPlayerMediaSkipNext_Handler',
    'SpotifyPlusPlayerMediaSkipPrevious_Handler',
    'SpotifyPlusPlayerMediaSkipStart_Handler',
    'SpotifyPlusPlayerSetRepeatMode_Handler',
    'SpotifyPlusPlayerSetShuffleMode_Handler',
    'SpotifyPlusPlayerSetVolumeLevel_Handler',
    'SpotifyPlusPlayerTransferPlayback_Handler',
    'SpotifyPlusPlayFavoriteTracks_Handler',
    'SpotifyPlusPlaylistCreate_Handler',
    'SpotifyPlusSearchPlayArtistAlbum_Handler',
    'SpotifyPlusSearchPlayArtistTrack_Handler',
    'SpotifyPlusSearchPlayAudiobook_Handler',
    'SpotifyPlusSearchPlayPlaylist_Handler',
    'SpotifyPlusSearchPlayPodcast_Handler',
    'SpotifyPlusSearchPlayPodcastEpisode_Handler',
    'SpotifyPlusSearchPlayTrack_Handler',
    'SpotifyPlusVolumeDown_Handler',
    'SpotifyPlusVolumeMuteOff_Handler',
    'SpotifyPlusVolumeMuteOn_Handler',
    'SpotifyPlusVolumeSetStep_Handler',
    'SpotifyPlusVolumeUp_Handler',
]
