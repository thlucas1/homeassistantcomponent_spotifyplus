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
from .spotifyplusplayfavoritetracks_handler import SpotifyPlusPlayFavoriteTracks_Handler
from .spotifyplusplaylistcreate_handler import SpotifyPlusPlaylistCreate_Handler
from .spotifyplussearchplayartistalbum_handler import SpotifyPlusSearchPlayArtistAlbum_Handler
from .spotifyplussearchplayartisttrack_handler import SpotifyPlusSearchPlayArtistTrack_Handler
from .spotifyplussearchplayaudiobook_handler import SpotifyPlusSearchPlayAudiobook_Handler
from .spotifyplussearchplayplaylist_handler import SpotifyPlusSearchPlayPlaylist_Handler
from .spotifyplussearchplaypodcast_handler import SpotifyPlusSearchPlayPodcast_Handler
from .spotifyplussearchplaypodcastepisode_handler import SpotifyPlusSearchPlayPodcastEpisode_Handler
from .spotifyplussearchplaytrack_handler import SpotifyPlusSearchPlayTrack_Handler

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
    'SpotifyPlusPlayFavoriteTracks_Handler',
    'SpotifyPlusPlaylistCreate_Handler',
    'SpotifyPlusSearchPlayArtistAlbum_Handler',
    'SpotifyPlusSearchPlayArtistTrack_Handler',
    'SpotifyPlusSearchPlayAudiobook_Handler',
    'SpotifyPlusSearchPlayPlaylist_Handler',
    'SpotifyPlusSearchPlayPodcast_Handler',
    'SpotifyPlusSearchPlayPodcastEpisode_Handler',
    'SpotifyPlusSearchPlayTrack_Handler',
]
