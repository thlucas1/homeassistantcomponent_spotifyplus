"""
The spotifyplus integration.
"""

from __future__ import annotations

from asyncio import run_coroutine_threadsafe
from datetime import timedelta
from typing import Any
from urllib3._version import __version__ as urllib3_version

import logging
import voluptuous as vol

from spotifywebapipython import SpotifyClient, SpotifyApiError, SpotifyWebApiError, SpotifyWebApiAuthenticationError
from spotifywebapipython.models import Device

from homeassistant.components.media_player import MediaPlayerEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform, CONF_ID
from homeassistant.core import HomeAssistant, ServiceCall, ServiceResponse, SupportsResponse
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady, HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.config_entry_oauth2_flow import (OAuth2Session, async_get_config_entry_implementation)
from homeassistant.helpers.issue_registry import IssueSeverity, async_create_issue
from homeassistant.helpers.typing import ConfigType
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .appmessages import STAppMessages
from .const import (
    DOMAIN, 
    SPOTIFY_SCOPES
)
from .instancedata_spotifyplus import InstanceDataSpotifyPlus

__all__ = [
    "DOMAIN",
]

_LOGGER = logging.getLogger(__name__)

try:

    from smartinspectpython.siauto import SIAuto, SILevel, SISession, SIConfigurationTimer

    # load SmartInspect settings from a configuration settings file.
    siConfigPath: str = "./smartinspect.cfg"
    SIAuto.Si.LoadConfiguration(siConfigPath)

    # start monitoring the configuration file for changes, and reload it when it changes.
    # this will check the file for changes every 60 seconds.
    siConfig:SIConfigurationTimer = SIConfigurationTimer(SIAuto.Si, siConfigPath)

    # get smartinspect logger reference; create a new session for this module name.
    _logsi:SISession = SIAuto.Si.GetSession(__name__)
    if (_logsi == None):
        _logsi = SIAuto.Si.AddSession(__name__, True)
    _logsi.SystemLogger = _LOGGER
    _logsi.LogSeparator(SILevel.Error)
    _logsi.LogVerbose("__init__.py HAS SpotifyPlus: initialization")
    _logsi.LogAppDomain(SILevel.Verbose)
    _logsi.LogSystem(SILevel.Verbose)

except Exception as ex:

    _LOGGER.warning("HAS SpotifyPlus could not init SmartInspect debugging! %s", str(ex))

PLATFORMS = [Platform.MEDIA_PLAYER]
""" 
List of platforms to support. 
There should be a matching .py file for each (e.g. "media_player")
"""

CONFIG_SCHEMA = cv.removed(DOMAIN, raise_if_present=False)
""" Configuration schema. """


# -----------------------------------------------------------------------------------
# Custom Service Schemas.
# -----------------------------------------------------------------------------------
SERVICE_SPOTIFY_GET_ALBUM:str = 'get_album'
SERVICE_SPOTIFY_GET_ALBUM_FAVORITES:str = 'get_album_favorites'
SERVICE_SPOTIFY_GET_ALBUM_NEW_RELEASES:str = 'get_album_new_releases'
SERVICE_SPOTIFY_GET_ARTIST:str = 'get_artist'
SERVICE_SPOTIFY_GET_ARTIST_ALBUMS:str = 'get_artist_albums'
SERVICE_SPOTIFY_GET_ARTISTS_FOLLOWED:str = 'get_artists_followed'
SERVICE_SPOTIFY_GET_BROWSE_CATEGORYS_LIST:str = 'get_browse_categorys_list'
SERVICE_SPOTIFY_GET_CATEGORY_PLAYLISTS:str = 'get_category_playlists'
SERVICE_SPOTIFY_GET_FEATURED_PLAYLISTS:str = 'get_featured_playlists'
SERVICE_SPOTIFY_GET_PLAYER_DEVICES:str = 'get_player_devices'
SERVICE_SPOTIFY_GET_PLAYER_QUEUE_INFO:str = 'get_player_queue_info'
SERVICE_SPOTIFY_GET_PLAYER_RECENT_TRACKS:str = 'get_player_recent_tracks'
SERVICE_SPOTIFY_GET_PLAYLIST:str = 'get_playlist'
SERVICE_SPOTIFY_GET_PLAYLIST_FAVORITES:str = 'get_playlist_favorites'
SERVICE_SPOTIFY_GET_SHOW:str = 'get_show'
SERVICE_SPOTIFY_GET_SHOW_EPISODES:str = 'get_show_episodes'
SERVICE_SPOTIFY_GET_SHOW_FAVORITES:str = 'get_show_favorites'
SERVICE_SPOTIFY_GET_TRACK_FAVORITES:str = 'get_track_favorites'
SERVICE_SPOTIFY_GET_USERS_TOP_ARTISTS:str = 'get_users_top_artists'
SERVICE_SPOTIFY_GET_USERS_TOP_TRACKS:str = 'get_users_top_tracks'
SERVICE_SPOTIFY_SEARCH_ALBUMS:str = 'search_albums'
SERVICE_SPOTIFY_SEARCH_ARTISTS:str = 'search_artists'
SERVICE_SPOTIFY_SEARCH_AUDIOBOOKS:str = 'search_audiobooks'
SERVICE_SPOTIFY_SEARCH_EPISODES:str = 'search_episodes'
SERVICE_SPOTIFY_SEARCH_PLAYLISTS:str = 'search_playlists'
SERVICE_SPOTIFY_SEARCH_SHOWS:str = 'search_shows'
SERVICE_SPOTIFY_SEARCH_TRACKS:str = 'search_tracks'


SERVICE_SPOTIFY_GET_ALBUM_SCHEMA = vol.Schema(
    {
        vol.Required("entity_id"): cv.entity_id,
        vol.Required("album_id"): cv.string,
        vol.Optional("market"): cv.string,
    }
)

SERVICE_SPOTIFY_GET_ALBUM_FAVORITES_SCHEMA = vol.Schema(
    {
        vol.Required("entity_id"): cv.entity_id,
        vol.Optional("limit", default=50): vol.All(vol.Range(min=1,max=50)),
        vol.Optional("offset", default=0): vol.All(vol.Range(min=0,max=500)),
        vol.Optional("market"): cv.string,
        vol.Optional("limit_total", default=0): vol.All(vol.Range(min=0,max=9999)),
    }
)

SERVICE_SPOTIFY_GET_ALBUM_NEW_RELEASES_SCHEMA = vol.Schema(
    {
        vol.Required("entity_id"): cv.entity_id,
        vol.Optional("limit", default=50): vol.All(vol.Range(min=1,max=50)),
        vol.Optional("offset", default=0): vol.All(vol.Range(min=0,max=500)),
        vol.Optional("country"): cv.string,
        vol.Optional("limit_total", default=0): vol.All(vol.Range(min=0,max=9999)),
    }
)

SERVICE_SPOTIFY_GET_ARTIST_SCHEMA = vol.Schema(
    {
        vol.Required("entity_id"): cv.entity_id,
        vol.Required("artist_id"): cv.string,
    }
)

SERVICE_SPOTIFY_GET_ARTIST_ALBUMS_SCHEMA = vol.Schema(
    {
        vol.Required("entity_id"): cv.entity_id,
        vol.Required("artist_id"): cv.string,
        vol.Optional("include_groups"): cv.string,
        vol.Optional("limit", default=50): vol.All(vol.Range(min=1,max=50)),
        vol.Optional("offset", default=0): vol.All(vol.Range(min=0,max=500)),
        vol.Optional("market"): cv.string,
        vol.Optional("limit_total", default=0): vol.All(vol.Range(min=0,max=9999)),
    }
)

SERVICE_SPOTIFY_GET_ARTISTS_FOLLOWED_SCHEMA = vol.Schema(
    {
        vol.Required("entity_id"): cv.entity_id,
        vol.Optional("after"): cv.string,
        vol.Optional("limit", default=50): vol.All(vol.Range(min=1,max=50)),
        vol.Optional("limit_total", default=0): vol.All(vol.Range(min=0,max=9999)),
    }
)

SERVICE_SPOTIFY_GET_BROWSE_CATEGORYS_LIST_SCHEMA = vol.Schema(
    {
        vol.Required("entity_id"): cv.entity_id,
        vol.Optional("country"): cv.string,
        vol.Optional("locale"): cv.string,
        vol.Optional("refresh"): cv.boolean,
    }
)

SERVICE_SPOTIFY_GET_CATEGORY_PLAYLISTS_SCHEMA = vol.Schema(
    {
        vol.Required("entity_id"): cv.entity_id,
        vol.Required("category_id"): cv.string,
        vol.Optional("limit", default=50): vol.All(vol.Range(min=1,max=50)),
        vol.Optional("offset", default=0): vol.All(vol.Range(min=0,max=500)),
        vol.Optional("country"): cv.string,
        vol.Optional("limit_total", default=0): vol.All(vol.Range(min=0,max=9999)),
    }
)

