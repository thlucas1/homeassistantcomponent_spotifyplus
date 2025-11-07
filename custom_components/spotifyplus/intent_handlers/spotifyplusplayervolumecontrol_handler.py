import voluptuous as vol

from homeassistant.components.media_player import MediaPlayerEntityFeature
from homeassistant.const import (
    SERVICE_VOLUME_DOWN,
    SERVICE_VOLUME_MUTE,
    SERVICE_VOLUME_UP,
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
    CONF_TEXT,
    CONF_VALUE,
    DOMAIN,
    DOMAIN_MEDIA_PLAYER,
    INTENT_PLAYER_VOLUME_CONTROL,
    PLATFORM_SPOTIFYPLUS,
    RESPONSE_ERROR_PLAYER_VOLUME_CONTROL_INVALID,
    RESPONSE_PLAYER_VOLUME_CONTROL_DOWN,
    RESPONSE_PLAYER_VOLUME_CONTROL_MUTE,
    RESPONSE_PLAYER_VOLUME_CONTROL_SET_STEP_LEVEL,
    RESPONSE_PLAYER_VOLUME_CONTROL_SET_LEVEL,
    RESPONSE_PLAYER_VOLUME_CONTROL_UNMUTE,
    RESPONSE_PLAYER_VOLUME_CONTROL_UP,
    SERVICE_SPOTIFY_PLAYER_SET_VOLUME_LEVEL,
    SERVICE_VOLUME_SET_STEP,
    SLOT_AREA,
    SLOT_DELAY,
    SLOT_FLOOR,
    SLOT_NAME,
    SLOT_PLAYER_VOLUME_LEVEL_PCT,
    SLOT_PLAYER_VOLUME_STEP_PCT,
    SLOT_PREFERRED_AREA_ID,
    SLOT_PREFERRED_FLOOR_ID,
    SLOT_SPOTIFYPLUS_PLAYER_VOLUME_CONTROL,
)

from .spotifyplusintenthandler import SpotifyPlusIntentHandler


