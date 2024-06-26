"""Support for interacting with Spotify Connect."""

# Important notes about HA State writes:
#
# `self.async_write_ha_state()` should always be used inside of the event loop (any method that is async itself or a callback). 
# If you are in a `async def` method or one wrapped in `@callback`, use `async_write_ha_state` since you are inside of the event loop. 

# `self.schedule_update_ha_state(force_refresh=False)` should be unsed when not inside of the event loop (e.g. for sync functions that are ran 
# inside of the executor thread).  If you are in a `def` method (no async) then use `schedule_update_ha_state` since you are inside of the event loop.

from __future__ import annotations

import datetime as dt
from datetime import timedelta, datetime
from typing import Any, Callable, Concatenate, ParamSpec, TypeVar, Tuple
from yarl import URL

from spotifywebapipython import SpotifyClient, SpotifyDiscovery, SpotifyApiError, SpotifyWebApiError
from spotifywebapipython.zeroconfapi import *
from spotifywebapipython.models import (
    Album,
    AlbumPageSaved,
    AlbumPageSimplified,
    Artist,
    ArtistPage,
    Category,
    CategoryPage,
    Context, 
    Device as PlayerDevice, 
    Episode, 
    EpisodePageSimplified,
    PlayerPlayState, 
    PlayerQueueInfo,
    PlayHistoryPage,
    Playlist, 
    PlaylistPageSimplified, 
    SearchResponse, 
    Show,
    ShowPageSaved,
    SpotifyConnectDevices,
    Track,
    TrackPage,
    TrackPageSaved,
    UserProfile
)

