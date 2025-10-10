"""
Constants for the SpotifyPlus component.
"""
import logging
from homeassistant.components.media_player import MediaType

DOMAIN = "spotifyplus"
""" Domain identifier for this integration (spotifyplus). """

PLATFORM_SPOTIFYPLUS = DOMAIN
""" Platform identifier for this integration (spotifyplus). """

DOMAIN_SCRIPT = "script"
""" Domain identifier for script integration (script). """

DOMAIN_MEDIA_PLAYER:str = "media_player"
""" Domain identifier for media players (media_player). """

LOGGER = logging.getLogger(__package__)

CONF_OPTION_ALWAYS_ON = "always_on"
CONF_OPTION_DEVICE_DEFAULT = "device_default"
CONF_OPTION_DEVICE_LOGINID = "device_loginid"
CONF_OPTION_DEVICE_PASSWORD = "device_password"
CONF_OPTION_DEVICE_USERNAME = "device_username"
CONF_OPTION_SCRIPT_TURN_ON = "script_turn_on"
CONF_OPTION_SCRIPT_TURN_OFF = "script_turn_off"
CONF_OPTION_SOURCE_LIST_HIDE = "source_list_hide"
CONF_OPTION_SPOTIFY_SCAN_INTERVAL = "spotify_scan_interval"
CONF_OPTION_TURN_OFF_AUTO_PAUSE = "turn_off_auto_pause"
CONF_OPTION_TURN_ON_AUTO_RESUME = "turn_on_auto_resume"
CONF_OPTION_TURN_ON_AUTO_SOURCE_SELECT = "turn_on_auto_source_select"

DEFAULT_OPTION_SPOTIFY_SCAN_INTERVAL = 30

# security scopes required by various Spotify Web API endpoints.
SPOTIFY_SCOPES:list = \
[
    'playlist-modify-private',
    'playlist-modify-public',
    'playlist-read-collaborative',
    'playlist-read-private',
    'ugc-image-upload',
    'user-follow-modify',
    'user-follow-read',
    'user-library-modify',
    'user-library-read',
    'user-modify-playback-state',
    'user-read-currently-playing',
    'user-read-email',
    'user-read-playback-position',
    'user-read-playback-state',
    'user-read-private',
    'user-read-recently-played',
    'user-top-read'
]

