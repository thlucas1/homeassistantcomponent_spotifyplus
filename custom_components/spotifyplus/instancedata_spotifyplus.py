from dataclasses import dataclass

from spotifywebapipython import SpotifyClient
from spotifywebapipython.models import Device

from homeassistant.components.media_player import MediaPlayerEntity
from homeassistant.helpers.config_entry_oauth2_flow import (
    OAuth2Session
)
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

@dataclass
class InstanceDataSpotifyPlus:
    """ 
    SpotifyPlus instance data stored in the Home Assistant data object.

    This contains various attributes and object instances that the integration needs
    to function.  It is created in `__init__.py`, and referenced in various other
    modules.
    """
    
    devices: DataUpdateCoordinator[list[Device]]
    """
    List of Spotify Connect devices that are available for this Spotify user.
    This property is refreshed every 5 minutes by a DataUpdateCoordinator.
    """
    
    media_player: MediaPlayerEntity
    """
    The media player instance used to control media playback.
    """
    
    session: OAuth2Session
    """
    The OAuth2 session used to communicate with the Spotify Web API.
    """

    spotifyClient: SpotifyClient
    """
    The SpotifyClient instance used to interface with the Spotify Web API.
    """
