import voluptuous as vol

from homeassistant.components.media_player import MediaPlayerEntityFeature
from homeassistant.components.media_player.const import (
    ATTR_MEDIA_ALBUM_NAME,
    ATTR_MEDIA_ARTIST,
    ATTR_MEDIA_CONTENT_ID,
    ATTR_MEDIA_TITLE,
)
from homeassistant.const import (
    STATE_PAUSED,
    STATE_PLAYING,
)
from homeassistant.core import State
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
    ATTR_SPOTIFYPLUS_ITEM_TYPE,
    ATTR_SPOTIFYPLUS_CONTEXT_URI,
    CONF_TEXT,
    CONF_VALUE,
    DOMAIN,
    INTENT_FAVORITE_AUDIOBOOK_ADD,
    PLATFORM_SPOTIFYPLUS,
    RESPONSE_NOWPLAYING_NO_MEDIA_AUDIOBOOK,
    RESPONSE_PLAYER_NOT_PLAYING_MEDIA,
    SERVICE_SPOTIFY_SAVE_AUDIOBOOK_FAVORITES,
    SLOT_AREA,
    SLOT_AUDIOBOOK_TITLE,
    SLOT_AUDIOBOOK_URL,
    SLOT_AUTHOR_TITLE,
    SLOT_CHAPTER_TITLE,
    SLOT_FLOOR,
    SLOT_NAME,
    SLOT_PREFERRED_AREA_ID,
    SLOT_PREFERRED_FLOOR_ID,
    SPOTIFY_WEB_URL_PFX,
)

from .spotifyplusintenthandler import SpotifyPlusIntentHandler


class SpotifyPlusFavoriteAudiobookAdd_Handler(SpotifyPlusIntentHandler):
    """
    Handles intents for SpotifyPlusFavoriteAudiobookAdd.
    """
    def __init__(self, intentLoader:IntentLoader) -> None:
        """
        Initializes a new instance of the IntentHandler class.
        """
        # invoke base class method.
        super().__init__(intentLoader)

        # set intent handler basics.
        self.description = "Adds the currently playing audiobook to Spotify user audiobook favorites."
        self.intent_type = INTENT_FAVORITE_AUDIOBOOK_ADD
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
            vol.Optional(SLOT_AUDIOBOOK_TITLE): cv.string,
            vol.Optional(SLOT_AUDIOBOOK_URL): cv.string,
            vol.Optional(SLOT_AUTHOR_TITLE): cv.string,
            vol.Optional(SLOT_CHAPTER_TITLE): cv.string,
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
            desiredStates=[STATE_PLAYING, STATE_PAUSED],
            desiredStateResponseKey=RESPONSE_PLAYER_NOT_PLAYING_MEDIA,
        )

        # if media player was not resolved, then we are done;
        # note that the base class method above already called `async_set_speech` with a response.
        if playerEntityState is None:
            return intentResponse
            
        # get optional arguments (if provided).
        # n/a

        # is now playing item an audiobook? if not, then we are done.
        item_type:str = playerEntityState.attributes.get(ATTR_SPOTIFYPLUS_ITEM_TYPE)
        if (item_type != SpotifyMediaTypes.AUDIOBOOK.value):
            return await self.ReturnResponseByKey(intentObj, intentResponse, RESPONSE_NOWPLAYING_NO_MEDIA_AUDIOBOOK)

        # get now playing details.
        audiobook_uri:str = playerEntityState.attributes.get(ATTR_SPOTIFYPLUS_CONTEXT_URI)
        audiobook_name:str = playerEntityState.attributes.get(ATTR_MEDIA_ALBUM_NAME)
        author_name:str = playerEntityState.attributes.get(ATTR_MEDIA_ARTIST)
        chapter_uri:str = playerEntityState.attributes.get(ATTR_MEDIA_CONTENT_ID)
        chapter_name:str = playerEntityState.attributes.get(ATTR_MEDIA_TITLE)

        # get id portion of spotify uri value.
        audiobook_id:str = get_id_from_uri(audiobook_uri)

        # update slots with returned info.
        intentObj.slots[SLOT_AUDIOBOOK_TITLE] = { CONF_VALUE: audiobook_uri, CONF_TEXT: audiobook_name }
        intentObj.slots[SLOT_AUDIOBOOK_URL] = { CONF_VALUE: f"{SPOTIFY_WEB_URL_PFX}/{SpotifyMediaTypes.SHOW.value}/{audiobook_id}", CONF_TEXT: "Spotify" }
        intentObj.slots[SLOT_AUTHOR_TITLE] = { CONF_VALUE: "", CONF_TEXT: author_name }
        intentObj.slots[SLOT_CHAPTER_TITLE] = { CONF_VALUE: chapter_uri, CONF_TEXT: chapter_name }

        # trace.
        if (self.logsi.IsOn(SILevel.Verbose)):
            self.logsi.LogDictionary(SILevel.Verbose, STAppMessages.MSG_INTENT_HANDLER_SLOT_INFO % intentObj.intent_type, intentObj.slots, colorValue=SIColors.Khaki)

        # set service name and build parameters.
        svcName:str = SERVICE_SPOTIFY_SAVE_AUDIOBOOK_FAVORITES
        svcData:dict = \
        {
            "entity_id": playerEntityState.entity_id,
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
           
        # trace.
        if (self.logsi.IsOn(SILevel.Verbose)):
            self.logsi.LogDictionary(SILevel.Verbose, STAppMessages.MSG_INTENT_HANDLER_SLOT_INFO % intentObj.intent_type, intentObj.slots, colorValue=SIColors.Khaki)

        # return intent response.
        intentResponse.speech_slots = intentObj.slots
        self.logsi.LogObject(SILevel.Verbose, STAppMessages.MSG_INTENT_HANDLER_RESPONSE % (intentObj.intent_type), intentResponse, colorValue=SIColors.Khaki)
        return intentResponse
