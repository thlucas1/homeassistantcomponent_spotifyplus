import voluptuous as vol

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
    CONF_TEXT,
    CONF_VALUE,
    DOMAIN,
    PLATFORM_SPOTIFYPLUS,
    INTENT_PLAY_FAVORITE_TRACKS,
    RESPONSE_PLAY_FAVORITE_TRACKS,
    RESPONSE_PLAY_FAVORITE_TRACKS_FOR_ARTIST,
    SERVICE_SPOTIFY_PLAYER_MEDIA_PLAY_TRACK_FAVORITES,
    SLOT_AREA,
    SLOT_ARTIST_NAME,
    SLOT_ARTIST_TITLE,
    SLOT_ARTIST_URL,
    SLOT_DELAY,
    SLOT_DEVICE_NAME,
    SLOT_FLOOR,
    SLOT_LIMIT_TOTAL,
    SLOT_NAME,
    SLOT_PLAYER_SHUFFLE_MODE,
    SLOT_PREFERRED_AREA_ID,
    SLOT_PREFERRED_FLOOR_ID,
    SPOTIFY_WEB_URL_PFX,
)

from .spotifyplusintenthandler import SpotifyPlusIntentHandler


class SpotifyPlusPlayFavoriteTracks_Handler(SpotifyPlusIntentHandler):
    """
    Handles intents for SpotifyPlusPlayFavoriteTracks.
    """
    def __init__(self, intentLoader:IntentLoader) -> None:
        """
        Initializes a new instance of the IntentHandler class.
        """
        # invoke base class method.
        super().__init__(intentLoader)

        # set intent handler basics.
        self.description = "Plays Spotify favorite tracks, with optional filtering by the specfied artist name."
        self.intent_type = INTENT_PLAY_FAVORITE_TRACKS
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
            vol.Optional(SLOT_DELAY, default=0.50): vol.Any(None, vol.All(vol.Coerce(float), vol.Range(min=0, max=10.0))),
            vol.Optional(SLOT_LIMIT_TOTAL, default=200): vol.Any(None, vol.All(vol.Coerce(int), vol.Range(min=1, max=750))),
            vol.Optional(SLOT_DEVICE_NAME): cv.string,
            vol.Optional(SLOT_ARTIST_NAME): cv.string,
            vol.Optional(SLOT_PLAYER_SHUFFLE_MODE): cv.string,
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
        device_name = intentObj.slots.get(SLOT_DEVICE_NAME, {}).get(CONF_VALUE, None)
        artist_name = intentObj.slots.get(SLOT_ARTIST_NAME, {}).get(CONF_TEXT, None)
        artist_title = artist_name
        artist_uri = intentObj.slots.get(SLOT_ARTIST_NAME, {}).get(CONF_VALUE, None)
        player_shuffle_mode = intentObj.slots.get(SLOT_PLAYER_SHUFFLE_MODE, {}).get(CONF_VALUE, "on")
        limit_total = intentObj.slots.get(SLOT_LIMIT_TOTAL, {}).get(CONF_VALUE, None)

        # was a uri supplied?
        if (artist_uri) and (artist_uri.startswith(f"spotify:{SpotifyMediaTypes.ARTIST.value}")):

            # if a uri was supplied, then it's from a pre-configured list of values; in this case,
            # we will bypass the search since it's (assumed to be) a valid uri value.

            # get id portion of spotify uri value.
            artist_id:str = get_id_from_uri(artist_uri)

            # load returned info that we care about.
            artist_url = f"{SPOTIFY_WEB_URL_PFX}/{SpotifyMediaTypes.ARTIST.value}/{artist_id}"

        else:

            artist_url = f"{SPOTIFY_WEB_URL_PFX}"

        # update slots with returned info.
        intentObj.slots[SLOT_ARTIST_TITLE] = { CONF_VALUE: artist_uri, CONF_TEXT: artist_title }
        intentObj.slots[SLOT_ARTIST_URL] = { CONF_VALUE: artist_url, CONF_TEXT: "Spotify" }

        # set service name and build parameters.
        svcName:str = SERVICE_SPOTIFY_PLAYER_MEDIA_PLAY_TRACK_FAVORITES
        svcData:dict = \
        {
            "entity_id": playerEntityState.entity_id,
            "filter_artist": artist_uri,  # will be a uri if slot artist_names list used; otherwise, just artist text or none.
            "shuffle": True if player_shuffle_mode == "on" else False,
            "device_id": device_name,
            "delay": delay,
            "limit_total": limit_total,
        }

        # play the media.
        self.logsi.LogVerbose(STAppMessages.MSG_SERVICE_EXECUTE % (svcName, playerEntityState.entity_id), colorValue=SIColors.Khaki)
        await intentObj.hass.services.async_call(
            DOMAIN,
            svcName,
            svcData,
            blocking=True,
            context=intentObj.context,
            return_response=False,
        )

        # set appropriate response.
        responseKey = RESPONSE_PLAY_FAVORITE_TRACKS_FOR_ARTIST
        if (artist_name is None):
            responseKey = RESPONSE_PLAY_FAVORITE_TRACKS
           
        # return intent response.
        return await self.ReturnResponseByKey(intentObj, intentResponse, responseKey)
