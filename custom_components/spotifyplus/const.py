"""
Constants for the SpotifyPlus component.
"""
import logging

DOMAIN = "spotifyplus"
""" Domain identifier for this integration (spotifyplus). """

PLATFORM_SPOTIFYPLUS = DOMAIN
""" Platform identifier for this integration (spotifyplus). """

DOMAIN_SCRIPT = "script"
""" Domain identifier for script integration (script). """

DOMAIN_MEDIA_PLAYER = "media_player"
""" Domain identifier for media players (media_player). """

SPOTIFY_WEB_URL_PFX = "https://open.spotify.com"

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
# Custom State attribute identifiers.
# -----------------------------------------------------------------------------------
ATTR_SPOTIFYPLUS_ARTIST_URI = "sp_artist_uri"
ATTR_SPOTIFYPLUS_CONTEXT_URI = "sp_context_uri"
ATTR_SPOTIFYPLUS_DEVICE_ID = "sp_device_id"
ATTR_SPOTIFYPLUS_DEVICE_NAME = "sp_device_name"
ATTR_SPOTIFYPLUS_DEVICE_IS_BRAND_SONOS = "sp_device_is_brand_sonos"
ATTR_SPOTIFYPLUS_DEVICE_IS_CHROMECAST = "sp_device_is_chromecast"
ATTR_SPOTIFYPLUS_DEVICE_IS_RESTRICTED = "sp_device_is_restricted"
ATTR_SPOTIFYPLUS_DEVICE_MUSIC_SOURCE = "sp_device_music_source"
ATTR_SPOTIFYPLUS_ITEM_TYPE = "sp_item_type"
ATTR_SPOTIFYPLUS_NOWPLAYING_IMAGE_URL = "sp_nowplaying_image_url"
ATTR_SPOTIFYPLUS_PLAY_TIME_REMAINING_EST = "sp_play_time_remaining_est"
ATTR_SPOTIFYPLUS_PLAYING_TYPE = "sp_playing_type"
ATTR_SPOTIFYPLUS_PLAYLIST_NAME = "sp_playlist_name"
ATTR_SPOTIFYPLUS_PLAYLIST_URI = "sp_playlist_uri"
ATTR_SPOTIFYPLUS_SOURCE_LIST_HIDE = "sp_source_list_hide"
ATTR_SPOTIFYPLUS_TRACK_IS_EXPLICIT = "sp_track_is_explicit"
ATTR_SPOTIFYPLUS_TRACK_URI_ORIGIN = "sp_track_uri_origin"
ATTR_SPOTIFYPLUS_USER_COUNTRY = "sp_user_country"
ATTR_SPOTIFYPLUS_USER_DISPLAY_NAME = "sp_user_display_name"
ATTR_SPOTIFYPLUS_USER_EMAIL = "sp_user_email"
ATTR_SPOTIFYPLUS_USER_HAS_WEB_PLAYER_CREDENTIALS = "sp_user_has_web_player_credentials"
ATTR_SPOTIFYPLUS_USER_ID = "sp_user_id"
ATTR_SPOTIFYPLUS_USER_PRODUCT = "sp_user_product"
ATTR_SPOTIFYPLUS_USER_URI = "sp_user_uri"
ATTR_VOLUME_STEP = "volume_step"

