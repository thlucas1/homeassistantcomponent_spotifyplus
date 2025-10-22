import voluptuous as vol

from homeassistant.components.media_player import MediaPlayerEntityFeature
from homeassistant.components.media_player.const import (
    ATTR_MEDIA_ALBUM_NAME,
    ATTR_MEDIA_ARTIST,
    ATTR_MEDIA_CONTENT_ID,
    ATTR_MEDIA_TITLE,
)
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

from spotifywebapipython.spotifymediatypes import SpotifyMediaTypes

from ..appmessages import STAppMessages
from ..intent_loader import IntentLoader
from ..utils import get_id_from_uri
from ..const import (
    ATTR_SPOTIFYPLUS_ITEM_TYPE,
    ATTR_SPOTIFYPLUS_CONTEXT_URI,
    CONF_TEXT,
    CONF_VALUE,
    INTENT_NOWPLAYING_INFO_AUDIOBOOK,
    PLATFORM_SPOTIFYPLUS,
    RESPONSE_NOWPLAYING_INFO_AUDIOBOOK,
    RESPONSE_NOWPLAYING_NO_MEDIA_AUDIOBOOK,
    RESPONSE_PLAYER_NOT_PLAYING_MEDIA,
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


class SpotifyPlusNowPlayingInfoAudiobook_Handler(SpotifyPlusIntentHandler):
    """
    Handles intents for SpotifyPlusNowPlayingInfoAudiobook.
    """
    def __init__(self, intentLoader:IntentLoader) -> None:
        """
        Initializes a new instance of the IntentHandler class.
        """
        # invoke base class method.
        super().__init__(intentLoader)

        # set intent handler basics.
        self.description = "Queries media player state for currently playing audiobook information."
        self.intent_type = INTENT_NOWPLAYING_INFO_AUDIOBOOK
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

        # is now playing item an audiobook? if not, then don't bother.
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
        intentObj.slots[SLOT_AUDIOBOOK_TITLE] = { CONF_TEXT: audiobook_name, CONF_VALUE: audiobook_uri }
        intentObj.slots[SLOT_AUDIOBOOK_URL] = { CONF_TEXT: "Spotify", CONF_VALUE: f"{SPOTIFY_WEB_URL_PFX}/{SpotifyMediaTypes.SHOW.value}/{audiobook_id}" }
        intentObj.slots[SLOT_AUTHOR_TITLE] = { CONF_TEXT: author_name, CONF_VALUE: "" }
        intentObj.slots[SLOT_CHAPTER_TITLE] = { CONF_TEXT: chapter_name, CONF_VALUE: chapter_uri }

        # return intent response.
        return await self.ReturnResponseByKey(intentObj, intentResponse, RESPONSE_NOWPLAYING_INFO_AUDIOBOOK)