SERVICE_SPOTIFY_GET_FEATURED_PLAYLISTS_SCHEMA = vol.Schema(
    {
        vol.Required("entity_id"): cv.entity_id,
        vol.Optional("limit", default=50): vol.All(vol.Range(min=1,max=50)),
        vol.Optional("offset", default=0): vol.All(vol.Range(min=0,max=500)),
        vol.Optional("country"): cv.string,
        vol.Optional("locale"): cv.string,
        vol.Optional("timestamp"): cv.string,
        vol.Optional("limit_total", default=0): vol.All(vol.Range(min=0,max=9999)),
    }
)

SERVICE_SPOTIFY_GET_PLAYER_DEVICES_SCHEMA = vol.Schema(
    {
        vol.Required("entity_id"): cv.entity_id,
        vol.Optional("refresh"): cv.boolean,
    }
)

SERVICE_SPOTIFY_GET_PLAYER_QUEUE_INFO_SCHEMA = vol.Schema(
    {
        vol.Required("entity_id"): cv.entity_id,
    }
)

SERVICE_SPOTIFY_GET_PLAYER_RECENT_TRACKS_SCHEMA = vol.Schema(
    {
        vol.Required("entity_id"): cv.entity_id,
        vol.Optional("limit", default=50): vol.All(vol.Range(min=1,max=50)),
        vol.Optional("after", default=0): vol.All(vol.Range(min=0,max=99999999999999)),
        vol.Optional("before", default=0): vol.All(vol.Range(min=0,max=99999999999999)),
        vol.Optional("limit_total", default=0): vol.All(vol.Range(min=0,max=9999)),
    }
)

SERVICE_SPOTIFY_GET_PLAYLIST_SCHEMA = vol.Schema(
    {
        vol.Required("entity_id"): cv.entity_id,
        vol.Required("playlist_id"): cv.string,
        vol.Optional("market"): cv.string,
        vol.Optional("fields"): cv.string,
        vol.Optional("additional_types"): cv.string,
    }
)

SERVICE_SPOTIFY_GET_PLAYLIST_FAVORITES_SCHEMA = vol.Schema(
    {
        vol.Required("entity_id"): cv.entity_id,
        vol.Optional("limit", default=50): vol.All(vol.Range(min=1,max=50)),
        vol.Optional("offset", default=0): vol.All(vol.Range(min=0,max=500)),
        vol.Optional("limit_total", default=0): vol.All(vol.Range(min=0,max=9999)),
    }
)

SERVICE_SPOTIFY_GET_SHOW_SCHEMA = vol.Schema(
    {
        vol.Required("entity_id"): cv.entity_id,
        vol.Required("show_id"): cv.string,
        vol.Optional("market"): cv.string,
    }
)

SERVICE_SPOTIFY_GET_SHOW_EPISODES_SCHEMA = vol.Schema(
    {
        vol.Required("entity_id"): cv.entity_id,
        vol.Required("show_id"): cv.string,
        vol.Optional("limit", default=50): vol.All(vol.Range(min=1,max=50)),
        vol.Optional("offset", default=0): vol.All(vol.Range(min=0,max=500)),
        vol.Optional("market"): cv.string,
        vol.Optional("limit_total", default=0): vol.All(vol.Range(min=0,max=9999)),
    }
)

SERVICE_SPOTIFY_GET_SHOW_FAVORITES_SCHEMA = vol.Schema(
    {
        vol.Required("entity_id"): cv.entity_id,
        vol.Optional("limit", default=50): vol.All(vol.Range(min=1,max=50)),
        vol.Optional("offset", default=0): vol.All(vol.Range(min=0,max=500)),
        vol.Optional("limit_total", default=0): vol.All(vol.Range(min=0,max=9999)),
    }
)

SERVICE_SPOTIFY_GET_TRACK_FAVORITES_SCHEMA = vol.Schema(
    {
        vol.Required("entity_id"): cv.entity_id,
        vol.Optional("limit", default=50): vol.All(vol.Range(min=1,max=50)),
        vol.Optional("offset", default=0): vol.All(vol.Range(min=0,max=500)),
        vol.Optional("market"): cv.string,
        vol.Optional("limit_total", default=0): vol.All(vol.Range(min=0,max=9999)),
    }
)

SERVICE_SPOTIFY_GET_USERS_TOP_ARTISTS_SCHEMA = vol.Schema(
    {
        vol.Required("entity_id"): cv.entity_id,
        vol.Optional("time_range"): cv.string,
        vol.Optional("limit", default=50): vol.All(vol.Range(min=1,max=50)),
        vol.Optional("offset", default=0): vol.All(vol.Range(min=0,max=500)),
        vol.Optional("limit_total", default=0): vol.All(vol.Range(min=0,max=9999)),
    }
)

SERVICE_SPOTIFY_GET_USERS_TOP_TRACKS_SCHEMA = vol.Schema(
    {
        vol.Required("entity_id"): cv.entity_id,
        vol.Optional("time_range"): cv.string,
        vol.Optional("limit", default=50): vol.All(vol.Range(min=1,max=50)),
        vol.Optional("offset", default=0): vol.All(vol.Range(min=0,max=500)),
        vol.Optional("limit_total", default=0): vol.All(vol.Range(min=0,max=9999)),
    }
)

SERVICE_SPOTIFY_SEARCH_ALBUMS_SCHEMA = vol.Schema(
    {
        vol.Required("entity_id"): cv.entity_id,
        vol.Required("criteria"): cv.string,
        vol.Optional("limit", default=50): vol.All(vol.Range(min=1,max=50)),
        vol.Optional("offset", default=0): vol.All(vol.Range(min=0,max=500)),
        vol.Optional("market"): cv.string,
        vol.Optional("include_external"): cv.string,
        vol.Optional("limit_total", default=0): vol.All(vol.Range(min=0,max=9999)),
    }
)

SERVICE_SPOTIFY_SEARCH_ARTISTS_SCHEMA = vol.Schema(
    {
        vol.Required("entity_id"): cv.entity_id,
        vol.Required("criteria"): cv.string,
        vol.Optional("limit", default=50): vol.All(vol.Range(min=1,max=50)),
        vol.Optional("offset", default=0): vol.All(vol.Range(min=0,max=500)),
        vol.Optional("market"): cv.string,
        vol.Optional("include_external"): cv.string,
        vol.Optional("limit_total", default=0): vol.All(vol.Range(min=0,max=9999)),
    }
)

SERVICE_SPOTIFY_SEARCH_AUDIOBOOKS_SCHEMA = vol.Schema(
    {
        vol.Required("entity_id"): cv.entity_id,
        vol.Required("criteria"): cv.string,
        vol.Optional("limit", default=50): vol.All(vol.Range(min=1,max=50)),
        vol.Optional("offset", default=0): vol.All(vol.Range(min=0,max=500)),
        vol.Optional("market"): cv.string,
        vol.Optional("include_external"): cv.string,
        vol.Optional("limit_total", default=0): vol.All(vol.Range(min=0,max=9999)),
    }
)

SERVICE_SPOTIFY_SEARCH_EPISODES_SCHEMA = vol.Schema(
    {
        vol.Required("entity_id"): cv.entity_id,
        vol.Required("criteria"): cv.string,
        vol.Optional("limit", default=50): vol.All(vol.Range(min=1,max=50)),
        vol.Optional("offset", default=0): vol.All(vol.Range(min=0,max=500)),
        vol.Optional("market"): cv.string,
        vol.Optional("include_external"): cv.string,
        vol.Optional("limit_total", default=0): vol.All(vol.Range(min=0,max=9999)),
    }
)

SERVICE_SPOTIFY_SEARCH_PLAYLISTS_SCHEMA = vol.Schema(
    {
        vol.Required("entity_id"): cv.entity_id,
        vol.Required("criteria"): cv.string,
        vol.Optional("limit", default=50): vol.All(vol.Range(min=1,max=50)),
        vol.Optional("offset", default=0): vol.All(vol.Range(min=0,max=500)),
        vol.Optional("market"): cv.string,
        vol.Optional("include_external"): cv.string,
        vol.Optional("limit_total", default=0): vol.All(vol.Range(min=0,max=9999)),
    }
)

SERVICE_SPOTIFY_SEARCH_SHOWS_SCHEMA = vol.Schema(
    {
        vol.Required("entity_id"): cv.entity_id,
        vol.Required("criteria"): cv.string,
        vol.Optional("limit", default=50): vol.All(vol.Range(min=1,max=50)),
        vol.Optional("offset", default=0): vol.All(vol.Range(min=0,max=500)),
        vol.Optional("market"): cv.string,
        vol.Optional("include_external"): cv.string,
        vol.Optional("limit_total", default=0): vol.All(vol.Range(min=0,max=9999)),
    }
)