# -----------------------------------------------------------------------------------
# Custom Service identifiers.
# -----------------------------------------------------------------------------------
SERVICE_SPOTIFY_ADD_PLAYER_QUEUE_ITEMS = 'add_player_queue_items'
SERVICE_SPOTIFY_CHECK_ALBUM_FAVORITES = 'check_album_favorites'
SERVICE_SPOTIFY_CHECK_ARTISTS_FOLLOWING = 'check_artists_following'
SERVICE_SPOTIFY_CHECK_AUDIOBOOK_FAVORITES = 'check_audiobook_favorites'
SERVICE_SPOTIFY_CHECK_EPISODE_FAVORITES = 'check_episode_favorites'
SERVICE_SPOTIFY_CHECK_PLAYLIST_FOLLOWERS = 'check_playlist_followers'
SERVICE_SPOTIFY_CHECK_SHOW_FAVORITES = 'check_show_favorites'
SERVICE_SPOTIFY_CHECK_TRACK_FAVORITES = 'check_track_favorites'
SERVICE_SPOTIFY_CHECK_USERS_FOLLOWING = 'check_users_following'
SERVICE_SPOTIFY_FOLLOW_ARTISTS = 'follow_artists'
SERVICE_SPOTIFY_FOLLOW_PLAYLIST = 'follow_playlist'
SERVICE_SPOTIFY_FOLLOW_USERS = 'follow_users'
SERVICE_SPOTIFY_GET_ALBUM = 'get_album'
SERVICE_SPOTIFY_GET_ALBUM_FAVORITES = 'get_album_favorites'
SERVICE_SPOTIFY_GET_ALBUM_NEW_RELEASES = 'get_album_new_releases'
SERVICE_SPOTIFY_GET_ALBUM_TRACKS = 'get_album_tracks'
SERVICE_SPOTIFY_GET_ARTIST = 'get_artist'
SERVICE_SPOTIFY_GET_ARTIST_ALBUMS = 'get_artist_albums'
SERVICE_SPOTIFY_GET_ARTIST_INFO = 'get_artist_info'
SERVICE_SPOTIFY_GET_ARTIST_RELATED_ARTISTS = 'get_artist_related_artists'
SERVICE_SPOTIFY_GET_ARTIST_TOP_TRACKS = 'get_artist_top_tracks'
SERVICE_SPOTIFY_GET_ARTISTS_FOLLOWED = 'get_artists_followed'
SERVICE_SPOTIFY_GET_AUDIOBOOK = 'get_audiobook'
SERVICE_SPOTIFY_GET_AUDIOBOOK_CHAPTERS = 'get_audiobook_chapters'
SERVICE_SPOTIFY_GET_AUDIOBOOK_FAVORITES = 'get_audiobook_favorites'
SERVICE_SPOTIFY_GET_BROWSE_CATEGORYS_LIST = 'get_browse_categorys_list'
SERVICE_SPOTIFY_GET_CATEGORY_PLAYLISTS = 'get_category_playlists'
SERVICE_SPOTIFY_GET_CHAPTER = 'get_chapter'
SERVICE_SPOTIFY_GET_COVER_IMAGE_FILE = 'get_cover_image_file'
SERVICE_SPOTIFY_GET_EPISODE = 'get_episode'
SERVICE_SPOTIFY_GET_EPISODE_FAVORITES = 'get_episode_favorites'
SERVICE_SPOTIFY_GET_FEATURED_PLAYLISTS = 'get_featured_playlists'
SERVICE_SPOTIFY_GET_ID_FROM_URI = 'get_id_from_uri'
SERVICE_SPOTIFY_GET_IMAGE_PALETTE_COLORS = 'get_image_palette_colors'
SERVICE_SPOTIFY_GET_IMAGE_VIBRANT_COLORS = 'get_image_vibrant_colors'
SERVICE_SPOTIFY_GET_PLAYER_DEVICES = 'get_player_devices'
SERVICE_SPOTIFY_GET_PLAYER_LAST_PLAYED_INFO = 'get_player_last_played_info'
SERVICE_SPOTIFY_GET_PLAYER_NOW_PLAYING = 'get_player_now_playing'
SERVICE_SPOTIFY_GET_PLAYER_PLAYBACK_STATE = 'get_player_playback_state'
SERVICE_SPOTIFY_GET_PLAYER_QUEUE_INFO = 'get_player_queue_info'
SERVICE_SPOTIFY_GET_PLAYER_RECENT_TRACKS = 'get_player_recent_tracks'
SERVICE_SPOTIFY_GET_PLAYLIST = 'get_playlist'
SERVICE_SPOTIFY_GET_PLAYLIST_COVER_IMAGE = 'get_playlist_cover_image'
SERVICE_SPOTIFY_GET_PLAYLIST_FAVORITES = 'get_playlist_favorites'
SERVICE_SPOTIFY_GET_PLAYLIST_ITEMS = 'get_playlist_items'
SERVICE_SPOTIFY_GET_PLAYLISTS_FOR_USER = 'get_playlists_for_user'
SERVICE_SPOTIFY_GET_SHOW = 'get_show'
SERVICE_SPOTIFY_GET_SHOW_EPISODES = 'get_show_episodes'
SERVICE_SPOTIFY_GET_SHOW_FAVORITES = 'get_show_favorites'
SERVICE_SPOTIFY_GET_SPOTIFY_CONNECT_DEVICE = 'get_spotify_connect_device'
SERVICE_SPOTIFY_GET_SPOTIFY_CONNECT_DEVICES = 'get_spotify_connect_devices'
SERVICE_SPOTIFY_GET_TRACK = 'get_track'
SERVICE_SPOTIFY_GET_TRACK_AUDIO_FEATURES = 'get_track_audio_features'
SERVICE_SPOTIFY_GET_TRACK_FAVORITES = 'get_track_favorites'
SERVICE_SPOTIFY_GET_TRACK_RECOMMENDATIONS = 'get_track_recommendations'
SERVICE_SPOTIFY_GET_TRACKS_AUDIO_FEATURES = 'get_tracks_audio_features'
SERVICE_SPOTIFY_GET_USERS_TOP_ARTISTS = 'get_users_top_artists'
SERVICE_SPOTIFY_GET_USERS_TOP_TRACKS = 'get_users_top_tracks'
SERVICE_SPOTIFY_PLAYER_MEDIA_PAUSE = 'player_media_pause'
SERVICE_SPOTIFY_PLAYER_MEDIA_PLAY_CONTEXT = 'player_media_play_context'
SERVICE_SPOTIFY_PLAYER_MEDIA_PLAY_TRACK_FAVORITES = 'player_media_play_track_favorites'
SERVICE_SPOTIFY_PLAYER_MEDIA_PLAY_TRACKS = 'player_media_play_tracks'
SERVICE_SPOTIFY_PLAYER_MEDIA_RESUME = 'player_media_resume'
SERVICE_SPOTIFY_PLAYER_MEDIA_SEEK = 'player_media_seek'
SERVICE_SPOTIFY_PLAYER_MEDIA_SKIP_NEXT = 'player_media_skip_next'
SERVICE_SPOTIFY_PLAYER_MEDIA_SKIP_PREVIOUS = 'player_media_skip_previous'
SERVICE_SPOTIFY_PLAYER_SET_REPEAT_MODE = 'player_set_repeat_mode'
SERVICE_SPOTIFY_PLAYER_SET_SHUFFLE_MODE = 'player_set_shuffle_mode'
SERVICE_SPOTIFY_PLAYER_SET_VOLUME_LEVEL = 'player_set_volume_level'
SERVICE_SPOTIFY_PLAYER_TRANSFER_PLAYBACK = 'player_transfer_playback'
SERVICE_SPOTIFY_PLAYLIST_CHANGE = 'playlist_change'
SERVICE_SPOTIFY_PLAYLIST_COVER_IMAGE_ADD = 'playlist_cover_image_add'
SERVICE_SPOTIFY_PLAYLIST_CREATE = 'playlist_create'
SERVICE_SPOTIFY_PLAYLIST_ITEMS_ADD = 'playlist_items_add'
SERVICE_SPOTIFY_PLAYLIST_ITEMS_CLEAR = 'playlist_items_clear'
SERVICE_SPOTIFY_PLAYLIST_ITEMS_REMOVE = 'playlist_items_remove'
SERVICE_SPOTIFY_PLAYLIST_ITEMS_REORDER = 'playlist_items_reorder'
SERVICE_SPOTIFY_PLAYLIST_ITEMS_REPLACE = 'playlist_items_replace'
SERVICE_SPOTIFY_REMOVE_ALBUM_FAVORITES = 'remove_album_favorites'
SERVICE_SPOTIFY_REMOVE_AUDIOBOOK_FAVORITES = 'remove_audiobook_favorites'
SERVICE_SPOTIFY_REMOVE_EPISODE_FAVORITES = 'remove_episode_favorites'
SERVICE_SPOTIFY_REMOVE_SHOW_FAVORITES = 'remove_show_favorites'
SERVICE_SPOTIFY_REMOVE_TRACK_FAVORITES = 'remove_track_favorites'
SERVICE_SPOTIFY_SAVE_ALBUM_FAVORITES = 'save_album_favorites'
SERVICE_SPOTIFY_SAVE_AUDIOBOOK_FAVORITES = 'save_audiobook_favorites'
SERVICE_SPOTIFY_SAVE_EPISODE_FAVORITES = 'save_episode_favorites'
SERVICE_SPOTIFY_SAVE_SHOW_FAVORITES = 'save_show_favorites'
SERVICE_SPOTIFY_SAVE_TRACK_FAVORITES = 'save_track_favorites'
SERVICE_SPOTIFY_SEARCH_ALL = 'search_all'
SERVICE_SPOTIFY_SEARCH_ALBUMS = 'search_albums'
SERVICE_SPOTIFY_SEARCH_ARTISTS = 'search_artists'
SERVICE_SPOTIFY_SEARCH_AUDIOBOOKS = 'search_audiobooks'
SERVICE_SPOTIFY_SEARCH_EPISODES = 'search_episodes'
SERVICE_SPOTIFY_SEARCH_PLAYLISTS = 'search_playlists'
SERVICE_SPOTIFY_SEARCH_SHOWS = 'search_shows'
SERVICE_SPOTIFY_SEARCH_TRACKS = 'search_tracks'
SERVICE_SPOTIFY_TRIGGER_SCAN_INTERVAL = 'trigger_scan_interval'
SERVICE_SPOTIFY_UNFOLLOW_ARTISTS = 'unfollow_artists'
SERVICE_SPOTIFY_UNFOLLOW_PLAYLIST = 'unfollow_playlist'
SERVICE_SPOTIFY_UNFOLLOW_USERS = 'unfollow_users'
SERVICE_SPOTIFY_ZEROCONF_DEVICE_CONNECT = 'zeroconf_device_connect'
SERVICE_SPOTIFY_ZEROCONF_DEVICE_DISCONNECT = 'zeroconf_device_disconnect'
SERVICE_SPOTIFY_ZEROCONF_DEVICE_GETINFO = 'zeroconf_device_getinfo'
SERVICE_SPOTIFY_ZEROCONF_DISCOVER_DEVICES = 'zeroconf_discover_devices'

