import voluptuous as vol

from homeassistant.core import State, ServiceResponse
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.intent import (
    Intent,
    IntentResponse, 
)

from smartinspectpython.siauto import SILevel, SIColors

from spotifywebapipython import SpotifyApiError, SpotifyMediaTypes

from ..appmessages import STAppMessages
from ..intent_loader import IntentLoader
from ..utils import get_id_from_uri
from ..const import (
    CONF_TEXT,
    CONF_VALUE,
    DOMAIN,
    PLATFORM_SPOTIFYPLUS,
    INTENT_PLAY_PLAYLIST,
    RESPONSE_PLAY_PLAYLIST,
    RESPONSE_SPOTIFY_SEARCH_NO_ITEMS_PLAYLIST,
    SERVICE_SPOTIFY_PLAYER_MEDIA_PLAY_CONTEXT,
    SERVICE_SPOTIFY_SEARCH_PLAYLISTS,
    SLOT_AREA,
    SLOT_DELAY,
    SLOT_DEVICE_NAME,
    SLOT_FLOOR,
    SLOT_NAME,
    SLOT_PLAYER_SHUFFLE_MODE,
    SLOT_PLAYLIST_NAME,
    SLOT_PLAYLIST_TITLE,
    SLOT_PLAYLIST_URL,
    SLOT_PREFERRED_AREA_ID,
    SLOT_PREFERRED_FLOOR_ID,
    SPOTIFY_WEB_URL_PFX,
)

from .spotifyplusintenthandler import SpotifyPlusIntentHandler


