import voluptuous as vol

from homeassistant.core import State, ServiceResponse
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import intent
from homeassistant.helpers.intent import (
    IntentHandleError,
    IntentResponse, 
    _SlotsType,
)

from smartinspectpython.siauto import SILevel, SIColors

from ..appmessages import STAppMessages
from ..utils import get_id_from_uri
from ..const import (
    CONF_TEXT,
    CONF_VALUE,
    DOMAIN,
    PLATFORM_SPOTIFYPLUS,
    INTENT_GET_INFO_ARTIST_BIO,
    RESPONSE_ERROR_UNHANDLED,
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
    SPOTIFY_WEB_URL_PFX,
)

from .spotifyplusintenthandler import SpotifyPlusIntentHandler, get_intent_response_resource


class SpotifyPlusGetInfoArtistBio_Handler(SpotifyPlusIntentHandler):
    """
    Handles intents for SpotifyPlusGetInfoArtistBio.
    """
    def __init__(self) -> None:
        """
        Initializes a new instance of the IntentHandler class.
        """
        # invoke base class method.
        super().__init__()

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


    async def async_handle(self, intentObj: intent.Intent) -> IntentResponse:
        """
        Handles the intent.

        Args:
            intentObj (Intent):
                Intent object.
        """
        playerEntityState:State = None
        slots:_SlotsType = None

        try:

            # trace.
            self.logsi.EnterMethod(SILevel.Debug, intentObj.intent_type, colorValue=SIColors.Khaki)
            self.logsi.LogVerbose(STAppMessages.MSG_INTENT_HANDLE_REQUEST % intentObj.intent_type, colorValue=SIColors.Khaki)
            self.logsi.LogObject(SILevel.Verbose, STAppMessages.MSG_INTENT_HANDLE_REQUEST_PARMS % intentObj.intent_type, intentObj, colorValue=SIColors.Khaki)
            self.logsi.LogDictionary(SILevel.Verbose, STAppMessages.MSG_INTENT_HANDLE_REQUEST_SLOTS % intentObj.intent_type, intentObj.slots, colorValue=SIColors.Khaki)

            # create intent response object.
            intentResponse:IntentResponse = intentObj.create_response()

            # invoke base class method to resolve the player entity.
            intentResponse, slots, playerEntityState = await super().async_get_matching_player_state(
                intentObj,
                intentResponse,
                slots=intentObj.slots,
                desiredFeatures=None,
                desiredStates=None,
                desiredStateResponseKey=None,
            )

            # if media player was not resolved, then we are done;
            # note that the base class method above already called `async_set_speech` with a response.
            if playerEntityState is None:
                return intentResponse
            
            # get optional arguments (if provided).
            artist_name = slots.get(SLOT_ARTIST_NAME, {}).get(CONF_VALUE, None)

            # update slots with returned info.
            slots[SLOT_ARTIST_TITLE] = { CONF_TEXT: artist_name, CONF_VALUE: "" }

            # set service name and build parameters.
            svcName:str = SERVICE_SPOTIFY_SEARCH_ARTISTS
            svcData:dict = \
            {
                "entity_id": playerEntityState.entity_id,
                "criteria": f"artist:{artist_name}",
                "limit_total": 1,
                "include_external": "audio"
            }

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

                # requested info is not available.
                responseText = await get_intent_response_resource(RESPONSE_SPOTIFY_NO_ARTIST_INFO, slots, intentObj, PLATFORM_SPOTIFYPLUS)
                intentResponse.async_set_speech(responseText)
                self.logsi.LogObject(SILevel.Verbose, STAppMessages.MSG_INTENT_HANDLER_RESPONSE % (intentObj.intent_type), intentResponse, colorValue=SIColors.Khaki)
                return intentResponse

            # load returned info that we care about.
            artist_title:str = search_result.get("result",{}).get("items")[0].get("name", "unknown")
            artist_uri:str = search_result.get("result",{}).get("items")[0].get("uri", "unknown")
            artist_url:str = search_result.get("result",{}).get("items")[0].get("external_urls", {}).get("spotify", SPOTIFY_WEB_URL_PFX)

            # get id portion of spotify uri value.
            artist_id:str = get_id_from_uri(artist_uri)

            # update slots with returned info.
            slots[SLOT_ARTIST_TITLE] = { CONF_TEXT: artist_title, CONF_VALUE: artist_uri }
            slots[SLOT_ARTIST_URL] = { CONF_TEXT: "Spotify", CONF_VALUE: artist_url }

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

                # trace.
                if (self.logsi.IsOn(SILevel.Verbose)):
                    self.logsi.LogDictionary(SILevel.Verbose, STAppMessages.MSG_INTENT_HANDLER_SLOT_INFO % intentObj.intent_type, slots, colorValue=SIColors.Khaki)

                # requested info is not available.
                responseText = await get_intent_response_resource(RESPONSE_SPOTIFY_NO_ARTIST_INFO, slots, intentObj, PLATFORM_SPOTIFYPLUS)
                intentResponse.async_set_speech(responseText)
                self.logsi.LogObject(SILevel.Verbose, STAppMessages.MSG_INTENT_HANDLER_RESPONSE % (intentObj.intent_type), intentResponse, colorValue=SIColors.Khaki)
                return intentResponse

            # update slot info.
            slots[SLOT_ARTIST_BIO] = { CONF_TEXT: artist_bio, CONF_VALUE: "" }

            # trace.
            if (self.logsi.IsOn(SILevel.Verbose)):
                self.logsi.LogDictionary(SILevel.Verbose, STAppMessages.MSG_INTENT_HANDLER_SLOT_INFO % intentObj.intent_type, slots, colorValue=SIColors.Khaki)

            # return intent response.
            intentResponse.speech_slots = slots
            responseText = await get_intent_response_resource(RESPONSE_GET_INFO_ARTIST_BIO, slots, intentObj, PLATFORM_SPOTIFYPLUS)
            intentResponse.async_set_speech(responseText)
            self.logsi.LogObject(SILevel.Verbose, STAppMessages.MSG_INTENT_HANDLER_RESPONSE % (intentObj.intent_type), intentResponse, colorValue=SIColors.Khaki)
            return intentResponse

        except HomeAssistantError: raise  # pass handled exceptions on thru
        except Exception as ex:

            # log exception, but not to system logger as HA will take care of it.
            self.logsi.LogException(STAppMessages.MSG_INTENT_HANDLER_EXCEPTION % (intentObj.intent_type, str(ex)), ex, logToSystemLogger=False, colorValue=SIColors.Khaki)
            raise IntentHandleError("Intent handler error for \"%s\"" % (intentObj.intent_type), RESPONSE_ERROR_UNHANDLED)

        finally:

            # trace.
            self.logsi.LeaveMethod(SILevel.Debug, intentObj.intent_type, colorValue=SIColors.Khaki)