# -----------------------------------------------------------------------------------
# Custom Service identifiers.
# -----------------------------------------------------------------------------------
SERVICE_SPOTIFY_ADD_PLAYER_QUEUE_ITEMS:str = 'add_player_queue_items'
SERVICE_SPOTIFY_CHECK_ALBUM_FAVORITES:str = 'check_album_favorites'
SERVICE_SPOTIFY_CHECK_ARTISTS_FOLLOWING:str = 'check_artists_following'
SERVICE_SPOTIFY_CHECK_AUDIOBOOK_FAVORITES:str = 'check_audiobook_favorites'
SERVICE_SPOTIFY_CHECK_EPISODE_FAVORITES:str = 'check_episode_favorites'
SERVICE_SPOTIFY_CHECK_PLAYLIST_FOLLOWERS:str = 'check_playlist_followers'
SERVICE_SPOTIFY_CHECK_SHOW_FAVORITES:str = 'check_show_favorites'
SERVICE_SPOTIFY_CHECK_TRACK_FAVORITES:str = 'check_track_favorites'
SERVICE_SPOTIFY_CHECK_USERS_FOLLOWING:str = 'check_users_following'
SERVICE_SPOTIFY_FOLLOW_ARTISTS:str = 'follow_artists'
SERVICE_SPOTIFY_FOLLOW_PLAYLIST:str = 'follow_playlist'
SERVICE_SPOTIFY_FOLLOW_USERS:str = 'follow_users'
SERVICE_SPOTIFY_GET_ALBUM:str = 'get_album'
SERVICE_SPOTIFY_GET_ALBUM_FAVORITES:str = 'get_album_favorites'
SERVICE_SPOTIFY_GET_ALBUM_NEW_RELEASES:str = 'get_album_new_releases'
SERVICE_SPOTIFY_GET_ALBUM_TRACKS:str = 'get_album_tracks'
SERVICE_SPOTIFY_GET_ARTIST:str = 'get_artist'
SERVICE_SPOTIFY_GET_ARTIST_ALBUMS:str = 'get_artist_albums'
SERVICE_SPOTIFY_GET_ARTIST_INFO:str = 'get_artist_info'
SERVICE_SPOTIFY_GET_ARTIST_RELATED_ARTISTS:str = 'get_artist_related_artists'
SERVICE_SPOTIFY_GET_ARTIST_TOP_TRACKS:str = 'get_artist_top_tracks'
SERVICE_SPOTIFY_GET_ARTISTS_FOLLOWED:str = 'get_artists_followed'
SERVICE_SPOTIFY_GET_AUDIOBOOK:str = 'get_audiobook'
SERVICE_SPOTIFY_GET_AUDIOBOOK_CHAPTERS:str = 'get_audiobook_chapters'
SERVICE_SPOTIFY_GET_AUDIOBOOK_FAVORITES:str = 'get_audiobook_favorites'
SERVICE_SPOTIFY_GET_BROWSE_CATEGORYS_LIST:str = 'get_browse_categorys_list'
SERVICE_SPOTIFY_GET_CATEGORY_PLAYLISTS:str = 'get_category_playlists'
SERVICE_SPOTIFY_GET_CHAPTER:str = 'get_chapter'
SERVICE_SPOTIFY_GET_COVER_IMAGE_FILE:str = 'get_cover_image_file'
SERVICE_SPOTIFY_GET_EPISODE:str = 'get_episode'
SERVICE_SPOTIFY_GET_EPISODE_FAVORITES:str = 'get_episode_favorites'
SERVICE_SPOTIFY_GET_FEATURED_PLAYLISTS:str = 'get_featured_playlists'
SERVICE_SPOTIFY_GET_ID_FROM_URI:str = 'get_id_from_uri'
SERVICE_SPOTIFY_GET_IMAGE_PALETTE_COLORS:str = 'get_image_palette_colors'
SERVICE_SPOTIFY_GET_IMAGE_VIBRANT_COLORS:str = 'get_image_vibrant_colors'
SERVICE_SPOTIFY_GET_PLAYER_DEVICES:str = 'get_player_devices'
SERVICE_SPOTIFY_GET_PLAYER_LAST_PLAYED_INFO:str = 'get_player_last_played_info'
SERVICE_SPOTIFY_GET_PLAYER_NOW_PLAYING:str = 'get_player_now_playing'
SERVICE_SPOTIFY_GET_PLAYER_PLAYBACK_STATE:str = 'get_player_playback_state'
SERVICE_SPOTIFY_GET_PLAYER_QUEUE_INFO:str = 'get_player_queue_info'
SERVICE_SPOTIFY_GET_PLAYER_RECENT_TRACKS:str = 'get_player_recent_tracks'
SERVICE_SPOTIFY_GET_PLAYLIST:str = 'get_playlist'
SERVICE_SPOTIFY_GET_PLAYLIST_COVER_IMAGE:str = 'get_playlist_cover_image'
SERVICE_SPOTIFY_GET_PLAYLIST_FAVORITES:str = 'get_playlist_favorites'
SERVICE_SPOTIFY_GET_PLAYLIST_ITEMS:str = 'get_playlist_items'
SERVICE_SPOTIFY_GET_PLAYLISTS_FOR_USER:str = 'get_playlists_for_user'
SERVICE_SPOTIFY_GET_SHOW:str = 'get_show'
SERVICE_SPOTIFY_GET_SHOW_EPISODES:str = 'get_show_episodes'
SERVICE_SPOTIFY_GET_SHOW_FAVORITES:str = 'get_show_favorites'
SERVICE_SPOTIFY_GET_SPOTIFY_CONNECT_DEVICE:str = 'get_spotify_connect_device'
SERVICE_SPOTIFY_GET_SPOTIFY_CONNECT_DEVICES:str = 'get_spotify_connect_devices'
SERVICE_SPOTIFY_GET_TRACK:str = 'get_track'
SERVICE_SPOTIFY_GET_TRACK_AUDIO_FEATURES:str = 'get_track_audio_features'
SERVICE_SPOTIFY_GET_TRACK_FAVORITES:str = 'get_track_favorites'
SERVICE_SPOTIFY_GET_TRACK_RECOMMENDATIONS:str = 'get_track_recommendations'
SERVICE_SPOTIFY_GET_TRACKS_AUDIO_FEATURES:str = 'get_tracks_audio_features'
SERVICE_SPOTIFY_GET_USERS_TOP_ARTISTS:str = 'get_users_top_artists'
SERVICE_SPOTIFY_GET_USERS_TOP_TRACKS:str = 'get_users_top_tracks'
SERVICE_SPOTIFY_PLAYER_MEDIA_PAUSE:str = 'player_media_pause'
SERVICE_SPOTIFY_PLAYER_MEDIA_PLAY_CONTEXT:str = 'player_media_play_context'
SERVICE_SPOTIFY_PLAYER_MEDIA_PLAY_TRACK_FAVORITES:str = 'player_media_play_track_favorites'
SERVICE_SPOTIFY_PLAYER_MEDIA_PLAY_TRACKS:str = 'player_media_play_tracks'
SERVICE_SPOTIFY_PLAYER_MEDIA_RESUME:str = 'player_media_resume'
SERVICE_SPOTIFY_PLAYER_MEDIA_SEEK:str = 'player_media_seek'
SERVICE_SPOTIFY_PLAYER_MEDIA_SKIP_NEXT:str = 'player_media_skip_next'
SERVICE_SPOTIFY_PLAYER_MEDIA_SKIP_PREVIOUS:str = 'player_media_skip_previous'
SERVICE_SPOTIFY_PLAYER_SET_REPEAT_MODE:str = 'player_set_repeat_mode'
SERVICE_SPOTIFY_PLAYER_SET_SHUFFLE_MODE:str = 'player_set_shuffle_mode'
SERVICE_SPOTIFY_PLAYER_SET_VOLUME_LEVEL:str = 'player_set_volume_level'
SERVICE_SPOTIFY_PLAYER_TRANSFER_PLAYBACK:str = 'player_transfer_playback'
SERVICE_SPOTIFY_PLAYLIST_CHANGE:str = 'playlist_change'
SERVICE_SPOTIFY_PLAYLIST_COVER_IMAGE_ADD:str = 'playlist_cover_image_add'
SERVICE_SPOTIFY_PLAYLIST_CREATE:str = 'playlist_create'
SERVICE_SPOTIFY_PLAYLIST_ITEMS_ADD:str = 'playlist_items_add'
SERVICE_SPOTIFY_PLAYLIST_ITEMS_CLEAR:str = 'playlist_items_clear'
SERVICE_SPOTIFY_PLAYLIST_ITEMS_REMOVE:str = 'playlist_items_remove'
SERVICE_SPOTIFY_PLAYLIST_ITEMS_REORDER:str = 'playlist_items_reorder'
SERVICE_SPOTIFY_PLAYLIST_ITEMS_REPLACE:str = 'playlist_items_replace'
SERVICE_SPOTIFY_REMOVE_ALBUM_FAVORITES:str = 'remove_album_favorites'
SERVICE_SPOTIFY_REMOVE_AUDIOBOOK_FAVORITES:str = 'remove_audiobook_favorites'
SERVICE_SPOTIFY_REMOVE_EPISODE_FAVORITES:str = 'remove_episode_favorites'
SERVICE_SPOTIFY_REMOVE_SHOW_FAVORITES:str = 'remove_show_favorites'
SERVICE_SPOTIFY_REMOVE_TRACK_FAVORITES:str = 'remove_track_favorites'
SERVICE_SPOTIFY_SAVE_ALBUM_FAVORITES:str = 'save_album_favorites'
SERVICE_SPOTIFY_SAVE_AUDIOBOOK_FAVORITES:str = 'save_audiobook_favorites'
SERVICE_SPOTIFY_SAVE_EPISODE_FAVORITES:str = 'save_episode_favorites'
SERVICE_SPOTIFY_SAVE_SHOW_FAVORITES:str = 'save_show_favorites'
SERVICE_SPOTIFY_SAVE_TRACK_FAVORITES:str = 'save_track_favorites'
SERVICE_SPOTIFY_SEARCH_ALL:str = 'search_all'
SERVICE_SPOTIFY_SEARCH_ALBUMS:str = 'search_albums'
SERVICE_SPOTIFY_SEARCH_ARTISTS:str = 'search_artists'
SERVICE_SPOTIFY_SEARCH_AUDIOBOOKS:str = 'search_audiobooks'
SERVICE_SPOTIFY_SEARCH_EPISODES:str = 'search_episodes'
SERVICE_SPOTIFY_SEARCH_PLAYLISTS:str = 'search_playlists'
SERVICE_SPOTIFY_SEARCH_SHOWS:str = 'search_shows'
SERVICE_SPOTIFY_SEARCH_TRACKS:str = 'search_tracks'
SERVICE_SPOTIFY_TRIGGER_SCAN_INTERVAL:str = 'trigger_scan_interval'
SERVICE_SPOTIFY_UNFOLLOW_ARTISTS:str = 'unfollow_artists'
SERVICE_SPOTIFY_UNFOLLOW_PLAYLIST:str = 'unfollow_playlist'
SERVICE_SPOTIFY_UNFOLLOW_USERS:str = 'unfollow_users'
SERVICE_SPOTIFY_ZEROCONF_DEVICE_CONNECT:str = 'zeroconf_device_connect'
SERVICE_SPOTIFY_ZEROCONF_DEVICE_DISCONNECT:str = 'zeroconf_device_disconnect'
SERVICE_SPOTIFY_ZEROCONF_DEVICE_GETINFO:str = 'zeroconf_device_getinfo'
SERVICE_SPOTIFY_ZEROCONF_DISCOVER_DEVICES:str = 'zeroconf_discover_devices'

