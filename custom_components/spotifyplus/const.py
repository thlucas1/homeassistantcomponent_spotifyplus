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

CONF_OPTION_DEVICE_DEFAULT = "device_default"
CONF_OPTION_SCRIPT_TURN_ON = "script_turn_on"
CONF_OPTION_SCRIPT_TURN_OFF = "script_turn_off"

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