class SpotifyPlusPlayerVolumeControl_Handler(SpotifyPlusIntentHandler):
    """
    Handles intents for SpotifyPlusPlayerVolumeControl.
    """
    def __init__(self, intentLoader:IntentLoader) -> None:
        """
        Initializes a new instance of the IntentHandler class.
        """
        # invoke base class method.
        super().__init__(intentLoader)

        # set intent handler basics.
        self.description = "Controls media player volume functions (mute, unmute, step up, step down, etc)."
        self.intent_type = INTENT_PLAYER_VOLUME_CONTROL
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
            vol.Optional(SLOT_SPOTIFYPLUS_PLAYER_VOLUME_CONTROL): cv.string,
            vol.Optional(SLOT_PLAYER_VOLUME_LEVEL_PCT, default=10): vol.Any(None, vol.All(vol.Coerce(int), vol.Range(min=0, max=100))),
            vol.Optional(SLOT_PLAYER_VOLUME_STEP_PCT, default=10): vol.Any(None, vol.All(vol.Coerce(int), vol.Range(min=1, max=100))),
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
        player_volume_control:str = intentObj.slots.get(SLOT_SPOTIFYPLUS_PLAYER_VOLUME_CONTROL, {}).get(CONF_VALUE, "").lower()

        # process based on media type.
        if (player_volume_control == "mute"):
            return await self.async_ProcessMute(intentObj, intentResponse)

        elif (player_volume_control == "unmute"):
            return await self.async_ProcessUnMute(intentObj, intentResponse)

        elif (player_volume_control == "step_down"):
            return await self.async_ProcessStepDown(intentObj, intentResponse)

        elif (player_volume_control == "step_up"):
            return await self.async_ProcessStepUp(intentObj, intentResponse)

        elif (player_volume_control == "set_step_level"):
            return await self.async_ProcessSetStepLevel(intentObj, intentResponse)

        elif (player_volume_control == "set_level"):
            return await self.async_ProcessSetLevel(intentObj, intentResponse)

        else:
            return await self.ReturnResponseByKey(intentObj, intentResponse, RESPONSE_ERROR_PLAYER_VOLUME_CONTROL_INVALID, IntentResponseErrorCode.FAILED_TO_HANDLE)


    async def async_ProcessMute(
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
                desiredFeatures=MediaPlayerEntityFeature.VOLUME_MUTE | MediaPlayerEntityFeature.PLAY_MEDIA,
                desiredStates=None,
                desiredStateResponseKey=None,
                requiresSpotifyPremium=True,
            )

            # if media player was not resolved, then we are done;
            # note that the base class method above already called `async_set_speech` with a response.
            if playerEntityState is None:
                return intentResponse
            
            # set service name and build parameters.
            svcName:str = SERVICE_VOLUME_MUTE
            svcData:dict = \
            {
                "entity_id": playerEntityState.entity_id,
                "is_volume_muted": True
            }

            # call integration service for this intent.
            self.logsi.LogVerbose(STAppMessages.MSG_SERVICE_EXECUTE % (svcName, playerEntityState.entity_id), colorValue=SIColors.Khaki)
            await intentObj.hass.services.async_call(
                DOMAIN_MEDIA_PLAYER,
                svcName,
                svcData,
                blocking=True,
                context=intentObj.context,
            )

            # return intent response.
            return await self.ReturnResponseByKey(intentObj, intentResponse, RESPONSE_PLAYER_VOLUME_CONTROL_MUTE)

        finally:

            # trace.
            self.logsi.LeaveMethod(SILevel.Debug, colorValue=SIColors.Khaki)


    async def async_ProcessUnMute(
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
                desiredFeatures=MediaPlayerEntityFeature.VOLUME_MUTE | MediaPlayerEntityFeature.PLAY_MEDIA,
                desiredStates=None,
                desiredStateResponseKey=None,
                requiresSpotifyPremium=True,
            )

            # if media player was not resolved, then we are done;
            # note that the base class method above already called `async_set_speech` with a response.
            if playerEntityState is None:
                return intentResponse
            
            # get optional arguments (if provided).
            # n/a

            # set service name and build parameters.
            svcName:str = SERVICE_VOLUME_MUTE
            svcData:dict = \
            {
                "entity_id": playerEntityState.entity_id,
                "is_volume_muted": False
            }

            # call integration service for this intent.
            self.logsi.LogVerbose(STAppMessages.MSG_SERVICE_EXECUTE % (svcName, playerEntityState.entity_id), colorValue=SIColors.Khaki)
            await intentObj.hass.services.async_call(
                DOMAIN_MEDIA_PLAYER,
                svcName,
                svcData,
                blocking=True,
                context=intentObj.context,
            )
           
            # return intent response.
            return await self.ReturnResponseByKey(intentObj, intentResponse, RESPONSE_PLAYER_VOLUME_CONTROL_UNMUTE)

        finally:

            # trace.
            self.logsi.LeaveMethod(SILevel.Debug, colorValue=SIColors.Khaki)


    async def async_ProcessStepDown(
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
                desiredFeatures=MediaPlayerEntityFeature.VOLUME_STEP | MediaPlayerEntityFeature.PLAY_MEDIA,
                desiredStates=None,
                desiredStateResponseKey=None,
                requiresSpotifyPremium=True,
            )

            # if media player was not resolved, then we are done;
            # note that the base class method above already called `async_set_speech` with a response.
            if playerEntityState is None:
                return intentResponse

            # get current step level from player attributes and update slot.
            player_volume_step_pct_default = int(intentObj.slots.get(SLOT_PLAYER_VOLUME_STEP_PCT, {}).get(CONF_VALUE, 10))
            player_volume_step = float(playerEntityState.attributes.get("volume_step", player_volume_step_pct_default / 100))
            player_volume_step_pct = int(player_volume_step * 100)
            intentObj.slots[SLOT_PLAYER_VOLUME_STEP_PCT] = { CONF_VALUE: player_volume_step_pct, CONF_TEXT: player_volume_step_pct }
            
            # set service name and build parameters.
            svcName:str = SERVICE_VOLUME_DOWN
            svcData:dict = \
            {
                "entity_id": playerEntityState.entity_id,
            }

            # call integration service for this intent.
            self.logsi.LogVerbose(STAppMessages.MSG_SERVICE_EXECUTE % (svcName, playerEntityState.entity_id), colorValue=SIColors.Khaki)
            await intentObj.hass.services.async_call(
                DOMAIN_MEDIA_PLAYER,
                svcName,
                svcData,
                blocking=True,
                context=intentObj.context,
            )
          
            # return intent response.
            return await self.ReturnResponseByKey(intentObj, intentResponse, RESPONSE_PLAYER_VOLUME_CONTROL_DOWN)

        finally:

            # trace.
            self.logsi.LeaveMethod(SILevel.Debug, colorValue=SIColors.Khaki)


    async def async_ProcessStepUp(
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
                desiredFeatures=MediaPlayerEntityFeature.VOLUME_STEP | MediaPlayerEntityFeature.PLAY_MEDIA,
                desiredStates=None,
                desiredStateResponseKey=None,
                requiresSpotifyPremium=True,
            )

            # if media player was not resolved, then we are done;
            # note that the base class method above already called `async_set_speech` with a response.
            if playerEntityState is None:
                return intentResponse
            
            # get current step level from player attributes and update slot.
            player_volume_step_pct_default = int(intentObj.slots.get(SLOT_PLAYER_VOLUME_STEP_PCT, {}).get(CONF_VALUE, 10))
            player_volume_step = float(playerEntityState.attributes.get("volume_step", player_volume_step_pct_default / 100))
            player_volume_step_pct = int(player_volume_step * 100)
            intentObj.slots[SLOT_PLAYER_VOLUME_STEP_PCT] = { CONF_VALUE: player_volume_step_pct, CONF_TEXT: player_volume_step_pct }
            
            # set service name and build parameters.
            svcName:str = SERVICE_VOLUME_UP
            svcData:dict = \
            {
                "entity_id": playerEntityState.entity_id,
            }

            # call integration service for this intent.
            self.logsi.LogVerbose(STAppMessages.MSG_SERVICE_EXECUTE % (svcName, playerEntityState.entity_id), colorValue=SIColors.Khaki)
            await intentObj.hass.services.async_call(
                DOMAIN_MEDIA_PLAYER,
                svcName,
                svcData,
                blocking=True,
                context=intentObj.context,
            )
           
            # return intent response.
            return await self.ReturnResponseByKey(intentObj, intentResponse, RESPONSE_PLAYER_VOLUME_CONTROL_UP)

        finally:

            # trace.
            self.logsi.LeaveMethod(SILevel.Debug, colorValue=SIColors.Khaki)


    async def async_ProcessSetStepLevel(
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
                desiredFeatures=MediaPlayerEntityFeature.VOLUME_STEP,
                desiredStates=None,
                desiredStateResponseKey=None,
                requiresSpotifyPremium=True,
            )

            # if media player was not resolved, then we are done;
            # note that the base class method above already called `async_set_speech` with a response.
            if playerEntityState is None:
                return intentResponse
            
            # get optional arguments (if provided).
            player_volume_step_pct = intentObj.slots.get(SLOT_PLAYER_VOLUME_STEP_PCT, {}).get(CONF_VALUE, 10)

            # set service name and build parameters.
            svcName:str = SERVICE_VOLUME_SET_STEP
            svcData:dict = \
            {
                "entity_id": playerEntityState.entity_id,
                "level_percent": player_volume_step_pct,
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
            return await self.ReturnResponseByKey(intentObj, intentResponse, RESPONSE_PLAYER_VOLUME_CONTROL_SET_STEP_LEVEL)

        finally:

            # trace.
            self.logsi.LeaveMethod(SILevel.Debug, colorValue=SIColors.Khaki)


    async def async_ProcessSetLevel(
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
                desiredFeatures=MediaPlayerEntityFeature.VOLUME_SET | MediaPlayerEntityFeature.PLAY_MEDIA,
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
            player_volume_level_pct = intentObj.slots.get(SLOT_PLAYER_VOLUME_LEVEL_PCT, {}).get(CONF_VALUE, "on")

            # set service name and build parameters.
            svcName:str = SERVICE_SPOTIFY_PLAYER_SET_VOLUME_LEVEL
            svcData:dict = \
            {
                "entity_id": playerEntityState.entity_id,
                "volume_level": player_volume_level_pct,
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
            return await self.ReturnResponseByKey(intentObj, intentResponse, RESPONSE_PLAYER_VOLUME_CONTROL_SET_LEVEL)

        finally:

            # trace.
            self.logsi.LeaveMethod(SILevel.Debug, colorValue=SIColors.Khaki)