SERVICE_SPOTIFY_SEARCH_TRACKS_SCHEMA = vol.Schema(
    {
        vol.Required("entity_id"): cv.entity_id,
        vol.Required("criteria"): cv.string,
        vol.Optional("limit", default=50): vol.All(vol.Range(min=1,max=50)),
        vol.Optional("offset", default=0): vol.All(vol.Range(min=0,max=500)),
        vol.Optional("market"): cv.string,
        vol.Optional("include_external"): cv.string,
        vol.Optional("limit_total", default=0): vol.All(vol.Range(min=0,max=9999)),
    }
)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """
    Set up the component.

    Args:
        hass (HomeAssistant):
            HomeAssistant instance.
        config (ConfigType):
            HomeAssistant validation configuration object.

    The __init__.py module "async_setup" method is executed once for the component 
    configuration, no matter how many devices are configured for the component.  
    It takes care of loading the services that the component provides, as well as the 
    ConfigType dictionary.  The ConfigType dictionary contains Home Assistant configuration 
    entries that reference this component type: 'default_config', 'frontend' (themes, etc), 
    'automation', 'script', and 'scenes' sub-dictionaries.
    """
    try:

        # trace.
        _logsi.EnterMethod(SILevel.Debug)
        if _logsi.IsOn(SILevel.Verbose):

            _logsi.LogVerbose("Component async_setup starting")

            # log the manifest file contents.
            myConfigDir:str = "%s/custom_components/%s" % (hass.config.config_dir, DOMAIN)
            myManifestPath:str = "%s/manifest.json" % (myConfigDir)
            _logsi.LogTextFile(SILevel.Verbose, "Integration Manifest File (%s)" % myManifestPath, myManifestPath)

            # log verion information for supporting packages.
            _logsi.LogValue(SILevel.Verbose, "urllib3 version", urllib3_version)

            for item in config:
                itemKey:str = str(item)
                itemObj = config[itemKey]
                if isinstance(itemObj,dict):
                    _logsi.LogDictionary(SILevel.Verbose, "ConfigType '%s' data (dictionary)" % itemKey, itemObj, prettyPrint=True)
                elif isinstance(itemObj,list):
                    _logsi.LogArray(SILevel.Verbose, "ConfigType '%s' data (list)" % itemKey, itemObj)
                else:
                    _logsi.LogObject(SILevel.Verbose, "ConfigType '%s' data (object)" % (itemKey), itemObj)

        if DOMAIN in config:
            # remind user to remove SpotifyPlus settings from configuration.yaml if present.
            async_create_issue(
                hass,
                DOMAIN,
                "removed_yaml",
                breaks_in_ha_version="2022.8.0",
                is_fixable=False,
                severity=IssueSeverity.WARNING,
                translation_key="removed_yaml",
            )


        async def service_handle_spotify_serviceresponse(service: ServiceCall) -> ServiceResponse:
            """
            Handle service requests that return service response data from Spotify endpoints.

            Args:
                service (ServiceCall):
                    ServiceCall instance that contains service data (requested service name, field parameters, etc).
            """
            try:

                _logsi.EnterMethod(SILevel.Debug)
                _logsi.LogVerbose(STAppMessages.MSG_SERVICE_CALL_START, service.service, 'service_handle_spotify_serviceresponse')
                _logsi.LogObject(SILevel.Verbose, STAppMessages.MSG_SERVICE_CALL_PARM, service)
                _logsi.LogDictionary(SILevel.Verbose, STAppMessages.MSG_SERVICE_CALL_DATA, service.data)

                # get player instance from service parameter; if not found, then we are done.
                entity = _GetEntityFromServiceData(hass, service, "entity_id")
                if entity is None:
                    return

                response:dict = {}

                # process service request.
                if service.service == SERVICE_SPOTIFY_GET_ALBUM:

                    # get spotify album.
                    album_id = service.data.get("album_id")
                    market = service.data.get("market")
                    _logsi.LogVerbose(STAppMessages.MSG_SERVICE_EXECUTE % (service.service, entity.name))
                    response = await hass.async_add_executor_job(entity.service_spotify_get_album, album_id, market)

                elif service.service == SERVICE_SPOTIFY_GET_ALBUM_FAVORITES:

                    # get spotify album favorites.
                    limit = service.data.get("limit")
                    offset = service.data.get("offset")
                    market = service.data.get("market")
                    limit_total = service.data.get("limit_total")
                    _logsi.LogVerbose(STAppMessages.MSG_SERVICE_EXECUTE % (service.service, entity.name))
                    response = await hass.async_add_executor_job(entity.service_spotify_get_album_favorites, limit, offset, market, limit_total)

                elif service.service == SERVICE_SPOTIFY_GET_ALBUM_NEW_RELEASES:

                    # get spotify album favorites.
                    limit = service.data.get("limit")
                    offset = service.data.get("offset")
                    country = service.data.get("country")
                    limit_total = service.data.get("limit_total")
                    _logsi.LogVerbose(STAppMessages.MSG_SERVICE_EXECUTE % (service.service, entity.name))
                    response = await hass.async_add_executor_job(entity.service_spotify_get_album_new_releases, limit, offset, country, limit_total)

                elif service.service == SERVICE_SPOTIFY_GET_ARTIST:

                    # get spotify artist.
                    artist_id = service.data.get("artist_id")
                    _logsi.LogVerbose(STAppMessages.MSG_SERVICE_EXECUTE % (service.service, entity.name))
                    response = await hass.async_add_executor_job(entity.service_spotify_get_artist, artist_id)

                elif service.service == SERVICE_SPOTIFY_GET_ARTIST_ALBUMS:

                    # get spotify artist albums.
                    artist_id = service.data.get("artist_id")
                    include_groups = service.data.get("include_groups")
                    limit = service.data.get("limit")
                    offset = service.data.get("offset")
                    market = service.data.get("market")
                    limit_total = service.data.get("limit_total")                   
                    _logsi.LogVerbose(STAppMessages.MSG_SERVICE_EXECUTE % (service.service, entity.name))
                    response = await hass.async_add_executor_job(entity.service_spotify_get_artist_albums, artist_id, include_groups, limit, offset, market, limit_total)

                elif service.service == SERVICE_SPOTIFY_GET_ARTISTS_FOLLOWED:

                    # get spotify artists followed.
                    after = service.data.get("after")
                    limit = service.data.get("limit")
                    limit_total = service.data.get("limit_total")
                    _logsi.LogVerbose(STAppMessages.MSG_SERVICE_EXECUTE % (service.service, entity.name))
                    response = await hass.async_add_executor_job(entity.service_spotify_get_artists_followed, after, limit, limit_total)

                elif service.service == SERVICE_SPOTIFY_GET_BROWSE_CATEGORYS_LIST:

                    # get spotify browse categorys.
                    country = service.data.get("country")
                    locale = service.data.get("locale")
                    refresh = service.data.get("refresh")
                    _logsi.LogVerbose(STAppMessages.MSG_SERVICE_EXECUTE % (service.service, entity.name))
                    response = await hass.async_add_executor_job(entity.service_spotify_get_browse_categorys_list, country, locale, refresh)

                elif service.service == SERVICE_SPOTIFY_GET_CATEGORY_PLAYLISTS:

                    # get spotify featured playlists.
                    category_id = service.data.get("category_id")
                    limit = service.data.get("limit")
                    offset = service.data.get("offset")
                    country = service.data.get("country")
                    limit_total = service.data.get("limit_total")
                    _logsi.LogVerbose(STAppMessages.MSG_SERVICE_EXECUTE % (service.service, entity.name))
                    response = await hass.async_add_executor_job(entity.service_spotify_get_category_playlists, category_id, limit, offset, country, limit_total)

                elif service.service == SERVICE_SPOTIFY_GET_FEATURED_PLAYLISTS:

                    # get spotify featured playlists.
                    limit = service.data.get("limit")
                    offset = service.data.get("offset")
                    country = service.data.get("country")
                    locale = service.data.get("locale")
                    timestamp = service.data.get("timestamp")
                    limit_total = service.data.get("limit_total")
                    _logsi.LogVerbose(STAppMessages.MSG_SERVICE_EXECUTE % (service.service, entity.name))
                    response = await hass.async_add_executor_job(entity.service_spotify_get_featured_playlists, limit, offset, country, locale, timestamp, limit_total)

                elif service.service == SERVICE_SPOTIFY_GET_PLAYER_DEVICES:

                    # get spotify connect device list.
                    refresh = service.data.get("refresh")
                    _logsi.LogVerbose(STAppMessages.MSG_SERVICE_EXECUTE % (service.service, entity.name))
                    response = await hass.async_add_executor_job(entity.service_spotify_get_player_devices, refresh)

                elif service.service == SERVICE_SPOTIFY_GET_PLAYER_QUEUE_INFO:

                    # get spotify queue info.
                    _logsi.LogVerbose(STAppMessages.MSG_SERVICE_EXECUTE % (service.service, entity.name))
                    response = await hass.async_add_executor_job(entity.service_spotify_get_player_queue_info)

                elif service.service == SERVICE_SPOTIFY_GET_PLAYER_RECENT_TRACKS:

                    # get spotify playlist favorites.
                    limit = service.data.get("limit")
                    after = service.data.get("after")
                    before = service.data.get("before")
                    limit_total = service.data.get("limit_total")
                    _logsi.LogVerbose(STAppMessages.MSG_SERVICE_EXECUTE % (service.service, entity.name))
                    response = await hass.async_add_executor_job(entity.service_spotify_get_player_recent_tracks, limit, after, before, limit_total)

                elif service.service == SERVICE_SPOTIFY_GET_PLAYLIST:

                    # get spotify playlist.
                    playlist_id = service.data.get("playlist_id")
                    market = service.data.get("market")
                    fields = service.data.get("fields")
                    additional_types = service.data.get("additional_types")
                    _logsi.LogVerbose(STAppMessages.MSG_SERVICE_EXECUTE % (service.service, entity.name))
                    response = await hass.async_add_executor_job(entity.service_spotify_get_playlist, playlist_id, market, fields, additional_types)

                elif service.service == SERVICE_SPOTIFY_GET_PLAYLIST_FAVORITES:

                    # get spotify playlist favorites.
                    limit = service.data.get("limit")
                    offset = service.data.get("offset")
                    limit_total = service.data.get("limit_total")
                    _logsi.LogVerbose(STAppMessages.MSG_SERVICE_EXECUTE % (service.service, entity.name))
                    response = await hass.async_add_executor_job(entity.service_spotify_get_playlist_favorites, limit, offset, limit_total)

                elif service.service == SERVICE_SPOTIFY_GET_SHOW:

                    # get spotify show (podcast) episodes.
                    show_id = service.data.get("show_id")
                    market = service.data.get("market")
                    _logsi.LogVerbose(STAppMessages.MSG_SERVICE_EXECUTE % (service.service, entity.name))
                    response = await hass.async_add_executor_job(entity.service_spotify_get_show, show_id, market)

                elif service.service == SERVICE_SPOTIFY_GET_SHOW_EPISODES:

                    # get spotify show (podcast) episodes.
                    show_id = service.data.get("show_id")
                    limit = service.data.get("limit")
                    offset = service.data.get("offset")
                    market = service.data.get("market")
                    limit_total = service.data.get("limit_total")
                    _logsi.LogVerbose(STAppMessages.MSG_SERVICE_EXECUTE % (service.service, entity.name))
                    response = await hass.async_add_executor_job(entity.service_spotify_get_show_episodes, show_id, limit, offset, market, limit_total)

                elif service.service == SERVICE_SPOTIFY_GET_SHOW_FAVORITES:

                    # get spotify show (podcast) favorites.
                    limit = service.data.get("limit")
                    offset = service.data.get("offset")
                    limit_total = service.data.get("limit_total")
                    _logsi.LogVerbose(STAppMessages.MSG_SERVICE_EXECUTE % (service.service, entity.name))
                    response = await hass.async_add_executor_job(entity.service_spotify_get_show_favorites, limit, offset, limit_total)

                elif service.service == SERVICE_SPOTIFY_GET_TRACK_FAVORITES:

                    # get spotify album favorites.
                    limit = service.data.get("limit")
                    offset = service.data.get("offset")
                    market = service.data.get("market")
                    limit_total = service.data.get("limit_total")
                    _logsi.LogVerbose(STAppMessages.MSG_SERVICE_EXECUTE % (service.service, entity.name))
                    response = await hass.async_add_executor_job(entity.service_spotify_get_track_favorites, limit, offset, market, limit_total)

                elif service.service == SERVICE_SPOTIFY_GET_USERS_TOP_ARTISTS:

                    # get spotify users top artists.
                    time_range = service.data.get("time_range")
                    limit = service.data.get("limit")
                    offset = service.data.get("offset")
                    limit_total = service.data.get("limit_total")
                    _logsi.LogVerbose(STAppMessages.MSG_SERVICE_EXECUTE % (service.service, entity.name))
                    response = await hass.async_add_executor_job(entity.service_spotify_get_users_top_artists, time_range, limit, offset, limit_total)

                elif service.service == SERVICE_SPOTIFY_GET_USERS_TOP_TRACKS:

                    # get spotify users top artists.
                    time_range = service.data.get("time_range")
                    limit = service.data.get("limit")
                    offset = service.data.get("offset")
                    limit_total = service.data.get("limit_total")
                    _logsi.LogVerbose(STAppMessages.MSG_SERVICE_EXECUTE % (service.service, entity.name))
                    response = await hass.async_add_executor_job(entity.service_spotify_get_users_top_tracks, time_range, limit, offset, limit_total)

                elif service.service == SERVICE_SPOTIFY_SEARCH_ALBUMS:

                    # search Spotify for specified criteria.
                    criteria = service.data.get("criteria")
                    limit = service.data.get("limit")
                    offset = service.data.get("offset")
                    market = service.data.get("market")
                    include_external = service.data.get("include_external")
                    limit_total = service.data.get("limit_total")
                    _logsi.LogVerbose(STAppMessages.MSG_SERVICE_EXECUTE % (service.service, entity.name))
                    response = await hass.async_add_executor_job(entity.service_spotify_search_albums, criteria, limit, offset, market, include_external, limit_total)
                    
                elif service.service == SERVICE_SPOTIFY_SEARCH_ARTISTS:

                    # search Spotify for specified criteria.
                    criteria = service.data.get("criteria")
                    limit = service.data.get("limit")
                    offset = service.data.get("offset")
                    market = service.data.get("market")
                    include_external = service.data.get("include_external")
                    limit_total = service.data.get("limit_total")
                    _logsi.LogVerbose(STAppMessages.MSG_SERVICE_EXECUTE % (service.service, entity.name))
                    response = await hass.async_add_executor_job(entity.service_spotify_search_artists, criteria, limit, offset, market, include_external, limit_total)
                    
                elif service.service == SERVICE_SPOTIFY_SEARCH_AUDIOBOOKS:

                    # search Spotify for specified criteria.
                    criteria = service.data.get("criteria")
                    limit = service.data.get("limit")
                    offset = service.data.get("offset")
                    market = service.data.get("market")
                    include_external = service.data.get("include_external")
                    limit_total = service.data.get("limit_total")
                    _logsi.LogVerbose(STAppMessages.MSG_SERVICE_EXECUTE % (service.service, entity.name))
                    response = await hass.async_add_executor_job(entity.service_spotify_search_audiobooks, criteria, limit, offset, market, include_external, limit_total)
                    
                elif service.service == SERVICE_SPOTIFY_SEARCH_EPISODES:

                    # search Spotify for specified criteria.
                    criteria = service.data.get("criteria")
                    limit = service.data.get("limit")
                    offset = service.data.get("offset")
                    market = service.data.get("market")
                    include_external = service.data.get("include_external")
                    limit_total = service.data.get("limit_total")
                    _logsi.LogVerbose(STAppMessages.MSG_SERVICE_EXECUTE % (service.service, entity.name))
                    response = await hass.async_add_executor_job(entity.service_spotify_search_episodes, criteria, limit, offset, market, include_external, limit_total)
                    
                elif service.service == SERVICE_SPOTIFY_SEARCH_PLAYLISTS:

                    # search Spotify for specified criteria.
                    criteria = service.data.get("criteria")
                    limit = service.data.get("limit")
                    offset = service.data.get("offset")
                    market = service.data.get("market")
                    include_external = service.data.get("include_external")
                    limit_total = service.data.get("limit_total")
                    _logsi.LogVerbose(STAppMessages.MSG_SERVICE_EXECUTE % (service.service, entity.name))
                    response = await hass.async_add_executor_job(entity.service_spotify_search_playlists, criteria, limit, offset, market, include_external, limit_total)
                    
                elif service.service == SERVICE_SPOTIFY_SEARCH_SHOWS:

                    # search Spotify for specified criteria.
                    criteria = service.data.get("criteria")
                    limit = service.data.get("limit")
                    offset = service.data.get("offset")
                    market = service.data.get("market")
                    include_external = service.data.get("include_external")
                    limit_total = service.data.get("limit_total")
                    _logsi.LogVerbose(STAppMessages.MSG_SERVICE_EXECUTE % (service.service, entity.name))
                    response = await hass.async_add_executor_job(entity.service_spotify_search_shows, criteria, limit, offset, market, include_external, limit_total)
                    
                elif service.service == SERVICE_SPOTIFY_SEARCH_TRACKS:

                    # search Spotify for specified criteria.
                    criteria = service.data.get("criteria")
                    limit = service.data.get("limit")
                    offset = service.data.get("offset")
                    market = service.data.get("market")
                    include_external = service.data.get("include_external")
                    limit_total = service.data.get("limit_total")
                    _logsi.LogVerbose(STAppMessages.MSG_SERVICE_EXECUTE % (service.service, entity.name))
                    response = await hass.async_add_executor_job(entity.service_spotify_search_tracks, criteria, limit, offset, market, include_external, limit_total)
                    
                else:
                    
                    raise HomeAssistantError("Unrecognized service identifier '%s' in method service_handle_spotify_serviceresponse" % service.service)

                # return the response.
                _logsi.LogDictionary(SILevel.Verbose, "Service Response data: '%s'" % (service.service), response, prettyPrint=True)
                return response 

            except HomeAssistantError as ex: 
                
                # log error, but not to system logger as HA will take care of it.
                _logsi.LogError(str(ex), logToSystemLogger=False)
                raise
            
            except Exception as ex:

                # log exception, but not to system logger as HA will take care of it.
                _logsi.LogException(STAppMessages.MSG_SERVICE_REQUEST_EXCEPTION % (service.service, "service_handle_getlist"), ex, logToSystemLogger=False)
                raise

            finally:
            
                # trace.
                _logsi.LeaveMethod(SILevel.Debug)


        @staticmethod
        def _GetEntityFromServiceData(hass:HomeAssistant, service:ServiceCall, field_id:str) -> MediaPlayerEntity:
            """
            Resolves a `MediaPlayerEntity` instance from a ServiceCall field id.

            Args:
                hass (HomeAssistant):
                    HomeAssistant instance.
                service (ServiceCall):
                    ServiceCall instance that contains service data (requested service name, field parameters, etc).
                field_id (str):
                    Service parameter field id whose value contains a SpotifyMediaPlayer entity id.  
                    The ServiceCall data area will be queried with the field id to retrieve the entity id value.

            Returns:
                A `MediaPlayerEntity` instance if one could be resolved; otherwise, None.
            
            The service.data collection is queried for the field_id argument name.  If not supplied, 
            then an error message is logged and the return value is None.  

            The Haas data is then queried for the entity_id to retrieve the `MediaPlayerEntity` instance.
            """
            # get service parameter: entity_id.
            entity_id = service.data.get(field_id)
            if entity_id is None:
                _logsi.LogError(STAppMessages.MSG_SERVICE_ARGUMENT_NULL, field_id, service.service)
                return None

            # search all MediaPlayerEntity instances for the specified entity_id.
            # if found, then return the MediaPlayerEntity instance.
            player:MediaPlayerEntity = None
            data:InstanceDataSpotifyPlus = None
            for data in hass.data[DOMAIN].values():
                if data.media_player.entity_id == entity_id:
                    player = data.media_player
                    break

            # did we resolve it? if not, then log a message.
            if player is None:
                raise HomeAssistantError("Entity id value of '%s' could not be resolved to a MediaPlayerEntity instance for the '%s' method call" % (str(entity_id), service.service))

            # return the MediaPlayerEntity instance.
            _logsi.LogVerbose("Entity id value of '%s' was resolved to MediaPlayerEntity instance for the '%s' method call" % (str(entity_id), service.service))
            return player
        

        # register all services this component provides, and their corresponding schemas.
        _logsi.LogObject(SILevel.Verbose, STAppMessages.MSG_SERVICE_REQUEST_REGISTER % SERVICE_SPOTIFY_GET_ALBUM, SERVICE_SPOTIFY_GET_ALBUM_SCHEMA)
        hass.services.async_register(
            DOMAIN,
            SERVICE_SPOTIFY_GET_ALBUM,
            service_handle_spotify_serviceresponse,
            schema=SERVICE_SPOTIFY_GET_ALBUM_SCHEMA,
            supports_response=SupportsResponse.ONLY,
        )

        _logsi.LogObject(SILevel.Verbose, STAppMessages.MSG_SERVICE_REQUEST_REGISTER % SERVICE_SPOTIFY_GET_ALBUM_FAVORITES, SERVICE_SPOTIFY_GET_ALBUM_FAVORITES_SCHEMA)
        hass.services.async_register(
            DOMAIN,
            SERVICE_SPOTIFY_GET_ALBUM_FAVORITES,
            service_handle_spotify_serviceresponse,
            schema=SERVICE_SPOTIFY_GET_ALBUM_FAVORITES_SCHEMA,
            supports_response=SupportsResponse.ONLY,
        )

        _logsi.LogObject(SILevel.Verbose, STAppMessages.MSG_SERVICE_REQUEST_REGISTER % SERVICE_SPOTIFY_GET_ALBUM_NEW_RELEASES, SERVICE_SPOTIFY_GET_ALBUM_NEW_RELEASES_SCHEMA)
        hass.services.async_register(
            DOMAIN,
            SERVICE_SPOTIFY_GET_ALBUM_NEW_RELEASES,
            service_handle_spotify_serviceresponse,
            schema=SERVICE_SPOTIFY_GET_ALBUM_NEW_RELEASES_SCHEMA,
            supports_response=SupportsResponse.ONLY,
        )

        _logsi.LogObject(SILevel.Verbose, STAppMessages.MSG_SERVICE_REQUEST_REGISTER % SERVICE_SPOTIFY_GET_ARTIST, SERVICE_SPOTIFY_GET_ARTIST_SCHEMA)
        hass.services.async_register(
            DOMAIN,
            SERVICE_SPOTIFY_GET_ARTIST,
            service_handle_spotify_serviceresponse,
            schema=SERVICE_SPOTIFY_GET_ARTIST_SCHEMA,
            supports_response=SupportsResponse.ONLY,
        )

        _logsi.LogObject(SILevel.Verbose, STAppMessages.MSG_SERVICE_REQUEST_REGISTER % SERVICE_SPOTIFY_GET_ARTIST_ALBUMS, SERVICE_SPOTIFY_GET_ARTIST_ALBUMS_SCHEMA)
        hass.services.async_register(
            DOMAIN,
            SERVICE_SPOTIFY_GET_ARTIST_ALBUMS,
            service_handle_spotify_serviceresponse,
            schema=SERVICE_SPOTIFY_GET_ARTIST_ALBUMS_SCHEMA,
            supports_response=SupportsResponse.ONLY,
        )

        _logsi.LogObject(SILevel.Verbose, STAppMessages.MSG_SERVICE_REQUEST_REGISTER % SERVICE_SPOTIFY_GET_ARTISTS_FOLLOWED, SERVICE_SPOTIFY_GET_ARTISTS_FOLLOWED_SCHEMA)
        hass.services.async_register(
            DOMAIN,
            SERVICE_SPOTIFY_GET_ARTISTS_FOLLOWED,
            service_handle_spotify_serviceresponse,
            schema=SERVICE_SPOTIFY_GET_ARTISTS_FOLLOWED_SCHEMA,
            supports_response=SupportsResponse.ONLY,
        )

        _logsi.LogObject(SILevel.Verbose, STAppMessages.MSG_SERVICE_REQUEST_REGISTER % SERVICE_SPOTIFY_GET_BROWSE_CATEGORYS_LIST, SERVICE_SPOTIFY_GET_BROWSE_CATEGORYS_LIST_SCHEMA)
        hass.services.async_register(
            DOMAIN,
            SERVICE_SPOTIFY_GET_BROWSE_CATEGORYS_LIST,
            service_handle_spotify_serviceresponse,
            schema=SERVICE_SPOTIFY_GET_BROWSE_CATEGORYS_LIST_SCHEMA,
            supports_response=SupportsResponse.ONLY,
        )

        _logsi.LogObject(SILevel.Verbose, STAppMessages.MSG_SERVICE_REQUEST_REGISTER % SERVICE_SPOTIFY_GET_CATEGORY_PLAYLISTS, SERVICE_SPOTIFY_GET_CATEGORY_PLAYLISTS_SCHEMA)
        hass.services.async_register(
            DOMAIN,
            SERVICE_SPOTIFY_GET_CATEGORY_PLAYLISTS,
            service_handle_spotify_serviceresponse,
            schema=SERVICE_SPOTIFY_GET_CATEGORY_PLAYLISTS_SCHEMA,
            supports_response=SupportsResponse.ONLY,
        )

        _logsi.LogObject(SILevel.Verbose, STAppMessages.MSG_SERVICE_REQUEST_REGISTER % SERVICE_SPOTIFY_GET_FEATURED_PLAYLISTS, SERVICE_SPOTIFY_GET_FEATURED_PLAYLISTS_SCHEMA)
        hass.services.async_register(
            DOMAIN,
            SERVICE_SPOTIFY_GET_FEATURED_PLAYLISTS,
            service_handle_spotify_serviceresponse,
            schema=SERVICE_SPOTIFY_GET_FEATURED_PLAYLISTS_SCHEMA,
            supports_response=SupportsResponse.ONLY,
        )

        _logsi.LogObject(SILevel.Verbose, STAppMessages.MSG_SERVICE_REQUEST_REGISTER % SERVICE_SPOTIFY_GET_PLAYER_DEVICES, SERVICE_SPOTIFY_GET_PLAYER_DEVICES_SCHEMA)
        hass.services.async_register(
            DOMAIN,
            SERVICE_SPOTIFY_GET_PLAYER_DEVICES,
            service_handle_spotify_serviceresponse,
            schema=SERVICE_SPOTIFY_GET_PLAYER_DEVICES_SCHEMA,
            supports_response=SupportsResponse.ONLY,
        )

        _logsi.LogObject(SILevel.Verbose, STAppMessages.MSG_SERVICE_REQUEST_REGISTER % SERVICE_SPOTIFY_GET_PLAYER_QUEUE_INFO, SERVICE_SPOTIFY_GET_PLAYER_QUEUE_INFO_SCHEMA)
        hass.services.async_register(
            DOMAIN,
            SERVICE_SPOTIFY_GET_PLAYER_QUEUE_INFO,
            service_handle_spotify_serviceresponse,
            schema=SERVICE_SPOTIFY_GET_PLAYER_QUEUE_INFO_SCHEMA,
            supports_response=SupportsResponse.ONLY,
        )

        _logsi.LogObject(SILevel.Verbose, STAppMessages.MSG_SERVICE_REQUEST_REGISTER % SERVICE_SPOTIFY_GET_PLAYER_RECENT_TRACKS, SERVICE_SPOTIFY_GET_PLAYER_RECENT_TRACKS_SCHEMA)
        hass.services.async_register(
            DOMAIN,
            SERVICE_SPOTIFY_GET_PLAYER_RECENT_TRACKS,
            service_handle_spotify_serviceresponse,
            schema=SERVICE_SPOTIFY_GET_PLAYER_RECENT_TRACKS_SCHEMA,
            supports_response=SupportsResponse.ONLY,
        )

        _logsi.LogObject(SILevel.Verbose, STAppMessages.MSG_SERVICE_REQUEST_REGISTER % SERVICE_SPOTIFY_GET_PLAYLIST, SERVICE_SPOTIFY_GET_PLAYLIST_SCHEMA)
        hass.services.async_register(
            DOMAIN,
            SERVICE_SPOTIFY_GET_PLAYLIST,
            service_handle_spotify_serviceresponse,
            schema=SERVICE_SPOTIFY_GET_PLAYLIST_SCHEMA,
            supports_response=SupportsResponse.ONLY,
        )

        _logsi.LogObject(SILevel.Verbose, STAppMessages.MSG_SERVICE_REQUEST_REGISTER % SERVICE_SPOTIFY_GET_PLAYLIST_FAVORITES, SERVICE_SPOTIFY_GET_PLAYLIST_FAVORITES_SCHEMA)
        hass.services.async_register(
            DOMAIN,
            SERVICE_SPOTIFY_GET_PLAYLIST_FAVORITES,
            service_handle_spotify_serviceresponse,
            schema=SERVICE_SPOTIFY_GET_PLAYLIST_FAVORITES_SCHEMA,
            supports_response=SupportsResponse.ONLY,
        )

        _logsi.LogObject(SILevel.Verbose, STAppMessages.MSG_SERVICE_REQUEST_REGISTER % SERVICE_SPOTIFY_GET_SHOW, SERVICE_SPOTIFY_GET_SHOW_SCHEMA)
        hass.services.async_register(
            DOMAIN,
            SERVICE_SPOTIFY_GET_SHOW,
            service_handle_spotify_serviceresponse,
            schema=SERVICE_SPOTIFY_GET_SHOW_SCHEMA,
            supports_response=SupportsResponse.ONLY,
        )

        _logsi.LogObject(SILevel.Verbose, STAppMessages.MSG_SERVICE_REQUEST_REGISTER % SERVICE_SPOTIFY_GET_SHOW_EPISODES, SERVICE_SPOTIFY_GET_SHOW_EPISODES_SCHEMA)
        hass.services.async_register(
            DOMAIN,
            SERVICE_SPOTIFY_GET_SHOW_EPISODES,
            service_handle_spotify_serviceresponse,
            schema=SERVICE_SPOTIFY_GET_SHOW_EPISODES_SCHEMA,
            supports_response=SupportsResponse.ONLY,
        )

        _logsi.LogObject(SILevel.Verbose, STAppMessages.MSG_SERVICE_REQUEST_REGISTER % SERVICE_SPOTIFY_GET_SHOW_FAVORITES, SERVICE_SPOTIFY_GET_SHOW_FAVORITES_SCHEMA)
        hass.services.async_register(
            DOMAIN,
            SERVICE_SPOTIFY_GET_SHOW_FAVORITES,
            service_handle_spotify_serviceresponse,
            schema=SERVICE_SPOTIFY_GET_SHOW_FAVORITES_SCHEMA,
            supports_response=SupportsResponse.ONLY,
        )

        _logsi.LogObject(SILevel.Verbose, STAppMessages.MSG_SERVICE_REQUEST_REGISTER % SERVICE_SPOTIFY_GET_TRACK_FAVORITES, SERVICE_SPOTIFY_GET_TRACK_FAVORITES_SCHEMA)
        hass.services.async_register(
            DOMAIN,
            SERVICE_SPOTIFY_GET_TRACK_FAVORITES,
            service_handle_spotify_serviceresponse,
            schema=SERVICE_SPOTIFY_GET_TRACK_FAVORITES_SCHEMA,
            supports_response=SupportsResponse.ONLY,
        )

        _logsi.LogObject(SILevel.Verbose, STAppMessages.MSG_SERVICE_REQUEST_REGISTER % SERVICE_SPOTIFY_GET_USERS_TOP_ARTISTS, SERVICE_SPOTIFY_GET_USERS_TOP_ARTISTS_SCHEMA)
        hass.services.async_register(
            DOMAIN,
            SERVICE_SPOTIFY_GET_USERS_TOP_ARTISTS,
            service_handle_spotify_serviceresponse,
            schema=SERVICE_SPOTIFY_GET_USERS_TOP_ARTISTS_SCHEMA,
            supports_response=SupportsResponse.ONLY,
        )

        _logsi.LogObject(SILevel.Verbose, STAppMessages.MSG_SERVICE_REQUEST_REGISTER % SERVICE_SPOTIFY_GET_USERS_TOP_TRACKS, SERVICE_SPOTIFY_GET_USERS_TOP_TRACKS_SCHEMA)
        hass.services.async_register(
            DOMAIN,
            SERVICE_SPOTIFY_GET_USERS_TOP_TRACKS,
            service_handle_spotify_serviceresponse,
            schema=SERVICE_SPOTIFY_GET_USERS_TOP_TRACKS_SCHEMA,
            supports_response=SupportsResponse.ONLY,
        )

        _logsi.LogObject(SILevel.Verbose, STAppMessages.MSG_SERVICE_REQUEST_REGISTER % SERVICE_SPOTIFY_SEARCH_ALBUMS, SERVICE_SPOTIFY_SEARCH_ALBUMS_SCHEMA)
        hass.services.async_register(
            DOMAIN,
            SERVICE_SPOTIFY_SEARCH_ALBUMS,
            service_handle_spotify_serviceresponse,
            schema=SERVICE_SPOTIFY_SEARCH_ALBUMS_SCHEMA,
            supports_response=SupportsResponse.ONLY,
        )

        _logsi.LogObject(SILevel.Verbose, STAppMessages.MSG_SERVICE_REQUEST_REGISTER % SERVICE_SPOTIFY_SEARCH_ARTISTS, SERVICE_SPOTIFY_SEARCH_ARTISTS_SCHEMA)
        hass.services.async_register(
            DOMAIN,
            SERVICE_SPOTIFY_SEARCH_ARTISTS,
            service_handle_spotify_serviceresponse,
            schema=SERVICE_SPOTIFY_SEARCH_ARTISTS_SCHEMA,
            supports_response=SupportsResponse.ONLY,
        )

        _logsi.LogObject(SILevel.Verbose, STAppMessages.MSG_SERVICE_REQUEST_REGISTER % SERVICE_SPOTIFY_SEARCH_AUDIOBOOKS, SERVICE_SPOTIFY_SEARCH_AUDIOBOOKS_SCHEMA)
        hass.services.async_register(
            DOMAIN,
            SERVICE_SPOTIFY_SEARCH_AUDIOBOOKS,
            service_handle_spotify_serviceresponse,
            schema=SERVICE_SPOTIFY_SEARCH_AUDIOBOOKS_SCHEMA,
            supports_response=SupportsResponse.ONLY,
        )

        _logsi.LogObject(SILevel.Verbose, STAppMessages.MSG_SERVICE_REQUEST_REGISTER % SERVICE_SPOTIFY_SEARCH_EPISODES, SERVICE_SPOTIFY_SEARCH_EPISODES_SCHEMA)
        hass.services.async_register(
            DOMAIN,
            SERVICE_SPOTIFY_SEARCH_EPISODES,
            service_handle_spotify_serviceresponse,
            schema=SERVICE_SPOTIFY_SEARCH_EPISODES_SCHEMA,
            supports_response=SupportsResponse.ONLY,
        )

        _logsi.LogObject(SILevel.Verbose, STAppMessages.MSG_SERVICE_REQUEST_REGISTER % SERVICE_SPOTIFY_SEARCH_PLAYLISTS, SERVICE_SPOTIFY_SEARCH_PLAYLISTS_SCHEMA)
        hass.services.async_register(
            DOMAIN,
            SERVICE_SPOTIFY_SEARCH_PLAYLISTS,
            service_handle_spotify_serviceresponse,
            schema=SERVICE_SPOTIFY_SEARCH_PLAYLISTS_SCHEMA,
            supports_response=SupportsResponse.ONLY,
        )

        _logsi.LogObject(SILevel.Verbose, STAppMessages.MSG_SERVICE_REQUEST_REGISTER % SERVICE_SPOTIFY_SEARCH_SHOWS, SERVICE_SPOTIFY_SEARCH_SHOWS_SCHEMA)
        hass.services.async_register(
            DOMAIN,
            SERVICE_SPOTIFY_SEARCH_SHOWS,
            service_handle_spotify_serviceresponse,
            schema=SERVICE_SPOTIFY_SEARCH_SHOWS_SCHEMA,
            supports_response=SupportsResponse.ONLY,
        )

        _logsi.LogObject(SILevel.Verbose, STAppMessages.MSG_SERVICE_REQUEST_REGISTER % SERVICE_SPOTIFY_SEARCH_TRACKS, SERVICE_SPOTIFY_SEARCH_TRACKS_SCHEMA)
        hass.services.async_register(
            DOMAIN,
            SERVICE_SPOTIFY_SEARCH_TRACKS,
            service_handle_spotify_serviceresponse,
            schema=SERVICE_SPOTIFY_SEARCH_TRACKS_SCHEMA,
            supports_response=SupportsResponse.ONLY,
        )

        # indicate success.
        _logsi.LogVerbose("Component async_setup complete")
        return True

    finally:

        # trace.
        _logsi.LeaveMethod(SILevel.Debug)