# -----------------------------------------------------------------------------------
# Custom Service Schemas - MediaPlayerEntity enhancements.
# -----------------------------------------------------------------------------------
SERVICE_VOLUME_SET_STEP = 'volume_set_step'

# -----------------------------------------------------------------------------------
# Custom Service Schemas - non-Spotify Web API related.
# -----------------------------------------------------------------------------------
SERVICE_LIST_APPLICATION_CREDENTIAL_MAPPPINGS = 'list_application_credential_mappings'
SERVICE_TEST_TOKEN_EXPIRE = 'test_token_expire'

# -----------------------------------------------------------------------------------
# Configuration constants.
# -----------------------------------------------------------------------------------
CONF_ADD = "add"
CONF_ENTITY_ID = "entity_id"
CONF_REMOVE = "remove"
CONF_TEXT = "text"
CONF_VALUE = "value"
CONF_LIMIT_TOTAL_MINIMUM = 5  # ensure more than 1 so that user favorites are considered.

# -----------------------------------------------------------------------------------
# Slot Argument constants.
# -----------------------------------------------------------------------------------
SLOT_AREA = "area"
SLOT_ALBUM_NAME = "album_name"
SLOT_ALBUM_TITLE = "album_title"
SLOT_ALBUM_URL = "album_url"
SLOT_ARTIST_BIO = "artist_bio"
SLOT_ARTIST_NAME = "artist_name"
SLOT_ARTIST_TITLE = "artist_title"
SLOT_ARTIST_URL = "artist_url"
SLOT_AUDIOBOOK_NAME = "audiobook_name"
SLOT_AUDIOBOOK_TITLE = "audiobook_title"
SLOT_AUDIOBOOK_URL = "audiobook_url"
SLOT_AUTHOR_NAME = "author_name"
SLOT_AUTHOR_TITLE = "author_title"
SLOT_CHAPTER_NAME = "chapter_name"
SLOT_CHAPTER_TITLE = "chapter_title"
SLOT_CHAPTER_URL = "chapter_url"
SLOT_CRITERIA_ARG_1 = "criteria_arg_1"
SLOT_CRITERIA_ARG_2 = "criteria_arg_2"
SLOT_DESCRIPTION = "description"
SLOT_DELAY = "delay"
SLOT_DEVICE_NAME = "device_name"
SLOT_DEVICE_TITLE = "device_title"
SLOT_EPISODE_NAME = "episode_name"
SLOT_EPISODE_TITLE = "episode_title"
SLOT_EPISODE_URL = "episode_url"
SLOT_ERROR_FEATURES = "error_features"
SLOT_ERROR_INFO = "error_info"
SLOT_ERROR_STATES = "error_states"
SLOT_FAVORITE_OPERATOR = "favorite_operator"
SLOT_FLOOR = "floor"
SLOT_ID = "id"
SLOT_IMAGE_PATH = "image_path"
SLOT_IS_COLLABORATIVE = "is_collaborative"
SLOT_IS_PUBLIC = "is_public"
SLOT_LATEST_EPISODE = "latest_episode"
SLOT_LIMIT_TOTAL = "limit_total"
SLOT_NAME = "name"
SLOT_PLAYER_REPEAT_MODE = "player_repeat_mode"
SLOT_PLAYER_SHUFFLE_MODE = "player_shuffle_mode"
SLOT_PLAYER_VOLUME_LEVEL_PCT = "player_volume_level_pct"
SLOT_PLAYER_VOLUME_STEP_PCT = "player_volume_step_pct"
SLOT_PLAYLIST_NAME = "playlist_name"
SLOT_PLAYLIST_TITLE = "playlist_title"
SLOT_PLAYLIST_URL = "playlist_url"
SLOT_PODCAST_NAME = "podcast_name"
SLOT_PODCAST_TITLE = "podcast_title"
SLOT_PODCAST_URL = "podcast_url"
SLOT_PREFERRED_AREA_ID = "preferred_area_id"
SLOT_PREFERRED_FLOOR_ID = "preferred_floor_id"
SLOT_SEARCH_CRITERIA = "search_criteria"
SLOT_SPOTIFYPLUS_MEDIA_TYPE = "spotifyplus_media_type"
SLOT_SPOTIFYPLUS_PLAYLIST_NAMES = "spotifyplus_playlist_names"
SLOT_SPOTIFYPLUS_PLAYER_DECK_CONTROL = "spotifyplus_player_deck_control"
SLOT_SPOTIFYPLUS_PLAYER_VOLUME_CONTROL = "spotifyplus_player_volume_control"
SLOT_SPOTIFYPLUS_SEARCH_PLAY_CONTROL = "spotifyplus_search_play_control"
SLOT_SPOTIFYPLUS_SEARCH_PLAY_CONTROL_MULTI = "spotifyplus_search_play_control_multi"
SLOT_SPOTIFYPLUS_SEARCH_PLAY_CONTROL_SINGLE = "spotifyplus_search_play_control_single"
SLOT_TARGET_PLAYER = "target_player"
SLOT_TRACK_NAME = "track_name"
SLOT_TRACK_TITLE = "track_title"
SLOT_TRACK_URL = "track_url"

