import voluptuous as vol

from homeassistant.components.media_player import MediaPlayerEntityFeature
from homeassistant.const import (
    STATE_IDLE,
    STATE_OFF,
    STATE_ON,
    STATE_PAUSED,
    STATE_PLAYING,
    STATE_UNKNOWN,
)
from homeassistant.core import State
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.intent import (
    Intent,
    IntentResponse, 
    IntentResponseErrorCode, 
)

from smartinspectpython.siauto import SILevel, SIColors

from ..appmessages import STAppMessages
from ..intent_loader import IntentLoader
from ..const import (
    CONF_VALUE,
    DOMAIN,
    INTENT_PLAYER_DECK_CONTROL,
    PLATFORM_SPOTIFYPLUS,
    RESPONSE_ERROR_PLAYER_DECK_CONTROL_INVALID,
    RESPONSE_PLAYER_ALREADY_PLAYING_MEDIA,
    RESPONSE_PLAYER_DECK_CONTROL_PAUSE,
    RESPONSE_PLAYER_DECK_CONTROL_RESUME,
    RESPONSE_PLAYER_DECK_CONTROL_SEEK_START,
    RESPONSE_PLAYER_DECK_CONTROL_SKIP_NEXT,
    RESPONSE_PLAYER_DECK_CONTROL_SKIP_PREVIOUS,
    RESPONSE_PLAYER_NOT_PLAYING_MEDIA,
    SERVICE_SPOTIFY_PLAYER_MEDIA_PAUSE,
    SERVICE_SPOTIFY_PLAYER_MEDIA_RESUME,
    SERVICE_SPOTIFY_PLAYER_MEDIA_SEEK,
    SERVICE_SPOTIFY_PLAYER_MEDIA_SKIP_NEXT,
    SERVICE_SPOTIFY_PLAYER_MEDIA_SKIP_PREVIOUS,
    SLOT_AREA,
    SLOT_DELAY,
    SLOT_FLOOR,
    SLOT_NAME,
    SLOT_PREFERRED_AREA_ID,
    SLOT_PREFERRED_FLOOR_ID,
    SLOT_SPOTIFYPLUS_PLAYER_DECK_CONTROL,
)

from .spotifyplusintenthandler import SpotifyPlusIntentHandler


