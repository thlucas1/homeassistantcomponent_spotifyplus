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
    INTENT_PLAYLIST_CREATE,
    RESPONSE_PLAYLIST_CREATED,
    SERVICE_SPOTIFY_PLAYLIST_CREATE,
    SLOT_AREA,
    SLOT_DESCRIPTION,
    SLOT_FLOOR,
    SLOT_IMAGE_PATH,
    SLOT_IS_COLLABORATIVE,
    SLOT_IS_PUBLIC,
    SLOT_NAME,
    SLOT_PLAYLIST_NAME,
    SLOT_PLAYLIST_TITLE,
    SLOT_PLAYLIST_URL,
    SLOT_PREFERRED_AREA_ID,
    SLOT_PREFERRED_FLOOR_ID,
    SPOTIFY_WEB_URL_PFX,
)

from .spotifyplusintenthandler import SpotifyPlusIntentHandler


class SpotifyPlusPlaylistCreate_Handler(SpotifyPlusIntentHandler):
    """
    Handles intents for SpotifyPlusPlaylistCreate.
    """
    def __init__(self, intentLoader:IntentLoader) -> None:
        """
        Initializes a new instance of the IntentHandler class.
        """
        # invoke base class method.
        super().__init__(intentLoader)

        # set intent handler basics.
        self.description = "Creates a new empty playlist for the current user."
        self.intent_type = INTENT_PLAYLIST_CREATE
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
            vol.Optional(SLOT_DESCRIPTION): cv.string,
            vol.Optional(SLOT_IMAGE_PATH): cv.string,
            vol.Optional(SLOT_IS_COLLABORATIVE): cv.boolean,
            vol.Optional(SLOT_IS_PUBLIC): cv.boolean,
            vol.Optional(SLOT_PLAYLIST_NAME): cv.string,
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
        playlist_name = intentObj.slots.get(SLOT_PLAYLIST_NAME, {}).get(CONF_TEXT, None)
        playlist_description = intentObj.slots.get(SLOT_DESCRIPTION, {}).get(CONF_TEXT, None)
        playlist_is_collaborative = intentObj.slots.get(SLOT_IS_COLLABORATIVE, {}).get(CONF_TEXT, False)
        playlist_is_public = intentObj.slots.get(SLOT_IS_PUBLIC, {}).get(CONF_TEXT, False)
        playlist_image_path = intentObj.slots.get(SLOT_IMAGE_PATH, {}).get(CONF_TEXT, None)

        # set service name and build parameters.
        svcName:str = SERVICE_SPOTIFY_PLAYLIST_CREATE
        svcData:dict = \
        {
            "entity_id": playerEntityState.entity_id,
            "name": playlist_name,
            "description": playlist_description,
            "public": playlist_is_public,
            "collaborative": playlist_is_collaborative,
        }
        if (playlist_image_path) and (len(playlist_image_path) > 0):
            svcData["image_path"] = playlist_image_path

        # create the new playlist.
        self.logsi.LogVerbose(STAppMessages.MSG_SERVICE_EXECUTE % (svcName, playerEntityState.entity_id), colorValue=SIColors.Khaki)
        info_result:ServiceResponse = await intentObj.hass.services.async_call(
            DOMAIN,
            svcName,
            svcData,
            blocking=True,
            context=intentObj.context,
            return_response=True,
        )
        self.logsi.LogDictionary(SILevel.Verbose, "SERVICE_SPOTIFY_PLAYLIST_CREATE result", info_result, prettyPrint=True, colorValue=SIColors.Khaki)
           
        # get related details and update slot info.
        playlist_uri:str = info_result.get("result",{}).get("uri",None)
        playlist_url:str = info_result.get("result",{}).get("external_urls", {}).get("spotify", SPOTIFY_WEB_URL_PFX)

        # update slots with returned info.
        intentObj.slots[SLOT_PLAYLIST_TITLE] = { CONF_VALUE: playlist_uri, CONF_TEXT: playlist_name }
        intentObj.slots[SLOT_PLAYLIST_URL] = { CONF_VALUE: playlist_url, CONF_TEXT: "Spotify" }

        # return intent response.
        return await self.ReturnResponseByKey(intentObj, intentResponse, RESPONSE_PLAYLIST_CREATED)