# -----------------------------------------------------------------------------------
# Configuration constants.
# -----------------------------------------------------------------------------------
CONF_AREA:str = "area"
CONF_FLOOR:str = "floor"
CONF_NAME:str = "name"
CONF_DEVICE_NAME:str = "device_name"
CONF_TEXT:str = "text"
CONF_VALUE:str = "value"
CONF_TARGET_PLAYER:str = "target_player"

# -----------------------------------------------------------------------------------
# Intent Handler identifiers.
# -----------------------------------------------------------------------------------
INTENT_PLAYER_MEDIA_SKIP_NEXT = "SpotifyPlusPlayerMediaSkipNext"
INTENT_PLAYER_MEDIA_SKIP_PREVIOUS = "SpotifyPlusPlayerMediaSkipPrevious"

# -----------------------------------------------------------------------------------
# Intent Handler response codes.
# -----------------------------------------------------------------------------------
RESPONSE_OK:str = "default"
RESPONSE_ERROR_UNHANDLED:str = "error_unhandled"
RESPONSE_PLAYER_FEATURES_NOT_SUPPORTED:str = "player_features_not_supported"
RESPONSE_PLAYER_NOT_EXPOSED_TO_VOICE:str = "player_not_exposed_to_voice"
RESPONSE_PLAYER_NOT_MATCHED:str = "player_not_matched"
RESPONSE_PLAYER_NOT_MATCHED_AREA:str = "player_not_matched_area"
RESPONSE_PLAYER_NOT_PLAYING_MEDIA:str = "player_not_playing_media"
RESPONSE_PLAYER_NOT_SPOTIFYPLUS:str = "player_not_spotifyplus"