async def async_setup_entry(hass:HomeAssistant, entry:ConfigEntry) -> bool:
    """
    Set up device instance from a config entry.

    Args:
        hass (HomeAssistant):
            HomeAssistant instance.
        entry (ConfigEntry):
            HomeAssistant configuration entry dictionary.  This contains configuration
            settings for the specific component device entry.

    The __init__.py module "async_setup_entry" method is executed for each device that is 
    configured for the component.  It takes care of loading the device controller instance 
    (e.g. SpotifyClient in our case) for each device that will be controlled.
    """
    try:

        # trace.
        _logsi.EnterMethod(SILevel.Debug)
        _logsi.LogObject(SILevel.Verbose, "'%s': Component async_setup_entry is starting - entry (ConfigEntry) object" % entry.title, entry)
        _logsi.LogDictionary(SILevel.Verbose, "'%s': Component async_setup_entry entry.data dictionary" % entry.title, entry.data)
        _logsi.LogDictionary(SILevel.Verbose, "'%s': Component async_setup_entry entry.options dictionary" % entry.title, entry.options)

        # load config entry user-specified parameters.
        # ** no custom options for this integration.

        spotifyClient:SpotifyClient = None

        # get OAuth2 implementation and create an OAuth2 session.
        implementation = await async_get_config_entry_implementation(hass, entry)
        session = OAuth2Session(hass, entry, implementation)

        _logsi.LogObject(SILevel.Verbose, "'%s': Component async_setup_entry OAuth2 implementation object" % entry.title, implementation)
        _logsi.LogObject(SILevel.Verbose, "'%s': Component async_setup_entry OAuth2 session object" % entry.title, session)
        _logsi.LogDictionary(SILevel.Verbose, "'%s': Component async_setup_entry OAuth2 session.token (dictionary)" % entry.title, session.token, prettyPrint=True)

        # ensure we have a valid session token, and that the session is fully created.
        _logsi.LogVerbose("'%s': Component async_setup_entry is calling async_ensure_token_valid to ensure OAuth2 session is fully-established" % entry.title)
        await session.async_ensure_token_valid()
            
        # -----------------------------------------------------------------------------------
        # Define DataUpdateCoordinator function.
        # -----------------------------------------------------------------------------------
        async def _update_devices() -> list[dict[str, Any]]:
            """
            DataUpdateCoordinator update method that will retrieve the list of Spotify Connect 
            devices that are available.  This method will be executed by the DataUpdateCoordinator
            every 5 minutes to refresh the device list.
            
            Returns:
                A list of Spotify Device class instances.
            """
            
            devices:list[Device] = []

            try:

                _logsi.LogVerbose("'%s': Component DataUpdateCoordinator is retrieving Spotify device list" % entry.title)

                # retrieve list of Spotify Connect devices.
                devices:list[Device] = await hass.async_add_executor_job(
                    spotifyClient.GetPlayerDevices
                )
                
                # trace.
                _logsi.LogDictionary(SILevel.Verbose, "'%s': Component DataUpdateCoordinator update results" % entry.title, devices, prettyPrint=True)
                return devices

            except Exception as ex:
                
                _logsi.LogException("'%s': Component DataUpdateCoordinator update exception" % entry.title, ex)
                raise UpdateFailed from ex


        # -----------------------------------------------------------------------------------
        # Define OAuth2 Session Token Updater
        # -----------------------------------------------------------------------------------
        def _TokenUpdater() -> dict:
            """
            Callback function that will inform HA OAuth2 that a token needs to be refreshed.
            This method is called from SpotifyClient whenever a token needs to be refreshed.

            Returns:
                A dictionaty that contains the refreshed token.
            """
            token:dict = None

            try:

                # trace.
                _logsi.EnterMethod(SILevel.Debug)
                _logsi.LogVerbose("'%s': Component OAuth2 session token is either expired or not valid; calling async_refresh_token to refresh the token" % entry.title)

                # note that we do NOT use the `async_ensure_token_valid` method here, as it may
                # determine that the token does not yet need to be refreshed (via self.valid_token).
                # at this point, the SpotifyClient instance KNOWS that the token needs to be refreshed.
                # we will call HA to refresh the token, and store the new token in the integration config entry.
                # 
                # note that the `config_entry.data['token']` and `session.token` values should match.
                #
                # the following steps will be performed to accomplish the above:
                # - get a reference to the HA OAuth2 session instance.
                # - call `async_refresh_token` to refresh the expired token.
                # - call `async_update_entry` to persist the refreshed token to config storage.
                # - return the refreshed token to the caller.

                # trace.
                _logsi.LogObject(SILevel.Debug, "'%s': Component OAuth2 implementation object" % entry.title, implementation)
                _logsi.LogDictionary(SILevel.Verbose, "'%s': Component OAuth2 session.token (pre-update)" % entry.title, session.token, prettyPrint=True)
                
                # we will refresh the token from the `session.config_entry.data['token']` value (instead of
                # the `session.token` value) in case the token was refreshed in the `update` method.
                # note - the `session.token` value will not change until AFTER `async_update_entry` is called.

                # refresh the session token. 
                _logsi.LogVerbose("'%s': Component is calling async_refresh_token to refresh the session token" % entry.title)
                token = run_coroutine_threadsafe(
                    session.implementation.async_refresh_token(session.config_entry.data['token']), hass.loop
                ).result()
                token['status'] = 'Token refreshed by _TokenUpdater method'

                # temporarily remove update listeners while we update the configuration entry data with the refreshed token.
                # if we don't do this, then the configuration entry is removed and reloaded by the update listener, which
                # we do not want.  we will re-add the update listeners after the call to async_update_entry.
                _logsi.LogArray(SILevel.Verbose, "'%s': Component is temporarily removing update listeners (%d items) while we store the refreshed token" % (entry.title, len(entry.update_listeners)), entry.update_listeners)
                listeners:list = entry.update_listeners.copy()    # shallow copy, so we don't destroy object references
                entry.update_listeners.clear()

                # update token value in configuration entry data.
                _logsi.LogVerbose("'%s': Component is updating configuration entry data with refreshed token" % entry.title)
                session.hass.config_entries.async_update_entry(
                    session.config_entry, 
                    data={**session.config_entry.data, "token": token}
                    )
                
                # restore the update listener(s).
                entry.update_listeners = listeners.copy()    # shallow copy, so we don't destroy object references
                _logsi.LogArray(SILevel.Verbose, "'%s': Component update listeners (%d items) have been restored" % (entry.title, len(entry.update_listeners)), entry.update_listeners)

                # trace.
                _logsi.LogDictionary(SILevel.Verbose, "'%s': Component OAuth2 session.token (post-update)" % entry.title, session.token, prettyPrint=True)
                _logsi.LogVerbose("'%s': Component OAuth2 session token refresh complete" % entry.title)

                # return refreshed token to caller.
                return token

            except Exception as ex:

                # trace.
                _logsi.LogException("'%s': Component OAuth2 session token refresh exception: %s" % (entry.title, str(ex)), ex)
                raise

            finally:

                # trace.
                _logsi.LeaveMethod(SILevel.Debug)

        # -----------------------------------------------------------------------------------
        # Continue with async_setup_entry
        # -----------------------------------------------------------------------------------

        # create new spotify web api python client instance.
        _logsi.LogVerbose("'%s': Component async_setup_entry is creating SpotifyClient instance" % entry.title)
        tokenStorageDir:str = "%s/custom_components/%s/data" % (hass.config.config_dir, DOMAIN)
        spotifyClient:SpotifyClient = await hass.async_add_executor_job(
            SpotifyClient, 
            None, 
            tokenStorageDir, 
            _TokenUpdater
        )
        _logsi.LogObject(SILevel.Verbose, "'%s': Component async_setup_entry spotifyClient object" % entry.title, spotifyClient)

        # set spotify web api python token authorization from HA-managed OAuth2 session token.
        tokenProfileId:str = entry.data.get(CONF_ID)
        _logsi.LogVerbose("'%s': Component async_setup_entry is setting SpotifyClient AuthToken from OAuth2 session token" % entry.title)
        await hass.async_add_executor_job(
            spotifyClient.SetAuthTokenFromToken, 
            implementation.client_id, 
            session.token, 
            tokenProfileId
        )
        
        # trace.
        _logsi.LogObject(SILevel.Verbose, "'%s': Component async_setup_entry spotifyClient object (with AuthToken)" % entry.title, spotifyClient)
        _logsi.LogObject(SILevel.Verbose, "'%s': Component async_setup_entry Spotify UserProfile object" % entry.title, spotifyClient.UserProfile)

        # define a data update coordinator that will poll for updated device entries every 5 minutes.
        device_coordinator:DataUpdateCoordinator[list[Device]] = DataUpdateCoordinator(
            hass,
            _LOGGER,
            name=f"{entry.title} Devices",
            update_interval=timedelta(minutes=5),
            update_method=_update_devices,
        )
        _logsi.LogObject(SILevel.Verbose, "'%s': Component async_setup_entry device DataUpdateCoordinator object" % entry.title, device_coordinator)

        # wait for first refresh of data update coordinator to get the initial device list.
        _logsi.LogObject(SILevel.Verbose, "'%s': Component async_setup_entry waiting for device DataUpdateCoordinator initial update" % entry.title, device_coordinator)
        await device_coordinator.async_config_entry_first_refresh()

        # create media player entity platform instance data.
        _logsi.LogVerbose("'%s': Component async_setup_entry is creating the media player platform instance data object" % entry.title)
        hass.data.setdefault(DOMAIN, {})
        hass.data[DOMAIN][entry.entry_id] = InstanceDataSpotifyPlus(
            devices=device_coordinator,
            session=session,
            spotifyClient=spotifyClient,
            media_player=None
        )
        _logsi.LogObject(SILevel.Verbose, "'%s': Component async_setup_entry media player platform instance data object" % entry.title, hass.data[DOMAIN][entry.entry_id])

        # ensure session scope has not changed for the authorization token.
        if not set(session.token["scope"].split(" ")).issuperset(SPOTIFY_SCOPES):
            _logsi.LogVerbose("'%s': Component async_setup_entry detected a session scope change" % entry.title)
            raise ConfigEntryAuthFailed

        # we are now ready for HA to create individual objects for each platform that
        # our device requires; in our case, it's just a media_player platform.
        # we initiate this by calling the `async_forward_entry_setups`, which 
        # calls the `async_setup_entry` function in each platform module (e.g.
        # media_player.py) for each device instance.
        _logsi.LogVerbose("'%s': Component async_setup_entry is forwarding configuration entry setups to create the individual media player platforms" % entry.title)
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
        
        # register an update listener to reload configuration entry when options are updated.
        # this will return an "unlisten" function, which will be added to the configuration
        # "on_unload" event handler to automatically unregister the update listener when
        # the configuration is unloaded.
        listenerRemovePtr = entry.add_update_listener(options_update_listener)
        _logsi.LogArray(SILevel.Verbose, "'%s': Component update listener has been registered and added to update listeners array (%d array items)" % (entry.title, len(entry.update_listeners)), entry.update_listeners)

        entry.async_on_unload(listenerRemovePtr)
        _logsi.LogArray(SILevel.Verbose, "'%s': Component update listener auto-unregister method has been added to on_unload event handlers array (%d array items)" % (entry.title, len(entry._on_unload)), entry._on_unload)

        # trace.
        _logsi.LogVerbose("'%s': Component async_setup_entry is complete" % entry.title)

        # indicate success.
        return True

    except Exception as ex:
            
        # this is usually caused by a temporary error (e.g. device unplugged, network connectivity, etc), in 
        # which case the user will need to manually reload the device when the temporary condition is cleared.
        # if it's a permanent error (e.g. ip address change), then the user needs to correct the configuration.
        
        # trace.
        _logsi.LogException("'%s': Component async_setup_entry exception" % entry.title, ex, logToSystemLogger=False)
        
        # reset storage.
        spotifyClient = None
        
        # inform HA that the configuration is not ready.
        raise ConfigEntryNotReady from ex

    finally:

        # trace.
        _logsi.LeaveMethod(SILevel.Debug)