class SpotifyPlusPlayerDeckControl_Handler(SpotifyPlusIntentHandler):
    """
    Handles intents for SpotifyPlusPlayerDeckControl.
    """
    def __init__(self, intentLoader:IntentLoader) -> None:
        """
        Initializes a new instance of the IntentHandler class.
        """
        # invoke base class method.
        super().__init__(intentLoader)

        # set intent handler basics.
        self.description = "Controls media player deck functions (pause, resume, next track, previous track, restart track, etc)."
        self.intent_type = INTENT_PLAYER_DECK_CONTROL
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
            vol.Optional(SLOT_SPOTIFYPLUS_PLAYER_DECK_CONTROL): cv.string,
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
        # get optional arguments (if provided).
        player_deck_control:str = intentObj.slots.get(SLOT_SPOTIFYPLUS_PLAYER_DECK_CONTROL, {}).get(CONF_VALUE, "").lower()

        # process based on media type.
        if (player_deck_control == "pause"):
            return await self.async_ProcessPause(intentObj, intentResponse)

        elif (player_deck_control == "resume"):
            return await self.async_ProcessResume(intentObj, intentResponse)

        elif (player_deck_control == "seek_start"):
            return await self.async_ProcessSeekStart(intentObj, intentResponse)

        elif (player_deck_control == "skip_previous"):
            return await self.async_ProcessSkipPrevious(intentObj, intentResponse)

        elif (player_deck_control == "skip_next"):
            return await self.async_ProcessSkipNext(intentObj, intentResponse)

        else:
            return await self.ReturnResponseByKey(intentObj, intentResponse, RESPONSE_ERROR_PLAYER_DECK_CONTROL_INVALID, IntentResponseErrorCode.FAILED_TO_HANDLE)


    async def async_ProcessPause(
        self, 
        intentObj: Intent, 
        intentResponse: IntentResponse,
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
        try:

            # trace.
            self.logsi.EnterMethod(SILevel.Debug, colorValue=SIColors.Khaki)

            # invoke base class method to resolve the player entity and its state.
            playerEntityState:State = await super().async_GetMatchingPlayerState(
                intentObj,
                intentResponse,
                desiredFeatures=MediaPlayerEntityFeature.PAUSE | MediaPlayerEntityFeature.PLAY_MEDIA,
                desiredStates=[STATE_PLAYING],
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
            svcName:str = SERVICE_SPOTIFY_PLAYER_MEDIA_PAUSE
            svcData:dict = \
            {
                "entity_id": playerEntityState.entity_id,
                "device_id": "",  # always use current device for this service call.
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
            return await self.ReturnResponseByKey(intentObj, intentResponse, RESPONSE_PLAYER_DECK_CONTROL_PAUSE)

        finally:

            # trace.
            self.logsi.LeaveMethod(SILevel.Debug, colorValue=SIColors.Khaki)


    async def async_ProcessResume(
        self, 
        intentObj: Intent, 
        intentResponse: IntentResponse,
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
        try:

            # trace.
            self.logsi.EnterMethod(SILevel.Debug, colorValue=SIColors.Khaki)

            # invoke base class method to resolve the player entity and its state.
            playerEntityState:State = await super().async_GetMatchingPlayerState(
                intentObj,
                intentResponse,
                desiredFeatures=MediaPlayerEntityFeature.PAUSE | MediaPlayerEntityFeature.PLAY_MEDIA,
                desiredStates=None,
                desiredStateResponseKey=None,
                requiresSpotifyPremium=True,
            )

            # if media player was not resolved, then we are done;
            # note that the base class method above already called `async_set_speech` with a response.
            if playerEntityState is None:
                return intentResponse

            # if already playing, then there is nothing to do.
            if (playerEntityState.state == STATE_PLAYING):
                return await self.ReturnResponseByKey(intentObj, intentResponse, RESPONSE_PLAYER_ALREADY_PLAYING_MEDIA)
            
            # get optional arguments (if provided).
            delay = intentObj.slots.get(SLOT_DELAY, {}).get(CONF_VALUE, None)

            # set service name and build parameters.
            svcName:str = SERVICE_SPOTIFY_PLAYER_MEDIA_RESUME
            svcData:dict = \
            {
                "entity_id": playerEntityState.entity_id,
                "device_id": "",  # always use current device for this service call.
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
            return await self.ReturnResponseByKey(intentObj, intentResponse, RESPONSE_PLAYER_DECK_CONTROL_RESUME)

        finally:

            # trace.
            self.logsi.LeaveMethod(SILevel.Debug, colorValue=SIColors.Khaki)


    async def async_ProcessSeekStart(
        self, 
        intentObj: Intent, 
        intentResponse: IntentResponse,
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
        try:

            # trace.
            self.logsi.EnterMethod(SILevel.Debug, colorValue=SIColors.Khaki)

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
            return await self.ReturnResponseByKey(intentObj, intentResponse, RESPONSE_PLAYER_DECK_CONTROL_SEEK_START)

        finally:

            # trace.
            self.logsi.LeaveMethod(SILevel.Debug, colorValue=SIColors.Khaki)


    async def async_ProcessSkipNext(
        self, 
        intentObj: Intent, 
        intentResponse: IntentResponse,
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
        try:

            # trace.
            self.logsi.EnterMethod(SILevel.Debug, colorValue=SIColors.Khaki)

            # invoke base class method to resolve the player entity and its state.
            playerEntityState:State = await super().async_GetMatchingPlayerState(
                intentObj,
                intentResponse,
                desiredFeatures=MediaPlayerEntityFeature.NEXT_TRACK | MediaPlayerEntityFeature.PLAY_MEDIA,
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
            svcName:str = SERVICE_SPOTIFY_PLAYER_MEDIA_SKIP_NEXT
            svcData:dict = \
            {
                "entity_id": playerEntityState.entity_id,
                "device_id": "",  # always use current device for this service call.
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
            return await self.ReturnResponseByKey(intentObj, intentResponse, RESPONSE_PLAYER_DECK_CONTROL_SKIP_NEXT)

        finally:

            # trace.
            self.logsi.LeaveMethod(SILevel.Debug, colorValue=SIColors.Khaki)


    async def async_ProcessSkipPrevious(
        self, 
        intentObj: Intent, 
        intentResponse: IntentResponse,
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
        try:

            # trace.
            self.logsi.EnterMethod(SILevel.Debug, colorValue=SIColors.Khaki)

            # invoke base class method to resolve the player entity and its state.
            playerEntityState:State = await super().async_GetMatchingPlayerState(
                intentObj,
                intentResponse,
                desiredFeatures=MediaPlayerEntityFeature.PREVIOUS_TRACK | MediaPlayerEntityFeature.PLAY_MEDIA,
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
            svcName:str = SERVICE_SPOTIFY_PLAYER_MEDIA_SKIP_PREVIOUS
            svcData:dict = \
            {
                "entity_id": playerEntityState.entity_id,
                "device_id": "",  # always use current device for this service call.
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
            return await self.ReturnResponseByKey(intentObj, intentResponse, RESPONSE_PLAYER_DECK_CONTROL_SKIP_PREVIOUS)

        finally:

            # trace.
            self.logsi.LeaveMethod(SILevel.Debug, colorValue=SIColors.Khaki)
