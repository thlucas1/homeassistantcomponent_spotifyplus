"""
Constants for the SpotifyPlus component.
"""
import logging
from homeassistant.components.media_player import MediaType

DOMAIN = "spotifyplus"
""" Domain identifier for this integration. """

DOMAIN_SCRIPT = "script"
""" Domain identifier for script integration. """

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
