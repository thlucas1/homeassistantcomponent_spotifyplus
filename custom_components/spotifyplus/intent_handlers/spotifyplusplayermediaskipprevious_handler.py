
import voluptuous as vol

from homeassistant.components.media_player import MediaPlayerEntityFeature
from homeassistant.core import State
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import intent
from homeassistant.helpers.intent import (
    IntentHandleError,
    IntentResponse, 
    _SlotsType,
)
from homeassistant.const import (
    STATE_PAUSED,
    STATE_PLAYING,
)

from smartinspectpython.siauto import SILevel, SIColors

from ..appmessages import STAppMessages
from ..const import (
    CONF_AREA,
    CONF_DEVICE_NAME,
    CONF_FLOOR,
    CONF_NAME,
    CONF_VALUE,
    DOMAIN,
    PLATFORM_SPOTIFYPLUS,
    INTENT_PLAYER_MEDIA_SKIP_PREVIOUS,
    RESPONSE_ERROR_UNHANDLED,
    RESPONSE_PLAYER_NOT_PLAYING_MEDIA,
    SERVICE_SPOTIFY_PLAYER_MEDIA_SKIP_PREVIOUS,
)

from .spotifyplusintenthandler import SpotifyPlusIntentHandler


class SpotifyPlusPlayerMediaSkipPrevious_Handler(SpotifyPlusIntentHandler):
    """
    Handles intents for SpotifyPlusPlayerMediaSkipPrevious.
    """
    def __init__(self) -> None:
        """
        Initializes a new instance of the IntentHandler class.
        """
        # invoke base class method.
        super().__init__()

        # set intent handler basics.
        self.description = "Skips to previous track in the user's queue for the specified SpotifyPlus media player."
        self.intent_type = INTENT_PLAYER_MEDIA_SKIP_PREVIOUS
        self.platforms = {PLATFORM_SPOTIFYPLUS}


    @property
    def slot_schema(self) -> dict | None:
        """
        Returns the slot schema for this intent.
        """
        return {

            # slots that determine which media player entity will be used.
            vol.Optional(CONF_NAME): cv.string,
            vol.Optional(CONF_AREA): cv.string,
            vol.Optional(CONF_FLOOR): cv.string,
            vol.Optional("preferred_area_id"): cv.string,
            vol.Optional("preferred_floor_id"): cv.string,

            # slots for other service arguments.
            vol.Optional(CONF_DEVICE_NAME, description="Spotify Connect device name or id"): vol.Any(None, cv.string),
            vol.Optional("delay", default=0.50): vol.Any(None, vol.All(vol.Coerce(float), vol.Range(min=0, max=10.0)))
        }


    #async def async_handle(self, intentObj) -> IntentResponse:
    async def async_handle(self, intentObj: intent.Intent) -> IntentResponse:    # <- "intent.Intent" causes circular reference!
        """
        Handles the intent.

        Args:
            intentObj (?):
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
                desiredFeatures=MediaPlayerEntityFeature.PREVIOUS_TRACK | MediaPlayerEntityFeature.PLAY_MEDIA,
                desiredStates=[STATE_PLAYING, STATE_PAUSED],
                desiredStateResponseKey=RESPONSE_PLAYER_NOT_PLAYING_MEDIA,
            )

            # if media player was not resolved, then we are done;
            # note that the base class method above already called `async_set_speech` with a response.
            if playerEntityState is None:
                return intentResponse
            
            # get optional arguments (if provided).
            device_name = slots.get(CONF_DEVICE_NAME, {}).get(CONF_VALUE, None)
            delay = slots.get("delay", {}).get(CONF_VALUE, None)

            # set service name and build parameters.
            svcName:str = SERVICE_SPOTIFY_PLAYER_MEDIA_SKIP_PREVIOUS
            svcData:dict = \
            {
                "entity_id": playerEntityState.entity_id,
                "device_id": device_name,
                "delay": delay
            }

            # call integration service for this intent.
            self.logsi.LogVerbose(STAppMessages.MSG_SERVICE_EXECUTE % (svcName, playerEntityState.entity_id), colorValue=SIColors.Khaki)
            await intentObj.hass.services.async_call(
                DOMAIN,
                svcName,
                svcData,
                blocking=True,
                context=intentObj.context,
            )

            # return intent response.
            intentResponse.speech_slots = slots
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
