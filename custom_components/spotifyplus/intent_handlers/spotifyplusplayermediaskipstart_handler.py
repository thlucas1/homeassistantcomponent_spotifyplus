import voluptuous as vol

from homeassistant.components.media_player import MediaPlayerEntityFeature
from homeassistant.core import State
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.intent import (
    Intent,
    IntentResponse, 
)
from homeassistant.const import (
    STATE_PAUSED,
    STATE_PLAYING,
)

from smartinspectpython.siauto import SILevel, SIColors

from ..appmessages import STAppMessages
from ..intent_loader import IntentLoader
from ..const import (
    CONF_VALUE,
    DOMAIN,
    INTENT_PLAYER_MEDIA_SKIP_START,
    PLATFORM_SPOTIFYPLUS,
    RESPONSE_PLAYER_NOT_PLAYING_MEDIA,
    SERVICE_SPOTIFY_PLAYER_MEDIA_SEEK,
    SLOT_AREA,
    SLOT_DELAY,
    SLOT_FLOOR,
    SLOT_NAME,
    SLOT_PREFERRED_AREA_ID,
    SLOT_PREFERRED_FLOOR_ID,
)

from .spotifyplusintenthandler import SpotifyPlusIntentHandler


class SpotifyPlusPlayerMediaSkipStart_Handler(SpotifyPlusIntentHandler):
    """
    Handles intents for SpotifyPlusPlayerMediaSkipStart.
    """
    def __init__(self, intentLoader:IntentLoader) -> None:
        """
        Initializes a new instance of the IntentHandler class.
        """
        # invoke base class method.
        super().__init__(intentLoader)

        # set intent handler basics.
        self.description = "Restarts the currently playing track for the specified SpotifyPlus media player."
        self.intent_type = INTENT_PLAYER_MEDIA_SKIP_START
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
            vol.Optional(SLOT_DELAY, default=0.50): vol.Any(None, vol.All(vol.Coerce(float), vol.Range(min=0, max=10.0)))
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
            desiredFeatures=MediaPlayerEntityFeature.SEEK | MediaPlayerEntityFeature.PLAY_MEDIA,
            desiredStates=[STATE_PLAYING, STATE_PAUSED],
            desiredStateResponseKey=RESPONSE_PLAYER_NOT_PLAYING_MEDIA,
            requiresSpotifyPremium=True,
        )

        # if media player was not resolved, then we are done;
        # note that the base class method above already called `async_set_speech` with a response.
        if playerEntityState is None:
            return intentResponse
            
        # get optional arguments (if provided).
        delay = intentObj.slots.get(SLOT_DELAY, {}).get(CONF_VALUE, None)

        # set service name and build parameters.
        svcName:str = SERVICE_SPOTIFY_PLAYER_MEDIA_SEEK
        svcData:dict = \
        {
            "entity_id": playerEntityState.entity_id,
            "device_id": "",  # always use current device for this service call.
            "position_ms": 0, # restart track
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
        intentResponse.speech_slots = intentObj.slots
        self.logsi.LogObject(SILevel.Verbose, STAppMessages.MSG_INTENT_HANDLER_RESPONSE % (intentObj.intent_type), intentResponse, colorValue=SIColors.Khaki)
        return intentResponse
