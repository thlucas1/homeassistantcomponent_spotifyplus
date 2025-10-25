import voluptuous as vol

from homeassistant.core import State, ServiceResponse
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.intent import (
    Intent,
    IntentResponse, 
)

from smartinspectpython.siauto import SILevel, SIColors

from spotifywebapipython import SpotifyMediaTypes

from ..appmessages import STAppMessages
from ..intent_loader import IntentLoader
from ..utils import get_id_from_uri
from ..const import (
    CONF_TEXT,
    CONF_VALUE,
    DOMAIN,
    PLATFORM_SPOTIFYPLUS,
    INTENT_SEARCH_PLAY_ARTIST_ALBUM,
    RESPONSE_PLAY_ALBUM,
    RESPONSE_PLAY_ALBUM_WITH_ARTIST,
    RESPONSE_SPOTIFY_SEARCH_NO_ITEMS_ALBUM,
    SERVICE_SPOTIFY_PLAYER_MEDIA_PLAY_CONTEXT,
    SERVICE_SPOTIFY_SEARCH_ALBUMS,
    SLOT_ALBUM_NAME,
    SLOT_ALBUM_TITLE,
    SLOT_ALBUM_URL,
    SLOT_AREA,
    SLOT_ARTIST_NAME,
    SLOT_ARTIST_TITLE,
    SLOT_ARTIST_URL,
    SLOT_DELAY,
    SLOT_DEVICE_NAME,
    SLOT_FLOOR,
    SLOT_NAME,
    SLOT_PLAYER_SHUFFLE_MODE,
    SLOT_SEARCH_CRITERIA,
    SLOT_PREFERRED_AREA_ID,
    SLOT_PREFERRED_FLOOR_ID,
    SPOTIFY_WEB_URL_PFX,
)

from .spotifyplusintenthandler import SpotifyPlusIntentHandler