class SpotifyPlusPlayPlaylist_Handler(SpotifyPlusIntentHandler):
    """
    Handles intents for SpotifyPlusPlayPlaylist.
    """
    def __init__(self, intentLoader:IntentLoader) -> None:
        """
        Initializes a new instance of the IntentHandler class.
        """
        # invoke base class method.
        super().__init__(intentLoader)

        # set intent handler basics.
        self.description = "Searches the Spotify catalog for a playlist name, and starts playing it if found."
        self.intent_type = INTENT_PLAY_PLAYLIST
        self.platforms = {PLATFORM_SPOTIFYPLUS}


    @property
    def slot_schema(self) -> dict | None:
        """
        Returns the slot schema for this intent.
        """
        return {

            # slots that determine which media player entity will be used.
            vol.Optional(SLOT_NAME): cv.string,
            vol.Optional(SLOT_AREA): cv.string,
            vol.Optional(SLOT_FLOOR): cv.string,
            vol.Optional(SLOT_PREFERRED_AREA_ID): cv.string,
            vol.Optional(SLOT_PREFERRED_FLOOR_ID): cv.string,

            # slots for other service arguments.
            vol.Optional(SLOT_DELAY, default=0.50): vol.Any(None, vol.All(vol.Coerce(float), vol.Range(min=0, max=10.0))),
            vol.Optional(SLOT_DEVICE_NAME): cv.string,
            vol.Optional(SLOT_PLAYLIST_NAME): cv.string,
            vol.Optional(SLOT_PLAYLIST_TITLE): cv.string,
            vol.Optional(SLOT_PLAYLIST_URL): cv.string,
            vol.Optional(SLOT_PLAYER_SHUFFLE_MODE): cv.string,
        }


    async def async_HandleIntent(
        self, 
        intentObj: Intent, 
        intentResponse: IntentResponse
        ) -> IntentResponse:
        """
        Handles the intent.

        Args:
            intentObj (Intent):
                Intent object.
            intentResponse (IntentResponse)
                Intent response object.

        Returns:
            An IntentResponse object.
        """
        # invoke base class method to resolve the player entity and its state.
        playerEntityState:State = await super().async_GetMatchingPlayerState(
            intentObj,
            intentResponse,
            desiredFeatures=None,
            desiredStates=None,
            desiredStateResponseKey=None,
            requiresSpotifyPremium=True,
        )

        # if media player was not resolved, then we are done;
        # note that the base class method above already called `async_set_speech` with a response.
        if playerEntityState is None:
            return intentResponse
            
        # get optional arguments (if provided).
        delay = intentObj.slots.get(SLOT_DELAY, {}).get(CONF_VALUE, None)
        device_name = intentObj.slots.get(SLOT_DEVICE_NAME, {}).get(CONF_TEXT, None)
        playlist_name = intentObj.slots.get(SLOT_PLAYLIST_NAME, {}).get(CONF_TEXT, None)
        playlist_uri = intentObj.slots.get(SLOT_PLAYLIST_NAME, {}).get(CONF_VALUE, None)
        player_shuffle_mode = intentObj.slots.get(SLOT_PLAYER_SHUFFLE_MODE, {}).get(CONF_VALUE, "on")

        # update slots with returned info.
        intentObj.slots[SLOT_PLAYLIST_TITLE] = { CONF_VALUE: playlist_uri, CONF_TEXT: playlist_name }

        # was a uri supplied?
        if (playlist_uri.startswith(f"spotify:{SpotifyMediaTypes.PLAYLIST.value}")):

            # if a uri was supplied, then it's from a pre-configured list of values; in this case,
            # we will bypass the search since it's (assumed to be) a valid uri value.

            # get id portion of spotify uri value.
            playlist_id:str = get_id_from_uri(playlist_uri)

            # load returned info that we care about.
            playlist_title = playlist_name
            playlist_url = f"{SPOTIFY_WEB_URL_PFX}/{SpotifyMediaTypes.PLAYLIST.value}/{playlist_id}"

        else:

            # set service name and build parameters.
            svcName:str = SERVICE_SPOTIFY_SEARCH_PLAYLISTS
            svcData:dict = \
            {
                "entity_id": playerEntityState.entity_id,
                "criteria": playlist_name,
                "limit_total": 1,
                "include_external": "audio"
            }

            # search spotify catalog for matching playlist name.
            self.logsi.LogVerbose(STAppMessages.MSG_SERVICE_EXECUTE % (svcName, playerEntityState.entity_id), colorValue=SIColors.Khaki)
            search_result:ServiceResponse = await intentObj.hass.services.async_call(
                DOMAIN,
                svcName,
                svcData,
                blocking=True,
                context=intentObj.context,
                return_response=True,
            )
            self.logsi.LogDictionary(SILevel.Verbose, "SERVICE_SPOTIFY_SEARCH_PLAYLISTS result", search_result, prettyPrint=True, colorValue=SIColors.Khaki)

            # if no matching items, then return appropriate response.
            items_count:int = search_result.get("result",{}).get("items_count", 0)
            if (items_count == 0):
                return await self.ReturnResponseByKey(intentObj, intentResponse, RESPONSE_SPOTIFY_SEARCH_NO_ITEMS_PLAYLIST)

            # load returned info that we care about.
            playlist_title:str = search_result.get("result",{}).get("items")[0].get("name", "unknown")
            playlist_uri:str = search_result.get("result",{}).get("items")[0].get("uri", "unknown")
            playlist_url:str = search_result.get("result",{}).get("items")[0].get("external_urls", {}).get("spotify", SPOTIFY_WEB_URL_PFX)

        # update slots with returned info.
        intentObj.slots[SLOT_PLAYLIST_TITLE] = { CONF_VALUE: playlist_uri, CONF_TEXT: playlist_title }
        intentObj.slots[SLOT_PLAYLIST_URL] = { CONF_VALUE: playlist_url, CONF_TEXT: "Spotify" }

        # set service name and build parameters.
        svcName:str = SERVICE_SPOTIFY_PLAYER_MEDIA_PLAY_CONTEXT
        svcData:dict = \
        {
            "entity_id": playerEntityState.entity_id,
            "context_uri": playlist_uri,
            "shuffle": True if player_shuffle_mode == "on" else False,
            "device_id": device_name,
            "delay": delay,
        }

        # get artist information.
        self.logsi.LogVerbose(STAppMessages.MSG_SERVICE_EXECUTE % (svcName, playerEntityState.entity_id), colorValue=SIColors.Khaki)
        await intentObj.hass.services.async_call(
            DOMAIN,
            svcName,
            svcData,
            blocking=True,
            context=intentObj.context,
            return_response=False,
        )
           
        # return intent response.
        return await self.ReturnResponseByKey(intentObj, intentResponse, RESPONSE_PLAY_PLAYLIST)
