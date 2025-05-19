from dataclasses import dataclass
from types import MappingProxyType
from typing import Any
import threading

from spotifywebapipython import SpotifyClient
from spotifywebapipython.models import SpotifyConnectDevices

from homeassistant.components.media_player import MediaPlayerEntity
from homeassistant.helpers.config_entry_oauth2_flow import (
    OAuth2Session
)

from .const import (
    CONF_OPTION_ALWAYS_ON,
    CONF_OPTION_DEVICE_DEFAULT,
    CONF_OPTION_DEVICE_LOGINID,
    CONF_OPTION_DEVICE_PASSWORD,
    CONF_OPTION_DEVICE_USERNAME,
    CONF_OPTION_SCRIPT_TURN_OFF,
    CONF_OPTION_SCRIPT_TURN_ON,
    CONF_OPTION_SOURCE_LIST_HIDE,
    CONF_OPTION_SPOTIFY_SCAN_INTERVAL,
    CONF_OPTION_TURN_OFF_AUTO_PAUSE,
    CONF_OPTION_TURN_ON_AUTO_RESUME,
    CONF_OPTION_TURN_ON_AUTO_SOURCE_SELECT,
    DEFAULT_OPTION_SPOTIFY_SCAN_INTERVAL,
)

@dataclass
class InstanceDataSpotifyPlus:
    """ 
    SpotifyPlus instance data stored in the Home Assistant data object.

    This contains various attributes and object instances that the integration needs
    to function.  It is created in `__init__.py`, and referenced in various other
    modules.
    """
       
    media_player: MediaPlayerEntity
    """
    The media player instance used to control media playback.
    """
    
    options: MappingProxyType[str, Any]
    """
    Configuration entry options.
    """

    session: OAuth2Session
    """
    The OAuth2 session used to communicate with the Spotify Web API.
    """

    spotifyClient: SpotifyClient
    """
    The SpotifyClient instance used to interface with the Spotify Web API.
    """

    tokenUpdater_lock: threading.Lock
    """
    Thread Lock object used to lock token refresh updates.
    """
    

    @property
    def OptionAlwaysOn(self) -> int:
        """
        True if player state should never be set to OFF;
        Otherwise, False to allow turn on / off of the player.
        Defaults to False if not set.

        If True, the player TURN_ON / TURN_OFF features are disabled will not be able
        to be called via the corresponding services.
        """
        return self.options.get(CONF_OPTION_ALWAYS_ON, False)

    @property
    def OptionDeviceDefault(self) -> str | None:
        """
        The default Spotify Connect player device.
        """
        return self.options.get(CONF_OPTION_DEVICE_DEFAULT, None)

    @property
    def OptionDeviceLoginId(self) -> str | None:
        """
        The default Spotify Connect loginid to use when connecting to an inactive device.
        """
        return self.options.get(CONF_OPTION_DEVICE_LOGINID, None)

    @property
    def OptionDevicePassword(self) -> str | None:
        """
        The default Spotify Connect password to use when connecting to an inactive device.
        """
        return self.options.get(CONF_OPTION_DEVICE_PASSWORD, None)

    @property
    def OptionDeviceUsername(self) -> str | None:
        """
        The default Spotify Connect username to use when connecting to an inactive device.
        """
        return self.options.get(CONF_OPTION_DEVICE_USERNAME, None)

    @property
    def OptionSpotifyScanInterval(self) -> int:
        """
        Scan Interval (in seconds) to use when querying Spotify Player for current playstate.
        Defaults to 30 (seconds) if not set.
        """
        return self.options.get(CONF_OPTION_SPOTIFY_SCAN_INTERVAL, DEFAULT_OPTION_SPOTIFY_SCAN_INTERVAL)

    @property
    def OptionScriptTurnOff(self) -> str | None:
        """
        Script entity id that will be called to power off the device that plays media content.
        """
        return self.options.get(CONF_OPTION_SCRIPT_TURN_OFF, None)
    
    @property
    def OptionScriptTurnOn(self) -> str | None:
        """
        Script entity id that will be called to power on the device that plays media content.
        """
        return self.options.get(CONF_OPTION_SCRIPT_TURN_ON, None)
    
    @property
    def OptionSourceListHide(self) -> list:
        """
        The list of device names (in lower-case) to hide from the source list.
        """
        result:list = []
        
        # get option value.
        value:str = self.options.get(CONF_OPTION_SOURCE_LIST_HIDE, None)
        
        # build a list from the semi-colon delimited string.
        if value is not None:
            result = value.split(';')
            for idx in range(0, len(result)):
                result[idx] = result[idx].strip().lower()
                
        # return result.
        return result

    @property
    def OptionTurnOffAutoPause(self) -> bool:
        """
        Automatically pause (True) or not (False) the Spotify Player when the media player is turned off.

        This option is only relevant if the player TURN_ON / TURN_OFF features are enabled.
        """
        return self.options.get(CONF_OPTION_TURN_OFF_AUTO_PAUSE, True)

    @property
    def OptionTurnOnAutoResume(self) -> bool:
        """
        Automatically resume (True) or not (False) the Spotify Player when the media player is turned on.

        This option is only relevant if the player TURN_ON / TURN_OFF features are enabled.
        """
        return self.options.get(CONF_OPTION_TURN_ON_AUTO_RESUME, True)

    @property
    def OptionTurnOnAutoSelectSource(self) -> bool:
        """
        Automatically select the source device to transfer playback to (True) or not (False) when the 
        media player is turned on (enabled by default).
        
        If False, then source will be obtained from Spotify Player Playback state.  If there is no active 
        Spotify Player device, then a source will not be selected.

        This option is only relevant if the player TURN_ON / TURN_OFF features are enabled.
        """
        return self.options.get(CONF_OPTION_TURN_ON_AUTO_SOURCE_SELECT, True)
