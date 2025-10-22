import voluptuous as vol

from homeassistant.components.media_player import MediaPlayerEntityFeature
from homeassistant.components.media_player.const import (
    ATTR_MEDIA_ALBUM_NAME,
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
    ATTR_SPOTIFYPLUS_CONTEXT_URI,
    ATTR_SPOTIFYPLUS_ITEM_TYPE,
    CONF_TEXT,
    CONF_VALUE,
    INTENT_NOWPLAYING_INFO_PODCAST,
    PLATFORM_SPOTIFYPLUS,
    RESPONSE_NOWPLAYING_INFO_PODCAST,
    RESPONSE_NOWPLAYING_NO_MEDIA_PODCAST,
    RESPONSE_PLAYER_NOT_PLAYING_MEDIA,
    SLOT_AREA,
    SLOT_EPISODE_TITLE,
    SLOT_EPISODE_URL,
    SLOT_FLOOR,
    SLOT_NAME,
    SLOT_PODCAST_TITLE,
    SLOT_PODCAST_URL,
    SLOT_PREFERRED_AREA_ID,
    SLOT_PREFERRED_FLOOR_ID,
    SPOTIFY_WEB_URL_PFX,
)

from .spotifyplusintenthandler import SpotifyPlusIntentHandler


class SpotifyPlusNowPlayingInfoPodcast_Handler(SpotifyPlusIntentHandler):
    """
    Handles intents for SpotifyPlusNowPlayingInfoPodcast.
    """
    def __init__(self, intentLoader:IntentLoader) -> None:
        """
        Initializes a new instance of the IntentHandler class.
        """
        # invoke base class method.
        super().__init__(intentLoader)

        # set intent handler basics.
        self.description = "Queries media player state for currently playing podcast episode information."
        self.intent_type = INTENT_NOWPLAYING_INFO_PODCAST
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
            vol.Optional(SLOT_PODCAST_TITLE): cv.string,
            vol.Optional(SLOT_PODCAST_URL): cv.string,
            vol.Optional(SLOT_EPISODE_TITLE): cv.string,
            vol.Optional(SLOT_EPISODE_URL): cv.string,
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

        # is now playing item a podcast episode? if not, then don't bother.
        item_type:str = playerEntityState.attributes.get(ATTR_SPOTIFYPLUS_ITEM_TYPE)
        if (item_type != SpotifyMediaTypes.PODCAST.value):
            return await self.ReturnResponseByKey(intentObj, intentResponse, RESPONSE_NOWPLAYING_NO_MEDIA_PODCAST)

        # get now playing details.
        podcast_name:str = playerEntityState.attributes.get(ATTR_MEDIA_ALBUM_NAME)
        podcast_uri:str = playerEntityState.attributes.get(ATTR_SPOTIFYPLUS_CONTEXT_URI)
        episode_name:str = playerEntityState.attributes.get(ATTR_MEDIA_TITLE)
        episode_uri:str = playerEntityState.attributes.get(ATTR_MEDIA_CONTENT_ID)

        # get id portion of spotify uri value.
        podcast_id:str = get_id_from_uri(podcast_uri)
        episode_id:str = get_id_from_uri(episode_uri)

        # update slots with returned info.
        intentObj.slots[SLOT_PODCAST_TITLE] = { CONF_TEXT: podcast_name, CONF_VALUE: podcast_uri }
        intentObj.slots[SLOT_PODCAST_URL] = { CONF_TEXT: "Spotify", CONF_VALUE: f"{SPOTIFY_WEB_URL_PFX}/{SpotifyMediaTypes.SHOW.value}/{podcast_id}" }
        intentObj.slots[SLOT_EPISODE_TITLE] = { CONF_TEXT: episode_name, CONF_VALUE: episode_uri }
        intentObj.slots[SLOT_EPISODE_URL] = { CONF_TEXT: "Spotify", CONF_VALUE: f"{SPOTIFY_WEB_URL_PFX}/{SpotifyMediaTypes.EPISODE.value}/{episode_id}" }

        # return intent response.
        return await self.ReturnResponseByKey(intentObj, intentResponse, RESPONSE_NOWPLAYING_INFO_PODCAST)