from homeassistant.components.media_player import (
    ATTR_MEDIA_ENQUEUE,
    BrowseMedia,
    MediaPlayerEnqueue,
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
    MediaType,
    RepeatMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError, IntegrationError
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.device_registry import DeviceEntryType
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity_registry import EntityRegistry, RegistryEntry
from homeassistant.util.dt import utcnow

from .appmessages import STAppMessages
from .browse_media import (
    async_browse_media_library_index, 
    BrowsableMedia,
    browse_media_node, 
    PLAYABLE_MEDIA_TYPES,
    SPOTIFY_LIBRARY_MAP
)
from .instancedata_spotifyplus import InstanceDataSpotifyPlus
from .const import (
    DOMAIN, 
    DOMAIN_SCRIPT,
    LOGGER,
)
from .utils import passwordMaskString

# get smartinspect logger reference; create a new session for this module name.
from smartinspectpython.siauto import SIAuto, SILevel, SISession, SIMethodParmListContext, SIColors
_logsi:SISession = SIAuto.Si.GetSession(__name__)
if (_logsi == None):
    _logsi = SIAuto.Si.AddSession(__name__, True)
_logsi.SystemLogger = LOGGER


# our extra state attribute names.
ATTR_SPOTIFYPLUS_DEVICE_ID = "spotifyplus_device_id"
ATTR_SPOTIFYPLUS_DEVICE_NAME = "spotifyplus_device_name"


# annotate the `spotify_exception_handler` callable.
_SpotifyMediaPlayerT = TypeVar("_SpotifyMediaPlayerT", bound="SpotifyMediaPlayer")
_R = TypeVar("_R")
_P = ParamSpec("_P")


SCAN_INTERVAL = timedelta(seconds=1)
""" 
Time interval (in seconds) for HA to scan for status updates. 
Note that the Spotify Web API does not get called every time HA update method is called
though; check update method for logic that controls this.
"""

SPOTIFY_SCAN_INTERVAL:int = 30
""" 
Time interval (in seconds) to scan spotify connect player for updates. 
"""

SPOTIFY_SCAN_INTERVAL_TRACK_ENDSTART:int = 3
""" 
Time interval (in seconds) to scan spotify connect player for updates
due to a track ending / starting.
"""

SPOTIFY_SCAN_INTERVAL_COMMAND:int = 6
""" 
Time interval (in seconds) to scan spotify connect player for updates
due to a player command.  This gives the Spotify Connect Player time to
update its PlayState status.
"""


REPEAT_MODE_MAPPING_TO_HA = {
    "context": RepeatMode.ALL,
    "off": RepeatMode.OFF,
    "track": RepeatMode.ONE,
}
""" maps spotify repeat modes to home assistant repeat modes. """


REPEAT_MODE_MAPPING_TO_SPOTIFY = {
    value: key for key, value in REPEAT_MODE_MAPPING_TO_HA.items()
}
""" maps home assistant repeat modes to spotify repeat modes. """


async def async_setup_entry(hass:HomeAssistant, entry:ConfigEntry, async_add_entities:AddEntitiesCallback) -> None:
    """
    Set up the media player based on a config entry.

    Args:
        hass (HomeAssistant):
            HomeAssistant instance.
        entry (ConfigEntry):
            HomeAssistant configuration entry dictionary.  This contains configuration
            settings for the specific component device entry.
        async_add_entities (AddEntitiesCallback):
            Callback function to add all entities to Home Assistant for this platform.
    
    This function is called as part of the __init__.async_setup_entry event flow,
    which was initiated via the `hass.config_entries.async_forward_entry_setup` call.
    """
    try:

        # trace.
        _logsi.EnterMethod(SILevel.Debug)
        _logsi.LogObject(SILevel.Verbose, "'%s': MediaPlayer async_setup_entry is starting - entry (ConfigEntry) object" % entry.title, entry)

        # get integration instance data from HA datastore.
        data:InstanceDataSpotifyPlus = hass.data[DOMAIN][entry.entry_id]

        # create the platform instance, passing our initialization parameters.
        _logsi.LogVerbose("'%s': MediaPlayer async_setup_entry is creating the SpotifyMediaPlayer instance" % entry.title)
        media_player = SpotifyMediaPlayer(data)

        # add all entities to Home Assistant.
        _logsi.LogVerbose("'%s': MediaPlayer async_setup_entry is adding SpotifyMediaPlayer instance entities to Home Assistant" % entry.title)
        async_add_entities([media_player], True)

        # store the reference to the media player object.
        _logsi.LogVerbose("'%s': MediaPlayer async_setup_entry is storing the SpotifyMediaPlayer reference to hass.data[DOMAIN]" % entry.title)
        hass.data[DOMAIN][entry.entry_id].media_player = media_player
        
        # trace.
        _logsi.LogVerbose("'%s': MediaPlayer async_setup_entry complete" % entry.title)

    except Exception as ex:
        
        # trace.
        _logsi.LogException("'%s': MediaPlayer async_setup_entry exception" % entry.title, ex, logToSystemLogger=False)
        raise

    finally:

        # trace.
        _logsi.LeaveMethod(SILevel.Debug)


def spotify_exception_handler(
        func: Callable[Concatenate[_SpotifyMediaPlayerT, _P], _R]
        ) -> Callable[Concatenate[_SpotifyMediaPlayerT, _P], _R | None]:
    """
    Decorate SpotifyClient calls to handle Spotify exception.

    A decorator that wraps the passed in function, catches Spotify errors,
    aiohttp exceptions and handles the availability of the media player.
    """

    def wrapper(self: _SpotifyMediaPlayerT, *args: _P.args, **kwargs: _P.kwargs) -> _R | None:
        
        try:

            # indicate we are in a command event.
            self._isInCommandEvent = True
            _logsi.WatchDateTime(SILevel.Debug, "HASpotifyCommandEventLastDT", datetime.now())

            # call the function.
            result = func(self, *args, **kwargs)
            
            # do not update HA state in this handler!  doing so causes UI buttons
            # pressed to "toggle" between states.  the "self.schedule_update_ha_state(force_refresh=False)" 
            # call should be done in the individual methods.
            
            # return function result to caller.
            return result

        except HomeAssistantError: raise  # pass handled exceptions on thru
        except ValueError: raise  # pass handled exceptions on thru
        except SpotifyApiError as ex:
            raise HomeAssistantError(ex.Message)
        except SpotifyWebApiError as ex:
            raise HomeAssistantError(ex.Message)
        except Exception as ex:
            _logsi.LogException(None, ex)
            raise HomeAssistantError(str(ex)) from ex
        
        finally:
            
            # indicate we are NOT in a command event.
            self._isInCommandEvent = False

            # media player command was processed, so force a scan window at the next interval.
            _logsi.LogVerbose("'%s': Processed a media player command - forcing a playerState scan window for the next %d updates" % (self.name, SPOTIFY_SCAN_INTERVAL_COMMAND - 1))
            self._commandScanInterval = SPOTIFY_SCAN_INTERVAL_COMMAND

    return wrapper


class SpotifyMediaPlayer(MediaPlayerEntity):
    """
    Representation of a SpotifyPlus media player device.
    """

    def __init__(self, data:InstanceDataSpotifyPlus) -> None:
        """
        Initializes a new instance of the SpotifyPlus media player entity class.
        
        Args:
            data (InstanceDataSpotifyPlus):
                The media player entity instance data parameters that were created
                in the `__init__.async_setup_entry` method.
        """
        methodParms:SIMethodParmListContext = None
        
        try:

            # trace.
            methodParms = _logsi.EnterMethodParmList(SILevel.Debug)
            #methodParms.AppendKeyValue("data.devices", str(data.devices))
            methodParms.AppendKeyValue("data.media_player", str(data.media_player))
            methodParms.AppendKeyValue("data.session", str(data.session))
            methodParms.AppendKeyValue("data.spotifyClient", str(data.spotifyClient))
            _logsi.LogMethodParmList(SILevel.Verbose, "SpotifyMediaPlayer initialization arguments", methodParms)

            # initialize instance storage.
            self._id = data.spotifyClient.UserProfile.Id
            self._playerState:PlayerPlayState = PlayerPlayState()
            self._playlist:Playlist = None
            self.data = data
            self._currentScanInterval:int = 0
            self._commandScanInterval:int = 0
            self._lastKnownTimeRemainingSeconds:int = 0
            self._isInCommandEvent:bool = False
            self._volume_level_saved:float = None

            # initialize base class attributes (MediaPlayerEntity).
            self._attr_icon = "mdi:spotify"
            self._attr_media_image_remotely_accessible = False
            self._attr_state = MediaPlayerState.OFF
            
            # A unique_id for this entity within this domain.
            # Note: This is NOT used to generate the user visible Entity ID used in automations.
            self._attr_unique_id = data.spotifyClient.UserProfile.Id

            # we will set "self._attr_has_entity_name = False", which causes the "self._attr_name"
            # to be used as-is.  use "self._attr_has_entity_name = True", to append the "self._attr_name"
            # value to the end of "DeviceInfo.name" value.
            self._attr_has_entity_name = False
            self._attr_name = f"SpotifyPlus {data.spotifyClient.UserProfile.DisplayName}"
            
            # set device information.
            # this contains information about the device that is partially visible in the UI.
            # for more information see: https://developers.home-assistant.io/docs/device_registry_index/#device-properties
            self._attr_device_info = DeviceInfo(
                identifiers={(DOMAIN, data.spotifyClient.UserProfile.Id)},
                manufacturer="Spotify AB",
                model=f"Spotify {self.data.spotifyClient.UserProfile.Product.capitalize()} Account",
                name=self._attr_name,
                entry_type=DeviceEntryType.SERVICE,
                configuration_url="https://open.spotify.com",
            )
            _logsi.LogDictionary(SILevel.Verbose, "'%s': MediaPlayer device information dictionary" % self.name, self._attr_device_info, prettyPrint=True)

            # set features supported by this media player.
            # most features will NOT be supported if the Spotify user does not have a PREMIUM
            # membership level, as the Spotify Web API requires a premium membership for most 
            # of the player control functions.
            if self.data.spotifyClient.UserProfile.Product == "premium":
                _logsi.LogVerbose("'%s': MediaPlayer is setting supported features for Spotify Premium user" % self.name)
                self._attr_supported_features = MediaPlayerEntityFeature.BROWSE_MEDIA \
                                              | MediaPlayerEntityFeature.MEDIA_ENQUEUE \
                                              | MediaPlayerEntityFeature.NEXT_TRACK \
                                              | MediaPlayerEntityFeature.PAUSE \
                                              | MediaPlayerEntityFeature.PLAY \
                                              | MediaPlayerEntityFeature.PLAY_MEDIA \
                                              | MediaPlayerEntityFeature.PREVIOUS_TRACK \
                                              | MediaPlayerEntityFeature.REPEAT_SET \
                                              | MediaPlayerEntityFeature.SEEK \
                                              | MediaPlayerEntityFeature.SELECT_SOURCE \
                                              | MediaPlayerEntityFeature.SHUFFLE_SET \
                                              | MediaPlayerEntityFeature.TURN_OFF \
                                              | MediaPlayerEntityFeature.TURN_ON \
                                              | MediaPlayerEntityFeature.VOLUME_MUTE \
                                              | MediaPlayerEntityFeature.VOLUME_SET \
                                              | MediaPlayerEntityFeature.VOLUME_STEP
            else:
                _logsi.LogVerbose("'%s': MediaPlayer is setting supported features for Spotify Non-Premium user" % self.name)
                self._attr_supported_features = MediaPlayerEntityFeature.BROWSE_MEDIA \
                                              | MediaPlayerEntityFeature.PLAY \
                                              | MediaPlayerEntityFeature.PLAY_MEDIA \
                                              | MediaPlayerEntityFeature.SELECT_SOURCE \
                                              | MediaPlayerEntityFeature.TURN_OFF \
                                              | MediaPlayerEntityFeature.TURN_ON \
                                              | MediaPlayerEntityFeature.VOLUME_MUTE \
                                              | MediaPlayerEntityFeature.VOLUME_SET \
                                              | MediaPlayerEntityFeature.VOLUME_STEP

            # we will (by default) set polling to true, as the SpotifyClient does not support websockets
            # for player update notifications.
            _logsi.LogVerbose("'%s': MediaPlayer device polling is being enabled, as the device does not support websockets" % self.name)
            self._attr_should_poll = True
        
            # trace.
            _logsi.LogObject(SILevel.Verbose, "'%s': MediaPlayer SpotifyClient object" % self.name, self.data.spotifyClient)
            _logsi.LogObject(SILevel.Verbose, "'%s': MediaPlayer initialization complete" % self.name, self)

        except Exception as ex:
        
            # trace.
            _logsi.LogException("'%s': MediaPlayer initialization exception" % self.name, ex, logToSystemLogger=False)
            raise

        finally:

            # trace.
            _logsi.LeaveMethod(SILevel.Debug)


    @property
    def extra_state_attributes(self) -> dict:
        """ Return entity specific state attributes. """
        # build list of our extra state attributes to return to HA UI.
        attributes = {}
        attributes[ATTR_SPOTIFYPLUS_DEVICE_ID] = "no_device"
        attributes[ATTR_SPOTIFYPLUS_DEVICE_NAME] = "no_device"
        
        # get currently active device id.
        if self._playerState is not None:
            if self._playerState.Device is not None:
                attributes[ATTR_SPOTIFYPLUS_DEVICE_ID] = self._playerState.Device.Id
                attributes[ATTR_SPOTIFYPLUS_DEVICE_NAME] = self._playerState.Device.Name
            if self._playerState.Context is not None:
                attributes['media_context_content_id'] = self._playerState.Context.Uri
                
        # add currently active playlist information.
        if self._playlist is not None:
            attributes['media_playlist_content_id'] = self._playlist.Uri
            
        return attributes


    @property
    def state(self) -> MediaPlayerState:
        """ Return the playback state. """
        return self._attr_state


    @property
    def media_content_id(self) -> str | None:
        """ Return the media URL. """
        return self._attr_media_content_id


    @property
    def media_content_type(self) -> str | None:
        """ Return the media type. """
        return self._attr_media_content_type
    

    @property
    def media_duration(self) -> int | None:
        """ Duration of current playing media in seconds. """
        return self._attr_media_duration


    @property
    def media_position(self) -> int | None:
        """ Position of current playing media in seconds. """
        return self._attr_media_position
    

    @property
    def media_position_updated_at(self) -> dt.datetime | None:
        """ 
        When was the position of the current playing media valid.
        
        Returns value from homeassistant.util.dt.utcnow().
        """
        return self._attr_media_position_updated_at


    @property
    def media_image_url(self) -> str | None:
        """ Return the media image URL. """
        return self._attr_media_image_url
        

    @property
    def media_title(self) -> str | None:
        """ Return the media title. """
        return self._attr_media_title


    @property
    def media_artist(self) -> str | None:
        """ Return the media artist. """
        return self._attr_media_artist


    @property
    def media_album_name(self) -> str | None:
        """ Return the media album. """
        return self._attr_media_album_name


    @property
    def media_track(self) -> int | None:
        """ Track number of current playing media, music track only. """
        return self._attr_media_track


    @property
    def media_playlist(self):
        """ Title of current playing playlist. """
        if self._playlist is not None:
            return self._playlist.Name
        return None


    @property
    def media_playlist_content_id(self):
        """ Content ID of current playing playlist. """
        if self._playlist is not None:
            return self._playlist.Uri
        return None


    @property
    def media_playlist_content_type(self):
        """ Content Type of current playing playlist. """
        if self._playlist is not None:
            return self._playlist.Type
        return None


    @property
    def media_playlist_description(self):
        """ Description of current playing playlist. """
        if self._playlist is not None:
            return self._playlist.Description
        return None


    @property
    def media_playlist_image_url(self):
        """ Image URL of current playing playlist. """
        if self._playlist is not None:
            return self._playlist.ImageUrl
        return None


    @property
    def source(self) -> str | None:
        """ Return the current playback device. """
        return self._attr_source


    @property
    def source_list(self) -> list[str] | None:
        """ Return a list of source devices. """

        # get spotify client cached device list.
        if "GetSpotifyConnectDevices" in self.data.spotifyClient.ConfigurationCache:
            result:SpotifyConnectDevices = self.data.spotifyClient.ConfigurationCache["GetSpotifyConnectDevices"]

            # build list of device names for the source list.
            deviceNames:list[str] = []
            for device in result.GetDeviceList():
                deviceNames.append(device.Name)
            return deviceNames
        
        return None


    @property
    def shuffle(self) -> bool | None:
        """Shuffling state."""
        return self._attr_shuffle


    @property
    def repeat(self) -> RepeatMode | str | None:
        """ Return current repeat mode. """
        return self._attr_repeat
    

    @property
    def volume_level(self) -> float | None:
        """ Volume level of the media player (0.0 to 1.0). """
        return self._attr_volume_level


    @property
    def is_volume_muted(self):
        """ Boolean if volume is currently muted. """
        return self._attr_is_volume_muted


    @spotify_exception_handler
    def media_play(self) -> None:
        """ Start or resume playback. """
        _logsi.LogVerbose(STAppMessages.MSG_MEDIAPLAYER_SERVICE, self.name, "media_play")
        
        # update ha state.
        self._attr_state = MediaPlayerState.PLAYING
        self.schedule_update_ha_state(force_refresh=False)

        # resume playback (use currently active player).
        self.data.spotifyClient.PlayerMediaResume()


    @spotify_exception_handler
    def media_pause(self) -> None:
        """ Pause playback. """
        _logsi.LogVerbose(STAppMessages.MSG_MEDIAPLAYER_SERVICE, self.name, "media_pause")
        
        # update ha state.
        self._attr_state = MediaPlayerState.PAUSED
        self.schedule_update_ha_state(force_refresh=False)
        
        # pause playback (use currently active player).
        self.data.spotifyClient.PlayerMediaPause()


    @spotify_exception_handler
    def media_previous_track(self) -> None:
        """ Skip to previous track. """
        _logsi.LogVerbose(STAppMessages.MSG_MEDIAPLAYER_SERVICE, self.name, "media_previous_track")
        
        # skip to previous track (use currently active player).
        self.data.spotifyClient.PlayerMediaSkipPrevious()


    @spotify_exception_handler
    def media_next_track(self) -> None:
        """ Skip to next track. """
        _logsi.LogVerbose(STAppMessages.MSG_MEDIAPLAYER_SERVICE, self.name, "media_next_track")

        # skip to next track (use currently active player).
        self.data.spotifyClient.PlayerMediaSkipNext()


    @spotify_exception_handler
    def media_seek(self, position: float) -> None:
        """ Send seek command. """
        _logsi.LogVerbose(STAppMessages.MSG_MEDIAPLAYER_SERVICE_WITH_PARMS, self.name, "media_seek", "position='%s'" % (position))

        # update ha state.
        self._attr_media_position = position
        self._attr_media_position_updated_at = utcnow()
        self.schedule_update_ha_state(force_refresh=False)
        
        # seek to track position (use currently active player).
        self.data.spotifyClient.PlayerMediaSeek(int(position * 1000))
        

    @spotify_exception_handler
    def mute_volume(self, mute:bool) -> None:
        """ Send mute command. """
        _logsi.LogVerbose(STAppMessages.MSG_MEDIAPLAYER_SERVICE_WITH_PARMS, self.name, "mute_volume", "mute='%s'" % (mute))

        self._attr_is_volume_muted = mute

        if mute:
            self._volume_level_saved = self._attr_volume_level
            self.schedule_update_ha_state(force_refresh=False)
            self.set_volume_level(0.0)
        else:
            # did we save the volume on a previous mute request?  if not, then default volume.
            if self._volume_level_saved is None or self._volume_level_saved == 0.0:
                _logsi.LogVerbose("Previously saved volume was not set; defaulting to 0.10")
                self._volume_level_saved = 0.10
            self._attr_volume_level = self._volume_level_saved
            self.schedule_update_ha_state(force_refresh=False)
            self.set_volume_level(self._volume_level_saved)
            

    @spotify_exception_handler
    def play_media(self, media_type: MediaType | str, media_id: str, **kwargs: Any) -> None:        
        """ 
        Play media; called by media browser when a browsed item is selected for playing.
        """
        methodParms:SIMethodParmListContext = None
        
        try:

            # trace.
            methodParms = _logsi.EnterMethodParmList(SILevel.Debug)
            methodParms.AppendKeyValue("media_type", media_type)
            methodParms.AppendKeyValue("media_id", media_id)
            methodParms.AppendKeyValue("**kwargs", kwargs)
            _logsi.LogMethodParmList(SILevel.Verbose, STAppMessages.MSG_MEDIAPLAYER_SERVICE % (self.name, "play_media"), methodParms)

            # get enqueue keyword arguments (if any).
            enqueue:MediaPlayerEnqueue = kwargs.get(ATTR_MEDIA_ENQUEUE, None)

            # are we currently powered off?  if so, then power on.
            if self._attr_state == MediaPlayerState.OFF:
                self.turn_on()
                self._isInCommandEvent = True  # turn "in a command event" indicator back on.

            # spotify can't handle URI's with query strings or anchors
            # yet, they do generate those types of URI in their official clients.
            media_id:str = str(URL(media_id).with_query(None).with_fragment(None))

            # is this an enqueue request?
            if enqueue is not None:

                _logsi.LogVerbose("Enqueue command received for this play media request: '%s'" % (enqueue))
                
                if enqueue == MediaPlayerEnqueue.ADD:
                    # add to queue request.
                    _logsi.LogVerbose("Adding uri to Spotify Player Queue: '%s'" % (media_id))
                    self.data.spotifyClient.AddPlayerQueueItem(media_id)
                    return

                elif enqueue == MediaPlayerEnqueue.NEXT:
                    # play next request.
                    _logsi.LogVerbose("Playing next item in the player queue")
                    self.data.spotifyClient.PlayerMediaSkipNext()
                    return
            
                elif enqueue == MediaPlayerEnqueue.PLAY:
                    # play request.
                    pass   # we will handle this below.
            
                elif enqueue == MediaPlayerEnqueue.REPLACE:
                    # play now and clear queue request.
                    pass   # we will handle this below.

                else:
                    _logsi.LogWarning("Spotify Connect Player does not support '%s' enqueue requests; request ignored" % enqueue)
                    return
                
            # if no source selected, then use the default source.
            deviceId:str = self._attr_source    
            if deviceId is None:
                deviceId = "*"
            deviceId = self._GetDefaultDeviceOption(deviceId)
                       
            # start play based upon the media type.
            if media_type in {MediaType.TRACK, MediaType.EPISODE, MediaType.MUSIC}:
                
                self._attr_state = MediaPlayerState.PLAYING
                self.schedule_update_ha_state(force_refresh=False)
                _logsi.LogVerbose("Playing via PlayerMediaPlayTracks: uris='%s', deviceId='%s'" % (media_id, deviceId))
                self.data.spotifyClient.PlayerMediaPlayTracks([media_id], deviceId=deviceId)
                
            elif media_type in PLAYABLE_MEDIA_TYPES:
                
                self._attr_state = MediaPlayerState.PLAYING
                self.schedule_update_ha_state(force_refresh=False)
                _logsi.LogVerbose("Playing via PlayerMediaPlayContext: contextUri='%s', deviceId='%s'" % (media_id, deviceId))
                self.data.spotifyClient.PlayerMediaPlayContext(media_id, deviceId=deviceId)
                
            else:
                
                _logsi.LogWarning("Media type '%s' is not supported" % media_type)
                return

        finally:
        
            # trace.
            _logsi.LeaveMethod(SILevel.Debug)


    @spotify_exception_handler
    def select_source(self, source: str) -> None:
        """ Select playback device. """
        _logsi.LogVerbose(STAppMessages.MSG_MEDIAPLAYER_SERVICE_WITH_PARMS, self.name, "select_source", "source='%s'" % (source))

        # are we currently powered off?  if so, then power on.
        wasTurnedOn:bool = False
        if self._attr_state == MediaPlayerState.OFF:
            self.turn_on()
            wasTurnedOn = True
            # immediately pause (if not already) to ensure media starts playing on the correct device after transfer.
            #self.media_pause()
            self._isInCommandEvent = True  # turn "in a command event" indicator back on.

        if source is not None:
            
            # transfer playback to the specified device if the source was changed.
            if (source != self._attr_source):
                self.data.spotifyClient.PlayerTransferPlayback(source, (self.state == MediaPlayerState.PLAYING))
                self._attr_source = source
           
            # if player was turned on, then start play.
            if wasTurnedOn:
                self.media_play()


    @spotify_exception_handler
    def set_shuffle(self, shuffle: bool) -> None:
        """ Enable/Disable shuffle mode. """
        _logsi.LogVerbose(STAppMessages.MSG_MEDIAPLAYER_SERVICE_WITH_PARMS, self.name, "set_shuffle", "shuffle='%s'" % (shuffle))

        # update ha state.
        self._attr_shuffle = shuffle
        self.schedule_update_ha_state(force_refresh=False)
        
        # set shuffle mode (use currently active player).
        self.data.spotifyClient.PlayerSetShuffleMode(shuffle)


    @spotify_exception_handler
    def set_repeat(self, repeat: RepeatMode) -> None:
        """ Set repeat mode. """
        _logsi.LogVerbose(STAppMessages.MSG_MEDIAPLAYER_SERVICE_WITH_PARMS, self.name, "set_repeat", "repeat='%s'" % (repeat))

        # update ha state.
        if repeat not in REPEAT_MODE_MAPPING_TO_SPOTIFY:
            raise ValueError(f"Unsupported repeat mode: {repeat}")
        self._attr_repeat = repeat
        self.schedule_update_ha_state(force_refresh=False)

        # set repeat mode (use currently active player).
        self.data.spotifyClient.PlayerSetRepeatMode(REPEAT_MODE_MAPPING_TO_SPOTIFY[repeat])


    @spotify_exception_handler
    def set_volume_level(self, volume: float) -> None:
        """ Set the volume level. """
        _logsi.LogVerbose(STAppMessages.MSG_MEDIAPLAYER_SERVICE_WITH_PARMS, self.name, "set_volume_level", "volume='%s'" % (volume))
        
        # validations.
        if volume is None:
            volume = 0.0

        # update ha state.
        self._attr_volume_level = volume
        self.schedule_update_ha_state(force_refresh=False)

        # set volume (use currently active player).
        self.data.spotifyClient.PlayerSetVolume(int(volume * 100))


    @spotify_exception_handler
    def turn_off(self) -> None:
        """ Turn off media player. """ 
        try:

            # trace.
            _logsi.EnterMethod(SILevel.Debug)
            _logsi.LogVerbose(STAppMessages.MSG_MEDIAPLAYER_SERVICE, self.name, "turn_off")
            _logsi.LogVerbose("'%s': entity_id=%s" % (self.name, self.entity_id))

            # set media player state and update ha state.
            self._attr_state = MediaPlayerState.OFF
            _logsi.LogVerbose("'%s': MediaPlayerState set to '%s'" % (self.name, self._attr_state))
            self.schedule_update_ha_state(force_refresh=False)

            # get current player state.
            self._playerState = self.data.spotifyClient.GetPlayerPlaybackState(additionalTypes=MediaType.EPISODE.value)
            _logsi.LogObject(SILevel.Verbose, "'%s': Spotify player state at power off" % self.name, self._playerState, excludeNonPublic=True)
            
            # if playing, then pause playback.
            if (self._playerState.IsPlaying) and (self.data.spotifyClient.UserProfile.IsProductPremium):
                _logsi.LogVerbose("'%s': Pausing Spotify playback on deviceId: %s" % (self.name, self._playerState.Device.Id))
                self.data.spotifyClient.PlayerMediaPause(self._playerState.Device.Id)

            # call script to power off device.
            self._CallScriptPower(self.data.OptionScriptTurnOff, "turn_off")
            
        # the following exceptions have already been logged, so we just need to
        # pass them back to HA for display in the log (or service UI).
        except SpotifyApiError as ex:
            raise HomeAssistantError(ex.Message)
        except SpotifyWebApiError as ex:
            raise HomeAssistantError(ex.Message)
        except Exception as ex:
            _logsi.LogException(None, ex)
            raise HomeAssistantError(str(ex)) from ex
        
        finally:
        
            # update ha state.
            self.schedule_update_ha_state(force_refresh=False)

            # trace.
            _logsi.LeaveMethod(SILevel.Debug)


    @spotify_exception_handler
    def turn_on(self) -> None:
        """ Turn on media player. """
        try:

            # trace.
            _logsi.EnterMethod(SILevel.Debug)
            _logsi.LogVerbose(STAppMessages.MSG_MEDIAPLAYER_SERVICE, self.name, "turn_on")
            
            # if already powered on then we are done.
            if self._attr_state is not MediaPlayerState.OFF:
                _logsi.LogVerbose("'%s': MediaPlayer is already powered on (state=%s); nothing to do" % (self.name, self._attr_state))
                return
            
            # set media player state and update ha state.
            self._attr_state = MediaPlayerState.IDLE
            _logsi.LogVerbose("'%s': MediaPlayerState set to '%s'" % (self.name, self._attr_state))
            self.schedule_update_ha_state(force_refresh=False)

            # call script to power on device.
            self._CallScriptPower(self.data.OptionScriptTurnOn, "turn_on")

            # get current Spotify Connect player state.
            playerStateCurrent:PlayerPlayState = self.data.spotifyClient.GetPlayerPlaybackState()

            # is playing content paused?
            if (playerStateCurrent.Device.Id is not None) \
            and (playerStateCurrent.Actions.Pausing):
                
                # resume play.
                _logsi.LogVerbose("'%s': Resuming playing media" % self.name)
                self.data.spotifyClient.PlayerMediaResume(playerStateCurrent.Device.Id)
            
        # the following exceptions have already been logged, so we just need to
        # pass them back to HA for display in the log (or service UI).
        except SpotifyApiError as ex:
            raise HomeAssistantError(ex.Message)
        except SpotifyWebApiError as ex:
            raise HomeAssistantError(ex.Message)
        except Exception as ex:
            _logsi.LogException(None, ex)
            raise HomeAssistantError(str(ex)) from ex
        
        finally:
        
            # update ha state.
            self.schedule_update_ha_state(force_refresh=False)

            # trace.
            _logsi.LeaveMethod(SILevel.Debug)


    def update(self) -> None:
        """ Update state and attributes. """

        # trace.
        _logsi.WatchDateTime(SILevel.Debug, "HASpotifyUpdateLastDT", datetime.now())
        
        # is the media player enabled?  if not, then there is nothing to do.
        if not self.enabled:
            _logsi.LogVerbose("'%s': Update - Integration is disabled; nothing to do" % self.name)
            return

        # is the media player powered off?  if so, then there is nothing to do.
        if self._attr_state == MediaPlayerState.OFF:
            _logsi.LogVerbose("'%s': Update - Integration is powered off; nothing to do" % self.name)
            return

        # is the media player in a command event?  if so, then exit as updates are
        # happening that we don't want overridden just yet.  
        if self._isInCommandEvent:
            _logsi.LogVerbose("'%s': Update - Integration is in a command event; bypassing update" % self.name)
            return

        try:

            # trace.
            _logsi.EnterMethod(SILevel.Debug)
        
            _logsi.LogVerbose("'%s': Scan interval %d check - commandScanInterval=%d, currentScanInterval=%d, lastKnownTimeRemainingSeconds=%d, state=%s" % (self.name, SPOTIFY_SCAN_INTERVAL, self._commandScanInterval, self._currentScanInterval, self._lastKnownTimeRemainingSeconds, str(self._attr_state)))
            
            # have we reached a scan interval?
            if not ((self._currentScanInterval % SPOTIFY_SCAN_INTERVAL) == 0):

                # no - decrement the current scan interval counts.
                self._currentScanInterval = self._currentScanInterval - 1
                if self._commandScanInterval > 0:
                    self._commandScanInterval = self._commandScanInterval - 1

                # if last known time remaining value is less than current scan interval then
                # use the lesser last known time remaining value as the current scan interval.
                # this can happen when a user seeks to a new position, and the track time
                # remaining is less than the current scan interval.  we will also check the
                # last known time remaining value for greater than zero, as it is zero at startup.
                if (self._lastKnownTimeRemainingSeconds > 0) \
                and (self._lastKnownTimeRemainingSeconds < self._currentScanInterval) \
                and (self._attr_state == MediaPlayerState.PLAYING):
                    self._currentScanInterval = self._lastKnownTimeRemainingSeconds
                    _logsi.LogVerbose("'%s': Resetting current scan interval to last known time remaining value - currentScanInterval=%d, lastKnownTimeRemainingSeconds=%d, state=%s" % (self.name, self._currentScanInterval, self._lastKnownTimeRemainingSeconds, str(self._attr_state)))

                # we will query Spotify for player state if ANY of the following:
                # - we reached a scan interval (e.g. 30 seconds).
                # - within specified seconds of an issued command (e.g. 5 seconds).
                # - within specified seconds of a playing track ending.
                if (self._currentScanInterval == 0) \
                or (self._commandScanInterval > 0 and self._commandScanInterval <= SPOTIFY_SCAN_INTERVAL_COMMAND) \
                or ((self._lastKnownTimeRemainingSeconds <= SPOTIFY_SCAN_INTERVAL_TRACK_ENDSTART) and (self._attr_state == MediaPlayerState.PLAYING)):
                    # yes - allow the update
                    pass
                else:
                    # no - keep waiting to update.
                    return

            # # TEST TODO - force token expire!!!
            # leave the following comments in here, in case you need to test token expire logic.  
            # this will force the token to expire in 30 seconds, instead of the 1 hour Spotify default.
            #
            # _logsi.LogWarning("TEST TODO - Forcing token expiration in 30 seconds for testing purposes", colorValue=SIColors.Red)
            # self.data.spotifyClient.AuthToken._ExpiresIn = 30
            # unix_epoch = datetime(1970, 1, 1)
            # dtUtcNow:datetime = datetime.utcnow()
            # self.data.spotifyClient.AuthToken._ExpireDateTimeUtc = dtUtcNow + timedelta(seconds=self.data.spotifyClient.AuthToken._ExpiresIn)
            # self.data.spotifyClient.AuthToken._ExpiresAt = int((dtUtcNow - unix_epoch).total_seconds())  # seconds from epoch, current date
            # self.data.spotifyClient.AuthToken._ExpiresAt = self.data.spotifyClient.AuthToken._ExpiresAt + self.data.spotifyClient.AuthToken._ExpiresIn             # add ExpiresIn seconds

            # get now playing status.
            _logsi.LogVerbose("'%s': update method - getting Spotify Connect Player state" % self.name)
            self._playerState = self.data.spotifyClient.GetPlayerPlaybackState(additionalTypes=MediaType.EPISODE.value)
            self._UpdateHAFromPlayerPlayState(self._playerState)
            _logsi.WatchDateTime(SILevel.Debug, "HASpotifyPlaystateLastUpdate", datetime.now())
            
            # update the scan interval for next time.
            self._currentScanInterval = SPOTIFY_SCAN_INTERVAL - 1

            # calculate the time (in seconds) remaining on the playing track.
            if self._playerState is not None:
                if self._playerState.Item is not None:
                    track:Track = self._playerState.Item
                    self._lastKnownTimeRemainingSeconds = track.DurationMS - self._playerState.ProgressMS
                    if self._lastKnownTimeRemainingSeconds > 1000:
                        self._lastKnownTimeRemainingSeconds = int(self._lastKnownTimeRemainingSeconds / 1000)  # convert MS to Seconds
                    else:
                        self._lastKnownTimeRemainingSeconds = 0
                    _logsi.LogVerbose("'%s': playerState track ProgressMS=%s, DurationMS=%d, lastKnownTimeRemainingSeconds=%d" % (self.name, self._playerState.ProgressMS, track.DurationMS, self._lastKnownTimeRemainingSeconds))

            # did the now playing context change?
            context:Context = self._playerState.Context
            if (context is not None) and (self._playlist is None or self._playlist.Uri != context.Uri):
                
                # yes - if it's a playlist, then we need to update the stored playlist reference.
                self._playlist = None
                if context.Type == MediaType.PLAYLIST:
                
                    try:
                        
                        _logsi.LogVerbose("Retrieving playlist for context uri '%s'" % context.Uri)
                        spotifyId:str = SpotifyClient.GetIdFromUri(context.Uri)
                        self._playlist = self.data.spotifyClient.GetPlaylist(spotifyId)
                        
                    except Exception as ex:
                        
                        _logsi.LogException("Unable to load spotify playlist '%s'. Continuing without playlist data" % context.Uri, ex)
                        self._playlist = None
                        
                else:
                    
                    self._playlist = None
                    
            elif (context is None):
                
                self._playlist = None
                    
        except SpotifyWebApiError as ex:
            
            _logsi.LogException(None, ex)
            raise HomeAssistantError(ex.Message) from ex
        
        except Exception as ex:

            _logsi.LogException(None, ex)
            raise HomeAssistantError(str(ex)) from ex

        finally:
        
            # trace.
            _logsi.LeaveMethod(SILevel.Debug)


    @callback
    def _handle_devices_update(self) -> None:
        """
        Handle updated data from the coordinator.
        """
        if not self.enabled:
            return
        
        # inform HA of our current state.
        self.schedule_update_ha_state(force_refresh=False)


    def _UpdateHAFromPlayerPlayState(self, playerPlayState:PlayerPlayState) -> None:
        """
        Updates all media_player attributes that have to do with now playing information.
        """
        try:

            # trace.
            _logsi.EnterMethod(SILevel.Debug)
            _logsi.LogObject(SILevel.Verbose, "'%s': Updating HA state from Spotify PlayerPlayState object" % self.name, playerPlayState, excludeNonPublic=True)
        
            # initialize media attributes.
            self._attr_media_album_name = None
            self._attr_media_artist = None
            self._attr_media_content_id = None
            self._attr_media_content_type = None
            self._attr_media_duration = None
            self._attr_media_image_url = None
            self._attr_media_position = None
            self._attr_media_position_updated_at = None
            self._attr_media_title = None
            self._attr_media_track = None
            self._attr_repeat = None
            self._attr_shuffle = None
            self._attr_source = None
            self._attr_volume_level = None
            self._attr_is_volume_muted = None

            # does player state exist?  if not, then we are done.
            if playerPlayState is None:
                _logsi.LogVerbose("'%s': Spotify PlayerPlayState object was not set; nothing to do" % self.name)
                return

            # if player is not OFF, then update media player state.
            if self._attr_state is not MediaPlayerState.OFF:
                if self._isInCommandEvent:
                    pass
                elif playerPlayState.IsPlaying == True:
                    self._attr_state = MediaPlayerState.PLAYING
                elif playerPlayState.IsPlaying == False:
                    self._attr_state = MediaPlayerState.PAUSED
                else:
                    self._attr_state = MediaPlayerState.IDLE
                _logsi.LogVerbose("'%s': MediaPlayerState set to '%s'" % (self.name, self._attr_state))
        
            self._attr_is_volume_muted = playerPlayState.IsMuted
            self._attr_shuffle = playerPlayState.ShuffleState
               
            # update item-related attributes (e.g. track? episode? etc)?
            if playerPlayState.Item is not None:
                item = playerPlayState.Item
                episode:Episode = playerPlayState.Item
                    
                self._attr_media_content_id = item.Uri
                self._attr_media_content_type = item.Type
                self._attr_media_duration = item.DurationMS / 1000
                self._attr_media_title = item.Name
                    
                # update media album name attribute.
                if item.Type == MediaType.EPISODE.value:
                    self._attr_media_album_name = episode.Show.Name
                else:
                    self._attr_media_album_name = item.Album.Name

                # update media artist attribute.
                if item.Type == MediaType.EPISODE.value:
                    self._attr_media_artist = episode.Show.Publisher
                else:
                    self._attr_media_artist = ", ".join(artist.Name for artist in item.Artists)
                        
                # update media content type attribute.
                if item.Type == MediaType.EPISODE.value:
                    self._attr_media_content_type = MediaType.PODCAST 
                else:
                    self._attr_media_content_type = MediaType.MUSIC

                # update media image url attribute.
                # for episodes, use the episode image if present; otherwise use the show image if present.
                # for everything else, use the album image if present.
                if item.Type == MediaType.EPISODE.value:
                    if episode.ImageUrl is not None:
                        self._attr_media_image_url = episode.ImageUrl
                    if episode.Show.ImageUrl is not None:
                        self._attr_media_image_url = episode.Show.ImageUrl
                elif item.Album.ImageUrl is not None:
                    self._attr_media_image_url = item.Album.ImageUrl
                        
                # update media track attribute (will not exist for episodes).
                if item.Type == MediaType.TRACK.value:
                    self._attr_media_track = item.TrackNumber

            # update device-related attributes.
            if playerPlayState.Device is not None:
                device = playerPlayState.Device
                self._attr_source = device.Name
                self._attr_volume_level = float(device.VolumePercent / 100)

            # update seek-related attributes.
            if playerPlayState.ProgressMS is not None:
                self._attr_media_position = playerPlayState.ProgressMS / 1000
                self._attr_media_position_updated_at = utcnow()
        
            # update repeat related attributes.
            if playerPlayState.RepeatState is not None:
                if playerPlayState.RepeatState == 'context':
                    self._attr_repeat = RepeatMode.ALL.value
                elif playerPlayState.RepeatState == 'track':
                    self._attr_repeat = RepeatMode.ONE.value
                else:
                    self._attr_repeat = RepeatMode.OFF.value

        except Exception as ex:

            _logsi.LogException(None, ex)
            raise HomeAssistantError(str(ex)) from ex

        finally:
        
            # trace.
            _logsi.LeaveMethod(SILevel.Debug)
            

    def _CallScriptPower(self, scriptEntityId:str, title:str) -> None:
        """
        Calls the supplied script for a power on / off event.
        
        Args:
            scriptEntityId (str):
                Name of the script to execute.
            title (str):
                Title to use in trace logs and error messages.
        
        Verifies that the script is installed, and the media player entity id
        is valid and available (not disabled).
        """
        entity_registry:EntityRegistry = None
        
        try:

            # trace.
            _logsi.EnterMethod(SILevel.Debug)
            _logsi.LogVerbose("'%s': MediaPlayer is verifying SpotifyPlus '%s' integration script configuration" % (self.name, title))

            # # if SpotifyPlus integration is NOT installed, then log the services that ARE installed in case we need it.
            #serviceAll = self.hass.services.async_services()
            #_logsi.LogDictionary(SILevel.Verbose, "'%s': MediaPlayer ALL services list" % self.name, serviceAll, prettyPrint=True)

            # if no script name was selected in config options then there is nothing else to do.
            if scriptEntityId is None:
                _logsi.LogVerbose("'%s': MediaPlayer '%s' script is not configured - nothing to do" % (self.name, title))
                return 

            # is the specified script entity id in the hass entity registry?
            # it will NOT be in the entity registry if it's deleted.
            # it WILL be in the entity registry if it is disabled, with disabled property = True.
            entity_registry = er.async_get(self.hass)
            registry_entry:RegistryEntry = entity_registry.async_get(scriptEntityId)
            _logsi.LogObject(SILevel.Verbose, "'%s': MediaPlayer RegistryEntry for entity_id: '%s'" % (self.name, scriptEntityId), registry_entry)

            # raise exceptions if SpotifyPlus Entity is not configured or is disabled.
            if registry_entry is None:
                raise HomeAssistantError("'%s': MediaPlayer '%s' script entity '%s' does not exist (recently deleted or renamed maybe?)" % (self.name, title, scriptEntityId))
            if registry_entry.disabled:
                raise HomeAssistantError("'%s': MediaPlayer '%s' script entity '%s' is currently disabled; re-enable the script to continue" % (self.name, title, scriptEntityId))

            # drop the domain suffix from the script entity id.
            #scriptEntityIdNoDomain:str = scriptEntityId[len(DOMAIN_SCRIPT)+1:]

            # call the script syncronously, so we wait until it returns.
            _logsi.LogVerbose("'%s': MediaPlayer is calling the '%s' script '%s' (entityid='%s', uniqueid='%s')" % (self.name, title, registry_entry.name or registry_entry.original_name, registry_entry.entity_id, registry_entry.unique_id))
            self.hass.services.call(
                DOMAIN_SCRIPT,
                registry_entry.unique_id,   # use the uniqueid
                {},                         # no parameters
                blocking=True,              # wait for service to complete before returning
                return_response=False       # does not return service response data.
            )

        finally:

            # free resources.
            entity_registry = None

            # trace.
            _logsi.LeaveMethod(SILevel.Debug)

    # -----------------------------------------------------------------------------------
    # Custom Services
    # -----------------------------------------------------------------------------------

    def _GetUserProfilePartialDictionary(self, userProfile:UserProfile) -> dict:
        """
        Returns a dictionary of a partial UserProfile object that can be returned with 
        selected service results.  This allows the caller to know exactly what Spotify
        user made the given request.
        """
        # return the user profile that retrieved the result, as well as the result.
        return {
            "country": userProfile.Country,
            "display_name": userProfile.DisplayName,
            "email": userProfile.EMail,
            "id": userProfile.Id,
            "product": userProfile.Product,
            "type": userProfile.Type,
            "uri": userProfile.Uri,
        }


    # def _VerifySourceDeviceActive(self, sourceName:str=None) -> str:
    #     """
    #     Verifies that the Spotify Player is active for the selected source.
        
    #     Args:
    #         sourceName (str):
    #             The media player source name to verify.
                
    #     Returns:
    #         A device ID if one could be resolved; otherwise, the device name.
    #     """
    #     apiMethodName:str = '_VerifySourceDeviceActive'
    #     apiMethodParms:SIMethodParmListContext = None

    #     try:

    #         # trace.
    #         apiMethodParms = _logsi.EnterMethodParmList(SILevel.Debug, apiMethodName)
    #         apiMethodParms.AppendKeyValue("sourceName", sourceName)
    #         _logsi.LogMethodParmList(SILevel.Verbose, "Verifying sourceName '%s' is the active Spotify Player" % sourceName, apiMethodParms)
        
    #         deviceId:str = sourceName
    #         playerState:PlayerPlayState = None

    #         # if source name was not specified, then try to resolve a default to use.
    #         if (sourceName is None):
                
    #             # get currently active Spotify Player device.
    #             _logsi.LogVerbose("'%s': Retrieving Spotify Player playback state and device info" % (self.name))
    #             playerState = self.data.spotifyClient.GetPlayerPlaybackState()

    #             if (playerState.Device.IsActive):
    #                 # if an active Spotify Player device was found, then use it.
    #                 sourceName = playerState.Device.Name
    #                 deviceId = playerState.Device.Id
    #                 _logsi.LogVerbose("'%s': Device was verified: '%s' - active Spotify Player device" % (self.name, sourceName))
    #                 return deviceId
                
    #             elif self._attr_source is not None:
    #                 # otherwise, use the media_player source if one was selected.
    #                 sourceName = self._attr_source
    #                 _logsi.LogVerbose("'%s': Default device was selected: '%s' - media_player source device" % (self.name, sourceName))
                        
    #             elif self._attr_source_list is not None:
    #                 # otherwise, use the first entry in the media_player source_list if one was specified.
    #                 sourceName = self._attr_source_list[0]
    #                 _logsi.LogVerbose("'%s': Default device was selected: '%s' - first media_player source_list device" % (self.name, sourceName))

    #             else:
    #                 # otherwise, the operation will probably fail.
    #                 _logsi.LogVerbose("'%s': Default device could not be resolved; operation will probably fail" % (self.name))

    #         # get currently active Spotify Player device.
    #         # if it matches the specified sourceName then we will consider it verified.        
    #         if playerState is None:
    #             _logsi.LogVerbose("'%s': Retrieving Spotify Player playback state and device info" % (self.name))
    #             playerState = self.data.spotifyClient.GetPlayerPlaybackState()

    #         # if an active Spotify Player device was found, then use it.
    #         if (playerState.Device.IsActive):
    #             if (playerState.Device.Name.lower() == sourceName.lower()):
    #                 _logsi.LogVerbose("'%s': Active Spotify Player device '%s' matched the selected source '%s' - verified" % (self.name, playerState.Device.Id, sourceName))
    #                 return playerState.Device.Id
                
    #         # at this point, the active Spotify Player device does not match the specified device,
    #         # which means that someone else took control of the device OR the device went to sleep
    #         # and dropped out of the Spotify Connect device list.
    #         # transfer playback to the specified device to make it the active player.
    #         _logsi.LogVerbose("'%s': Active Spotify Player device '%s' does not match sourceName '%s'; transferring playback to selected source" % (self.name, playerState.Device.Name or '', sourceName))
    #         self.data.spotifyClient.PlayerTransferPlayback(sourceName, (self.state == MediaPlayerState.PLAYING))

    #         # return the sourceName.
    #         return deviceId

    #     finally:
        
    #         # trace.
    #         _logsi.LeaveMethod(SILevel.Debug, apiMethodName)


    def _GetDefaultDeviceOption(
            self, 
            deviceId:str=None,
            ) -> str:
        """
        Returns the SpotifyPlus defult device option if an "*" was specified for the `deviceId` argument.
        
        Args:
            deviceId (str):
                The Spotify Player device id to verify.
        Returns:
            One of the following values:
            - if the `deviceId` argument is not an "*", then the argument value is returned as-is.
            - otherwise, if a SpotifyPlus default device option was configured then it's deviceId value is returned.
            - otherwise, None is returned to indicate that the active player will be used.
        """
        if (deviceId == "*"):
               
            if (self.data.OptionDeviceDefault is not None):
                deviceId = PlayerDevice.GetIdFromSelectItem(self.data.OptionDeviceDefault)
                deviceName = PlayerDevice.GetNameFromSelectItem(self.data.OptionDeviceDefault)
                _logsi.LogVerbose("'%s': SpotifyPlus default device will be used: '%s' (%s)" %  (self.name, deviceName, deviceId))
            else:
                _logsi.LogVerbose("'%s': SpotifyPlus default device was not configured; will use currently active Spotify Player device" %  (self.name))
                deviceId = None

        return deviceId


    def service_spotify_follow_artists(self, 
                                       ids:str=None, 
                                       ) -> None:
        """
        Add the current user as a follower of one or more artists.
        
        Args:
            ids (str):  
                A comma-separated list of the Spotify IDs for the artists.  
                Maximum: 50 IDs.  
                Example: `2CIMQHirSU0MQqyYHq0eOx,1IQ2e1buppatiN1bxUVkrk`
                If null, the currently playing track artist uri id value is used.
        """
        apiMethodName:str = 'service_spotify_follow_artists'
        apiMethodParms:SIMethodParmListContext = None

        try:

            # trace.
            apiMethodParms = _logsi.EnterMethodParmList(SILevel.Debug, apiMethodName)
            apiMethodParms.AppendKeyValue("ids", ids)
            _logsi.LogMethodParmList(SILevel.Verbose, "Spotify Follow Artists Service", apiMethodParms)
                           
            # follow artist(s).
            _logsi.LogVerbose("Adding items(s) to Spotify Artist Favorites")
            self.data.spotifyClient.FollowArtists(ids)

        # the following exceptions have already been logged, so we just need to
        # pass them back to HA for display in the log (or service UI).
        except SpotifyApiError as ex:
            raise HomeAssistantError(ex.Message)
        except SpotifyWebApiError as ex:
            raise HomeAssistantError(ex.Message)
        
        finally:
        
            # trace.
            _logsi.LeaveMethod(SILevel.Debug, apiMethodName)


    def service_spotify_follow_playlist(self, 
                                        playlistId:str=None, 
                                        public:bool=True, 
                                        ) -> None:
        """
        Add the current user as a follower of a playlist.

        Args:
            playlistId (str):  
                The Spotify ID of the playlist.  
                Example: `3cEYpjA9oz9GiPac4AsH4n`
            public (bool):
                If true the playlist will be included in user's public playlists, if false it 
                will remain private.  
                Default = True. 
        """
        apiMethodName:str = 'service_spotify_follow_playlist'
        apiMethodParms:SIMethodParmListContext = None

        try:

            # trace.
            apiMethodParms = _logsi.EnterMethodParmList(SILevel.Debug, apiMethodName)
            apiMethodParms.AppendKeyValue("playlistId", playlistId)
            apiMethodParms.AppendKeyValue("public", public)
            _logsi.LogMethodParmList(SILevel.Verbose, "Spotify Follow Playlist Service", apiMethodParms)
                           
            # follow playlist.
            _logsi.LogVerbose("Adding items to Spotify Playlist Favorites")
            self.data.spotifyClient.FollowPlaylist(playlistId, public)

        # the following exceptions have already been logged, so we just need to
        # pass them back to HA for display in the log (or service UI).
        except SpotifyApiError as ex:
            raise HomeAssistantError(ex.Message)
        except SpotifyWebApiError as ex:
            raise HomeAssistantError(ex.Message)
        
        finally:
        
            # trace.
            _logsi.LeaveMethod(SILevel.Debug, apiMethodName)


    def service_spotify_follow_users(self, 
                                     ids:str=None, 
                                     ) -> None:
        """
        Add the current user as a follower of one or more users.

        Args:
            ids (str):  
                A comma-separated list of the Spotify user IDs.  
                A maximum of 50 IDs can be sent in one request.
                Example: `smedjan`
        """
        apiMethodName:str = 'service_spotify_follow_users'
        apiMethodParms:SIMethodParmListContext = None

        try:

            # trace.
            apiMethodParms = _logsi.EnterMethodParmList(SILevel.Debug, apiMethodName)
            apiMethodParms.AppendKeyValue("ids", ids)
            _logsi.LogMethodParmList(SILevel.Verbose, "Spotify Follow Artists Service", apiMethodParms)
                           
            # follow user(s).
            _logsi.LogVerbose("Adding items(s) to Spotify User Favorites")
            self.data.spotifyClient.FollowUsers(ids)

        # the following exceptions have already been logged, so we just need to
        # pass them back to HA for display in the log (or service UI).
        except SpotifyApiError as ex:
            raise HomeAssistantError(ex.Message)
        except SpotifyWebApiError as ex:
            raise HomeAssistantError(ex.Message)
        
        finally:
        
            # trace.
            _logsi.LeaveMethod(SILevel.Debug, apiMethodName)


    def service_spotify_get_album(self, 
                                  albumId:str, 
                                  market:str=None,
                                  ) -> dict:
        """
        Get Spotify catalog information for a single album.
        
        Args:
            albumId (str):  
                The Spotify ID of the album.  
                Example: `6vc9OTcyd3hyzabCmsdnwE`
            market (str):
                An ISO 3166-1 alpha-2 country code. If a country code is specified, only content that 
                is available in that market will be returned.  If a valid user access token is specified 
                in the request header, the country associated with the user account will take priority over 
                this parameter.  
                Note: If neither market or user country are provided, the content is considered unavailable for the client.  
                Users can view the country that is associated with their account in the account settings.  
                Example: `ES`
                
        Returns:
            A dictionary that contains the following keys:
            - user_profile: A (partial) user profile that retrieved the result.
            - result: An `Album` object that contains the album details.
        """
        apiMethodName:str = 'service_spotify_get_album'
        apiMethodParms:SIMethodParmListContext = None
        result:Album = None

        try:

            # trace.
            apiMethodParms = _logsi.EnterMethodParmList(SILevel.Debug, apiMethodName)
            apiMethodParms.AppendKeyValue("albumId", albumId)
            apiMethodParms.AppendKeyValue("market", market)
            _logsi.LogMethodParmList(SILevel.Verbose, "Spotify Get Album Service", apiMethodParms)
                
            # request information from Spotify Web API.
            _logsi.LogVerbose(STAppMessages.MSG_SERVICE_QUERY_WEB_API)
            result = self.data.spotifyClient.GetAlbum(albumId, market)

            # return the (partial) user profile that retrieved the result, as well as the result itself.
            return {
                "user_profile": self._GetUserProfilePartialDictionary(self.data.spotifyClient.UserProfile),
                "result": result.ToDictionary()
            }

        # the following exceptions have already been logged, so we just need to
        # pass them back to HA for display in the log (or service UI).
        except SpotifyApiError as ex:
            raise HomeAssistantError(ex.Message)
        except SpotifyWebApiError as ex:
            raise HomeAssistantError(ex.Message)
        
        finally:
        
            # trace.
            _logsi.LeaveMethod(SILevel.Debug, apiMethodName)


    def service_spotify_get_album_favorites(self, 
                                            limit:int, 
                                            offset:int,
                                            market:str,
                                            limitTotal:int=None
                                            ) -> dict:
        """
        Get a list of the albums saved in the current Spotify user's 'Your Library'.
        
        Args:
            limit (int):
                The maximum number of items to return in a page of items.  
                Default: 20, Range: 1 to 50.  
            offset (int):
                The index of the first item to return.  
                Use with limit to get the next set of items.  
                Default: 0 (the first item).  
            market (str):
                An ISO 3166-1 alpha-2 country code. If a country code is specified, only content that 
                is available in that market will be returned.  If a valid user access token is specified 
                in the request header, the country associated with the user account will take priority over 
                this parameter.  
                Example: `ES`
            limitTotal (int):
                The maximum number of items to return for the request.
                If specified, this argument overrides the limit and offset argument values
                and paging is automatically used to retrieve all available items up to the
                maximum count specified.
                Default: None (disabled)
                
        Returns:
            A dictionary that contains the following keys:
            - user_profile: A (partial) user profile that retrieved the result.
            - result: A `AlbumPageSaved` object that contains album information.
        """
        apiMethodName:str = 'service_spotify_get_album_favorites'
        apiMethodParms:SIMethodParmListContext = None

        try:

            # trace.
            apiMethodParms = _logsi.EnterMethodParmList(SILevel.Debug, apiMethodName)
            apiMethodParms.AppendKeyValue("limit", limit)
            apiMethodParms.AppendKeyValue("offset", offset)
            apiMethodParms.AppendKeyValue("market", market)
            apiMethodParms.AppendKeyValue("limitTotal", limitTotal)
            _logsi.LogMethodParmList(SILevel.Verbose, "Spotify Get Album Favorites Service", apiMethodParms)
                
            # request information from Spotify Web API.
            _logsi.LogVerbose(STAppMessages.MSG_SERVICE_QUERY_WEB_API)
            result:AlbumPageSaved = self.data.spotifyClient.GetAlbumFavorites(limit, offset, market, limitTotal)

            # return the (partial) user profile that retrieved the result, as well as the result itself.
            return {
                "user_profile": self._GetUserProfilePartialDictionary(self.data.spotifyClient.UserProfile),
                "result": result.ToDictionary()
            }

        # the following exceptions have already been logged, so we just need to
        # pass them back to HA for display in the log (or service UI).
        except SpotifyApiError as ex:
            raise HomeAssistantError(ex.Message)
        except SpotifyWebApiError as ex:
            raise HomeAssistantError(ex.Message)
        
        finally:
        
            # trace.
            _logsi.LeaveMethod(SILevel.Debug, apiMethodName)


    def service_spotify_get_album_new_releases(self, 
                                               limit:int, 
                                               offset:int,
                                               country:str,
                                               limitTotal:int=None
                                               ) -> dict:
        """
        Get a list of new album releases featured in Spotify.
        
        Args:
            limit (int):
                The maximum number of items to return in a page of items.  
                Default: 20, Range: 1 to 50.  
            offset (int):
                The index of the first item to return.  
                Use with limit to get the next set of items.  
                Default: 0 (the first item).  
            country (str):
                An ISO 3166-1 alpha-2 country code. If a country code is specified, only content that 
                is available in that market will be returned.  If a valid user access token is specified 
                in the request header, the country associated with the user account will take priority over 
                this parameter.  
                Example: `ES`
            limitTotal (int):
                The maximum number of items to return for the request.
                If specified, this argument overrides the limit and offset argument values
                and paging is automatically used to retrieve all available items up to the
                maximum count specified.
                Default: None (disabled)
                
        Returns:
            A dictionary that contains the following keys:
            - user_profile: A (partial) user profile that retrieved the result.
            - result: A `AlbumPageSimplified` object that contains album information.
        """
        apiMethodName:str = 'service_spotify_get_album_new_releases'
        apiMethodParms:SIMethodParmListContext = None

        try:

            # trace.
            apiMethodParms = _logsi.EnterMethodParmList(SILevel.Debug, apiMethodName)
            apiMethodParms.AppendKeyValue("limit", limit)
            apiMethodParms.AppendKeyValue("offset", offset)
            apiMethodParms.AppendKeyValue("country", country)
            apiMethodParms.AppendKeyValue("limitTotal", limitTotal)
            _logsi.LogMethodParmList(SILevel.Verbose, "Spotify Get Album New Releases Service", apiMethodParms)
                
            # request information from Spotify Web API.
            _logsi.LogVerbose(STAppMessages.MSG_SERVICE_QUERY_WEB_API)
            result:AlbumPageSimplified = self.data.spotifyClient.GetAlbumNewReleases(limit, offset, country, limitTotal)

            # return the (partial) user profile that retrieved the result, as well as the result itself.
            return {
                "user_profile": self._GetUserProfilePartialDictionary(self.data.spotifyClient.UserProfile),
                "result": result.ToDictionary()
            }

        # the following exceptions have already been logged, so we just need to
        # pass them back to HA for display in the log (or service UI).
        except SpotifyApiError as ex:
            raise HomeAssistantError(ex.Message)
        except SpotifyWebApiError as ex:
            raise HomeAssistantError(ex.Message)
        
        finally:
        
            # trace.
            _logsi.LeaveMethod(SILevel.Debug, apiMethodName)


    def service_spotify_get_artist(self, 
                                  artistId:str, 
                                  ) -> dict:
        """
        Get Spotify catalog information for a single artist.
        
        Args:
            artistId (str):  
                The Spotify ID of the artist.  
                Example: `6APm8EjxOHSYM5B4i3vT3q`
                
        Returns:
            A dictionary that contains the following keys:
            - user_profile: A (partial) user profile that retrieved the result.
            - result: An `Artist` object that contains the artist details.
        """
        apiMethodName:str = 'service_spotify_get_artist'
        apiMethodParms:SIMethodParmListContext = None
        result:Artist = None

        try:

            # trace.
            apiMethodParms = _logsi.EnterMethodParmList(SILevel.Debug, apiMethodName)
            apiMethodParms.AppendKeyValue("artistId", artistId)
            _logsi.LogMethodParmList(SILevel.Verbose, "Spotify Get Artist Service", apiMethodParms)
                
            # request information from Spotify Web API.
            _logsi.LogVerbose(STAppMessages.MSG_SERVICE_QUERY_WEB_API)
            result = self.data.spotifyClient.GetArtist(artistId)

            # return the (partial) user profile that retrieved the result, as well as the result itself.
            return {
                "user_profile": self._GetUserProfilePartialDictionary(self.data.spotifyClient.UserProfile),
                "result": result.ToDictionary()
            }

        # the following exceptions have already been logged, so we just need to
        # pass them back to HA for display in the log (or service UI).
        except SpotifyApiError as ex:
            raise HomeAssistantError(ex.Message)
        except SpotifyWebApiError as ex:
            raise HomeAssistantError(ex.Message)
        
        finally:
        
            # trace.
            _logsi.LeaveMethod(SILevel.Debug, apiMethodName)


    def service_spotify_get_artist_albums(self, 
                                          artistId:str, 
                                          include_groups:str='album', 
                                          limit:int=20, 
                                          offset:int=0,
                                          market:str=None,
                                          limitTotal:int=None
                                          ) -> dict:
        """
        Get Spotify catalog information about an artist's albums.
        
        Args:
            artistId (str):  
                The Spotify ID of the artist.  
                Example: `6APm8EjxOHSYM5B4i3vT3q`
            include_groups (str):  
                A comma-separated list of keywords that will be used to filter the response.  
                If not supplied, all album types will be returned.  
                Valid values are: `album`, `single`, `appears_on`, `compilation`  
                Example: `single,appears_on`
            limit (int):  
                The maximum number of items to return in a page of items.  
                Default: 20, Range: 1 to 50.  
            offset (int):  
                The index of the first item to return; use with limit to get the next set of items.  
                Default: 0 (the first item).  
            market (str):  
                An ISO 3166-1 alpha-2 country code. If a country code is specified, only content that is 
                available in that market will be returned.
                If a valid user access token is specified in the request header, the country associated with 
                the user account will take priority over this parameter.
                Example: `ES`
            limitTotal (int):
                The maximum number of items to return for the request.
                If specified, this argument overrides the limit and offset argument values
                and paging is automatically used to retrieve all available items up to the
                maximum count specified.
                Default: None (disabled)
                
        Returns:
            A dictionary that contains the following keys:
            - user_profile: A (partial) user profile that retrieved the result.
            - result: An `AlbumPageSimplified` object that contains artist album information.
        """
        apiMethodName:str = 'service_spotify_get_artist_albums'
        apiMethodParms:SIMethodParmListContext = None

        try:

            # trace.
            apiMethodParms = _logsi.EnterMethodParmList(SILevel.Debug, apiMethodName)
            apiMethodParms.AppendKeyValue("artistId", artistId)
            apiMethodParms.AppendKeyValue("include_groups", include_groups)
            apiMethodParms.AppendKeyValue("limit", limit)
            apiMethodParms.AppendKeyValue("offset", offset)
            apiMethodParms.AppendKeyValue("market", market)
            apiMethodParms.AppendKeyValue("limitTotal", limitTotal)
            _logsi.LogMethodParmList(SILevel.Verbose, "Spotify Get Artist Albums Service", apiMethodParms)
                
            # request information from Spotify Web API.
            _logsi.LogVerbose(STAppMessages.MSG_SERVICE_QUERY_WEB_API)
            result:AlbumPageSimplified = self.data.spotifyClient.GetArtistAlbums(artistId, include_groups, limit, offset, market, limitTotal)

            # return the (partial) user profile that retrieved the result, as well as the result itself.
            return {
                "user_profile": self._GetUserProfilePartialDictionary(self.data.spotifyClient.UserProfile),
                "result": result.ToDictionary()
            }

        # the following exceptions have already been logged, so we just need to
        # pass them back to HA for display in the log (or service UI).
        except SpotifyApiError as ex:
            raise HomeAssistantError(ex.Message)
        except SpotifyWebApiError as ex:
            raise HomeAssistantError(ex.Message)
        
        finally:
        
            # trace.
            _logsi.LeaveMethod(SILevel.Debug, apiMethodName)


    def service_spotify_get_artists_followed(self, 
                                             after:str, 
                                             limit:int,
                                             limitTotal:int=None
                                             ) -> dict:
        """
        Get the current user's followed artists.

        Args:
            after (str):
                The last artist ID retrieved from the previous request, or null for
                the first request.  
                Example: `0I2XqVXqHScXjHhk6AYYRe`  
            limit (int):
                The maximum number of items to return in a page of items.  
                Default: 20, Range: 1 to 50.  
            limitTotal (int):
                The maximum number of items to return for the request.
                If specified, this argument overrides the limit and offset argument values
                and paging is automatically used to retrieve all available items up to the
                maximum count specified.
                Default: None (disabled)
                
        Returns:
            A dictionary that contains the following keys:
            - user_profile: A (partial) user profile that retrieved the result.
            - result: An `ArtistPage` object that contains artist information.
        """
        apiMethodName:str = 'service_spotify_get_artists_followed'
        apiMethodParms:SIMethodParmListContext = None

        try:

            # trace.
            apiMethodParms = _logsi.EnterMethodParmList(SILevel.Debug, apiMethodName)
            apiMethodParms.AppendKeyValue("after", after)
            apiMethodParms.AppendKeyValue("limit", limit)
            apiMethodParms.AppendKeyValue("limitTotal", limitTotal)
            _logsi.LogMethodParmList(SILevel.Verbose, "Spotify Get Artists Followed Service", apiMethodParms)
                
            # request information from Spotify Web API.
            _logsi.LogVerbose(STAppMessages.MSG_SERVICE_QUERY_WEB_API)
            result:ArtistPage = self.data.spotifyClient.GetArtistsFollowed(after, limit, limitTotal)

            # return the (partial) user profile that retrieved the result, as well as the result itself.
            return {
                "user_profile": self._GetUserProfilePartialDictionary(self.data.spotifyClient.UserProfile),
                "result": result.ToDictionary()
            }

        # the following exceptions have already been logged, so we just need to
        # pass them back to HA for display in the log (or service UI).
        except SpotifyApiError as ex:
            raise HomeAssistantError(ex.Message)
        except SpotifyWebApiError as ex:
            raise HomeAssistantError(ex.Message)
        
        finally:
        
            # trace.
            _logsi.LeaveMethod(SILevel.Debug, apiMethodName)


    def service_spotify_get_browse_categorys_list(self, 
                                                  country:str=None, 
                                                  locale:str=None,
                                                  refresh:str=False,
                                                  ) -> dict:
        """
        Get a sorted list of ALL categories used to tag items in Spotify.
        
        Args:
            country (str):
                A country: an ISO 3166-1 alpha-2 country code.  
                Provide this parameter if you want the list of returned items to be relevant to a 
                particular country. If omitted, the returned items will be relevant to all countries.  
                Example: `SE`
            locale (str):
                The desired language, consisting of a lowercase ISO 639-1 language code and an uppercase 
                ISO 3166-1 alpha-2 country code, joined by an underscore.  
                For example: `es_MX`, meaning "Spanish (Mexico)".  
                Provide this parameter if you want the results returned in a particular language (where available).  
                Note: if locale is not supplied, or if the specified language is not available, all strings will 
                be returned in the Spotify default language (American English). The locale parameter, combined with 
                the country parameter, may give odd results if not carefully matched. For example country=`SE` and
                locale=`de_DE` will return a list of categories relevant to Sweden but as German language strings.  
                Example: `sv_SE`  
            refresh (bool):
                True to return real-time information from the spotify web api and
                update the cache; otherwise, False to just return the cached value.       
                
        Returns:
            A dictionary that contains the following keys:
            - user_profile: A (partial) user profile that retrieved the result.
            - result: A `CategoryPage` object that contains the list category details.
        """
        apiMethodName:str = 'service_spotify_get_browse_categorys_list'
        apiMethodParms:SIMethodParmListContext = None
        result:CategoryPage = CategoryPage()

        try:

            # trace.
            apiMethodParms = _logsi.EnterMethodParmList(SILevel.Debug, apiMethodName)
            apiMethodParms.AppendKeyValue("country", country)
            apiMethodParms.AppendKeyValue("locale", locale)
            apiMethodParms.AppendKeyValue("refresh", refresh)
            _logsi.LogMethodParmList(SILevel.Verbose, "Spotify Get Browse Categorys Service", apiMethodParms)
                
            # request information from Spotify Web API.
            _logsi.LogVerbose(STAppMessages.MSG_SERVICE_QUERY_WEB_API)
            resultArray:list[Category] = self.data.spotifyClient.GetBrowseCategorysList(country, locale, refresh)
            
            # build a CategoryPage object so we can convert to a dictionary.
            category:Category
            for category in resultArray:
                result.Items.append(category)

            # return the (partial) user profile that retrieved the result, as well as the result itself.
            return {
                "user_profile": self._GetUserProfilePartialDictionary(self.data.spotifyClient.UserProfile),
                "result": result.ToDictionary()
            }

        # the following exceptions have already been logged, so we just need to
        # pass them back to HA for display in the log (or service UI).
        except SpotifyApiError as ex:
            raise HomeAssistantError(ex.Message)
        except SpotifyWebApiError as ex:
            raise HomeAssistantError(ex.Message)
        
        finally:
        
            # trace.
            _logsi.LeaveMethod(SILevel.Debug, apiMethodName)


    def service_spotify_get_category_playlists(self, 
                                               categoryId:str=None,
                                               limit:int=20, 
                                               offset:int=0,
                                               country:str=None,
                                               limitTotal:int=None
                                               ) -> dict:
        """
        Get a list of Spotify playlists tagged with a particular category.
        
        Args:
            categoryId (str):
                The Spotify category ID for the category.  
                Example: `dinner`
            limit (int):
                The maximum number of items to return in a page of items.  
                Default: 20, Range: 1 to 50.  
            offset (int):
                The page index offset of the first item to return.  
                Use with limit to get the next set of items.  
                Default: 0 (the first item).  
            country (str):
                A country: an ISO 3166-1 alpha-2 country code.  
                Provide this parameter if you want the list of returned items to be relevant to a 
                particular country. If omitted, the returned items will be relevant to all countries.  
                Example: `SE`
            limitTotal (int):
                The maximum number of items to return for the request.  
                If specified, this argument overrides the limit and offset argument values
                and paging is automatically used to retrieve all available items up to the
                maximum number specified.  
                Default: None (disabled)
                
        Returns:
            A dictionary that contains the following keys:
            - user_profile: A (partial) user profile that retrieved the result.
            - result: An `PlaylistPageSimplified` object that contains playlist information.
            - message: string that describes what was returned (e.g. 'Popular Playlists').
        """
        apiMethodName:str = 'service_spotify_get_category_playlists'
        apiMethodParms:SIMethodParmListContext = None

        try:

            # trace.
            apiMethodParms = _logsi.EnterMethodParmList(SILevel.Debug, apiMethodName)
            apiMethodParms.AppendKeyValue("categoryId", categoryId)
            apiMethodParms.AppendKeyValue("limit", limit)
            apiMethodParms.AppendKeyValue("offset", offset)
            apiMethodParms.AppendKeyValue("country", country)
            apiMethodParms.AppendKeyValue("limitTotal", limitTotal)
            _logsi.LogMethodParmList(SILevel.Verbose, "Spotify Get Category Playlists Service", apiMethodParms)
                
            # request information from Spotify Web API.
            # have to treat this one a little bit differently due to return of a Tuple[] value.
            _logsi.LogVerbose(STAppMessages.MSG_SERVICE_QUERY_WEB_API)
            response:Tuple[PlaylistPageSimplified, str]
            response = self.data.spotifyClient.GetCategoryPlaylists(categoryId, limit, offset, country, limitTotal)
            _logsi.LogObject(SILevel.Verbose, "response Tuple object", response)

            result:PlaylistPageSimplified = response[0]
            message:str = response[1]

            # return the (partial) user profile that retrieved the result, as well as the result itself.
            return {
                "user_profile": self._GetUserProfilePartialDictionary(self.data.spotifyClient.UserProfile),
                "result": result.ToDictionary(),
                "message": message
            }

        # the following exceptions have already been logged, so we just need to
        # pass them back to HA for display in the log (or service UI).
        except SpotifyApiError as ex:
            raise HomeAssistantError(ex.Message)
        except SpotifyWebApiError as ex:
            raise HomeAssistantError(ex.Message)
        
        finally:
        
            # trace.
            _logsi.LeaveMethod(SILevel.Debug, apiMethodName)


    def service_spotify_get_featured_playlists(self, 
                                               limit:int=20, 
                                               offset:int=0,
                                               country:str=None,
                                               locale:str=None,
                                               timestamp:str=None,
                                               limitTotal:int=None
                                               ) -> dict:
        """
        Get a list of Spotify featured playlists (shown, for example, on a Spotify player's 'Browse' tab).
        
        Args:
            limit (int):
                The maximum number of items to return in a page of items.  
                Default: 20, Range: 1 to 50.  
            offset (int):
                The page index offset of the first item to return.  
                Use with limit to get the next set of items.  
                Default: 0 (the first item).  
            country (str):
                A country: an ISO 3166-1 alpha-2 country code.  
                Provide this parameter if you want the list of returned items to be relevant to a 
                particular country. If omitted, the returned items will be relevant to all countries.  
                Example: `SE`
            locale (str):
                The desired language, consisting of a lowercase ISO 639-1 language code and an uppercase 
                ISO 3166-1 alpha-2 country code, joined by an underscore.  
                For example: `es_MX`, meaning "Spanish (Mexico)".  
                Provide this parameter if you want the results returned in a particular language (where available).  
                Note: if locale is not supplied, or if the specified language is not available, all strings will 
                be returned in the Spotify default language (American English). The locale parameter, combined with 
                the country parameter, may give odd results if not carefully matched. For example country=`SE` and
                locale=`de_DE` will return a list of categories relevant to Sweden but as German language strings.  
                Example: `sv_SE`
            timestamp (str):
                A timestamp in ISO 8601 format: yyyy-MM-ddTHH:mm:ss.  
                Use this parameter to specify the user's local time to get results tailored for that specific date 
                and time in the day. If not provided, the response defaults to the current UTC time. 
                Example: `2023-10-23T09:00:00` for a user whose local time is 9AM. 
                If there were no featured playlists (or there is no data) at the specified time, the response will 
                revert to the current UTC time.
                Example: `2023-10-23T09:00:00`
            limitTotal (int):
                The maximum number of items to return for the request.  
                If specified, this argument overrides the limit and offset argument values
                and paging is automatically used to retrieve all available items up to the
                maximum number specified.  
                Default: None (disabled)
                
        Returns:
            A dictionary that contains the following keys:
            - user_profile: A (partial) user profile that retrieved the result.
            - result: An `PlaylistPageSimplified` object that contains playlist information.
            - message: string that describes what was returned (e.g. 'Popular Playlists').
        """
        apiMethodName:str = 'service_spotify_get_featured_playlists'
        apiMethodParms:SIMethodParmListContext = None

        try:

            # trace.
            apiMethodParms = _logsi.EnterMethodParmList(SILevel.Debug, apiMethodName)
            apiMethodParms.AppendKeyValue("limit", limit)
            apiMethodParms.AppendKeyValue("offset", offset)
            apiMethodParms.AppendKeyValue("country", country)
            apiMethodParms.AppendKeyValue("locale", locale)
            apiMethodParms.AppendKeyValue("timestamp", timestamp)
            apiMethodParms.AppendKeyValue("limitTotal", limitTotal)
            _logsi.LogMethodParmList(SILevel.Verbose, "Spotify Get Featured Playlists Service", apiMethodParms)
                
            # request information from Spotify Web API.
            # have to treat this one a little bit differently due to return of a Tuple[] value.
            _logsi.LogVerbose(STAppMessages.MSG_SERVICE_QUERY_WEB_API)
            response:Tuple[PlaylistPageSimplified, str]
            response = self.data.spotifyClient.GetFeaturedPlaylists(limit, offset, country, locale, timestamp, limitTotal)
            _logsi.LogObject(SILevel.Verbose, "response Tuple object", response)

            result:PlaylistPageSimplified = response[0]
            message:str = response[1]
                
            # return the (partial) user profile that retrieved the result, as well as the result itself.
            return {
                "user_profile": self._GetUserProfilePartialDictionary(self.data.spotifyClient.UserProfile),
                "result": result.ToDictionary(),
                "message": message
            }

        # the following exceptions have already been logged, so we just need to
        # pass them back to HA for display in the log (or service UI).
        except SpotifyApiError as ex:
            raise HomeAssistantError(ex.Message)
        except SpotifyWebApiError as ex:
            raise HomeAssistantError(ex.Message)
        
        finally:
        
            # trace.
            _logsi.LeaveMethod(SILevel.Debug, apiMethodName)


    def service_spotify_get_player_devices(self,
                                           refresh:bool=True
                                           ) -> dict:
        """
        Get information about a user's available Spotify Connect player devices. 
        
        Some device models are not supported and will not be listed in the API response.
        
        This method requires the `user-read-playback-state` scope.

        Args:
            refresh (bool):
                True (default) to return real-time information from the spotify web api and
                update the cache; otherwise, False to just return the cached value.
        
        Returns:
            A dictionary that contains the following keys:
            - user_profile: A (partial) user profile that retrieved the result.
            - result: A list of `Device` objects that contain the device details, sorted by name.
        """
        apiMethodName:str = 'service_spotify_get_player_devices'
        apiMethodParms:SIMethodParmListContext = None
        result:PlayerQueueInfo = None

        try:

            # trace.
            apiMethodParms = _logsi.EnterMethodParmList(SILevel.Debug, apiMethodName)
            _logsi.LogMethodParmList(SILevel.Verbose, "Spotify Get Player Devices Service", apiMethodParms)
                
            # request information from Spotify Web API.
            _logsi.LogVerbose(STAppMessages.MSG_SERVICE_QUERY_WEB_API)
            result = self.data.spotifyClient.GetPlayerDevices(refresh)
            
            # build dictionary result from array.
            resultArray:list = []
            item:PlayerDevice
            for item in result: 
                resultArray.append(item.ToDictionary())

            # return the (partial) user profile that retrieved the result, as well as the result itself.
            return {
                "user_profile": self._GetUserProfilePartialDictionary(self.data.spotifyClient.UserProfile),
                "result": resultArray
            }

        # the following exceptions have already been logged, so we just need to
        # pass them back to HA for display in the log (or service UI).
        except SpotifyApiError as ex:
            raise HomeAssistantError(ex.Message)
        except SpotifyWebApiError as ex:
            raise HomeAssistantError(ex.Message)
        
        finally:
        
            # trace.
            _logsi.LeaveMethod(SILevel.Debug, apiMethodName)


    def service_spotify_get_player_now_playing(
            self, 
            market:str=None,
            additionalTypes:str=None
            ) -> dict:
        """
        Get the object currently being played on the user's Spotify account.
        
        This method requires the `user-read-currently-playing` scope.
        
        Args:
            market (str):
                An ISO 3166-1 alpha-2 country code. If a country code is specified, only content that 
                is available in that market will be returned.  If a valid user access token is specified 
                in the request header, the country associated with the user account will take priority over 
                this parameter.  
                Note: If neither market or user country are provided, the content is considered unavailable for the client.  
                Users can view the country that is associated with their account in the account settings.  
                Example: `ES`
            additionalTypes (str):
                A comma-separated list of item types that your client supports besides the default track type.  
                Valid types are: `track` and `episode`.  
                Specify `episode` to get podcast track information.  
                Note: This parameter was introduced to allow existing clients to maintain their current behaviour 
                and might be deprecated in the future. In addition to providing this parameter, make sure that your client 
                properly handles cases of new types in the future by checking against the type field of each object.
                
        Returns:
            A dictionary that contains the following keys:
            - user_profile: A (partial) user profile that retrieved the result.
            - result: A `PlayerPlayState` object that contains the player now playing details.
        """
        apiMethodName:str = 'service_spotify_get_player_now_playing'
        apiMethodParms:SIMethodParmListContext = None
        result:PlayerPlayState = None

        try:

            # trace.
            apiMethodParms = _logsi.EnterMethodParmList(SILevel.Debug, apiMethodName)
            apiMethodParms.AppendKeyValue("market", market)
            apiMethodParms.AppendKeyValue("additionalTypes", additionalTypes)
            _logsi.LogMethodParmList(SILevel.Verbose, "Spotify Get Player Now Playing Service", apiMethodParms)
                
            # request information from Spotify Web API.
            _logsi.LogVerbose(STAppMessages.MSG_SERVICE_QUERY_WEB_API)
            result = self.data.spotifyClient.GetPlayerNowPlaying(market, additionalTypes)

            # return the (partial) user profile that retrieved the result, as well as the result itself.
            return {
                "user_profile": self._GetUserProfilePartialDictionary(self.data.spotifyClient.UserProfile),
                "result": result.ToDictionary()
            }

        # the following exceptions have already been logged, so we just need to
        # pass them back to HA for display in the log (or service UI).
        except SpotifyApiError as ex:
            raise HomeAssistantError(ex.Message)
        except SpotifyWebApiError as ex:
            raise HomeAssistantError(ex.Message)
        
        finally:
        
            # trace.
            _logsi.LeaveMethod(SILevel.Debug, apiMethodName)


    def service_spotify_get_player_playback_state(
            self, 
            market:str=None,
            additionalTypes:str=None
            ) -> dict:
        """
        Get information about the user's current playback state, including track or episode, progress, 
        and active device.
        
        This method requires the `user-read-playback-state` scope.
        
        Args:
            market (str):
                An ISO 3166-1 alpha-2 country code. If a country code is specified, only content that 
                is available in that market will be returned.  If a valid user access token is specified 
                in the request header, the country associated with the user account will take priority over 
                this parameter.  
                Note: If neither market or user country are provided, the content is considered unavailable for the client.  
                Users can view the country that is associated with their account in the account settings.  
                Example: `ES`
            additionalTypes (str):
                A comma-separated list of item types that your client supports besides the default track type.  
                Valid types are: `track` and `episode`.  
                Specify `episode` to get podcast track information.  
                Note: This parameter was introduced to allow existing clients to maintain their current behaviour 
                and might be deprecated in the future. In addition to providing this parameter, make sure that your client 
                properly handles cases of new types in the future by checking against the type field of each object.
                
        Returns:
            A dictionary that contains the following keys:
            - user_profile: A (partial) user profile that retrieved the result.
            - result: A `PlayerPlayState` object that contains the playback state details.
        """
        apiMethodName:str = 'service_spotify_get_player_playback_state'
        apiMethodParms:SIMethodParmListContext = None
        result:PlayerPlayState = None

        try:

            # trace.
            apiMethodParms = _logsi.EnterMethodParmList(SILevel.Debug, apiMethodName)
            apiMethodParms.AppendKeyValue("market", market)
            apiMethodParms.AppendKeyValue("additionalTypes", additionalTypes)
            _logsi.LogMethodParmList(SILevel.Verbose, "Spotify Get Player Playback State Service", apiMethodParms)
                
            # request information from Spotify Web API.
            _logsi.LogVerbose(STAppMessages.MSG_SERVICE_QUERY_WEB_API)
            result = self.data.spotifyClient.GetPlayerPlaybackState(market, additionalTypes)

            # return the (partial) user profile that retrieved the result, as well as the result itself.
            return {
                "user_profile": self._GetUserProfilePartialDictionary(self.data.spotifyClient.UserProfile),
                "result": result.ToDictionary()
            }

        # the following exceptions have already been logged, so we just need to
        # pass them back to HA for display in the log (or service UI).
        except SpotifyApiError as ex:
            raise HomeAssistantError(ex.Message)
        except SpotifyWebApiError as ex:
            raise HomeAssistantError(ex.Message)
        
        finally:
        
            # trace.
            _logsi.LeaveMethod(SILevel.Debug, apiMethodName)


    def service_spotify_get_player_queue_info(self) -> dict:
        """
        Get the list of objects that make up the user's playback queue.
        
        This method requires the `user-read-currently-playing` and `user-read-playback-state` scope.
        
        Returns:
            A dictionary that contains the following keys:
            - user_profile: A (partial) user profile that retrieved the result.
            - result: A `PlayerQueueInfo` object that contains the player queue information.
        """
        apiMethodName:str = 'service_spotify_get_player_queue_info'
        apiMethodParms:SIMethodParmListContext = None
        result:PlayerQueueInfo = None

        try:

            # trace.
            apiMethodParms = _logsi.EnterMethodParmList(SILevel.Debug, apiMethodName)
            _logsi.LogMethodParmList(SILevel.Verbose, "Spotify Get Player Queue Info Service", apiMethodParms)
                
            # request information from Spotify Web API.
            _logsi.LogVerbose(STAppMessages.MSG_SERVICE_QUERY_WEB_API)
            result = self.data.spotifyClient.GetPlayerQueueInfo()

            # return the (partial) user profile that retrieved the result, as well as the result itself.
            return {
                "user_profile": self._GetUserProfilePartialDictionary(self.data.spotifyClient.UserProfile),
                "result": result.ToDictionary()
            }

        # the following exceptions have already been logged, so we just need to
        # pass them back to HA for display in the log (or service UI).
        except SpotifyApiError as ex:
            raise HomeAssistantError(ex.Message)
        except SpotifyWebApiError as ex:
            raise HomeAssistantError(ex.Message)
        
        finally:
        
            # trace.
            _logsi.LeaveMethod(SILevel.Debug, apiMethodName)


    def service_spotify_get_player_recent_tracks(self, 
                                                 limit:int, 
                                                 after:int, 
                                                 before:int,
                                                 limitTotal:int=None
                                                 ) -> dict:
        """
        Get tracks from the current user's recently played tracks.  
        Note: Currently doesn't support podcast episodes.
        
        This method requires the `user-read-recently-played` scope.
        
        Args:
            limit (int):
                The maximum number of items to return in a page of items.  
                Default: `20`, Range: `1` to `50`.  
            after (int):
                Returns all items after (but not including) this cursor position, which is 
                a Unix timestamp in milliseconds.  
                If `after` is specified, `before` must not be specified.  
                Use with limit to get the next set of items.  
                Default: `0` (the first item).  
            before (int):
                Returns all items before (but not including) this cursor position, which is 
                a Unix timestamp in milliseconds.  
                If `before` is specified, `after` must not be specified.  
                Use with limit to get the next set of items.  
                Default: `0` (the first item).  
            limitTotal (int):
                The maximum number of items to return for the request.  
                If specified, this argument overrides the limit and offset argument values
                and paging is automatically used to retrieve all available items up to the
                maximum number specified.  
                Default: None (disabled)
                
        The `after` and `before` arguments are based upon local time (not UTC time).  Recently
        played item history uses a local timestamp, and NOT a UTC timestamp.
                
        Returns:
            A dictionary that contains the following keys:
            - user_profile: A (partial) user profile that retrieved the result.
            - result: A `PlayHistoryPage` object that contains the playlist details.
        """
        apiMethodName:str = 'service_spotify_get_player_recent_tracks'
        apiMethodParms:SIMethodParmListContext = None
        result:PlayHistoryPage = None

        try:

            # trace.
            apiMethodParms = _logsi.EnterMethodParmList(SILevel.Debug, apiMethodName)
            apiMethodParms.AppendKeyValue("limit", limit)
            apiMethodParms.AppendKeyValue("after", after)
            apiMethodParms.AppendKeyValue("before", before)
            apiMethodParms.AppendKeyValue("limitTotal", limitTotal)
            _logsi.LogMethodParmList(SILevel.Verbose, "Spotify Get Player Recent Tracks Service", apiMethodParms)
                
            # request information from Spotify Web API.
            _logsi.LogVerbose(STAppMessages.MSG_SERVICE_QUERY_WEB_API)
            result = self.data.spotifyClient.GetPlayerRecentTracks(limit, after, before, limitTotal)

            # return the (partial) user profile that retrieved the result, as well as the result itself.
            return {
                "user_profile": self._GetUserProfilePartialDictionary(self.data.spotifyClient.UserProfile),
                "result": result.ToDictionary()
            }

        # the following exceptions have already been logged, so we just need to
        # pass them back to HA for display in the log (or service UI).
        except SpotifyApiError as ex:
            raise HomeAssistantError(ex.Message)
        except SpotifyWebApiError as ex:
            raise HomeAssistantError(ex.Message)
        
        finally:
        
            # trace.
            _logsi.LeaveMethod(SILevel.Debug, apiMethodName)


    def service_spotify_get_playlist(self, 
                                     playlistId:str, 
                                     market:str=None,
                                     fields:str=None,
                                     additionalTypes:str=None
                                     ) -> dict:
        """
        Get a playlist owned by a Spotify user.
        
        Args:
            playlistId (str):  
                The Spotify ID of the playlist.  
                Example: `5v5ETK9WFXAnGQ3MRubKuE`
            market (str):
                An ISO 3166-1 alpha-2 country code. If a country code is specified, only content that 
                is available in that market will be returned.  If a valid user access token is specified 
                in the request header, the country associated with the user account will take priority over 
                this parameter.  
                Example: `ES`
            fields (str):
                Filters for the query: a comma-separated list of the fields to return.  
                If omitted, all fields are returned. 
            additionalTypes (str):
                A comma-separated list of item types that your client supports besides the default track type.  
                Valid types are: track and episode.  
                
        Returns:
            A dictionary that contains the following keys:
            - user_profile: A (partial) user profile that retrieved the result.
            - result: A `Playlist` object that contains the playlist details.
        """
        apiMethodName:str = 'service_spotify_get_playlist'
        apiMethodParms:SIMethodParmListContext = None
        result:Playlist = None

        try:

            # trace.
            apiMethodParms = _logsi.EnterMethodParmList(SILevel.Debug, apiMethodName)
            apiMethodParms.AppendKeyValue("playlistId", playlistId)
            apiMethodParms.AppendKeyValue("market", market)
            apiMethodParms.AppendKeyValue("fields", fields)
            apiMethodParms.AppendKeyValue("additionalTypes", additionalTypes)
            _logsi.LogMethodParmList(SILevel.Verbose, "Spotify Get Playlist Service", apiMethodParms)
                
            # request information from Spotify Web API.
            _logsi.LogVerbose(STAppMessages.MSG_SERVICE_QUERY_WEB_API)
            result = self.data.spotifyClient.GetPlaylist(playlistId, market, fields, additionalTypes)

            # return the (partial) user profile that retrieved the result, as well as the result itself.
            return {
                "user_profile": self._GetUserProfilePartialDictionary(self.data.spotifyClient.UserProfile),
                "result": result.ToDictionary()
            }

        # the following exceptions have already been logged, so we just need to
        # pass them back to HA for display in the log (or service UI).
        except SpotifyApiError as ex:
            raise HomeAssistantError(ex.Message)
        except SpotifyWebApiError as ex:
            raise HomeAssistantError(ex.Message)
        
        finally:
        
            # trace.
            _logsi.LeaveMethod(SILevel.Debug, apiMethodName)


    def service_spotify_get_playlist_favorites(self, 
                                               limit:int, 
                                               offset:int,
                                               limitTotal:int=None
                                               ) -> dict:
        """
        Get a list of the playlists owned or followed by the current Spotify user.

        Args:
            limit (int):
                The maximum number of items to return in a page of items.  
                Default: 20, Range: 1 to 50.  
            offset (int):
                The index of the first item to return.  
                Use with limit to get the next set of items.  
                Default: 0 (the first item).  
            limitTotal (int):
                The maximum number of items to return for the request.
                If specified, this argument overrides the limit and offset argument values
                and paging is automatically used to retrieve all available items up to the
                maximum count specified.
                Default: None (disabled)

        Returns:
            A dictionary that contains the following keys:
            - user_profile: A (partial) user profile that retrieved the result.
            - result: A `PlaylistPageSimplified` object that contains playlist information.
        """
        apiMethodName:str = 'service_spotify_get_playlist_favorites'
        apiMethodParms:SIMethodParmListContext = None

        try:

            # trace.
            apiMethodParms = _logsi.EnterMethodParmList(SILevel.Debug, apiMethodName)
            apiMethodParms.AppendKeyValue("limit", limit)
            apiMethodParms.AppendKeyValue("offset", offset)
            apiMethodParms.AppendKeyValue("limitTotal", limitTotal)
            _logsi.LogMethodParmList(SILevel.Verbose, "Spotify Get Playlist Favorites Service", apiMethodParms)
                
            # request information from Spotify Web API.
            _logsi.LogVerbose(STAppMessages.MSG_SERVICE_QUERY_WEB_API)
            result:PlaylistPageSimplified = self.data.spotifyClient.GetPlaylistFavorites(limit, offset, limitTotal)

            # return the (partial) user profile that retrieved the result, as well as the result itself.
            return {
                "user_profile": self._GetUserProfilePartialDictionary(self.data.spotifyClient.UserProfile),
                "result": result.ToDictionary()
            }

        # the following exceptions have already been logged, so we just need to
        # pass them back to HA for display in the log (or service UI).
        except SpotifyApiError as ex:
            raise HomeAssistantError(ex.Message)
        except SpotifyWebApiError as ex:
            raise HomeAssistantError(ex.Message)
        
        finally:
        
            # trace.
            _logsi.LeaveMethod(SILevel.Debug, apiMethodName)


    def service_spotify_get_show(self, 
                                 showId:str, 
                                 market:str=None,
                                 ) -> dict:
        """
        Get Spotify catalog information for a single show identified by its unique Spotify ID.
        
        Args:
            showId (str):  
                The Spotify ID for the show.
                Example: `5CfCWKI5pZ28U0uOzXkDHe`
            market (str):
                An ISO 3166-1 alpha-2 country code. If a country code is specified, only content that 
                is available in that market will be returned.  If a valid user access token is specified 
                in the request header, the country associated with the user account will take priority over 
                this parameter.  
                Example: `ES`
                
        Returns:
            A dictionary that contains the following keys:
            - user_profile: A (partial) user profile that retrieved the result.
            - result: A `Show` object that contain the show details.
        """
        apiMethodName:str = 'service_spotify_get_show'
        apiMethodParms:SIMethodParmListContext = None
        result:Show = None

        try:

            # trace.
            apiMethodParms = _logsi.EnterMethodParmList(SILevel.Debug, apiMethodName)
            apiMethodParms.AppendKeyValue("showId", showId)
            apiMethodParms.AppendKeyValue("market", market)
            _logsi.LogMethodParmList(SILevel.Verbose, "Spotify Get Show Service", apiMethodParms)
                
            # request information from Spotify Web API.
            _logsi.LogVerbose(STAppMessages.MSG_SERVICE_QUERY_WEB_API)
            result = self.data.spotifyClient.GetShow(showId, market)

            # return the (partial) user profile that retrieved the result, as well as the result itself.
            return {
                "user_profile": self._GetUserProfilePartialDictionary(self.data.spotifyClient.UserProfile),
                "result": result.ToDictionary()
            }

        # the following exceptions have already been logged, so we just need to
        # pass them back to HA for display in the log (or service UI).
        except SpotifyApiError as ex:
            raise HomeAssistantError(ex.Message)
        except SpotifyWebApiError as ex:
            raise HomeAssistantError(ex.Message)
        
        finally:
        
            # trace.
            _logsi.LeaveMethod(SILevel.Debug, apiMethodName)


    def service_spotify_get_show_episodes(self, 
                                          showId:str, 
                                          limit:int, 
                                          offset:int,
                                          market:str=None,
                                          limitTotal:int=None
                                          ) -> dict:
        """
        Get Spotify catalog information about a show's episodes.
        
        Args:
            showId (str):  
                The Spotify ID for the show.
                Example: `6kAsbP8pxwaU2kPibKTuHE`
            limit (int):  
                The maximum number of items to return in a page of items.  
                Default: 20, Range: 1 to 50.  
            offset (int):  
                The index of the first item to return; use with limit to get the next set of items.  
                Default: 0 (the first item).  
            market (str):
                An ISO 3166-1 alpha-2 country code. If a country code is specified, only content that 
                is available in that market will be returned.  If a valid user access token is specified 
                in the request header, the country associated with the user account will take priority over 
                this parameter.  
                Note: If neither market or user country are provided, the content is considered unavailable for the client.  
                Users can view the country that is associated with their account in the account settings.  
                Example: `ES`
            limitTotal (int):
                The maximum number of items to return for the request.
                If specified, this argument overrides the limit and offset argument values
                and paging is automatically used to retrieve all available items up to the
                maximum count specified.
                Default: None (disabled)
                
        Returns:
            A dictionary that contains the following keys:
            - user_profile: A (partial) user profile that retrieved the result.
            - result: A `EpisodePageSimplified` object that contains the show episodes.
        """
        apiMethodName:str = 'service_spotify_get_show_episodes'
        apiMethodParms:SIMethodParmListContext = None
        result:EpisodePageSimplified = None

        try:

            # trace.
            apiMethodParms = _logsi.EnterMethodParmList(SILevel.Debug, apiMethodName)
            apiMethodParms.AppendKeyValue("showId", showId)
            apiMethodParms.AppendKeyValue("limit", limit)
            apiMethodParms.AppendKeyValue("additionaoffsetlTypes", offset)
            apiMethodParms.AppendKeyValue("market", market)
            apiMethodParms.AppendKeyValue("limitTotal", limitTotal)
            _logsi.LogMethodParmList(SILevel.Verbose, "Spotify Get Show Episodes Service", apiMethodParms)
                
            # request information from Spotify Web API.
            _logsi.LogVerbose(STAppMessages.MSG_SERVICE_QUERY_WEB_API)
            result = self.data.spotifyClient.GetShowEpisodes(showId, limit, offset, market, limitTotal)

            # return the (partial) user profile that retrieved the result, as well as the result itself.
            return {
                "user_profile": self._GetUserProfilePartialDictionary(self.data.spotifyClient.UserProfile),
                "result": result.ToDictionary()
            }

        # the following exceptions have already been logged, so we just need to
        # pass them back to HA for display in the log (or service UI).
        except SpotifyApiError as ex:
            raise HomeAssistantError(ex.Message)
        except SpotifyWebApiError as ex:
            raise HomeAssistantError(ex.Message)
        
        finally:
        
            # trace.
            _logsi.LeaveMethod(SILevel.Debug, apiMethodName)


    def service_spotify_get_show_favorites(self, 
                                            limit:int, 
                                            offset:int,
                                            limitTotal:int=None
                                            ) -> dict:
        """
        Get a list of the shows saved in the current Spotify user's 'Your Library'.
        
        Args:
            limit (int):
                The maximum number of items to return in a page of items.  
                Default: 20, Range: 1 to 50.  
            offset (int):
                The index of the first item to return.  
                Use with limit to get the next set of items.  
                Default: 0 (the first item).  
            limitTotal (int):
                The maximum number of items to return for the request.
                If specified, this argument overrides the limit and offset argument values
                and paging is automatically used to retrieve all available items up to the
                maximum count specified.
                Default: None (disabled)
                
        Returns:
            A dictionary that contains the following keys:
            - user_profile: A (partial) user profile that retrieved the result.
            - result: A `ShowPageSaved` object that contains playlist information.
        """
        apiMethodName:str = 'service_spotify_get_show_favorites'
        apiMethodParms:SIMethodParmListContext = None

        try:

            # trace.
            apiMethodParms = _logsi.EnterMethodParmList(SILevel.Debug, apiMethodName)
            apiMethodParms.AppendKeyValue("limit", limit)
            apiMethodParms.AppendKeyValue("offset", offset)
            apiMethodParms.AppendKeyValue("limitTotal", limitTotal)
            _logsi.LogMethodParmList(SILevel.Verbose, "Spotify Get Show Favorites Service", apiMethodParms)
                
            # request information from Spotify Web API.
            _logsi.LogVerbose(STAppMessages.MSG_SERVICE_QUERY_WEB_API)
            result:ShowPageSaved = self.data.spotifyClient.GetShowFavorites(limit, offset, limitTotal)

            # return the (partial) user profile that retrieved the result, as well as the result itself.
            return {
                "user_profile": self._GetUserProfilePartialDictionary(self.data.spotifyClient.UserProfile),
                "result": result.ToDictionary()
            }

        # the following exceptions have already been logged, so we just need to
        # pass them back to HA for display in the log (or service UI).
        except SpotifyApiError as ex:
            raise HomeAssistantError(ex.Message)
        except SpotifyWebApiError as ex:
            raise HomeAssistantError(ex.Message)
        
        finally:
        
            # trace.
            _logsi.LeaveMethod(SILevel.Debug, apiMethodName)


    def service_spotify_get_spotify_connect_devices(
            self,
            ) -> dict:
        """
        Get information about all available Spotify Connect player devices.
        
        This method requires the `user-read-playback-state` scope.

        Returns:
            A dictionary that contains the following keys:
            - user_profile: A (partial) user profile that retrieved the result.
            - result: A list of `Device` objects that contain the device details, sorted by name.
        """
        apiMethodName:str = 'service_spotify_get_spotify_connect_devices'
        apiMethodParms:SIMethodParmListContext = None
        result:SpotifyConnectDevices = None

        try:

            # trace.
            apiMethodParms = _logsi.EnterMethodParmList(SILevel.Debug, apiMethodName)
            _logsi.LogMethodParmList(SILevel.Verbose, "Spotify Get Spotify Connect Devices Service", apiMethodParms)
                
            # request information from Spotify Web API.
            _logsi.LogVerbose(STAppMessages.MSG_SERVICE_QUERY_WEB_API)
            result = self.data.spotifyClient.GetSpotifyConnectDevices()
            
            # build dictionary result from array.
            resultArray:list = []
            item:PlayerDevice
            for item in result.GetDeviceList():
                resultArray.append(item.ToDictionary())

            # return the (partial) user profile that retrieved the result, as well as the result itself.
            return {
                "user_profile": self._GetUserProfilePartialDictionary(self.data.spotifyClient.UserProfile),
                "result": resultArray
            }

        # the following exceptions have already been logged, so we just need to
        # pass them back to HA for display in the log (or service UI).
        except SpotifyApiError as ex:
            raise HomeAssistantError(ex.Message)
        except SpotifyWebApiError as ex:
            raise HomeAssistantError(ex.Message)
        
        finally:
        
            # trace.
            _logsi.LeaveMethod(SILevel.Debug, apiMethodName)


    def service_spotify_get_track_favorites(self, 
                                            limit:int, 
                                            offset:int,
                                            market:str,
                                            limitTotal:int=None
                                            ) -> dict:
        """
        Get a list of the tracks saved in the current Spotify user's 'Your Library'.
        
        Args:
            limit (int):
                The maximum number of items to return in a page of items.  
                Default: 20, Range: 1 to 50.  
            offset (int):
                The index of the first item to return.  
                Use with limit to get the next set of items.  
                Default: 0 (the first item).  
            market (str):
                An ISO 3166-1 alpha-2 country code. If a country code is specified, only content that 
                is available in that market will be returned.  If a valid user access token is specified 
                in the request header, the country associated with the user account will take priority over 
                this parameter.  
                Example: `ES`
            limitTotal (int):
                The maximum number of items to return for the request.
                If specified, this argument overrides the limit and offset argument values
                and paging is automatically used to retrieve all available items up to the
                maximum count specified.
                Default: None (disabled)
                
        Returns:
            A dictionary that contains the following keys:
            - user_profile: A (partial) user profile that retrieved the result.
            - result: A `TrackPageSaved` object that contains playlist information.
        """
        apiMethodName:str = 'service_spotify_get_track_favorites'
        apiMethodParms:SIMethodParmListContext = None
        result:TrackPageSaved = TrackPageSaved()

        try:

            # trace.
            apiMethodParms = _logsi.EnterMethodParmList(SILevel.Debug, apiMethodName)
            apiMethodParms.AppendKeyValue("limit", limit)
            apiMethodParms.AppendKeyValue("offset", offset)
            apiMethodParms.AppendKeyValue("market", market)
            apiMethodParms.AppendKeyValue("limitTotal", limitTotal)
            _logsi.LogMethodParmList(SILevel.Verbose, "Spotify Get Track Favorites Service", apiMethodParms)
                
            # request information from Spotify Web API.
            _logsi.LogVerbose(STAppMessages.MSG_SERVICE_QUERY_WEB_API)
            result:TrackPageSaved = self.data.spotifyClient.GetTrackFavorites(limit, offset, market, limitTotal)

            # return the (partial) user profile that retrieved the result, as well as the result itself.
            return {
                "user_profile": self._GetUserProfilePartialDictionary(self.data.spotifyClient.UserProfile),
                "result": result.ToDictionary()
            }

        # the following exceptions have already been logged, so we just need to
        # pass them back to HA for display in the log (or service UI).
        except SpotifyApiError as ex:
            raise HomeAssistantError(ex.Message)
        except SpotifyWebApiError as ex:
            raise HomeAssistantError(ex.Message)
        
        finally:
        
            # trace.
            _logsi.LeaveMethod(SILevel.Debug, apiMethodName)


    def service_spotify_get_users_top_artists(self, 
                                              timeRange:str,
                                              limit:int, 
                                              offset:int,
                                              limitTotal:int=None
                                              ) -> dict:
        """
        Get the current user's top artists based on calculated affinity.
        
        Args:
            timeRange (str):
                Over what time frame the affinities are computed.  
                Valid values:  
                - long_term (calculated from several years of data and including all new data as it becomes available).  
                - medium_term (approximately last 6 months).  
                - short_term (approximately last 4 weeks).  
                Default: `medium_term`  
                Example: `long_term`
            limit (int):
                The maximum number of items to return in a page of items.  
                Default: 20, Range: 1 to 50.  
            offset (int):
                The index of the first item to return.  
                Use with limit to get the next set of items.  
                Default: 0 (the first item), Range: 0 to 1000
            limitTotal (int):
                The maximum number of items to return for the request.
                If specified, this argument overrides the limit and offset argument values
                and paging is automatically used to retrieve all available items up to the
                maximum count specified.
                Default: None (disabled)
                
        Returns:
            A dictionary that contains the following keys:
            - user_profile: A (partial) user profile that retrieved the result.
            - result: An `ArtistPage` object of matching results.
        """
        apiMethodName:str = 'service_spotify_get_users_top_artists'
        apiMethodParms:SIMethodParmListContext = None

        try:

            # trace.
            apiMethodParms = _logsi.EnterMethodParmList(SILevel.Debug, apiMethodName)
            apiMethodParms.AppendKeyValue("timeRange", timeRange)
            apiMethodParms.AppendKeyValue("limit", limit)
            apiMethodParms.AppendKeyValue("offset", offset)
            apiMethodParms.AppendKeyValue("limitTotal", limitTotal)
            _logsi.LogMethodParmList(SILevel.Verbose, "Spotify Get Users Top Artists Service", apiMethodParms)
                
            # request information from Spotify Web API.
            _logsi.LogVerbose(STAppMessages.MSG_SERVICE_QUERY_WEB_API)
            result:ArtistPage = self.data.spotifyClient.GetUsersTopArtists(timeRange, limit, offset, limitTotal)

            # return the (partial) user profile that retrieved the result, as well as the result itself.
            return {
                "user_profile": self._GetUserProfilePartialDictionary(self.data.spotifyClient.UserProfile),
                "result": result.ToDictionary()
            }

        # the following exceptions have already been logged, so we just need to
        # pass them back to HA for display in the log (or service UI).
        except SpotifyApiError as ex:
            raise HomeAssistantError(ex.Message)
        except SpotifyWebApiError as ex:
            raise HomeAssistantError(ex.Message)
        
        finally:
        
            # trace.
            _logsi.LeaveMethod(SILevel.Debug, apiMethodName)


    def service_spotify_get_users_top_tracks(self, 
                                             timeRange:str,
                                             limit:int, 
                                             offset:int,
                                             limitTotal:int=None
                                             ) -> dict:
        """
        Get the current user's top tracks based on calculated affinity.
        
        Args:
            timeRange (str):
                Over what time frame the affinities are computed.  
                Valid values:  
                - long_term (calculated from several years of data and including all new data as it becomes available).  
                - medium_term (approximately last 6 months).  
                - short_term (approximately last 4 weeks).  
                Default: `medium_term`  
                Example: `long_term`
            limit (int):
                The maximum number of items to return in a page of items.  
                Default: 20, Range: 1 to 50.  
            offset (int):
                The index of the first item to return.  
                Use with limit to get the next set of items.  
                Default: 0 (the first item), Range: 0 to 1000
            limitTotal (int):
                The maximum number of items to return for the request.
                If specified, this argument overrides the limit and offset argument values
                and paging is automatically used to retrieve all available items up to the
                maximum count specified.
                Default: None (disabled)
                
        Returns:
            A dictionary that contains the following keys:
            - user_profile: A (partial) user profile that retrieved the result.
            - result: A `TrackPage` object of matching results.
        """
        apiMethodName:str = 'service_spotify_get_users_top_tracks'
        apiMethodParms:SIMethodParmListContext = None

        try:

            # trace.
            apiMethodParms = _logsi.EnterMethodParmList(SILevel.Debug, apiMethodName)
            apiMethodParms.AppendKeyValue("timeRange", timeRange)
            apiMethodParms.AppendKeyValue("limit", limit)
            apiMethodParms.AppendKeyValue("offset", offset)
            apiMethodParms.AppendKeyValue("limitTotal", limitTotal)
            _logsi.LogMethodParmList(SILevel.Verbose, "Spotify Get Users Top Tracks Service", apiMethodParms)
            
            # request information from Spotify Web API.
            _logsi.LogVerbose(STAppMessages.MSG_SERVICE_QUERY_WEB_API)
            result:TrackPage = self.data.spotifyClient.GetUsersTopTracks(timeRange, limit, offset, limitTotal)

            # return the (partial) user profile that retrieved the result, as well as the result itself.
            return {
                "user_profile": self._GetUserProfilePartialDictionary(self.data.spotifyClient.UserProfile),
                "result": result.ToDictionary()
            }

        # the following exceptions have already been logged, so we just need to
        # pass them back to HA for display in the log (or service UI).
        except SpotifyApiError as ex:
            raise HomeAssistantError(ex.Message)
        except SpotifyWebApiError as ex:
            raise HomeAssistantError(ex.Message)
        
        finally:
        
            # trace.
            _logsi.LeaveMethod(SILevel.Debug, apiMethodName)


    def service_spotify_player_activate_devices(
            self,
            verifyUserContext:bool=False,
            delay:float=0.50,
            ) -> dict:
        """
        Activates all Spotify Connect player devices, and (optionally) switches the active user
        context to the current user context for each device.
        
        Args:
            verifyUserContext (bool):
                If True, the active user context of the resolved device is checked to ensure it
                matches the user context specified on the class constructor.
                If False, the user context will not be checked.
                Default is False.
            delay (float):
                Time delay (in seconds) to wait AFTER issuing the final Connect command (if necessary).
                This delay will give the spotify web api time to process the device list change before 
                another command is issued.  
                Default is 0.50; value range is 0 - 10.
        """
        apiMethodName:str = 'service_spotify_player_activate_devices'
        apiMethodParms:SIMethodParmListContext = None

        try:

            # trace.
            apiMethodParms = _logsi.EnterMethodParmList(SILevel.Debug, apiMethodName)
            apiMethodParms.AppendKeyValue("verifyUserContext", verifyUserContext)
            apiMethodParms.AppendKeyValue("delay", delay)
            _logsi.LogMethodParmList(SILevel.Verbose, "Spotify Player Activate Devices Service", apiMethodParms)
                
            # process Spotify Web API request.
            _logsi.LogVerbose(STAppMessages.MSG_SERVICE_QUERY_WEB_API)
            result = self.data.spotifyClient.PlayerActivateDevices(verifyUserContext, delay)
            
            # return the (partial) user profile that retrieved the result, as well as the result itself.
            return {
                "user_profile": self._GetUserProfilePartialDictionary(self.data.spotifyClient.UserProfile),
                "result": result
            }

        # the following exceptions have already been logged, so we just need to
        # pass them back to HA for display in the log (or service UI).
        except SpotifyApiError as ex:
            raise HomeAssistantError(ex.Message)
        except SpotifyWebApiError as ex:
            raise HomeAssistantError(ex.Message)
        except SpotifyZeroconfApiError as ex:
            raise HomeAssistantError(ex.Message)
        
        finally:
        
            # trace.
            _logsi.LeaveMethod(SILevel.Debug, apiMethodName)


    @spotify_exception_handler
    def service_spotify_player_media_play_context(self, 
                                                  contextUri:str, 
                                                  offsetUri:str, 
                                                  offsetPosition:int, 
                                                  positionMS:int, 
                                                  deviceId:str, 
                                                  ) -> None:
        """
        Start playing one or more tracks of the specified context on a Spotify Connect device.
        
        Args:
            contextUri (str):
                Spotify URI of the context to play.  
                Valid contexts are albums, artists & playlists.  
                Example: `spotify:album:6vc9OTcyd3hyzabCmsdnwE`.   
            offsetUri (str):
                Indicates from what Uri in the context playback should start.  
                Only available when contextUri corresponds to an artist, album or playlist.  
                The offsetPosition argument will be used if this value is null.  
                Default is null.  
                Example: `spotify:track:1301WleyT98MSxVHPZCA6M` start playing at the specified track Uri.  
            offsetPosition (int):
                Indicates from what position in the context playback should start.  
                The value is zero-based, and can't be negative.  
                Only available when contextUri corresponds to an album or playlist.  
                Default is `0`.  
                Example: `3`  start playing at track number 4.
            positionMS (int):
                The position in milliseconds to seek to; must be a positive number.  
                Passing in a position that is greater than the length of the track will cause the 
                player to start playing the next track.  
                Default is `0`.  
                Example: `25000`  
            deviceId (str):
                The id of the device this command is targeting.  
                If not supplied, the user's currently active device is the target.  
                Example: `0d1841b0976bae2a3a310dd74c0f3df354899bc8`
        """
        apiMethodName:str = 'service_spotify_player_media_play_context'
        apiMethodParms:SIMethodParmListContext = None

        try:

            # trace.
            apiMethodParms = _logsi.EnterMethodParmList(SILevel.Debug, apiMethodName)
            apiMethodParms.AppendKeyValue("contextUri", contextUri)
            apiMethodParms.AppendKeyValue("offsetUri", offsetUri)
            apiMethodParms.AppendKeyValue("offsetPosition", offsetPosition)
            apiMethodParms.AppendKeyValue("positionMS", positionMS)
            apiMethodParms.AppendKeyValue("deviceId", deviceId)
            _logsi.LogMethodParmList(SILevel.Verbose, "Spotify Player Media Play Context Service", apiMethodParms)
            
            # see if default device option was specified (e.g. deviceId="*").
            deviceId = self._GetDefaultDeviceOption(deviceId)

            # start playing one or more tracks of the specified context on a Spotify Connect device.
            _logsi.LogVerbose("Playing Media Context on device")
            self.data.spotifyClient.PlayerMediaPlayContext(contextUri, offsetUri, offsetPosition, positionMS, deviceId)

            # update ha state.
            self.schedule_update_ha_state(force_refresh=False)

        # the following exceptions have already been logged, so we just need to
        # pass them back to HA for display in the log (or service UI).
        except SpotifyApiError as ex:
            raise HomeAssistantError(ex.Message)

        except SpotifyWebApiError as ex:
            raise HomeAssistantError(ex.Message)
        
        finally:
        
            # trace.
            _logsi.LeaveMethod(SILevel.Debug, apiMethodName)


    @spotify_exception_handler
    def service_spotify_player_media_play_track_favorites(self, 
                                                          deviceId:str, 
                                                          shuffle:bool,
                                                          delay:float
                                                          ) -> None:
        """
        Start playing one or more tracks on the specified Spotify Connect device.
        
        Args:
            deviceId (str):
                The id of the device this command is targeting.  
                If not supplied, the user's currently active device is the target.  
                Example: `0d1841b0976bae2a3a310dd74c0f3df354899bc8`
            shuffle (bool):
                True to set player shuffle mode to on; otherwise, False for no shuffle.
            delay (float):
                Time delay (in seconds) to wait AFTER issuing the command to the player.  
                This delay will give the spotify web api time to process the change before 
                another command is issued.  
                Default is 0.50; value range is 0 - 10.
        """
        apiMethodName:str = 'service_spotify_player_media_play_track_favorites'
        apiMethodParms:SIMethodParmListContext = None

        try:

            # trace.
            apiMethodParms = _logsi.EnterMethodParmList(SILevel.Debug, apiMethodName)
            apiMethodParms.AppendKeyValue("deviceId", deviceId)
            apiMethodParms.AppendKeyValue("shuffle", shuffle)
            apiMethodParms.AppendKeyValue("delay", delay)
            _logsi.LogMethodParmList(SILevel.Verbose, "Spotify Player Media Play Favorite Tracks Service", apiMethodParms)
            
            # see if default device option was specified (e.g. deviceId="*").
            deviceId = self._GetDefaultDeviceOption(deviceId)

            # start playing track favorites on the specified Spotify Connect device.
            _logsi.LogVerbose("Playing Media Favorite Tracks on device")
            self.data.spotifyClient.PlayerMediaPlayTrackFavorites(deviceId, shuffle, delay)

            # update ha state.
            self.schedule_update_ha_state(force_refresh=False)

        # the following exceptions have already been logged, so we just need to
        # pass them back to HA for display in the log (or service UI).
        except SpotifyApiError as ex:
            raise HomeAssistantError(ex.Message)
        except SpotifyWebApiError as ex:
            raise HomeAssistantError(ex.Message)
        
        finally:
        
            # trace.
            _logsi.LeaveMethod(SILevel.Debug, apiMethodName)


    @spotify_exception_handler
    def service_spotify_player_media_play_tracks(self, 
                                                 uris:str, 
                                                 positionMS:int, 
                                                 deviceId:str, 
                                                 ) -> None:
        """
        Start playing one or more tracks on the specified Spotify Connect device.
        
        Args:
            uris (str):
                A list of Spotify track URIs to play; can be track or episode URIs.  
                Example: [`spotify:track:4iV5W9uYEdYUVa79Axb7Rh` ,`spotify:episode:512ojhOuo1ktJprKbVcKyQ`].  
                It can also be specified as a comma-delimited string.  
                Example: `spotify:track:4iV5W9uYEdYUVa79Axb7Rh,spotify:episode:512ojhOuo1ktJprKbVcKyQ`.  
                A maximum of 50 items can be added in one request.
            positionMS (int):
                The position in milliseconds to seek to; must be a positive number.  
                Passing in a position that is greater than the length of the track will cause the 
                player to start playing the next track.  
                Default is `0`.  
                Example: `25000`  
            deviceId (str):
                The id of the device this command is targeting.  
                If not supplied, the user's currently active device is the target.  
                Example: `0d1841b0976bae2a3a310dd74c0f3df354899bc8`
        """
        apiMethodName:str = 'service_spotify_player_media_play_tracks'
        apiMethodParms:SIMethodParmListContext = None

        try:

            # trace.
            apiMethodParms = _logsi.EnterMethodParmList(SILevel.Debug, apiMethodName)
            apiMethodParms.AppendKeyValue("uris", uris)
            apiMethodParms.AppendKeyValue("positionMS", positionMS)
            apiMethodParms.AppendKeyValue("deviceId", deviceId)
            _logsi.LogMethodParmList(SILevel.Verbose, "Spotify Player Media Play Tracks Service", apiMethodParms)
            
            # see if default device option was specified (e.g. deviceId="*").
            deviceId = self._GetDefaultDeviceOption(deviceId)

            # start playing one or more tracks on the specified Spotify Connect device.
            _logsi.LogVerbose("Playing Media Tracks on device")
            self.data.spotifyClient.PlayerMediaPlayTracks(uris, positionMS, deviceId)

            # update ha state.
            self.schedule_update_ha_state(force_refresh=False)

        # the following exceptions have already been logged, so we just need to
        # pass them back to HA for display in the log (or service UI).
        except SpotifyApiError as ex:
            raise HomeAssistantError(ex.Message)
        except SpotifyWebApiError as ex:
            raise HomeAssistantError(ex.Message)
        
        finally:
        
            # trace.
            _logsi.LeaveMethod(SILevel.Debug, apiMethodName)


    def service_spotify_player_resolve_device_id(
            self,
            deviceValue:str, 
            verifyUserContext:bool=True,
            verifyTimeout:float=5.0,
            ) -> dict:
        """
        Resolves a Spotify Connect device identifier from a specified device id, name, alias id,
        or alias name.  This will ensure that the device id can be found on the network, as well 
        as connect to the device if necessary with the current user context.  
        
        Args:
            deviceValue (str):
                The device id / name value to check.
            verifyUserContext (bool):
                If True, the active user context of the resolved device is checked to ensure it
                matches the user context specified on the class constructor.
                If False, the user context will not be checked.
                Default is True.
            verifyTimeout (float):
                Maximum time to wait (in seconds) for the device to become active in the Spotify
                Connect device list.  This value is only used if a Connect command has to be
                issued to activate the device.
                Default is 5; value range is 0 - 10.
        """
        apiMethodName:str = 'service_spotify_player_resolve_device_id'
        apiMethodParms:SIMethodParmListContext = None

        try:

            # trace.
            apiMethodParms = _logsi.EnterMethodParmList(SILevel.Debug, apiMethodName)
            apiMethodParms.AppendKeyValue("deviceValue", deviceValue)
            apiMethodParms.AppendKeyValue("verifyUserContext", verifyUserContext)
            apiMethodParms.AppendKeyValue("verifyTimeout", verifyTimeout)
            _logsi.LogMethodParmList(SILevel.Verbose, "Spotify Player Resolve Device Id Service", apiMethodParms)
                
            # process Spotify Web API request.
            _logsi.LogVerbose(STAppMessages.MSG_SERVICE_QUERY_WEB_API)
            result = self.data.spotifyClient.PlayerResolveDeviceId(deviceValue, verifyUserContext, verifyTimeout)
            
            # return the (partial) user profile that retrieved the result, as well as the result itself.
            return {
                "user_profile": self._GetUserProfilePartialDictionary(self.data.spotifyClient.UserProfile),
                "result": result
            }

        # the following exceptions have already been logged, so we just need to
        # pass them back to HA for display in the log (or service UI).
        except SpotifyApiError as ex:
            raise HomeAssistantError(ex.Message)
        except SpotifyWebApiError as ex:
            raise HomeAssistantError(ex.Message)
        except SpotifyZeroconfApiError as ex:
            raise HomeAssistantError(ex.Message)
        
        finally:
        
            # trace.
            _logsi.LeaveMethod(SILevel.Debug, apiMethodName)


    def service_spotify_player_transfer_playback(self, 
                                                 deviceId:str, 
                                                 play:bool=True, 
                                                 ) -> None:
        """
        Transfer playback to a new Spotify Connect device and optionally begin playback.
        
        Args:
            deviceId (str):
                The id of the device on which playback should be started/transferred.
                Example: `0d1841b0976bae2a3a310dd74c0f3df354899bc8`
            play (bool):
                The transfer method:  
                - `True`  - ensure playback happens on new device.   
                - `False` - keep the current playback state.  
                Default: `True`  
        """
        apiMethodName:str = 'service_spotify_player_transfer_playback'
        apiMethodParms:SIMethodParmListContext = None

        try:

            # trace.
            apiMethodParms = _logsi.EnterMethodParmList(SILevel.Debug, apiMethodName)
            apiMethodParms.AppendKeyValue("deviceId", deviceId)
            apiMethodParms.AppendKeyValue("play", play)
            _logsi.LogMethodParmList(SILevel.Verbose, "Spotify Player Transfer Playback Service", apiMethodParms)
            
            # validations.
            if play is None:
                play = True
            if deviceId is None or deviceId == "*":
                deviceId = PlayerDevice.GetIdFromSelectItem(self.data.OptionDeviceDefault)
                
            # ensure spotify client has the most current device list.
            # we don't do anything with them here, but it will refresh the cache which is
            # what the PlayerTransferPlayback method uses to resolve device id from a device name.
            self.data.spotifyClient.GetPlayerDevices(True)
                
            # transfer playback to the specified Spotify Connect device.
            _logsi.LogVerbose("'%s': Transferring Spotify Playback to device '%s'" % (self.name, deviceId))
            self.data.spotifyClient.PlayerTransferPlayback(deviceId, play)

            # update ha state.
            self.schedule_update_ha_state(force_refresh=False)

        # the following exceptions have already been logged, so we just need to
        # pass them back to HA for display in the log (or service UI).
        except SpotifyApiError as ex:
            raise HomeAssistantError(ex.Message)
        except SpotifyWebApiError as ex:
            raise HomeAssistantError(ex.Message)
        
        finally:
        
            # trace.
            _logsi.LeaveMethod(SILevel.Debug, apiMethodName)


    def service_spotify_playlist_cover_image_add(self, 
                                                 playlistId:str, 
                                                 imagePath:str, 
                                                 ) -> None:
        """
        Replace the image used to represent a specific playlist.
        
        Args:
            playlistId (str):  
                The Spotify ID of the playlist.  
                Example: `5v5ETK9WFXAnGQ3MRubKuE`
            imagePath (str):
                The fully-qualified path of the image to be uploaded.  
                The image must be in JPEG format, and cannot exceed 256KB in Base64 encoded size.  
        """
        apiMethodName:str = 'service_spotify_playlist_cover_image_add'
        apiMethodParms:SIMethodParmListContext = None

        try:

            # trace.
            apiMethodParms = _logsi.EnterMethodParmList(SILevel.Debug, apiMethodName)
            apiMethodParms.AppendKeyValue("playlistId", playlistId)
            apiMethodParms.AppendKeyValue("imagePath", imagePath)
            _logsi.LogMethodParmList(SILevel.Verbose, "Spotify Playlist Add Cover Image Service", apiMethodParms)
            
            # add playlist cover image.
            _logsi.LogVerbose("Adding cover image to Spotify playlist")
            self.data.spotifyClient.AddPlaylistCoverImage(playlistId, imagePath)

        # the following exceptions have already been logged, so we just need to
        # pass them back to HA for display in the log (or service UI).
        except SpotifyApiError as ex:
            raise HomeAssistantError(ex.Message)
        except SpotifyWebApiError as ex:
            raise HomeAssistantError(ex.Message)
        
        finally:
        
            # trace.
            _logsi.LeaveMethod(SILevel.Debug, apiMethodName)


    def service_spotify_playlist_change(self, 
                                        playlistId:str, 
                                        name:str=None,
                                        description:str=None,
                                        public:bool=True,
                                        collaborative:bool=False,
                                        imagePath:str=None
                                        ) -> None:
        """
        Change a playlist's details (name, description, and public / private state).
        
        Args:
        
            playlistId (str):  
                The Spotify ID of the playlist.
                Example: `5AC9ZXA7nJ7oGWO911FuDG`
            name (str):
                The updated name for the playlist, for example "My New Playlist Title"
                This name does not need to be unique; a user may have several playlists with 
                the same name.
            description (str):
                The updated playlist description, as displayed in Spotify Clients and in the Web API.
            public (bool):
                If true, the playlist will be public; if false, it will be private.  
            collaborative (bool):
                If true, the playlist will become collaborative and other users will be able to modify 
                the playlist in their Spotify client.  
                Note: You can only set collaborative to true on non-public playlists.
            imagePath (str):
                A fully-qualified path of an image to display for the playlist.
                The image must be in JPEG format, and cannot exceed 256KB in Base64 encoded size.  
                Specify null if you do not wish to update the existing playlist image.  
        """
        apiMethodName:str = 'service_spotify_playlist_change'
        apiMethodParms:SIMethodParmListContext = None

        try:

            # trace.
            apiMethodParms = _logsi.EnterMethodParmList(SILevel.Debug, apiMethodName)
            apiMethodParms.AppendKeyValue("playlistId", playlistId)
            apiMethodParms.AppendKeyValue("name", name)
            apiMethodParms.AppendKeyValue("description", description)
            apiMethodParms.AppendKeyValue("public", public)
            apiMethodParms.AppendKeyValue("collaborative", collaborative)
            apiMethodParms.AppendKeyValue("imagePath", imagePath)
            _logsi.LogMethodParmList(SILevel.Verbose, "Spotify Playlist Change Service", imagePath)
                
            # create Spotify playlist.
            _logsi.LogVerbose("Changing Spotify Playlist Details")
            self.data.spotifyClient.ChangePlaylistDetails(playlistId, name, description, public, collaborative, imagePath)

        # the following exceptions have already been logged, so we just need to
        # pass them back to HA for display in the log (or service UI).
        except SpotifyApiError as ex:
            raise HomeAssistantError(ex.Message)
        except SpotifyWebApiError as ex:
            raise HomeAssistantError(ex.Message)
        
        finally:
        
            # trace.
            _logsi.LeaveMethod(SILevel.Debug, apiMethodName)


    def service_spotify_playlist_create(self, 
                                        userId:str, 
                                        name:str=None,
                                        description:str=None,
                                        public:bool=True,
                                        collaborative:bool=False,
                                        imagePath:str=None
                                        ) -> dict:
        """
        Create an empty playlist for a Spotify user.  
        
        This method requires the `playlist-modify-public` and `playlist-modify-private` scope.
        
        Args:
        
            userId (str):  
                The user's Spotify user ID.
                Example: `32k99y2kg5lnn3mxhtmd2bpdkjfu`
            name (str):
                The name for the new playlist, for example "My Playlist".  
                This name does not need to be unique; a user may have several playlists with 
                the same name.
            description (str):
                The playlist description, as displayed in Spotify Clients and in the Web API.
            public (bool):
                If true, the playlist will be public; if false, it will be private.  
                To be able to create private playlists, the user must have granted the 
                `playlist-modify-private` scope.  
                Defaults to true. 
            collaborative (bool):
                If true, the playlist will be collaborative.  
                Note: to create a collaborative playlist you must also set public to false. 
                To create collaborative playlists you must have granted `playlist-modify-private`
                and `playlist-modify-public` scope.  
                Defaults to false.
            imagePath (str):
                A fully-qualified path of an image to display for the playlist.
                The image must be in JPEG format, and cannot exceed 256KB in Base64 encoded size.  
                Omit this argument if you do not wish to add a playlist image.  

        Returns:
            A dictionary that contains the following keys:
            - user_profile: A (partial) user profile that retrieved the result.
            - result: A `Playlist` object that contains the playlist details.  
        """
        apiMethodName:str = 'service_spotify_playlist_create'
        apiMethodParms:SIMethodParmListContext = None
        result:Playlist = None

        try:

            # trace.
            apiMethodParms = _logsi.EnterMethodParmList(SILevel.Debug, apiMethodName)
            apiMethodParms.AppendKeyValue("userId", userId)
            apiMethodParms.AppendKeyValue("name", name)
            apiMethodParms.AppendKeyValue("description", description)
            apiMethodParms.AppendKeyValue("public", public)
            apiMethodParms.AppendKeyValue("collaborative", collaborative)
            apiMethodParms.AppendKeyValue("imagePath", imagePath)
            _logsi.LogMethodParmList(SILevel.Verbose, "Spotify Playlist Create Service", apiMethodParms)
                
            # create Spotify playlist.
            _logsi.LogVerbose("Creating Spotify Playlist")
            result = self.data.spotifyClient.CreatePlaylist(userId, name, description, public, collaborative, imagePath)

            # return the (partial) user profile that retrieved the result, as well as the result itself.
            return {
                "user_profile": self._GetUserProfilePartialDictionary(self.data.spotifyClient.UserProfile),
                "result": result.ToDictionary()
            }

        # the following exceptions have already been logged, so we just need to
        # pass them back to HA for display in the log (or service UI).
        except SpotifyApiError as ex:
            raise HomeAssistantError(ex.Message)
        except SpotifyWebApiError as ex:
            raise HomeAssistantError(ex.Message)
        
        finally:
        
            # trace.
            _logsi.LeaveMethod(SILevel.Debug, apiMethodName)


    def service_spotify_playlist_items_add(self, 
                                           playlistId:str, 
                                           uris:str, 
                                           position:int,
                                           ) -> None:
        """
        Add one or more items to a user's playlist.
        
        Args:
        
            playlistId (str):  
                The Spotify ID of the playlist.
                Example: `5AC9ZXA7nJ7oGWO911FuDG`
            uris (str):  
                A comma-separated list of Spotify URIs to add; can be track or episode URIs.  
                Example: `spotify:track:4iV5W9uYEdYUVa79Axb7Rh,spotify:episode:512ojhOuo1ktJprKbVcKyQ`.  
                A maximum of 100 items can be specified in one request.
                If nothing is specified, then the track (or episode) uri currently playing is used.
            position (int):  
                The position to insert the items, a zero-based index.  
                For example, to insert the items in the first position: position=0;  
                to insert the items in the third position: position=2.  
                If omitted, the items will be appended to the playlist.  
                Items are added in the order they are listed in the `uris` argument.
        """
        apiMethodName:str = 'service_spotify_playlist_items_add'
        apiMethodParms:SIMethodParmListContext = None

        try:

            # trace.
            apiMethodParms = _logsi.EnterMethodParmList(SILevel.Debug, apiMethodName)
            apiMethodParms.AppendKeyValue("playlistId", playlistId)
            apiMethodParms.AppendKeyValue("uris", uris)
            apiMethodParms.AppendKeyValue("position", position)
            _logsi.LogMethodParmList(SILevel.Verbose, "Spotify Playlist Add Items Service", apiMethodParms)
            
            # validation - if position is -1 then set it to None (treat as append).
            if isinstance(position, int) and position == -1:
                position = None
               
            # add items to Spotify playlist.
            _logsi.LogVerbose("Adding item(s) to Spotify playlist")
            self.data.spotifyClient.AddPlaylistItems(playlistId, uris, position)

        # the following exceptions have already been logged, so we just need to
        # pass them back to HA for display in the log (or service UI).
        except SpotifyApiError as ex:
            raise HomeAssistantError(ex.Message)
        except SpotifyWebApiError as ex:
            raise HomeAssistantError(ex.Message)
        
        finally:
        
            # trace.
            _logsi.LeaveMethod(SILevel.Debug, apiMethodName)


    def service_spotify_playlist_items_clear(self, 
                                             playlistId:str, 
                                             ) -> None:
        """
        Removes (clears) all items from a user's playlist.
        
        Args:
        
            playlistId (str):  
                The Spotify ID of the playlist.
                Example: `5AC9ZXA7nJ7oGWO911FuDG`
        """
        apiMethodName:str = 'service_spotify_playlist_items_clear'
        apiMethodParms:SIMethodParmListContext = None

        try:

            # trace.
            apiMethodParms = _logsi.EnterMethodParmList(SILevel.Debug, apiMethodName)
            apiMethodParms.AppendKeyValue("playlistId", playlistId)
            _logsi.LogMethodParmList(SILevel.Verbose, "Spotify Playlist Clear Items Service", apiMethodParms)
            
            # clear items from Spotify playlist.
            _logsi.LogVerbose("Clearing item(s) from Spotify playlist")
            self.data.spotifyClient.ClearPlaylistItems(playlistId)

        # the following exceptions have already been logged, so we just need to
        # pass them back to HA for display in the log (or service UI).
        except SpotifyApiError as ex:
            raise HomeAssistantError(ex.Message)
        except SpotifyWebApiError as ex:
            raise HomeAssistantError(ex.Message)
        
        finally:
        
            # trace.
            _logsi.LeaveMethod(SILevel.Debug, apiMethodName)


    def service_spotify_playlist_items_remove(self, 
                                              playlistId:str, 
                                              uris:str, 
                                              snapshotId:str,
                                              ) -> None:
        """
        Remove one or more items from a user's playlist.
        
        Args:
        
            playlistId (str):  
                The Spotify ID of the playlist.
                Example: `5AC9ZXA7nJ7oGWO911FuDG`
            uris (str):  
                A comma-separated list of Spotify URIs to remove; can be track or episode URIs.  
                Example: `spotify:track:4iV5W9uYEdYUVa79Axb7Rh,spotify:episode:512ojhOuo1ktJprKbVcKyQ`.  
                A maximum of 100 items can be specified in one request.
                If nothing is specified, then the track (or episode) uri currently playing is used.
            snapshotId (str):  
                The playlist's snapshot ID against which you want to make the changes.  
                The API will validate that the specified items exist and in the specified positions and 
                make the changes, even if more recent changes have been made to the playlist.
                If null, the current playlist is updated.  
                Default is null.
        """
        apiMethodName:str = 'service_spotify_playlist_items_remove'
        apiMethodParms:SIMethodParmListContext = None

        try:

            # trace.
            apiMethodParms = _logsi.EnterMethodParmList(SILevel.Debug, apiMethodName)
            apiMethodParms.AppendKeyValue("playlistId", playlistId)
            apiMethodParms.AppendKeyValue("uris", uris)
            apiMethodParms.AppendKeyValue("snapshotId", snapshotId)
            _logsi.LogMethodParmList(SILevel.Verbose, "Spotify Playlist Remove Items Service", apiMethodParms)
                           
            # remove items from Spotify playlist.
            _logsi.LogVerbose("Removing item(s) from Spotify playlist")
            self.data.spotifyClient.RemovePlaylistItems(playlistId, uris, snapshotId)

        # the following exceptions have already been logged, so we just need to
        # pass them back to HA for display in the log (or service UI).
        except SpotifyApiError as ex:
            raise HomeAssistantError(ex.Message)
        except SpotifyWebApiError as ex:
            raise HomeAssistantError(ex.Message)
        
        finally:
        
            # trace.
            _logsi.LeaveMethod(SILevel.Debug, apiMethodName)


    def service_spotify_remove_album_favorites(self, 
                                               ids:str=None, 
                                               ) -> None:
        """
        Remove one or more albums from the current user's 'Your Library'.
        
        Args:
            ids (str):  
                A comma-separated list of the Spotify IDs for the albums.  
                Maximum: 50 IDs.  
                Example: `6vc9OTcyd3hyzabCmsdnwE,382ObEPsp2rxGrnsizN5TX`
                If null, the currently playing track album uri id value is used.
        """
        apiMethodName:str = 'service_spotify_remove_album_favorites'
        apiMethodParms:SIMethodParmListContext = None

        try:

            # trace.
            apiMethodParms = _logsi.EnterMethodParmList(SILevel.Debug, apiMethodName)
            apiMethodParms.AppendKeyValue("ids", ids)
            _logsi.LogMethodParmList(SILevel.Verbose, "Spotify Remove Album Favorites Service", apiMethodParms)
                           
            # remove items from Spotify album favorites.
            _logsi.LogVerbose("Removing items(s) from Spotify Album Favorites")
            self.data.spotifyClient.RemoveAlbumFavorites(ids)

        # the following exceptions have already been logged, so we just need to
        # pass them back to HA for display in the log (or service UI).
        except SpotifyApiError as ex:
            raise HomeAssistantError(ex.Message)
        except SpotifyWebApiError as ex:
            raise HomeAssistantError(ex.Message)
        
        finally:
        
            # trace.
            _logsi.LeaveMethod(SILevel.Debug, apiMethodName)


    def service_spotify_remove_track_favorites(self, 
                                               ids:str=None, 
                                               ) -> None:
        """
        Remove one or more tracks from the current user's 'Your Library'.
        
        Args:
            ids (str):  
                A comma-separated list of the Spotify IDs for the tracks.  
                Maximum: 50 IDs.  
                Example: `1kWUud3vY5ij5r62zxpTRy,4eoYKv2kDwJS7gRGh5q6SK`
                If null, the currently playing context uri id value is used.
        """
        apiMethodName:str = 'service_spotify_remove_track_favorites'
        apiMethodParms:SIMethodParmListContext = None

        try:

            # trace.
            apiMethodParms = _logsi.EnterMethodParmList(SILevel.Debug, apiMethodName)
            apiMethodParms.AppendKeyValue("ids", ids)
            _logsi.LogMethodParmList(SILevel.Verbose, "Spotify Remove Track Favorites Service", apiMethodParms)
                           
            # remove items from Spotify track favorites.
            _logsi.LogVerbose("Removing items(s) from Spotify Track Favorites")
            self.data.spotifyClient.RemoveTrackFavorites(ids)

        # the following exceptions have already been logged, so we just need to
        # pass them back to HA for display in the log (or service UI).
        except SpotifyApiError as ex:
            raise HomeAssistantError(ex.Message)
        except SpotifyWebApiError as ex:
            raise HomeAssistantError(ex.Message)
        
        finally:
        
            # trace.
            _logsi.LeaveMethod(SILevel.Debug, apiMethodName)


    def service_spotify_save_album_favorites(self, 
                                             ids:str=None, 
                                             ) -> None:
        """
        Save one or more albums to the current user's 'Your Library'.
        
        Args:
            ids (str):  
                A comma-separated list of the Spotify IDs for the albums.  
                Maximum: 50 IDs.  
                Example: `6vc9OTcyd3hyzabCmsdnwE,382ObEPsp2rxGrnsizN5TX`
                If null, the currently playing track album uri id value is used.
        """
        apiMethodName:str = 'service_spotify_save_album_favorites'
        apiMethodParms:SIMethodParmListContext = None

        try:

            # trace.
            apiMethodParms = _logsi.EnterMethodParmList(SILevel.Debug, apiMethodName)
            apiMethodParms.AppendKeyValue("ids", ids)
            _logsi.LogMethodParmList(SILevel.Verbose, "Spotify Save Album Favorites Service", apiMethodParms)
                           
            # save items to Spotify album favorites.
            _logsi.LogVerbose("Saving items(s) to Spotify Album Favorites")
            self.data.spotifyClient.SaveAlbumFavorites(ids)

        # the following exceptions have already been logged, so we just need to
        # pass them back to HA for display in the log (or service UI).
        except SpotifyApiError as ex:
            raise HomeAssistantError(ex.Message)
        except SpotifyWebApiError as ex:
            raise HomeAssistantError(ex.Message)
        
        finally:
        
            # trace.
            _logsi.LeaveMethod(SILevel.Debug, apiMethodName)


    def service_spotify_save_track_favorites(self, 
                                             ids:str=None, 
                                             ) -> None:
        """
        Save one or more tracks to the current user's 'Your Library'.
        
        Args:
            ids (str):  
                A comma-separated list of the Spotify IDs for the tracks.  
                Maximum: 50 IDs.  
                Example: `1kWUud3vY5ij5r62zxpTRy,4eoYKv2kDwJS7gRGh5q6SK`
                If null, the currently playing context uri id value is used.
        """
        apiMethodName:str = 'service_spotify_save_track_favorites'
        apiMethodParms:SIMethodParmListContext = None

        try:

            # trace.
            apiMethodParms = _logsi.EnterMethodParmList(SILevel.Debug, apiMethodName)
            apiMethodParms.AppendKeyValue("ids", ids)
            _logsi.LogMethodParmList(SILevel.Verbose, "Spotify Save Track Favorites Service", apiMethodParms)
                           
            # save items to Spotify track favorites.
            _logsi.LogVerbose("Saving items(s) to Spotify Track Favorites")
            self.data.spotifyClient.SaveTrackFavorites(ids)

        # the following exceptions have already been logged, so we just need to
        # pass them back to HA for display in the log (or service UI).
        except SpotifyApiError as ex:
            raise HomeAssistantError(ex.Message)
        except SpotifyWebApiError as ex:
            raise HomeAssistantError(ex.Message)
        
        finally:
        
            # trace.
            _logsi.LeaveMethod(SILevel.Debug, apiMethodName)


    def service_spotify_search_albums(self, 
                                      criteria:str, 
                                      limit:int, 
                                      offset:int, 
                                      market:str,
                                      includeExternal:str,
                                      limitTotal:int,
                                      ) -> dict:
        """
        Get Spotify catalog information about albums that match a keyword string.

        Args:
            criteria (str):
                Your search query.  
                You can narrow down your search using field filters.  
                The available filters are album, artist, track, year, upc, tag:hipster, tag:new, 
                isrc, and genre. Each field filter only applies to certain result types.  
                The artist and year filters can be used while searching albums, artists and tracks.
                You can filter on a single year or a range (e.g. 1955-1960).  
                The album filter can be used while searching albums and tracks.  
                The genre filter can be used while searching artists and tracks.  
                The isrc and track filters can be used while searching tracks.  
                The upc, tag:new and tag:hipster filters can only be used while searching albums. 
                The tag:new filter will return albums released in the past two weeks and tag:hipster 
                can be used to return only albums with the lowest 10% popularity.
            limit (int):
                The maximum number of items to return in a page of items.  
                Default: 20, Range: 1 to 50.  
            offset (int):
                The page index offset of the first item to return.  
                Use with limit to get the next set of items.  
                Default: 0 (the first item).  Range: 0 to 1000.  
            market (str):
                An ISO 3166-1 alpha-2 country code. If a country code is specified, only content that 
                is available in that market will be returned.  If a valid user access token is specified 
                in the request header, the country associated with the user account will take priority over 
                this parameter.  
                Note: If neither market or user country are provided, the content is considered unavailable for the client.  
                Users can view the country that is associated with their account in the account settings.  
                Example: `ES`
            includeExternal (str):
                If "audio" is specified it signals that the client can play externally hosted audio content, and 
                marks the content as playable in the response. By default externally hosted audio content is marked 
                as unplayable in the response.  
                Allowed values: "audio"
            limitTotal (int):
                The maximum number of items to return for the request.  
                If specified, this argument overrides the limit and offset argument values
                and paging is automatically used to retrieve all available items up to the
                maximum number specified.  
                Default: None (disabled)

        Returns:
            A dictionary that contains the following keys:
            - user_profile: A (partial) user profile that retrieved the result.
            - result: An `AlbumPageSimplified` object of matching results.            
        """
        apiMethodName:str = 'service_spotify_search_albums'
        apiMethodParms:SIMethodParmListContext = None
        result:SearchResponse = None

        try:

            # trace.
            apiMethodParms = _logsi.EnterMethodParmList(SILevel.Debug, apiMethodName)
            apiMethodParms.AppendKeyValue("criteria", criteria)
            apiMethodParms.AppendKeyValue("limit", limit)
            apiMethodParms.AppendKeyValue("offset", offset)
            apiMethodParms.AppendKeyValue("market", market)
            apiMethodParms.AppendKeyValue("includeExternal", includeExternal)
            apiMethodParms.AppendKeyValue("limitTotal", limitTotal)
            _logsi.LogMethodParmList(SILevel.Verbose, "Spotify Search Albums Service", apiMethodParms)
                
            # get Spotify catalog information about Albums that match a keyword string.
            _logsi.LogVerbose("Searching Spotify Albums for criteria")
            searchResponse:SearchResponse = self.data.spotifyClient.SearchAlbums(criteria, limit, offset, market, includeExternal, limitTotal)

            # return the (partial) user profile that retrieved the result, as well as the result itself.
            return {
                "user_profile": self._GetUserProfilePartialDictionary(self.data.spotifyClient.UserProfile),
                "result": searchResponse.Albums.ToDictionary()
            }

        # the following exceptions have already been logged, so we just need to
        # pass them back to HA for display in the log (or service UI).
        except SpotifyApiError as ex:
            raise HomeAssistantError(ex.Message)
        except SpotifyWebApiError as ex:
            raise HomeAssistantError(ex.Message)
        
        finally:
        
            # trace.
            _logsi.LeaveMethod(SILevel.Debug, apiMethodName)


    def service_spotify_search_artists(self, 
                                       criteria:str, 
                                       limit:int, 
                                       offset:int, 
                                       market:str,
                                       includeExternal:str,
                                       limitTotal:int,
                                       ) -> dict:
        """
        Get Spotify catalog information about artists that match a keyword string.

        Args:
            criteria (str):
                Your search query.  
                You can narrow down your search using field filters.  
                The available filters are album, artist, track, year, upc, tag:hipster, tag:new, 
                isrc, and genre. Each field filter only applies to certain result types.  
                The artist and year filters can be used while searching albums, artists and tracks.
                You can filter on a single year or a range (e.g. 1955-1960).  
                The album filter can be used while searching albums and tracks.  
                The genre filter can be used while searching artists and tracks.  
                The isrc and track filters can be used while searching tracks.  
                The upc, tag:new and tag:hipster filters can only be used while searching albums. 
                The tag:new filter will return albums released in the past two weeks and tag:hipster 
                can be used to return only albums with the lowest 10% popularity.
            limit (int):
                The maximum number of items to return in a page of items.  
                Default: 20, Range: 1 to 50.  
            offset (int):
                The page index offset of the first item to return.  
                Use with limit to get the next set of items.  
                Default: 0 (the first item).  Range: 0 to 1000.  
            market (str):
                An ISO 3166-1 alpha-2 country code. If a country code is specified, only content that 
                is available in that market will be returned.  If a valid user access token is specified 
                in the request header, the country associated with the user account will take priority over 
                this parameter.  
                Note: If neither market or user country are provided, the content is considered unavailable for the client.  
                Users can view the country that is associated with their account in the account settings.  
                Example: `ES`
            includeExternal (str):
                If "audio" is specified it signals that the client can play externally hosted audio content, and 
                marks the content as playable in the response. By default externally hosted audio content is marked 
                as unplayable in the response.  
                Allowed values: "audio"
            limitTotal (int):
                The maximum number of items to return for the request.  
                If specified, this argument overrides the limit and offset argument values
                and paging is automatically used to retrieve all available items up to the
                maximum number specified.  
                Default: None (disabled)

        Returns:
            A dictionary that contains the following keys:
            - user_profile: A (partial) user profile that retrieved the result.
            - result: An `ArtistPage` object of matching results.            
        """
        apiMethodName:str = 'service_spotify_search_artists'
        apiMethodParms:SIMethodParmListContext = None
        result:SearchResponse = None

        try:

            # trace.
            apiMethodParms = _logsi.EnterMethodParmList(SILevel.Debug, apiMethodName)
            apiMethodParms.AppendKeyValue("criteria", criteria)
            apiMethodParms.AppendKeyValue("limit", limit)
            apiMethodParms.AppendKeyValue("offset", offset)
            apiMethodParms.AppendKeyValue("market", market)
            apiMethodParms.AppendKeyValue("includeExternal", includeExternal)
            apiMethodParms.AppendKeyValue("limitTotal", limitTotal)
            _logsi.LogMethodParmList(SILevel.Verbose, "Spotify Search Artists Service", apiMethodParms)
                
            # get Spotify catalog information about Artists that match a keyword string.
            _logsi.LogVerbose("Searching Spotify Artists for criteria")
            searchResponse:SearchResponse = self.data.spotifyClient.SearchArtists(criteria, limit, offset, market, includeExternal, limitTotal)

            # return the (partial) user profile that retrieved the result, as well as the result itself.
            return {
                "user_profile": self._GetUserProfilePartialDictionary(self.data.spotifyClient.UserProfile),
                "result": searchResponse.Artists.ToDictionary()
            }

        # the following exceptions have already been logged, so we just need to
        # pass them back to HA for display in the log (or service UI).
        except SpotifyApiError as ex:
            raise HomeAssistantError(ex.Message)
        except SpotifyWebApiError as ex:
            raise HomeAssistantError(ex.Message)
        
        finally:
        
            # trace.
            _logsi.LeaveMethod(SILevel.Debug, apiMethodName)


    def service_spotify_search_audiobooks(self, 
                                          criteria:str, 
                                          limit:int, 
                                          offset:int, 
                                          market:str,
                                          includeExternal:str,
                                          limitTotal:int,
                                          ) -> dict:
        """
        Get Spotify catalog information about audiobooks that match a keyword string.

        Args:
            criteria (str):
                Your search query.  
                You can narrow down your search using field filters.  
                The available filters are album, artist, track, year, upc, tag:hipster, tag:new, 
                isrc, and genre. Each field filter only applies to certain result types.  
                The artist and year filters can be used while searching albums, artists and tracks.
                You can filter on a single year or a range (e.g. 1955-1960).  
                The album filter can be used while searching albums and tracks.  
                The genre filter can be used while searching artists and tracks.  
                The isrc and track filters can be used while searching tracks.  
                The upc, tag:new and tag:hipster filters can only be used while searching albums. 
                The tag:new filter will return albums released in the past two weeks and tag:hipster 
                can be used to return only albums with the lowest 10% popularity.
            limit (int):
                The maximum number of items to return in a page of items.  
                Default: 20, Range: 1 to 50.  
            offset (int):
                The page index offset of the first item to return.  
                Use with limit to get the next set of items.  
                Default: 0 (the first item).  Range: 0 to 1000.  
            market (str):
                An ISO 3166-1 alpha-2 country code. If a country code is specified, only content that 
                is available in that market will be returned.  If a valid user access token is specified 
                in the request header, the country associated with the user account will take priority over 
                this parameter.  
                Note: If neither market or user country are provided, the content is considered unavailable for the client.  
                Users can view the country that is associated with their account in the account settings.  
                Example: `ES`
            includeExternal (str):
                If "audio" is specified it signals that the client can play externally hosted audio content, and 
                marks the content as playable in the response. By default externally hosted audio content is marked 
                as unplayable in the response.  
                Allowed values: "audio"
            limitTotal (int):
                The maximum number of items to return for the request.  
                If specified, this argument overrides the limit and offset argument values
                and paging is automatically used to retrieve all available items up to the
                maximum number specified.  
                Default: None (disabled)

        Returns:
            A dictionary that contains the following keys:
            - user_profile: A (partial) user profile that retrieved the result.
            - result: An `AudiobookPageSimplified` object of matching results.            
        """
        apiMethodName:str = 'service_spotify_search_audiobooks'
        apiMethodParms:SIMethodParmListContext = None
        result:SearchResponse = None

        try:

            # trace.
            apiMethodParms = _logsi.EnterMethodParmList(SILevel.Debug, apiMethodName)
            apiMethodParms.AppendKeyValue("criteria", criteria)
            apiMethodParms.AppendKeyValue("limit", limit)
            apiMethodParms.AppendKeyValue("offset", offset)
            apiMethodParms.AppendKeyValue("market", market)
            apiMethodParms.AppendKeyValue("includeExternal", includeExternal)
            apiMethodParms.AppendKeyValue("limitTotal", limitTotal)
            _logsi.LogMethodParmList(SILevel.Verbose, "Spotify Search Audiobooks Service", apiMethodParms)
                
            # get Spotify catalog information about Audiobooks that match a keyword string.
            _logsi.LogVerbose("Searching Spotify Audiobooks for criteria")
            searchResponse:SearchResponse = self.data.spotifyClient.SearchAudiobooks(criteria, limit, offset, market, includeExternal, limitTotal)

            # return the (partial) user profile that retrieved the result, as well as the result itself.
            return {
                "user_profile": self._GetUserProfilePartialDictionary(self.data.spotifyClient.UserProfile),
                "result": searchResponse.Audiobooks.ToDictionary()
            }

        # the following exceptions have already been logged, so we just need to
        # pass them back to HA for display in the log (or service UI).
        except SpotifyApiError as ex:
            raise HomeAssistantError(ex.Message)
        except SpotifyWebApiError as ex:
            raise HomeAssistantError(ex.Message)
        
        finally:
        
            # trace.
            _logsi.LeaveMethod(SILevel.Debug, apiMethodName)


    def service_spotify_search_episodes(self, 
                                        criteria:str, 
                                        limit:int, 
                                        offset:int, 
                                        market:str,
                                        includeExternal:str,
                                        limitTotal:int,
                                        ) -> dict:
        """
        Get Spotify catalog information about episodes that match a keyword string.

        Args:
            criteria (str):
                Your search query.  
                You can narrow down your search using field filters.  
                The available filters are album, artist, track, year, upc, tag:hipster, tag:new, 
                isrc, and genre. Each field filter only applies to certain result types.  
                The artist and year filters can be used while searching albums, artists and tracks.
                You can filter on a single year or a range (e.g. 1955-1960).  
                The album filter can be used while searching albums and tracks.  
                The genre filter can be used while searching artists and tracks.  
                The isrc and track filters can be used while searching tracks.  
                The upc, tag:new and tag:hipster filters can only be used while searching albums. 
                The tag:new filter will return albums released in the past two weeks and tag:hipster 
                can be used to return only albums with the lowest 10% popularity.
            limit (int):
                The maximum number of items to return in a page of items.  
                Default: 20, Range: 1 to 50.  
            offset (int):
                The page index offset of the first item to return.  
                Use with limit to get the next set of items.  
                Default: 0 (the first item).  Range: 0 to 1000.  
            market (str):
                An ISO 3166-1 alpha-2 country code. If a country code is specified, only content that 
                is available in that market will be returned.  If a valid user access token is specified 
                in the request header, the country associated with the user account will take priority over 
                this parameter.  
                Note: If neither market or user country are provided, the content is considered unavailable for the client.  
                Users can view the country that is associated with their account in the account settings.  
                Example: `ES`
            includeExternal (str):
                If "audio" is specified it signals that the client can play externally hosted audio content, and 
                marks the content as playable in the response. By default externally hosted audio content is marked 
                as unplayable in the response.  
                Allowed values: "audio"
            limitTotal (int):
                The maximum number of items to return for the request.  
                If specified, this argument overrides the limit and offset argument values
                and paging is automatically used to retrieve all available items up to the
                maximum number specified.  
                Default: None (disabled)

        Returns:
            A dictionary that contains the following keys:
            - user_profile: A (partial) user profile that retrieved the result.
            - result: An `EpisodePageSimplified` object of matching results.            
        """
        apiMethodName:str = 'service_spotify_search_episodes'
        apiMethodParms:SIMethodParmListContext = None
        result:SearchResponse = None

        try:

            # trace.
            apiMethodParms = _logsi.EnterMethodParmList(SILevel.Debug, apiMethodName)
            apiMethodParms.AppendKeyValue("criteria", criteria)
            apiMethodParms.AppendKeyValue("limit", limit)
            apiMethodParms.AppendKeyValue("offset", offset)
            apiMethodParms.AppendKeyValue("market", market)
            apiMethodParms.AppendKeyValue("includeExternal", includeExternal)
            apiMethodParms.AppendKeyValue("limitTotal", limitTotal)
            _logsi.LogMethodParmList(SILevel.Verbose, "Spotify Search Episodes Service", apiMethodParms)
                
            # get Spotify catalog information about Episodes that match a keyword string.
            _logsi.LogVerbose("Searching Spotify Episodes for criteria")
            searchResponse:SearchResponse = self.data.spotifyClient.SearchEpisodes(criteria, limit, offset, market, includeExternal, limitTotal)

            # return the (partial) user profile that retrieved the result, as well as the result itself.
            return {
                "user_profile": self._GetUserProfilePartialDictionary(self.data.spotifyClient.UserProfile),
                "result": searchResponse.Episodes.ToDictionary()
            }

        # the following exceptions have already been logged, so we just need to
        # pass them back to HA for display in the log (or service UI).
        except SpotifyApiError as ex:
            raise HomeAssistantError(ex.Message)
        except SpotifyWebApiError as ex:
            raise HomeAssistantError(ex.Message)
        
        finally:
        
            # trace.
            _logsi.LeaveMethod(SILevel.Debug, apiMethodName)


    def service_spotify_search_playlists(self, 
                                         criteria:str, 
                                         limit:int, 
                                         offset:int, 
                                         market:str,
                                         includeExternal:str,
                                         limitTotal:int,
                                         ) -> dict:
        """
        Get Spotify catalog information about playlists that match a keyword string.

        Args:
            criteria (str):
                Your search query.  
                You can narrow down your search using field filters.  
                The available filters are album, artist, track, year, upc, tag:hipster, tag:new, 
                isrc, and genre. Each field filter only applies to certain result types.  
                The artist and year filters can be used while searching albums, artists and tracks.
                You can filter on a single year or a range (e.g. 1955-1960).  
                The album filter can be used while searching albums and tracks.  
                The genre filter can be used while searching artists and tracks.  
                The isrc and track filters can be used while searching tracks.  
                The upc, tag:new and tag:hipster filters can only be used while searching albums. 
                The tag:new filter will return albums released in the past two weeks and tag:hipster 
                can be used to return only albums with the lowest 10% popularity.
            limit (int):
                The maximum number of items to return in a page of items.  
                Default: 20, Range: 1 to 50.  
            offset (int):
                The page index offset of the first item to return.  
                Use with limit to get the next set of items.  
                Default: 0 (the first item).  Range: 0 to 1000.  
            market (str):
                An ISO 3166-1 alpha-2 country code. If a country code is specified, only content that 
                is available in that market will be returned.  If a valid user access token is specified 
                in the request header, the country associated with the user account will take priority over 
                this parameter.  
                Note: If neither market or user country are provided, the content is considered unavailable for the client.  
                Users can view the country that is associated with their account in the account settings.  
                Example: `ES`
            includeExternal (str):
                If "audio" is specified it signals that the client can play externally hosted audio content, and 
                marks the content as playable in the response. By default externally hosted audio content is marked 
                as unplayable in the response.  
                Allowed values: "audio"
            limitTotal (int):
                The maximum number of items to return for the request.  
                If specified, this argument overrides the limit and offset argument values
                and paging is automatically used to retrieve all available items up to the
                maximum number specified.  
                Default: None (disabled)

        Returns:
            A dictionary that contains the following keys:
            - user_profile: A (partial) user profile that retrieved the result.
            - result: A `PlaylistPageSimplified` object of matching results.            
        """
        apiMethodName:str = 'service_spotify_search_playlists'
        apiMethodParms:SIMethodParmListContext = None
        result:SearchResponse = None

        try:

            # trace.
            apiMethodParms = _logsi.EnterMethodParmList(SILevel.Debug, apiMethodName)
            apiMethodParms.AppendKeyValue("criteria", criteria)
            apiMethodParms.AppendKeyValue("limit", limit)
            apiMethodParms.AppendKeyValue("offset", offset)
            apiMethodParms.AppendKeyValue("market", market)
            apiMethodParms.AppendKeyValue("includeExternal", includeExternal)
            apiMethodParms.AppendKeyValue("limitTotal", limitTotal)
            _logsi.LogMethodParmList(SILevel.Verbose, "Spotify Search Playlists Service", apiMethodParms)
                
            # get Spotify catalog information about Playlists that match a keyword string.
            _logsi.LogVerbose("Searching Spotify Playlists for criteria")
            searchResponse:SearchResponse = self.data.spotifyClient.SearchPlaylists(criteria, limit, offset, market, includeExternal, limitTotal)

            # return the (partial) user profile that retrieved the result, as well as the result itself.
            return {
                "user_profile": self._GetUserProfilePartialDictionary(self.data.spotifyClient.UserProfile),
                "result": searchResponse.Playlists.ToDictionary()
            }

        # the following exceptions have already been logged, so we just need to
        # pass them back to HA for display in the log (or service UI).
        except SpotifyApiError as ex:
            raise HomeAssistantError(ex.Message)
        except SpotifyWebApiError as ex:
            raise HomeAssistantError(ex.Message)
        
        finally:
        
            # trace.
            _logsi.LeaveMethod(SILevel.Debug, apiMethodName)


    def service_spotify_search_shows(self, 
                                     criteria:str, 
                                     limit:int, 
                                     offset:int, 
                                     market:str,
                                     includeExternal:str,
                                     limitTotal:int,
                                     ) -> dict:
        """
        Get Spotify catalog information about shows (aka. podcasts) that match a keyword string.

        Args:
            criteria (str):
                Your search query.  
                You can narrow down your search using field filters.  
                The available filters are album, artist, track, year, upc, tag:hipster, tag:new, 
                isrc, and genre. Each field filter only applies to certain result types.  
                The artist and year filters can be used while searching albums, artists and tracks.
                You can filter on a single year or a range (e.g. 1955-1960).  
                The album filter can be used while searching albums and tracks.  
                The genre filter can be used while searching artists and tracks.  
                The isrc and track filters can be used while searching tracks.  
                The upc, tag:new and tag:hipster filters can only be used while searching albums. 
                The tag:new filter will return albums released in the past two weeks and tag:hipster 
                can be used to return only albums with the lowest 10% popularity.
            limit (int):
                The maximum number of items to return in a page of items.  
                Default: 20, Range: 1 to 50.  
            offset (int):
                The page index offset of the first item to return.  
                Use with limit to get the next set of items.  
                Default: 0 (the first item).  Range: 0 to 1000.  
            market (str):
                An ISO 3166-1 alpha-2 country code. If a country code is specified, only content that 
                is available in that market will be returned.  If a valid user access token is specified 
                in the request header, the country associated with the user account will take priority over 
                this parameter.  
                Note: If neither market or user country are provided, the content is considered unavailable for the client.  
                Users can view the country that is associated with their account in the account settings.  
                Example: `ES`
            includeExternal (str):
                If "audio" is specified it signals that the client can play externally hosted audio content, and 
                marks the content as playable in the response. By default externally hosted audio content is marked 
                as unplayable in the response.  
                Allowed values: "audio"
            limitTotal (int):
                The maximum number of items to return for the request.  
                If specified, this argument overrides the limit and offset argument values
                and paging is automatically used to retrieve all available items up to the
                maximum number specified.  
                Default: None (disabled)

        Returns:
            A dictionary that contains the following keys:
            - user_profile: A (partial) user profile that retrieved the result.
            - result: An `ShowPageSimplified` object of matching results.            
        """
        apiMethodName:str = 'service_spotify_search_shows'
        apiMethodParms:SIMethodParmListContext = None
        result:SearchResponse = None

        try:

            # trace.
            apiMethodParms = _logsi.EnterMethodParmList(SILevel.Debug, apiMethodName)
            apiMethodParms.AppendKeyValue("criteria", criteria)
            apiMethodParms.AppendKeyValue("limit", limit)
            apiMethodParms.AppendKeyValue("offset", offset)
            apiMethodParms.AppendKeyValue("market", market)
            apiMethodParms.AppendKeyValue("includeExternal", includeExternal)
            apiMethodParms.AppendKeyValue("limitTotal", limitTotal)
            _logsi.LogMethodParmList(SILevel.Verbose, "Spotify Search Shows Service", apiMethodParms)
                
            # get Spotify catalog information about Episodes that match a keyword string.
            _logsi.LogVerbose("Searching Spotify Shows for criteria")
            searchResponse:SearchResponse = self.data.spotifyClient.SearchShows(criteria, limit, offset, market, includeExternal, limitTotal)

            # return the (partial) user profile that retrieved the result, as well as the result itself.
            return {
                "user_profile": self._GetUserProfilePartialDictionary(self.data.spotifyClient.UserProfile),
                "result": searchResponse.Shows.ToDictionary()
            }

        # the following exceptions have already been logged, so we just need to
        # pass them back to HA for display in the log (or service UI).
        except SpotifyApiError as ex:
            raise HomeAssistantError(ex.Message)
        except SpotifyWebApiError as ex:
            raise HomeAssistantError(ex.Message)
        
        finally:
        
            # trace.
            _logsi.LeaveMethod(SILevel.Debug, apiMethodName)


    def service_spotify_search_tracks(self, 
                                      criteria:str, 
                                      limit:int, 
                                      offset:int, 
                                      market:str,
                                      includeExternal:str,
                                      limitTotal:int,
                                      ) -> dict:
        """
        Get Spotify catalog information about tracks that match a keyword string.

        Args:
            criteria (str):
                Your search query.  
                You can narrow down your search using field filters.  
                The available filters are album, artist, track, year, upc, tag:hipster, tag:new, 
                isrc, and genre. Each field filter only applies to certain result types.  
                The artist and year filters can be used while searching albums, artists and tracks.
                You can filter on a single year or a range (e.g. 1955-1960).  
                The album filter can be used while searching albums and tracks.  
                The genre filter can be used while searching artists and tracks.  
                The isrc and track filters can be used while searching tracks.  
                The upc, tag:new and tag:hipster filters can only be used while searching albums. 
                The tag:new filter will return albums released in the past two weeks and tag:hipster 
                can be used to return only albums with the lowest 10% popularity.
            limit (int):
                The maximum number of items to return in a page of items.  
                Default: 20, Range: 1 to 50.  
            offset (int):
                The page index offset of the first item to return.  
                Use with limit to get the next set of items.  
                Default: 0 (the first item).  Range: 0 to 1000.  
            market (str):
                An ISO 3166-1 alpha-2 country code. If a country code is specified, only content that 
                is available in that market will be returned.  If a valid user access token is specified 
                in the request header, the country associated with the user account will take priority over 
                this parameter.  
                Note: If neither market or user country are provided, the content is considered unavailable for the client.  
                Users can view the country that is associated with their account in the account settings.  
                Example: `ES`
            includeExternal (str):
                If "audio" is specified it signals that the client can play externally hosted audio content, and 
                marks the content as playable in the response. By default externally hosted audio content is marked 
                as unplayable in the response.  
                Allowed values: "audio"
            limitTotal (int):
                The maximum number of items to return for the request.  
                If specified, this argument overrides the limit and offset argument values
                and paging is automatically used to retrieve all available items up to the
                maximum number specified.  
                Default: None (disabled)

        Returns:
            A dictionary that contains the following keys:
            - user_profile: A (partial) user profile that retrieved the result.
            - result: A `TrackPage` object of matching results.            
        """
        apiMethodName:str = 'service_spotify_search_tracks'
        apiMethodParms:SIMethodParmListContext = None
        result:SearchResponse = None

        try:

            # trace.
            apiMethodParms = _logsi.EnterMethodParmList(SILevel.Debug, apiMethodName)
            apiMethodParms.AppendKeyValue("criteria", criteria)
            apiMethodParms.AppendKeyValue("limit", limit)
            apiMethodParms.AppendKeyValue("offset", offset)
            apiMethodParms.AppendKeyValue("market", market)
            apiMethodParms.AppendKeyValue("includeExternal", includeExternal)
            apiMethodParms.AppendKeyValue("limitTotal", limitTotal)
            _logsi.LogMethodParmList(SILevel.Verbose, "Spotify Search Tracks Service", apiMethodParms)
                
            # get Spotify catalog information about Playlists that match a keyword string.
            _logsi.LogVerbose("Searching Spotify Tracks for criteria")
            searchResponse:SearchResponse = self.data.spotifyClient.SearchTracks(criteria, limit, offset, market, includeExternal, limitTotal)

            # return the (partial) user profile that retrieved the result, as well as the result itself.
            return {
                "user_profile": self._GetUserProfilePartialDictionary(self.data.spotifyClient.UserProfile),
                "result": searchResponse.Tracks.ToDictionary()
            }

        # the following exceptions have already been logged, so we just need to
        # pass them back to HA for display in the log (or service UI).
        except SpotifyApiError as ex:
            raise HomeAssistantError(ex.Message)
        except SpotifyWebApiError as ex:
            raise HomeAssistantError(ex.Message)
        
        finally:
        
            # trace.
            _logsi.LeaveMethod(SILevel.Debug, apiMethodName)


    def service_spotify_unfollow_artists(self, 
                                         ids:str=None, 
                                         ) -> None:
        """
        Remove the current user as a follower of one or more artists.
        
        Args:
            ids (str):  
                A comma-separated list of the Spotify IDs for the artists.  
                Maximum: 50 IDs.  
                Example: `2CIMQHirSU0MQqyYHq0eOx,1IQ2e1buppatiN1bxUVkrk`
                If null, the currently playing track artist uri id value is used.
        """
        apiMethodName:str = 'service_spotify_unfollow_artists'
        apiMethodParms:SIMethodParmListContext = None

        try:

            # trace.
            apiMethodParms = _logsi.EnterMethodParmList(SILevel.Debug, apiMethodName)
            apiMethodParms.AppendKeyValue("ids", ids)
            _logsi.LogMethodParmList(SILevel.Verbose, "Spotify Unfollow Artists Service", apiMethodParms)
                           
            # unfollow artist(s).
            _logsi.LogVerbose("Removing items(s) from Spotify Artist Favorites")
            self.data.spotifyClient.UnfollowArtists(ids)

        # the following exceptions have already been logged, so we just need to
        # pass them back to HA for display in the log (or service UI).
        except SpotifyApiError as ex:
            raise HomeAssistantError(ex.Message)
        except SpotifyWebApiError as ex:
            raise HomeAssistantError(ex.Message)
        
        finally:
        
            # trace.
            _logsi.LeaveMethod(SILevel.Debug, apiMethodName)


    def service_spotify_unfollow_playlist(self, 
                                          playlistId:str=None, 
                                          ) -> None:
        """
        Remove the current user as a follower of a playlist.

        Args:
            playlistId (str):  
                The Spotify ID of the playlist.  
                Example: `3cEYpjA9oz9GiPac4AsH4n`
        """
        apiMethodName:str = 'service_spotify_unfollow_playlist'
        apiMethodParms:SIMethodParmListContext = None

        try:

            # trace.
            apiMethodParms = _logsi.EnterMethodParmList(SILevel.Debug, apiMethodName)
            apiMethodParms.AppendKeyValue("playlistId", playlistId)
            _logsi.LogMethodParmList(SILevel.Verbose, "Spotify Unfollow Playlist Service", apiMethodParms)
                           
            # unfollow playlist.
            _logsi.LogVerbose("Removing items from Spotify Playlist Favorites")
            self.data.spotifyClient.UnfollowPlaylist(playlistId)

        # the following exceptions have already been logged, so we just need to
        # pass them back to HA for display in the log (or service UI).
        except SpotifyApiError as ex:
            raise HomeAssistantError(ex.Message)
        except SpotifyWebApiError as ex:
            raise HomeAssistantError(ex.Message)
        
        finally:
        
            # trace.
            _logsi.LeaveMethod(SILevel.Debug, apiMethodName)


    def service_spotify_unfollow_users(self, 
                                       ids:str=None, 
                                       ) -> None:
        """
        Remove the current user as a follower of one or more users.

        Args:
            ids (str):  
                A comma-separated list of Spotify user IDs.  
                A maximum of 50 IDs can be sent in one request.
                Example: `smedjan`
        """
        apiMethodName:str = 'service_spotify_unfollow_users'
        apiMethodParms:SIMethodParmListContext = None

        try:

            # trace.
            apiMethodParms = _logsi.EnterMethodParmList(SILevel.Debug, apiMethodName)
            apiMethodParms.AppendKeyValue("ids", ids)
            _logsi.LogMethodParmList(SILevel.Verbose, "Spotify Unfollow Users Service", apiMethodParms)
                           
            # unfollow user(s).
            _logsi.LogVerbose("Removing items(s) from Spotify Users Favorites")
            self.data.spotifyClient.UnfollowUsers(ids)

        # the following exceptions have already been logged, so we just need to
        # pass them back to HA for display in the log (or service UI).
        except SpotifyApiError as ex:
            raise HomeAssistantError(ex.Message)
        except SpotifyWebApiError as ex:
            raise HomeAssistantError(ex.Message)
        
        finally:
        
            # trace.
            _logsi.LeaveMethod(SILevel.Debug, apiMethodName)


    def service_spotify_zeroconf_device_connect(
            self, 
            username:str,
            password:str,
            hostIpv4Address:str,
            hostIpPort:str,
            cpath:str,
            version:str='1.0',
            useSSL:bool=False,
            preDisconnect:bool=False,
            verifyDeviceListEntry:bool=False,
        ) -> dict:
        """
        Calls the `addUser` Spotify Zeroconf API endpoint to issue a call to SpConnectionLoginBlob.  If successful,
        the associated device id is added to the Spotify Connect active device list for the specified user account.
        
        Args:
            username (str):
                Spotify Connect user name to login with.  
                This MUST match the account name (or one of them) that was used to configure Spotify Connect 
                on the manufacturer device.
            password (str):
                Spotify Connect user password to login with.  
            hostIpv4Address (str):
                IPV4 address (as a string) at which the Spotify Connect Zeroconf API can be reached
                on the Spotify Connect device (e.g. "192.168.1.81").
            hostIpPort (int):
                Port number (as an integer) at which the Spotify Connect Zeroconf API can be reached
                on the Spotify Connect device (e.g. "8200").
            cpath (str):
                Spotify Connect Zeroconf API CPath property value (e.g. "/zc").
            version (str):
                Spotify Connect Zeroconf API version number that the device supports (e.g. "2.10.0").  
                Default is '1.0'.
            useSSL (bool):
                True if the host device utilizes HTTPS Secure Sockets Layer (SSL) support; 
                otherwise, False to utilize HTTP.  
                Default is False (HTTP).
            preDisconnect (bool):
                True if a Disconnect should be made prior to the Connect call.  This will ensure that the
                active user is logged out, which must be done if switching user accounts;
                otherwise, False to not issue a Disconnect call.
                Default is False.
            verifyDeviceListEntry (bool):
                True to ensure that the device id is present in the Spotify Connect device list before
                issuing a call to Connect; otherwise, False to always call Connect to add the device.
                Default is False.

        The login (on the device) is performed asynchronously, so the return result only indicates whether the library 
        is able to perform the login attempt.  You should issue a call to the Spotify Web API `Get Available Devices` 
        endpoint to check the current device list to ensure that the device id was successfully added or not.

        Use the `verifyDeviceListEntry` argument to check if the device is currently listed in the Spotify Connect
        device list.  If True, a `GetInformation` call is issued to get the device id, and a `GetPlayerDevice` call
        is made to check if the device id is in the Spotify Connect device list.  If the device id is found in the 
        Spotify Connect device list then the Connect command is not issued; if the device id is NOT found in the Spotify 
        Connect device list then the Connect command is issued
        
        Returns:
            A dictionary that contains the following keys:
            - user_profile: A (partial) user profile that retrieved the result.
            - result: A `ZeroconfResponse` object that contains the response.
        """
        apiMethodName:str = 'service_spotify_zeroconf_device_connect'
        apiMethodParms:SIMethodParmListContext = None
        result:ZeroconfResponse = None

        try:

            # trace.
            apiMethodParms = _logsi.EnterMethodParmList(SILevel.Debug, apiMethodName)
            apiMethodParms.AppendKeyValue("hostIpv4Address", hostIpv4Address)
            apiMethodParms.AppendKeyValue("hostIpPort", hostIpPort)
            apiMethodParms.AppendKeyValue("cpath", cpath)
            apiMethodParms.AppendKeyValue("version", version)
            apiMethodParms.AppendKeyValue("useSSL", useSSL)
            apiMethodParms.AppendKeyValue("username", username)
            apiMethodParms.AppendKeyValue("password (with mask)", passwordMaskString(password))
            apiMethodParms.AppendKeyValue("preDisconnect", preDisconnect)
            apiMethodParms.AppendKeyValue("verifyDeviceListEntry", verifyDeviceListEntry)
            _logsi.LogMethodParmList(SILevel.Verbose, "Spotify Connect ZeroConf Device Connect Service", apiMethodParms)
                
            # create Spotify Zeroconf API connection object for the device.
            zconn:ZeroconfConnect = ZeroconfConnect(hostIpv4Address, hostIpPort, cpath, version, useSSL)
            
            # are we verifying if the device id is already in the Spotify Connect device list?
            if (verifyDeviceListEntry):

                # trace.
                _logsi.LogVerbose("'%s': Checking current Spotify Connect device list for Device ID (%s) ..." % (self.name, zconn.Uri))
                           
                # get the device id of the device.
                info:ZeroconfGetInfo = zconn.GetInformation()
                
                # is the device in the current Spotify Connect device list?  if so, then we are done.
                playerDevice:PlayerDevice = self.data.spotifyClient.GetPlayerDevice(info.DeviceId, True)
                if playerDevice is not None:
                    _logsi.LogVerbose("'%s': Device ID '%s' (%s) is already in the Spotify Connect device list; nothing to do" % (self.name, playerDevice.Id, playerDevice.Name))

                    # return the (partial) user profile that retrieved the result, as well as the result itself.
                    return {
                        "user_profile": self._GetUserProfilePartialDictionary(self.data.spotifyClient.UserProfile),
                        "result": info.ToDictionary()
                    }

                # trace.
                _logsi.LogVerbose("'%s': Device ID '%s' (%s) was not found in the Spotify Connect device list; device will be activated" % (self.name, info.DeviceId, info.RemoteName))
            
            # disconnect the device from Spotify Connect.
            if (preDisconnect == True):
                result = zconn.Disconnect()

            # connect the device to Spotify Connect, which should make it known to any available
            # Spotify Connect player clients.
            result = zconn.Connect(username, password)

            # return the (partial) user profile that retrieved the result, as well as the result itself.
            return {
                "user_profile": self._GetUserProfilePartialDictionary(self.data.spotifyClient.UserProfile),
                "result": result.ToDictionary()
            }

        # the following exceptions have already been logged, so we just need to
        # pass them back to HA for display in the log (or service UI).
        except SpotifyApiError as ex:
            raise HomeAssistantError(ex.Message)
        except SpotifyZeroconfApiError as ex:
            raise HomeAssistantError(ex.Message)
        except Exception as ex:
            _logsi.LogException("'%s': MediaPlayer %s exception: %s" % (self.name, apiMethodName, str(ex)), ex, logToSystemLogger=False)
            raise HomeAssistantError(str(ex)) from ex
        
        finally:
        
            # trace.
            _logsi.LeaveMethod(SILevel.Debug, apiMethodName)


    def service_spotify_zeroconf_device_disconnect(
            self, 
            hostIpv4Address:str,
            hostIpPort:str,
            cpath:str,
            version:str='1.0',
            useSSL:bool=False
        ) -> dict:
        """
        Calls the `resetUsers` Spotify Zeroconf API endpoint to issue a call to SpConnectionLogout.
        The currently logged in user (if any) will be logged out of Spotify Connect, and the 
        device id removed from the active Spotify Connect device list.        
        
        Args:
            hostIpv4Address (str):
                IPV4 address (as a string) at which the Spotify Connect Zeroconf API can be reached
                on the Spotify Connect device (e.g. "192.168.1.81").
            hostIpPort (int):
                Port number (as an integer) at which the Spotify Connect Zeroconf API can be reached
                on the Spotify Connect device (e.g. "8200").
            cpath (str):
                Spotify Connect Zeroconf API CPath property value (e.g. "/zc").
            version (str):
                Spotify Connect Zeroconf API version number that the device supports (e.g. "2.10.0").  
                Default is '1.0'.
            useSSL (bool):
                True if the host device utilizes HTTPS Secure Sockets Layer (SSL) support; 
                otherwise, False to utilize HTTP.  
                Default is False (HTTP).

        The URI value consists of an IP Address, port, CPath, and version value that are used to send
        requests to / receive responses from a headless Spotify Connect device.  These values can be
        obtained from a Zeroconf discovery process.

        Returns:
            A dictionary that contains the following keys:
            - user_profile: A (partial) user profile that retrieved the result.
            - result: A `ZeroconfResponse` object that contains the response.
        """
        apiMethodName:str = 'service_spotify_zeroconf_device_disconnect'
        apiMethodParms:SIMethodParmListContext = None
        result:ZeroconfResponse = None

        try:

            # trace.
            apiMethodParms = _logsi.EnterMethodParmList(SILevel.Debug, apiMethodName)
            apiMethodParms.AppendKeyValue("hostIpv4Address", hostIpv4Address)
            apiMethodParms.AppendKeyValue("hostIpPort", hostIpPort)
            apiMethodParms.AppendKeyValue("cpath", cpath)
            apiMethodParms.AppendKeyValue("version", version)
            apiMethodParms.AppendKeyValue("useSSL", useSSL)
            _logsi.LogMethodParmList(SILevel.Verbose, "Spotify Connect ZeroConf Device Disconnect Service", apiMethodParms)
                
            # create Spotify Zeroconf API connection object for the device.
            zconn:ZeroconfConnect = ZeroconfConnect(hostIpv4Address, hostIpPort, cpath, version, useSSL)
            
            # disconnect the device from Spotify Connect.
            result = zconn.Disconnect()

            # return the (partial) user profile that retrieved the result, as well as the result itself.
            return {
                "user_profile": self._GetUserProfilePartialDictionary(self.data.spotifyClient.UserProfile),
                "result": result.ToDictionary()
            }

        # the following exceptions have already been logged, so we just need to
        # pass them back to HA for display in the log (or service UI).
        except SpotifyApiError as ex:
            raise HomeAssistantError(ex.Message)
        except SpotifyZeroconfApiError as ex:
            raise HomeAssistantError(ex.Message)
        except Exception as ex:
            _logsi.LogException("'%s': MediaPlayer %s exception: %s" % (self.name, apiMethodName, str(ex)), ex, logToSystemLogger=False)
            raise HomeAssistantError(str(ex)) from ex
        
        finally:
        
            # trace.
            _logsi.LeaveMethod(SILevel.Debug, apiMethodName)


    def service_spotify_zeroconf_device_getinfo(
            self, 
            hostIpv4Address:str,
            hostIpPort:str,
            cpath:str,
            version:str='1.0',
            useSSL:bool=False
            ) -> dict:
        """
        Calls the `getInfo` Spotify Zeroconf API endpoint to return information about the device.

        Args:
            hostIpv4Address (str):
                IPV4 address (as a string) at which the Spotify Connect Zeroconf API can be reached
                on the Spotify Connect device (e.g. "192.168.1.81").
            hostIpPort (int):
                Port number (as an integer) at which the Spotify Connect Zeroconf API can be reached
                on the Spotify Connect device (e.g. "8200").
            cpath (str):
                Spotify Connect Zeroconf API CPath property value (e.g. "/zc").
            version (str):
                Spotify Connect Zeroconf API version number that the device supports (e.g. "2.10.0").  
                Default is '1.0'.
            useSSL (bool):
                True if the host device utilizes HTTPS Secure Sockets Layer (SSL) support; 
                otherwise, False to utilize HTTP.  
                Default is False (HTTP).

        Returns:
            A dictionary that contains the following keys:
            - user_profile: A (partial) user profile that retrieved the result.
            - result: A `ZeroconfGetInfo` object that contains the response.
        """
        apiMethodName:str = 'service_spotify_zeroconf_getinfo'
        apiMethodParms:SIMethodParmListContext = None
        result:ZeroconfGetInfo = None

        try:

            # trace.
            apiMethodParms = _logsi.EnterMethodParmList(SILevel.Debug, apiMethodName)
            apiMethodParms.AppendKeyValue("hostIpv4Address", hostIpv4Address)
            apiMethodParms.AppendKeyValue("hostIpPort", hostIpPort)
            apiMethodParms.AppendKeyValue("cpath", cpath)
            apiMethodParms.AppendKeyValue("version", version)
            apiMethodParms.AppendKeyValue("useSSL", useSSL)
            _logsi.LogMethodParmList(SILevel.Verbose, "Spotify Connect ZeroConf Device Get Information Service", apiMethodParms)
                
            # create Spotify Zeroconf API connection object for the device.
            zconn:ZeroconfConnect = ZeroconfConnect(hostIpv4Address, hostIpPort, cpath, version, useSSL)

            # get Spotify Connect device information.
            result = zconn.GetInformation()
                
            # return the (partial) user profile that retrieved the result, as well as the result itself.
            return {
                "user_profile": self._GetUserProfilePartialDictionary(self.data.spotifyClient.UserProfile),
                "result": result.ToDictionary()
            }

        # the following exceptions have already been logged, so we just need to
        # pass them back to HA for display in the log (or service UI).
        except SpotifyApiError as ex:
            raise HomeAssistantError(ex.Message)
        except SpotifyZeroconfApiError as ex:
            raise HomeAssistantError(ex.Message)
        except Exception as ex:
            _logsi.LogException("'%s': MediaPlayer %s exception: %s" % (self.name, apiMethodName, str(ex)), ex, logToSystemLogger=False)
            raise HomeAssistantError(str(ex)) from ex
        
        finally:
        
            # trace.
            _logsi.LeaveMethod(SILevel.Debug, apiMethodName)


    def service_spotify_zeroconf_discover_devices(self, 
                                                  timeout:int=5, 
                                                  ) -> dict:
        """
        Discover Spotify Connect devices on the local network via the 
        ZeroConf (aka MDNS) service, and return details about each device. 

        Args:
            timeout (int):
                Maximum amount of time to wait (in seconds) for the 
                discovery to complete.  
                Default is 5 seconds.

        Returns:
            A dictionary that contains the following keys:
            - user_profile: A (partial) user profile that retrieved the result.
            - result: An array of `ZeroconfDiscoveryResult` objects of matching results.
        """
        apiMethodName:str = 'service_spotify_zeroconf_discover_devices'
        apiMethodParms:SIMethodParmListContext = None

        try:

            # trace.
            apiMethodParms = _logsi.EnterMethodParmList(SILevel.Debug, apiMethodName)
            apiMethodParms.AppendKeyValue("timeout", timeout)
            _logsi.LogMethodParmList(SILevel.Verbose, "Spotify ZeroConf Discover Devices Service", apiMethodParms)
                
            # create a new instance of the discovery class.
            # do not verify device connections;
            # do not print device details to the console as they are discovered.
            discovery:SpotifyDiscovery = SpotifyDiscovery(self.data.spotifyClient.ZeroconfClient, printToConsole=False)

            # discover Spotify Connect devices on the network, waiting up to the specified
            # time in seconds for all devices to be discovered.
            discovery.DiscoverDevices(timeout)

            # return the (partial) user profile that retrieved the result, as well as the result itself.
            return {
                "user_profile": self._GetUserProfilePartialDictionary(self.data.spotifyClient.UserProfile),
                "result": [ item.ToDictionary() for item in discovery.DiscoveryResults ]
            }

        # the following exceptions have already been logged, so we just need to
        # pass them back to HA for display in the log (or service UI).
        except SpotifyApiError as ex:
            raise HomeAssistantError(ex.Message)
        except SpotifyWebApiError as ex:
            raise HomeAssistantError(ex.Message)
        except Exception as ex:
            _logsi.LogException("'%s': MediaPlayer %s exception: %s" % (self.name, apiMethodName, str(ex)), ex, logToSystemLogger=False)
            raise HomeAssistantError(str(ex)) from ex
        
        finally:
        
            # trace.
            _logsi.LeaveMethod(SILevel.Debug, apiMethodName)


    async def async_added_to_hass(self) -> None:
        """
        Run when this Entity has been added to HA.

        Importantly for a push integration, the module that will be getting updates
        needs to notify HA of changes.  In our case, we created a DataUpdateCoordinator
        instance that will inform us when the Spotify Connect device list has changed.  We
        will register some callback methods here so that we can forward the change
        notifications on to Home Assistant (e.g. a call to `self.async_write_ha_state`).

        The call back registration is done once this entity is registered with Home
        Assistant (rather than in the `__init__` method).
        """
        try:

            # trace.
            _logsi.EnterMethod(SILevel.Debug)

            # call base class method.
            await super().async_added_to_hass()

            # load list of supported sources (also caches them in the client for later).
            _logsi.LogVerbose("'%s': MediaPlayer is loading list of ALL sources that the device supports" % self.name)
            result:SpotifyConnectDevices = await self.hass.async_add_executor_job(self.data.spotifyClient.GetSpotifyConnectDevices, True)

            # add listener that will inform HA of our state if a user removes the device instance.
            _logsi.LogVerbose("'%s': adding '_handle_devices_update' listener" % self.name)
            self.async_on_remove(
                self.data.devices.async_add_listener(self._handle_devices_update)
            )

        finally:
                
            # trace.
            _logsi.LeaveMethod(SILevel.Debug)


    async def async_will_remove_from_hass(self) -> None:
        """
        Entity being removed from hass (the opposite of async_added_to_hass).

        Remove any registered call backs here.
        """
        try:

            # trace.
            _logsi.EnterMethod(SILevel.Debug)
            _logsi.LogVerbose("'%s': removing instance from hass" % self.name)
       
            # nothing to do here.

        finally:

            # trace.
            _logsi.LeaveMethod(SILevel.Debug)


    async def async_browse_media(
        self,
        media_content_type: MediaType | str | None = None,
        media_content_id: str | None = None,
    ) -> BrowseMedia:
        """
        Implement the websocket media browsing helper.
        """
        methodParms:SIMethodParmListContext = None
        
        try:

            # trace.
            methodParms = _logsi.EnterMethodParmList(SILevel.Debug)
            methodParms.AppendKeyValue("media_content_type", media_content_type)
            methodParms.AppendKeyValue("media_content_id", media_content_id)
            _logsi.LogMethodParmList(SILevel.Verbose, "'%s': MediaPlayer is browsing for media content type '%s'" % (self.name, media_content_type), methodParms)
            
            # browse spotifysplus device media.
            if media_content_type is None and media_content_id is None:

                # handle initial media browser selection (e.g. show the starting index).
                _logsi.LogVerbose("'%s': MediaPlayer is browsing main media library index content id '%s'" % (self.name, media_content_id))
                return await async_browse_media_library_index(
                    self.hass,
                    self.data.spotifyClient,
                    self.name,
                    self.source,
                    SPOTIFY_LIBRARY_MAP,
                    BrowsableMedia.SPOTIFY_LIBRARY_INDEX,
                    media_content_type,
                    media_content_id,
                )

            elif media_content_type == 'favorites':
                # ignore Sonos-Card "favorites" node queries.
                _logsi.LogVerbose("'%s': ignoring Sonos-Card favorites query (no SoundTouch equivalent)" % self.name)
                
                # Sonos-Card requires a valid BrowseMedia object, so return an empty one.
                browseMedia:BrowseMedia = BrowseMedia(
                    can_expand=False,
                    can_play=False,
                    children=[],
                    children_media_class=None,
                    media_class=None,
                    media_content_id=media_content_id,
                    media_content_type=media_content_type,
                    title="Favorites not supported",
                    )
                return browseMedia
                        
            else:
                
                # handle spotifysplus media library selection.
                # note that this is NOT async, as SpotifyClient is not async!
                _logsi.LogVerbose("'%s': MediaPlayer is browsing media node content id '%s'" % (self.name, media_content_id))
                return await self.hass.async_add_executor_job(
                    browse_media_node,
                    self.hass,
                    self.data.spotifyClient,
                    self.name,
                    self.source,
                    SPOTIFY_LIBRARY_MAP,
                    media_content_type,
                    media_content_id,
                )

        except Exception as ex:
            
            # trace.
            _logsi.LogException("'%s': MediaPlayer async_browse_media exception: %s" % (self.name, str(ex)), ex, logToSystemLogger=False)
            raise HomeAssistantError(str(ex)) from ex
        
        finally:

            # trace.
            _logsi.LeaveMethod(SILevel.Debug)