async def async_unload_entry(hass:HomeAssistant, entry:ConfigEntry) -> bool:
    """
    Unloads a configuration entry.

    Args:
        hass (HomeAssistant):
            HomeAssistant instance.
        entry (ConfigEntry):
            HomeAssistant configuration entry object.

    The __init__.py module "async_unload_entry" unloads a configuration entry.
            
    This method is called when a configuration entry is to be removed. The class
    needs to unload itself, and remove any callbacks.  
    
    Note that any options update listeners (added via "add_update_listener") do not need 
    to be removed, as they are already removed by the time this method is called.
    This is accomplished by the "entry.async_on_unload(listener)" call in async_setup_entry,
    which removes them from the configuration entry just before it is unloaded.
    """
    try:

        # trace.
        _logsi.EnterMethod(SILevel.Debug)
        _logsi.LogObject(SILevel.Verbose, "'%s': Component async_unload_entry configuration entry" % entry.title, entry)

        # unload any platforms this device supports.
        _logsi.LogVerbose("'%s':Component async_unload_entry is unloading our device instance from the domain" % entry.title)
        unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

        # if unload was successful, then remove data associated with the device.
        if unload_ok:

            # remove instance data from domain.
            _logsi.LogVerbose("'%s': Component async_unload_entry is removing our device instance data from the domain" % entry.title)
            data:InstanceDataSpotifyPlus = hass.data[DOMAIN].pop(entry.entry_id)
            _logsi.LogObject(SILevel.Verbose, "'%s': Component async_unload_entry unloaded configuration entry instance data" % entry.title, data)

            # a quick check to make sure all update listeners were removed (see method doc notes above).
            if len(entry.update_listeners) > 0:
                _logsi.LogArray(SILevel.Warning, "'%s': Component configuration update_listener(s) did not get removed before configuration unload (%d items - should be 0)" % (entry.title, len(entry.update_listeners)), entry.update_listeners)
                entry.update_listeners.clear()

        # return status to caller.
        _logsi.LogVerbose("'%s': Component async_unload_entry completed" % entry.title)
        return unload_ok

    finally:

        # trace.
        _logsi.LeaveMethod(SILevel.Debug)