# -----------------------------------------------------------------------------------
# Intent Handler identifiers.
# -----------------------------------------------------------------------------------
INTENT_FAVORITE_ADD_REMOVE = "SpotifyPlusFavoriteAddRemove"
INTENT_GET_INFO_ARTIST_BIO = "SpotifyPlusGetInfoArtistBio"
INTENT_GET_NOWPLAYING_INFO = "SpotifyPlusGetNowPlayingInfo"
INTENT_PLAYER_DECK_CONTROL = "SpotifyPlusPlayerDeckControl"
INTENT_PLAYER_SET_REPEAT_MODE = "SpotifyPlusPlayerSetRepeatMode"
INTENT_PLAYER_SET_SHUFFLE_MODE = "SpotifyPlusPlayerSetShuffleMode"
INTENT_PLAYER_TRANSFER_PLAYBACK = "SpotifyPlusPlayerTransferPlayback"
INTENT_PLAYER_VOLUME_CONTROL = "SpotifyPlusPlayerVolumeControl"
INTENT_PLAYLIST_CREATE = "SpotifyPlusPlaylistCreate"
INTENT_SEARCH_PLAY_CONTROL = "SpotifyPlusSearchPlayControl"

# -----------------------------------------------------------------------------------
# Intent Handler response codes.
# -----------------------------------------------------------------------------------
RESPONSE_OK = "default"
RESPONSE_ERROR_FAILED_TO_HANDLE = "error_failed_to_handle"
RESPONSE_ERROR_MEDIA_TYPE_INVALID = "error_media_type_invalid"
RESPONSE_ERROR_PLAYER_DECK_CONTROL_INVALID = "error_player_deck_control_invalid"
RESPONSE_ERROR_PLAYER_VOLUME_CONTROL_INVALID = "error_player_volume_control_invalid"
RESPONSE_ERROR_SEARCH_NO_CRITERIA = "error_search_no_criteria"
RESPONSE_ERROR_SEARCH_PLAY_CONTROL_INVALID = "error_search_play_control_invalid"
RESPONSE_FAVORITE_ADD_REMOVE_ALBUM_OK = "favorite_add_remove_album_ok"
RESPONSE_FAVORITE_ADD_REMOVE_ARTIST_OK = "favorite_add_remove_artist_ok"
RESPONSE_FAVORITE_ADD_REMOVE_AUDIOBOOK_OK = "favorite_add_remove_audiobook_ok"
RESPONSE_FAVORITE_ADD_REMOVE_PLAYLIST_OK = "favorite_add_remove_playlist_ok"
RESPONSE_FAVORITE_ADD_REMOVE_PODCAST_OK = "favorite_add_remove_podcast_ok"
RESPONSE_FAVORITE_ADD_REMOVE_PODCAST_EPISODE_OK = "favorite_add_remove_podcast_episode_ok"
RESPONSE_FAVORITE_ADD_REMOVE_TRACK_OK = "favorite_add_remove_track_ok"
RESPONSE_FAVORITE_OPERATION_INVALID = "favorite_operation_invalid"
RESPONSE_GET_INFO_ARTIST_BIO = "get_info_artist_bio"
RESPONSE_NOWPLAYING_NO_MEDIA_ALBUM = "nowplaying_no_media_album"
RESPONSE_NOWPLAYING_NO_MEDIA_ARTIST = "nowplaying_no_media_artist"
RESPONSE_NOWPLAYING_NO_MEDIA_AUDIOBOOK = "nowplaying_no_media_audiobook"
RESPONSE_NOWPLAYING_NO_MEDIA_PLAYLIST = "nowplaying_no_media_playlist"
RESPONSE_NOWPLAYING_NO_MEDIA_PODCAST = "nowplaying_no_media_podcast"
RESPONSE_NOWPLAYING_NO_MEDIA_PODCAST_EPISODE = "nowplaying_no_media_podcast_episode"
RESPONSE_NOWPLAYING_NO_MEDIA_TRACK = "nowplaying_no_media_track"
RESPONSE_NOWPLAYING_INFO_ALBUM = "nowplaying_info_album"
RESPONSE_NOWPLAYING_INFO_AUDIOBOOK = "nowplaying_info_audiobook"
RESPONSE_NOWPLAYING_INFO_PODCAST = "nowplaying_info_podcast"
RESPONSE_NOWPLAYING_INFO_PODCAST_EPISODE = "nowplaying_info_podcast_episode"
RESPONSE_NOWPLAYING_INFO_PLAYLIST = "nowplaying_info_playlist"
RESPONSE_NOWPLAYING_INFO_TRACK = "nowplaying_info_track"
RESPONSE_PLAY_ALBUM = "play_album"
RESPONSE_PLAY_ALBUM_WITH_ARTIST = "play_album_with_artist"
RESPONSE_PLAY_ARTIST = "play_artist"
RESPONSE_PLAY_AUDIOBOOK = "play_audiobook"
RESPONSE_PLAY_AUDIOBOOK_WITH_AUTHOR = "play_audiobook_with_author"
RESPONSE_PLAY_FAVORITE_TRACKS = "play_favorite_tracks"
RESPONSE_PLAY_FAVORITE_TRACKS_FOR_ARTIST = "play_favorite_tracks_for_artist"
RESPONSE_PLAY_PLAYLIST = "play_playlist"
RESPONSE_PLAY_PODCAST = "play_podcast"
RESPONSE_PLAY_PODCAST_EPISODE = "play_podcast_episode"
RESPONSE_PLAY_TRACK = "play_track"
RESPONSE_PLAY_TRACK_WITH_ARTIST = "play_track_with_artist"
RESPONSE_PLAYER_ALREADY_PLAYING_MEDIA = "player_already_playing_media"
RESPONSE_PLAYER_DECK_CONTROL_PAUSE = "player_deck_control_pause"
RESPONSE_PLAYER_DECK_CONTROL_RESUME = "player_deck_control_resume"
RESPONSE_PLAYER_DECK_CONTROL_SEEK_START = "player_deck_control_seek_start"
RESPONSE_PLAYER_DECK_CONTROL_SKIP_NEXT = "player_deck_control_skip_next"
RESPONSE_PLAYER_DECK_CONTROL_SKIP_PREVIOUS = "player_deck_control_skip_previous"
RESPONSE_PLAYER_FEATURES_NOT_SUPPORTED = "player_features_not_supported"
RESPONSE_PLAYER_NOT_EXPOSED_TO_VOICE = "player_not_exposed_to_voice"
RESPONSE_PLAYER_NOT_MATCHED = "player_not_matched"
RESPONSE_PLAYER_NOT_MATCHED_AREA = "player_not_matched_area"
RESPONSE_PLAYER_NOT_PLAYING_MEDIA = "player_not_playing_media"
RESPONSE_PLAYER_NOT_SPOTIFYPLUS = "player_not_spotifyplus"
RESPONSE_PLAYER_VOLUME_CONTROL_DOWN = "player_volume_control_down"
RESPONSE_PLAYER_VOLUME_CONTROL_MUTE = "player_volume_control_mute"
RESPONSE_PLAYER_VOLUME_CONTROL_SET_LEVEL = "player_volume_control_set_level"
RESPONSE_PLAYER_VOLUME_CONTROL_SET_STEP_LEVEL = "player_volume_control_set_step_level"
RESPONSE_PLAYER_VOLUME_CONTROL_UNMUTE = "player_volume_control_unmute"
RESPONSE_PLAYER_VOLUME_CONTROL_UP = "player_volume_control_up"
RESPONSE_PLAYLIST_CREATED = "playlist_created"
RESPONSE_SPOTIFY_NO_ARTIST_INFO = "spotify_no_artist_info"
RESPONSE_SPOTIFY_PREMIUM_REQUIRED = "spotify_premium_required"
RESPONSE_SPOTIFY_SEARCH_NO_ITEMS_ALBUM = "spotify_search_no_items_album"
RESPONSE_SPOTIFY_SEARCH_NO_ITEMS_ARTIST = "spotify_search_no_items_artist"
RESPONSE_SPOTIFY_SEARCH_NO_ITEMS_AUDIOBOOK = "spotify_search_no_items_audiobook"
RESPONSE_SPOTIFY_SEARCH_NO_ITEMS_PLAYLIST = "spotify_search_no_items_playlist"
RESPONSE_SPOTIFY_SEARCH_NO_ITEMS_PODCAST = "spotify_search_no_items_podcast"
RESPONSE_SPOTIFY_SEARCH_NO_ITEMS_PODCAST_EPISODE = "spotify_search_no_items_podcast_episode"
RESPONSE_SPOTIFY_SEARCH_NO_ITEMS_TRACK = "spotify_search_no_items_track"
