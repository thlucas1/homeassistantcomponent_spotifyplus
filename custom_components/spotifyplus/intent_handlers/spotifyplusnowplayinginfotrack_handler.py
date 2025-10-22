import voluptuous as vol

from homeassistant.components.media_player import MediaPlayerEntityFeature
from homeassistant.components.media_player.const import (
    ATTR_MEDIA_ALBUM_NAME,
    ATTR_MEDIA_ARTIST,
    ATTR_MEDIA_TITLE,
)
from homeassistant.const import (
    STATE_PAUSED,
    STATE_PLAYING,
)
from homeassistant.core import State, ServiceResponse
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
    ATTR_SPOTIFYPLUS_TRACK_URI_ORIGIN,
    CONF_TEXT,
    CONF_VALUE,
    DOMAIN,
    INTENT_NOWPLAYING_INFO_TRACK,
    PLATFORM_SPOTIFYPLUS,
    RESPONSE_NOWPLAYING_INFO_TRACK,
    RESPONSE_NOWPLAYING_NO_MEDIA_TRACK,
    RESPONSE_PLAYER_NOT_PLAYING_MEDIA,
    SERVICE_SPOTIFY_GET_TRACK,
    SLOT_AREA,
    SLOT_ALBUM_TITLE,
    SLOT_ALBUM_URL,
    SLOT_ARTIST_TITLE,
    SLOT_ARTIST_URL,
    SLOT_FLOOR,
    SLOT_NAME,
    SLOT_PREFERRED_AREA_ID,
    SLOT_PREFERRED_FLOOR_ID,
    SLOT_TRACK_TITLE,
    SLOT_TRACK_URL,
    SPOTIFY_WEB_URL_PFX,
)

from .spotifyplusintenthandler import SpotifyPlusIntentHandler


class SpotifyPlusNowPlayingInfoTrack_Handler(SpotifyPlusIntentHandler):
    """
    Handles intents for SpotifyPlusNowPlayingInfoTrack.
    """
    def __init__(self, intentLoader:IntentLoader) -> None:
        """
        Initializes a new instance of the IntentHandler class.
        """
        # invoke base class method.
        super().__init__(intentLoader)

        # set intent handler basics.
        self.description = "Queries media player state for currently playing track information."
        self.intent_type = INTENT_NOWPLAYING_INFO_TRACK
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
            vol.Optional(SLOT_ALBUM_TITLE): cv.string,
            vol.Optional(SLOT_ALBUM_URL): cv.string,
            vol.Optional(SLOT_ARTIST_TITLE): cv.string,
            vol.Optional(SLOT_ARTIST_URL): cv.string,
            vol.Optional(SLOT_TRACK_TITLE): cv.string,
            vol.Optional(SLOT_TRACK_URL): cv.string,
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

        # is now playing item a track? if not, then don't bother.
        item_type:str = playerEntityState.attributes.get(ATTR_SPOTIFYPLUS_ITEM_TYPE)
        if (item_type != SpotifyMediaTypes.TRACK.value):
            return await self.ReturnResponseByKey(intentObj, intentResponse, RESPONSE_NOWPLAYING_NO_MEDIA_TRACK)

        # get now playing details.
        album_name:str = playerEntityState.attributes.get(ATTR_MEDIA_ALBUM_NAME)
        artist_name:str = playerEntityState.attributes.get(ATTR_MEDIA_ARTIST)
        artist_uri:str = playerEntityState.attributes.get(ATTR_SPOTIFYPLUS_ARTIST_URI)
        track_name:str = playerEntityState.attributes.get(ATTR_MEDIA_TITLE)
        track_uri:str = playerEntityState.attributes.get(ATTR_SPOTIFYPLUS_TRACK_URI_ORIGIN)

        # get id portion of spotify uri value.
        artist_id:str = get_id_from_uri(artist_uri)
        track_id:str = get_id_from_uri(track_uri)

        # update slots with returned info.
        intentObj.slots[SLOT_ARTIST_TITLE] = { CONF_TEXT: artist_name, CONF_VALUE: artist_uri }
        intentObj.slots[SLOT_ARTIST_URL] = { CONF_TEXT: "Spotify", CONF_VALUE: f"{SPOTIFY_WEB_URL_PFX}/{SpotifyMediaTypes.ARTIST.value}/{artist_id}" }
        intentObj.slots[SLOT_TRACK_TITLE] = { CONF_TEXT: track_name, CONF_VALUE: track_uri }
        intentObj.slots[SLOT_TRACK_URL] = { CONF_TEXT: "Spotify", CONF_VALUE: f"{SPOTIFY_WEB_URL_PFX}/{SpotifyMediaTypes.TRACK.value}/{track_id}" }

        # trace.
        if (self.logsi.IsOn(SILevel.Verbose)):
            self.logsi.LogDictionary(SILevel.Verbose, STAppMessages.MSG_INTENT_HANDLER_SLOT_INFO % intentObj.intent_type, intentObj.slots, colorValue=SIColors.Khaki)

        # set service name and build parameters.
        svcName:str = SERVICE_SPOTIFY_GET_TRACK
        svcData:dict = \
        {
            "entity_id": playerEntityState.entity_id,
            "track_id": track_id,
        }

        # call integration service for this intent.
        self.logsi.LogVerbose(STAppMessages.MSG_SERVICE_EXECUTE % (svcName, playerEntityState.entity_id), colorValue=SIColors.Khaki)
        info_result:ServiceResponse = await intentObj.hass.services.async_call(
            DOMAIN,
            svcName,
            svcData,
            blocking=True,
            context=intentObj.context,
            return_response=True,
        )

        self.logsi.LogDictionary(SILevel.Verbose, "SERVICE_SPOTIFY_GET_TRACK result", info_result, prettyPrint=True, colorValue=SIColors.Khaki)

        # get related details and update slot info.
        album_uri:str = info_result.get("result",{}).get("album",{}).get("uri",None)
        album_url:str = info_result.get("result",{}).get("album",{}).get("external_urls", {}).get("spotify", SPOTIFY_WEB_URL_PFX)
        artist_url:str = info_result.get("result",{}).get("artists",[])[0].get("external_urls", {}).get("spotify", SPOTIFY_WEB_URL_PFX)
        track_url:str = info_result.get("result",{}).get("external_urls", {}).get("spotify", SPOTIFY_WEB_URL_PFX)

        # update slots with returned info.
        intentObj.slots[SLOT_ALBUM_TITLE] = { CONF_TEXT: album_name, CONF_VALUE: album_uri }
        intentObj.slots[SLOT_ALBUM_URL] = { CONF_TEXT: "Spotify", CONF_VALUE: album_url }
        intentObj.slots[SLOT_ARTIST_URL] = { CONF_TEXT: "Spotify", CONF_VALUE: artist_url }
        intentObj.slots[SLOT_TRACK_URL] = { CONF_TEXT: "Spotify", CONF_VALUE: track_url }
            
        # return intent response.
        return await self.ReturnResponseByKey(intentObj, intentResponse, RESPONSE_NOWPLAYING_INFO_TRACK)
