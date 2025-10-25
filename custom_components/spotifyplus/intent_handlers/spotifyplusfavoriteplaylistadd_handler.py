import voluptuous as vol

from homeassistant.components.media_player import MediaPlayerEntityFeature
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
    ATTR_SPOTIFYPLUS_CONTEXT_URI,
    ATTR_SPOTIFYPLUS_PLAYLIST_NAME,
    ATTR_SPOTIFYPLUS_PLAYLIST_URI,
    CONF_TEXT,
    CONF_VALUE,
    DOMAIN,
    INTENT_FAVORITE_PLAYLIST_ADD,
    PLATFORM_SPOTIFYPLUS,
    RESPONSE_NOWPLAYING_NO_MEDIA_PLAYLIST,
    RESPONSE_PLAYER_NOT_PLAYING_MEDIA,
    SERVICE_SPOTIFY_FOLLOW_PLAYLIST,
    SLOT_AREA,
    SLOT_FLOOR,
    SLOT_IS_PUBLIC,
    SLOT_NAME,
    SLOT_PLAYLIST_TITLE,
    SLOT_PLAYLIST_URL,
    SLOT_PREFERRED_AREA_ID,
    SLOT_PREFERRED_FLOOR_ID,
    SPOTIFY_WEB_URL_PFX,
)

from .spotifyplusintenthandler import SpotifyPlusIntentHandler


class SpotifyPlusFavoritePlaylistAdd_Handler(SpotifyPlusIntentHandler):
    """
    Handles intents for SpotifyPlusFavoritePlaylistAdd.
    """
    def __init__(self, intentLoader:IntentLoader) -> None:
        """
        Initializes a new instance of the IntentHandler class.
        """
        # invoke base class method.
        super().__init__(intentLoader)

        # set intent handler basics.
        self.description = "Adds the currently playing playlist to Spotify user playlist favorites."
        self.intent_type = INTENT_FAVORITE_PLAYLIST_ADD
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
            vol.Optional(SLOT_PLAYLIST_TITLE): cv.string,
            vol.Optional(SLOT_PLAYLIST_URL): cv.string,
            vol.Optional(SLOT_IS_PUBLIC): cv.boolean,
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
        is_public = intentObj.slots.get(SLOT_IS_PUBLIC, {}).get(CONF_VALUE, True)

        # is now playing item a playlist (e.g. spotify:playlist:x)? if not, then we are done.
        item_type:str = playerEntityState.attributes.get(ATTR_SPOTIFYPLUS_CONTEXT_URI)
        if (item_type is None) or (item_type.find(SpotifyMediaTypes.PLAYLIST.value) == -1):
            return await self.ReturnResponseByKey(intentObj, intentResponse, RESPONSE_NOWPLAYING_NO_MEDIA_PLAYLIST)

        # get now playing details.
        playlist_name:str = playerEntityState.attributes.get(ATTR_SPOTIFYPLUS_PLAYLIST_NAME)
        playlist_uri:str = playerEntityState.attributes.get(ATTR_SPOTIFYPLUS_PLAYLIST_URI)

        # if playlist name is "unknown", then it's probably a Spotify generated list; if so
        # then we will indicate this to the user.  Note that the favorite will be shown in 
        # the Spotify Favorites with the correct name (e.g. "Daily Mix 01").
        if ((playlist_name or "").lower() == "unknown"):
            playlist_name = "Spotify Algorithmic Playlist"

        # get id portion of spotify uri value.
        playlist_id:str = get_id_from_uri(playlist_uri)

        # update slots with returned info.
        intentObj.slots[SLOT_PLAYLIST_TITLE] = { CONF_TEXT: playlist_name, CONF_VALUE: playlist_uri }
        intentObj.slots[SLOT_PLAYLIST_URL] = { CONF_TEXT: "Spotify", CONF_VALUE: f"{SPOTIFY_WEB_URL_PFX}/{SpotifyMediaTypes.PLAYLIST.value}/{playlist_id}" }

        # trace.
        if (self.logsi.IsOn(SILevel.Verbose)):
            self.logsi.LogDictionary(SILevel.Verbose, STAppMessages.MSG_INTENT_HANDLER_SLOT_INFO % intentObj.intent_type, intentObj.slots, colorValue=SIColors.Khaki)

        # set service name and build parameters.
        svcName:str = SERVICE_SPOTIFY_FOLLOW_PLAYLIST
        svcData:dict = \
        {
            "entity_id": playerEntityState.entity_id,
            "public": is_public
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
