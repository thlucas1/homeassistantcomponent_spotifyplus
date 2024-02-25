"""
Constants for the SpotifyPlus component.
"""
import logging
from homeassistant.components.media_player import MediaType

DOMAIN = "spotifyplus"
""" Domain identifier for this integration. """

LOGGER = logging.getLogger(__package__)

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