async def async_reload_entry(hass:HomeAssistant, entry:ConfigEntry) -> None:
    """
    Reload config entry.

    Args:
        hass (HomeAssistant):
            HomeAssistant instance.
        entry (ConfigEntry):
            HomeAssistant configuration entry object.

    The __init__.py module "async_reload_entry" reloads a configuration entry.
            
    This method is called when an entry/configured device is to be reloaded. The class
    needs to unload itself, remove callbacks, and call async_setup_entry.
    """
    try:

        # trace.
        _logsi.EnterMethod(SILevel.Debug)
        _logsi.LogObject(SILevel.Verbose, "'%s': Component async_reload_entry configuration entry" % entry.title, entry)

        # unload the configuration entry.
        _logsi.LogVerbose("'%s': Component async_reload_entry is unloading the configuration entry" % entry.title)
        await async_unload_entry(hass, entry)

        # reload (setup) the configuration entry.
        _logsi.LogVerbose("'%s': Component async_reload_entry is reloading the configuration entry" % entry.title)
        await async_setup_entry(hass, entry)

        # trace.
        _logsi.LogVerbose("'%s': Component async_reload_entry completed" % entry.title)

    finally:

        # trace.
        _logsi.LeaveMethod(SILevel.Debug)


async def options_update_listener(hass:HomeAssistant, entry:ConfigEntry) -> None:
    """
    Configuration entry update event handler.
    
    Args:
        hass (HomeAssistant):
            HomeAssistant instance.
        entry (ConfigEntry):
            HomeAssistant configuration entry object.
    
    Reloads the config entry after updates have been applied to a configuration entry.

    This method is called when a user has updated configuration options via the UI, or
    when a call is made to async_update_entry with changed configuration data.
    """
    try:

        # trace.
        _logsi.EnterMethod(SILevel.Debug)
        _logsi.LogObject(SILevel.Verbose, "'%s': Component detected configuration entry options update" % entry.title, entry)
        
        # reload the configuration entry.
        await hass.config_entries.async_reload(entry.entry_id)

        # trace.
        _logsi.LogVerbose("'%s': Component options_update_listener completed" % entry.title)

    finally:

        # trace.
        _logsi.LeaveMethod(SILevel.Debug)
