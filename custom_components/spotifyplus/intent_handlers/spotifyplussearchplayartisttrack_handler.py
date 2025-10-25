import voluptuous as vol

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
    CONF_TEXT,
    CONF_VALUE,
    DOMAIN,
    PLATFORM_SPOTIFYPLUS,
    INTENT_SEARCH_PLAY_ARTIST_TRACK,
    RESPONSE_PLAY_TRACK,
    RESPONSE_PLAY_TRACK_WITH_ARTIST,
    RESPONSE_SPOTIFY_SEARCH_NO_ITEMS_TRACK,
    SERVICE_SPOTIFY_PLAYER_MEDIA_PLAY_TRACKS,
    SERVICE_SPOTIFY_SEARCH_TRACKS,
    SLOT_AREA,
    SLOT_ARTIST_NAME,
    SLOT_ARTIST_TITLE,
    SLOT_ARTIST_URL,
    SLOT_DELAY,
    SLOT_DEVICE_NAME,
    SLOT_FLOOR,
    SLOT_NAME,
    SLOT_PLAYER_SHUFFLE_MODE,
    SLOT_SEARCH_CRITERIA,
    SLOT_TRACK_NAME,
    SLOT_TRACK_TITLE,
    SLOT_TRACK_URL,
    SLOT_PREFERRED_AREA_ID,
    SLOT_PREFERRED_FLOOR_ID,
    SPOTIFY_WEB_URL_PFX,
)

from .spotifyplusintenthandler import SpotifyPlusIntentHandler


class SpotifyPlusSearchPlayArtistTrack_Handler(SpotifyPlusIntentHandler):
    """
    Handles intents for SpotifyPlusSearchPlayArtistTrack.
    """
    def __init__(self, intentLoader:IntentLoader) -> None:
        """
        Initializes a new instance of the IntentHandler class.
        """
        # invoke base class method.
        super().__init__(intentLoader)

        # set intent handler basics.
        self.description = "Searches the Spotify catalog for a track name by a specific artist, and starts playing it if found."
        self.intent_type = INTENT_SEARCH_PLAY_ARTIST_TRACK
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
            vol.Optional(SLOT_DEVICE_NAME): cv.string,
            vol.Optional(SLOT_ARTIST_NAME): cv.string,
            vol.Optional(SLOT_ARTIST_TITLE): cv.string,
            vol.Optional(SLOT_ARTIST_URL): cv.string,
            vol.Optional(SLOT_TRACK_NAME): cv.string,
            vol.Optional(SLOT_TRACK_TITLE): cv.string,
            vol.Optional(SLOT_TRACK_URL): cv.string,
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
        artist_uri = intentObj.slots.get(SLOT_ARTIST_NAME, {}).get(CONF_VALUE, None)
        track_name = intentObj.slots.get(SLOT_TRACK_NAME, {}).get(CONF_TEXT, None)
        track_uri = intentObj.slots.get(SLOT_TRACK_NAME, {}).get(CONF_VALUE, None)
        player_shuffle_mode = intentObj.slots.get(SLOT_PLAYER_SHUFFLE_MODE, {}).get(CONF_VALUE, "on")

        # update slots with returned info.
        intentObj.slots[SLOT_ARTIST_TITLE] = { CONF_VALUE: artist_uri, CONF_TEXT: artist_name }
        intentObj.slots[SLOT_TRACK_TITLE] = { CONF_VALUE: track_uri, CONF_TEXT: track_name }

        # was a uri supplied?
        if (track_uri.startswith(f"spotify:{SpotifyMediaTypes.TRACK.value}")):

            # if a uri was supplied, then it's from a pre-configured list of values; in this case,
            # we will bypass the search since it's (assumed to be) a valid uri value.

            # get id portion of spotify uri value.
            track_id:str = get_id_from_uri(track_uri)

            # load returned info that we care about.
            track_title = track_name
            track_url = f"{SPOTIFY_WEB_URL_PFX}/{SpotifyMediaTypes.TRACK.value}/{track_id}"

            # artist variables are unknwon, since only the track name / uri were supplied.
            artist_title = artist_name
            artist_url = SPOTIFY_WEB_URL_PFX

        else:

            # format criteria if searching by artist.
            artist_criteria = ""
            if artist_name is not None:
                artist_criteria = f" artist:{artist_name}" 

            # set service name and build parameters.
            svcName:str = SERVICE_SPOTIFY_SEARCH_TRACKS
            svcData:dict = \
            {
                "entity_id": playerEntityState.entity_id,
                "criteria": track_name + artist_criteria,
                "limit_total": 1,
                "include_external": "audio"
            }

            # update slots with search criteria.
            intentObj.slots[SLOT_SEARCH_CRITERIA] = { CONF_VALUE: "", CONF_TEXT: svcData["criteria"] }

            # search spotify catalog for matching track name.
            self.logsi.LogVerbose(STAppMessages.MSG_SERVICE_EXECUTE % (svcName, playerEntityState.entity_id), colorValue=SIColors.Khaki)
            search_result:ServiceResponse = await intentObj.hass.services.async_call(
                DOMAIN,
                svcName,
                svcData,
                blocking=True,
                context=intentObj.context,
                return_response=True,
            )
            self.logsi.LogDictionary(SILevel.Verbose, "SERVICE_SPOTIFY_SEARCH_TRACKS result", search_result, prettyPrint=True, colorValue=SIColors.Khaki)

            # if no matching items, then return appropriate response.
            items_count:int = search_result.get("result",{}).get("items_count", 0)
            if (items_count == 0):
                return await self.ReturnResponseByKey(intentObj, intentResponse, RESPONSE_SPOTIFY_SEARCH_NO_ITEMS_TRACK)

            # load returned info that we care about.
            track_title:str = search_result.get("result",{}).get("items")[0].get("name", "unknown")
            track_uri:str = search_result.get("result",{}).get("items")[0].get("uri", "unknown")
            track_url:str = search_result.get("result",{}).get("items")[0].get("external_urls", {}).get("spotify", SPOTIFY_WEB_URL_PFX)

            artist_title:str = search_result.get("result",{}).get("items")[0].get("artists")[0].get("name", "unknown")
            artist_uri:str = search_result.get("result",{}).get("items")[0].get("artists")[0].get("uri", "unknown")
            artist_url:str = search_result.get("result",{}).get("items")[0].get("artists")[0].get("external_urls", {}).get("spotify", SPOTIFY_WEB_URL_PFX)

        # update slots with returned info.
        intentObj.slots[SLOT_ARTIST_TITLE] = { CONF_VALUE: artist_uri, CONF_TEXT: artist_title }
        intentObj.slots[SLOT_ARTIST_URL] = { CONF_VALUE: artist_url, CONF_TEXT: "Spotify" }
        intentObj.slots[SLOT_TRACK_TITLE] = { CONF_VALUE: track_uri, CONF_TEXT: track_title }
        intentObj.slots[SLOT_TRACK_URL] = { CONF_VALUE: track_url, CONF_TEXT: "Spotify" }

        # set service name and build parameters.
        svcName:str = SERVICE_SPOTIFY_PLAYER_MEDIA_PLAY_TRACKS
        svcData:dict = \
        {
            "entity_id": playerEntityState.entity_id,
            "uris": track_uri,
            "shuffle": True if player_shuffle_mode == "on" else False,
            "device_id": device_name,
            "delay": delay,
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
        responseKey = RESPONSE_PLAY_TRACK_WITH_ARTIST
        if (artist_name is None):
            responseKey = RESPONSE_PLAY_TRACK
           
        # return intent response.
        return await self.ReturnResponseByKey(intentObj, intentResponse, responseKey)
