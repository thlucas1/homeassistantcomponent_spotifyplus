import voluptuous as vol

from homeassistant.components.media_player import MediaPlayerEntityFeature
from homeassistant.components.media_player.const import (
    ATTR_MEDIA_ARTIST,
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
    ATTR_SPOTIFYPLUS_ARTIST_URI,
    CONF_TEXT,
    CONF_VALUE,
    DOMAIN,
    INTENT_FAVORITE_ARTIST_ADD,
    PLATFORM_SPOTIFYPLUS,
    RESPONSE_NOWPLAYING_NO_MEDIA_ARTIST,
    RESPONSE_PLAYER_NOT_PLAYING_MEDIA,
    SERVICE_SPOTIFY_FOLLOW_ARTISTS,
    SLOT_AREA,
    SLOT_ARTIST_TITLE,
    SLOT_ARTIST_URL,
    SLOT_FLOOR,
    SLOT_NAME,
    SLOT_PREFERRED_AREA_ID,
    SLOT_PREFERRED_FLOOR_ID,
    SPOTIFY_WEB_URL_PFX,
)

from .spotifyplusintenthandler import SpotifyPlusIntentHandler


class SpotifyPlusFavoriteArtistAdd_Handler(SpotifyPlusIntentHandler):
    """
    Handles intents for SpotifyPlusFavoriteArtistAdd.
    """
    def __init__(self, intentLoader:IntentLoader) -> None:
        """
        Initializes a new instance of the IntentHandler class.
        """
        # invoke base class method.
        super().__init__(intentLoader)

        # set intent handler basics.
        self.description = "Adds the currently playing track artist to Spotify user artist favorites."
        self.intent_type = INTENT_FAVORITE_ARTIST_ADD
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
            desiredStates=[STATE_PLAYING, STATE_PAUSED],
            desiredStateResponseKey=RESPONSE_PLAYER_NOT_PLAYING_MEDIA,
        )

        # if media player was not resolved, then we are done;
        # note that the base class method above already called `async_set_speech` with a response.
        if playerEntityState is None:
            return intentResponse
            
        # get optional arguments (if provided).
        # n/a

        # is now playing item a track? if not, then we are done.
        item_type:str = playerEntityState.attributes.get(ATTR_SPOTIFYPLUS_ITEM_TYPE)
        if (item_type != SpotifyMediaTypes.TRACK.value):
            return await self.ReturnResponseByKey(intentObj, intentResponse, RESPONSE_NOWPLAYING_NO_MEDIA_ARTIST)

        # get now playing details.
        artist_name:str = playerEntityState.attributes.get(ATTR_MEDIA_ARTIST)
        artist_uri:str = playerEntityState.attributes.get(ATTR_SPOTIFYPLUS_ARTIST_URI)

        # get id portion of spotify uri value.
        artist_id:str = get_id_from_uri(artist_uri)

        # update slots with returned info.
        intentObj.slots[SLOT_ARTIST_TITLE] = { CONF_TEXT: artist_name, CONF_VALUE: artist_uri }
        intentObj.slots[SLOT_ARTIST_URL] = { CONF_TEXT: "Spotify", CONF_VALUE: f"{SPOTIFY_WEB_URL_PFX}/{SpotifyMediaTypes.ARTIST.value}/{artist_id}" }

        # trace.
        if (self.logsi.IsOn(SILevel.Verbose)):
            self.logsi.LogDictionary(SILevel.Verbose, STAppMessages.MSG_INTENT_HANDLER_SLOT_INFO % intentObj.intent_type, intentObj.slots, colorValue=SIColors.Khaki)

        # set service name and build parameters.
        svcName:str = SERVICE_SPOTIFY_FOLLOW_ARTISTS
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