class SpotifyPlusSearchPlayArtistAlbum_Handler(SpotifyPlusIntentHandler):
    """
    Handles intents for SpotifyPlusSearchPlayArtistAlbum.
    """
    def __init__(self, intentLoader:IntentLoader) -> None:
        """
        Initializes a new instance of the IntentHandler class.
        """
        # invoke base class method.
        super().__init__(intentLoader)

        # set intent handler basics.
        self.description = "Searches the Spotify catalog for an album name by a specific artist, and starts playing it if found."
        self.intent_type = INTENT_SEARCH_PLAY_ARTIST_ALBUM
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
            vol.Optional(SLOT_ARTIST_NAME): cv.string,
            vol.Optional(SLOT_ARTIST_TITLE): cv.string,
            vol.Optional(SLOT_ARTIST_URL): cv.string,
            vol.Optional(SLOT_ALBUM_NAME): cv.string,
            vol.Optional(SLOT_ALBUM_TITLE): cv.string,
            vol.Optional(SLOT_ALBUM_URL): cv.string,
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
        device_name = intentObj.slots.get(SLOT_DEVICE_NAME, {}).get(CONF_VALUE, None)
        artist_name = intentObj.slots.get(SLOT_ARTIST_NAME, {}).get(CONF_TEXT, None)
        artist_uri = intentObj.slots.get(SLOT_ARTIST_NAME, {}).get(CONF_VALUE, None)
        album_name = intentObj.slots.get(SLOT_ALBUM_NAME, {}).get(CONF_TEXT, None)
        album_uri = intentObj.slots.get(SLOT_ALBUM_NAME, {}).get(CONF_VALUE, None)
        player_shuffle_mode = intentObj.slots.get(SLOT_PLAYER_SHUFFLE_MODE, {}).get(CONF_VALUE, "on")

        # update slots with returned info.
        intentObj.slots[SLOT_ARTIST_TITLE] = { CONF_VALUE: artist_uri, CONF_TEXT: artist_name }
        intentObj.slots[SLOT_ALBUM_TITLE] = { CONF_VALUE: album_uri, CONF_TEXT: album_name }

        # was a uri supplied?
        if (album_uri.startswith(f"spotify:{SpotifyMediaTypes.ALBUM.value}")):

            # if a uri was supplied, then it's from a pre-configured list of values; in this case,
            # we will bypass the search since it's (assumed to be) a valid uri value.

            # get id portion of spotify uri value.
            album_id:str = get_id_from_uri(album_uri)

            # load returned info that we care about.
            album_title = album_name
            album_url = f"{SPOTIFY_WEB_URL_PFX}/{SpotifyMediaTypes.ALBUM.value}/{album_id}"

            # artist variables are unknwon, since only the album name / uri were supplied.
            artist_title = artist_name
            artist_url = SPOTIFY_WEB_URL_PFX

        else:

            # format criteria if searching by artist.
            artist_criteria = ""
            if artist_name is not None:
                artist_criteria = f" artist:{artist_name}" 

            # set service name and build parameters.
            svcName:str = SERVICE_SPOTIFY_SEARCH_ALBUMS
            svcData:dict = \
            {
                "entity_id": playerEntityState.entity_id,
                "criteria": album_name + artist_criteria,
                "limit_total": 1,
                "include_external": "audio"
            }

            # update slots with search criteria.
            intentObj.slots[SLOT_SEARCH_CRITERIA] = { CONF_VALUE: "", CONF_TEXT: svcData["criteria"] }

            # search spotify catalog for matching album name.
            self.logsi.LogVerbose(STAppMessages.MSG_SERVICE_EXECUTE % (svcName, playerEntityState.entity_id), colorValue=SIColors.Khaki)
            search_result:ServiceResponse = await intentObj.hass.services.async_call(
                DOMAIN,
                svcName,
                svcData,
                blocking=True,
                context=intentObj.context,
                return_response=True,
            )
            self.logsi.LogDictionary(SILevel.Verbose, "SERVICE_SPOTIFY_SEARCH_ALBUMS result", search_result, prettyPrint=True, colorValue=SIColors.Khaki)

            # if no matching items, then return appropriate response.
            items_count:int = search_result.get("result",{}).get("items_count", 0)
            if (items_count == 0):
                return await self.ReturnResponseByKey(intentObj, intentResponse, RESPONSE_SPOTIFY_SEARCH_NO_ITEMS_ALBUM)

            # load returned info that we care about.
            album_title:str = search_result.get("result",{}).get("items")[0].get("name", "unknown")
            album_uri:str = search_result.get("result",{}).get("items")[0].get("uri", "unknown")
            album_url:str = search_result.get("result",{}).get("items")[0].get("external_urls", {}).get("spotify", SPOTIFY_WEB_URL_PFX)

            artist_title:str = search_result.get("result",{}).get("items")[0].get("artists")[0].get("name", "unknown")
            artist_uri:str = search_result.get("result",{}).get("items")[0].get("artists")[0].get("uri", "unknown")
            artist_url:str = search_result.get("result",{}).get("items")[0].get("artists")[0].get("external_urls", {}).get("spotify", SPOTIFY_WEB_URL_PFX)

        # update slots with returned info.
        intentObj.slots[SLOT_ARTIST_TITLE] = { CONF_VALUE: artist_uri, CONF_TEXT: artist_title }
        intentObj.slots[SLOT_ARTIST_URL] = { CONF_VALUE: artist_url, CONF_TEXT: "Spotify" }
        intentObj.slots[SLOT_ALBUM_TITLE] = { CONF_VALUE: album_uri, CONF_TEXT: album_title }
        intentObj.slots[SLOT_ALBUM_URL] = { CONF_VALUE: album_url, CONF_TEXT: "Spotify" }

        # set service name and build parameters.
        svcName:str = SERVICE_SPOTIFY_PLAYER_MEDIA_PLAY_CONTEXT
        svcData:dict = \
        {
            "entity_id": playerEntityState.entity_id,
            "context_uri": album_uri,
            "shuffle": True if player_shuffle_mode == "on" else False,
            "device_id": device_name,
            "delay": delay,
        }

        # play the media.
        self.logsi.LogVerbose(STAppMessages.MSG_SERVICE_EXECUTE % (svcName, playerEntityState.entity_id), colorValue=SIColors.Khaki)
        await intentObj.hass.services.async_call(
            DOMAIN,
            svcName,
            svcData,
            blocking=True,
            context=intentObj.context,
            return_response=False,
        )

        # set appropriate response.
        responseKey = RESPONSE_PLAY_ALBUM_WITH_ARTIST
        if (artist_name is None):
            responseKey = RESPONSE_PLAY_ALBUM
           
        # return intent response.
        return await self.ReturnResponseByKey(intentObj, intentResponse, responseKey)
