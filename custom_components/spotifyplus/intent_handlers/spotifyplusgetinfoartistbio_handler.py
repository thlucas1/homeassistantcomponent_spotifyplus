import voluptuous as vol

from homeassistant.core import State, ServiceResponse
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.intent import (
    Intent,
    IntentResponse, 
)

from smartinspectpython.siauto import SILevel, SIColors

from ..appmessages import STAppMessages
from ..intent_loader import IntentLoader
from ..utils import get_id_from_uri
from ..const import (
    CONF_TEXT,
    CONF_VALUE,
    DOMAIN,
    PLATFORM_SPOTIFYPLUS,
    INTENT_GET_INFO_ARTIST_BIO,
    RESPONSE_GET_INFO_ARTIST_BIO,
    RESPONSE_SPOTIFY_NO_ARTIST_INFO,
    SERVICE_SPOTIFY_GET_ARTIST_INFO,
    SERVICE_SPOTIFY_SEARCH_ARTISTS,
    SLOT_AREA,
    SLOT_ARTIST_BIO,
    SLOT_ARTIST_NAME,
    SLOT_ARTIST_TITLE,
    SLOT_ARTIST_URL,
    SLOT_NAME,
    SLOT_FLOOR,
    SLOT_PREFERRED_AREA_ID,
    SLOT_PREFERRED_FLOOR_ID,
    SLOT_SEARCH_CRITERIA,
    SPOTIFY_WEB_URL_PFX,
)

from .spotifyplusintenthandler import SpotifyPlusIntentHandler


class SpotifyPlusGetInfoArtistBio_Handler(SpotifyPlusIntentHandler):
    """
    Handles intents for SpotifyPlusGetInfoArtistBio.
    """
    def __init__(self, intentLoader:IntentLoader) -> None:
        """
        Initializes a new instance of the IntentHandler class.
        """
        # invoke base class method.
        super().__init__(intentLoader)

        # set intent handler basics.
        self.description = "Gets Spotify artist bio information for the specified artist.  Up to 400 characters of information are returned (if bio was found)."
        self.intent_type = INTENT_GET_INFO_ARTIST_BIO
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
            vol.Optional(SLOT_ARTIST_BIO): cv.string,
            vol.Optional(SLOT_ARTIST_NAME): cv.string,
            vol.Optional(SLOT_ARTIST_TITLE): cv.string,
            vol.Optional(SLOT_ARTIST_URL): cv.string,
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
        )

        # if media player was not resolved, then we are done;
        # note that the base class method above already called `async_set_speech` with a response.
        if playerEntityState is None:
            return intentResponse
            
        # get optional arguments (if provided).
        artist_name = intentObj.slots.get(SLOT_ARTIST_NAME, {}).get(CONF_VALUE, None)

        # update slots with returned info.
        intentObj.slots[SLOT_ARTIST_TITLE] = { CONF_VALUE: "", CONF_TEXT: artist_name }

        # set service name and build parameters.
        svcName:str = SERVICE_SPOTIFY_SEARCH_ARTISTS
        svcData:dict = \
        {
            "entity_id": playerEntityState.entity_id,
            "criteria": f"artist:{artist_name}",
            "limit_total": 1,
            "include_external": "audio"
        }

        # update slots with search criteria.
        intentObj.slots[SLOT_SEARCH_CRITERIA] = { CONF_VALUE: "", CONF_TEXT: svcData["criteria"] }

        # search spotify catalog for matching artist name.
        self.logsi.LogVerbose(STAppMessages.MSG_SERVICE_EXECUTE % (svcName, playerEntityState.entity_id), colorValue=SIColors.Khaki)
        search_result:ServiceResponse = await intentObj.hass.services.async_call(
            DOMAIN,
            svcName,
            svcData,
            blocking=True,
            context=intentObj.context,
            return_response=True,
        )
        self.logsi.LogDictionary(SILevel.Verbose, "SERVICE_SPOTIFY_SEARCH_ARTISTS result", search_result, prettyPrint=True, colorValue=SIColors.Khaki)

        # if no matching items, then return appropriate response.
        items_count:int = search_result.get("result",{}).get("items_count", 0)
        if (items_count == 0):
            return await self.ReturnResponseByKey(intentObj, intentResponse, RESPONSE_SPOTIFY_NO_ARTIST_INFO)

        # load returned info that we care about.
        artist_title:str = search_result.get("result",{}).get("items")[0].get("name", "unknown")
        artist_uri:str = search_result.get("result",{}).get("items")[0].get("uri", "unknown")
        artist_url:str = search_result.get("result",{}).get("items")[0].get("external_urls", {}).get("spotify", SPOTIFY_WEB_URL_PFX)

        # get id portion of spotify uri value.
        artist_id:str = get_id_from_uri(artist_uri)

        # update slots with returned info.
        intentObj.slots[SLOT_ARTIST_TITLE] = { CONF_VALUE: artist_uri, CONF_TEXT: artist_title }
        intentObj.slots[SLOT_ARTIST_URL] = { CONF_VALUE: artist_url, CONF_TEXT: "Spotify" }

        # set service name and build parameters.
        svcName:str = SERVICE_SPOTIFY_GET_ARTIST_INFO
        svcData:dict = \
        {
            "entity_id": playerEntityState.entity_id,
            "artist_id": artist_id,
        }

        # get artist information.
        self.logsi.LogVerbose(STAppMessages.MSG_SERVICE_EXECUTE % (svcName, playerEntityState.entity_id), colorValue=SIColors.Khaki)
        info_result:ServiceResponse = await intentObj.hass.services.async_call(
            DOMAIN,
            svcName,
            svcData,
            blocking=True,
            context=intentObj.context,
            return_response=True,
        )
        self.logsi.LogDictionary(SILevel.Verbose, "SERVICE_SPOTIFY_GET_ARTIST_INFO result", info_result, prettyPrint=True, colorValue=SIColors.Khaki)
           
        # if artist info not found, then return appropriate response.
        artist_bio:str = info_result.get("result",{}).get("bio", None)
        if (artist_bio is None):
            return await self.ReturnResponseByKey(intentObj, intentResponse, RESPONSE_SPOTIFY_NO_ARTIST_INFO)

        # update slots with returned info.
        intentObj.slots[SLOT_ARTIST_BIO] = { CONF_VALUE: "", CONF_TEXT: artist_bio }

        # return intent response.
        return await self.ReturnResponseByKey(intentObj, intentResponse, RESPONSE_GET_INFO_ARTIST_BIO)
