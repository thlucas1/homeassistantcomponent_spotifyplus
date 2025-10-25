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
    INTENT_SEARCH_PLAY_PODCAST_EPISODE,
    RESPONSE_PLAY_PODCAST,
    RESPONSE_PLAY_PODCAST_EPISODE,
    RESPONSE_SPOTIFY_SEARCH_NO_ITEMS_PODCAST_EPISODE,
    SERVICE_SPOTIFY_GET_EPISODE,
    SERVICE_SPOTIFY_PLAYER_MEDIA_PLAY_TRACKS,
    SERVICE_SPOTIFY_SEARCH_EPISODES,
    SLOT_AREA,
    SLOT_DELAY,
    SLOT_DEVICE_NAME,
    SLOT_FLOOR,
    SLOT_NAME,
    SLOT_PLAYER_SHUFFLE_MODE,
    SLOT_PODCAST_NAME,
    SLOT_PODCAST_TITLE,
    SLOT_PODCAST_URL,
    SLOT_SEARCH_CRITERIA,
    SLOT_EPISODE_NAME,
    SLOT_EPISODE_TITLE,
    SLOT_EPISODE_URL,
    SLOT_PREFERRED_AREA_ID,
    SLOT_PREFERRED_FLOOR_ID,
    SPOTIFY_WEB_URL_PFX,
)

from .spotifyplusintenthandler import SpotifyPlusIntentHandler


class SpotifyPlusSearchPlayPodcastEpisode_Handler(SpotifyPlusIntentHandler):
    """
    Handles intents for SpotifyPlusSearchPlayPodcastEpisode.
    """
    def __init__(self, intentLoader:IntentLoader) -> None:
        """
        Initializes a new instance of the IntentHandler class.
        """
        # invoke base class method.
        super().__init__(intentLoader)

        # set intent handler basics.
        self.description = "Searches the Spotify catalog for an episode name for a specific podcast, and starts playing it if found."
        self.intent_type = INTENT_SEARCH_PLAY_PODCAST_EPISODE
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
            vol.Optional(SLOT_PODCAST_NAME): cv.string,
            vol.Optional(SLOT_PODCAST_TITLE): cv.string,
            vol.Optional(SLOT_PODCAST_URL): cv.string,
            vol.Optional(SLOT_EPISODE_NAME): cv.string,
            vol.Optional(SLOT_EPISODE_TITLE): cv.string,
            vol.Optional(SLOT_EPISODE_URL): cv.string,
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
        podcast_name = intentObj.slots.get(SLOT_PODCAST_NAME, {}).get(CONF_TEXT, None)
        podcast_uri = intentObj.slots.get(SLOT_PODCAST_NAME, {}).get(CONF_VALUE, None)
        episode_name = intentObj.slots.get(SLOT_EPISODE_NAME, {}).get(CONF_TEXT, None)
        episode_uri = intentObj.slots.get(SLOT_EPISODE_NAME, {}).get(CONF_VALUE, None)
        player_shuffle_mode = intentObj.slots.get(SLOT_PLAYER_SHUFFLE_MODE, {}).get(CONF_VALUE, "on")

        # update slots with returned info.
        intentObj.slots[SLOT_PODCAST_TITLE] = { CONF_VALUE: podcast_uri, CONF_TEXT: podcast_name }
        intentObj.slots[SLOT_EPISODE_TITLE] = { CONF_VALUE: episode_uri, CONF_TEXT: episode_name }

        # was a uri supplied?
        if (episode_uri.startswith(f"spotify:{SpotifyMediaTypes.EPISODE.value}")):

            # if a uri was supplied, then it's from a pre-configured list of values; in this case,
            # we will bypass the search since it's (assumed to be) a valid uri value.

            # get id portion of spotify uri value.
            episode_id:str = get_id_from_uri(episode_uri)

            # load returned info that we care about.
            episode_title = episode_name
            episode_url = f"{SPOTIFY_WEB_URL_PFX}/{SpotifyMediaTypes.EPISODE.value}/{episode_id}"

            # podcast variables are unknwon, since only the track name / uri were supplied.
            podcast_title = podcast_name
            podcast_url = SPOTIFY_WEB_URL_PFX

        else:

            # format criteria if searching by podcast.
            podcast_criteria = ""
            if podcast_name is not None:
                podcast_criteria = f", {podcast_name}" 

            # set service name and build parameters.
            svcName:str = SERVICE_SPOTIFY_SEARCH_EPISODES
            svcData:dict = \
            {
                "entity_id": playerEntityState.entity_id,
                "criteria": episode_name + podcast_criteria,
                "limit_total": 1,
                "include_external": "audio"
            }

            # update slots with search criteria.
            intentObj.slots[SLOT_SEARCH_CRITERIA] = { CONF_VALUE: "", CONF_TEXT: svcData["criteria"] }

            # search spotify catalog for matching episode name.
            self.logsi.LogVerbose(STAppMessages.MSG_SERVICE_EXECUTE % (svcName, playerEntityState.entity_id), colorValue=SIColors.Khaki)
            search_result:ServiceResponse = await intentObj.hass.services.async_call(
                DOMAIN,
                svcName,
                svcData,
                blocking=True,
                context=intentObj.context,
                return_response=True,
            )
            self.logsi.LogDictionary(SILevel.Verbose, "SERVICE_SPOTIFY_SEARCH_EPISODES result", search_result, prettyPrint=True, colorValue=SIColors.Khaki)

            # if no matching items, then return appropriate response.
            items_count:int = search_result.get("result",{}).get("items_count", 0)
            if (items_count == 0):
                return await self.ReturnResponseByKey(intentObj, intentResponse, RESPONSE_SPOTIFY_SEARCH_NO_ITEMS_PODCAST_EPISODE)

            # load returned info that we care about.
            episode_title:str = search_result.get("result",{}).get("items")[0].get("name", "unknown")
            episode_uri:str = search_result.get("result",{}).get("items")[0].get("uri", "unknown")
            episode_url:str = search_result.get("result",{}).get("items")[0].get("external_urls", {}).get("spotify", SPOTIFY_WEB_URL_PFX)

            # get id portion of spotify uri value.
            episode_id:str = get_id_from_uri(episode_uri)

        # note that search response does not contain the parent show details, so
        # we need to call "get_episode" to retrieve them.

        # set service name and build parameters.
        svcName:str = SERVICE_SPOTIFY_GET_EPISODE
        svcData:dict = \
        {
            "entity_id": playerEntityState.entity_id,
            "episode_id": episode_id,
        }

        # get episode details.
        self.logsi.LogVerbose(STAppMessages.MSG_SERVICE_EXECUTE % (svcName, playerEntityState.entity_id), colorValue=SIColors.Khaki)
        search_result:ServiceResponse = await intentObj.hass.services.async_call(
            DOMAIN,
            svcName,
            svcData,
            blocking=True,
            context=intentObj.context,
            return_response=True,
        )
        self.logsi.LogDictionary(SILevel.Verbose, "SERVICE_SPOTIFY_GET_EPISODE result", search_result, prettyPrint=True, colorValue=SIColors.Khaki)

        # load returned info that we care about.
        podcast_title:str = search_result.get("result",{}).get("show").get("name", "unknown")
        podcast_uri:str = search_result.get("result",{}).get("show").get("uri", "unknown")
        podcast_url:str = search_result.get("result",{}).get("show").get("external_urls", {}).get("spotify", SPOTIFY_WEB_URL_PFX)

        # update slots with returned info.
        intentObj.slots[SLOT_PODCAST_TITLE] = { CONF_VALUE: podcast_uri, CONF_TEXT: podcast_title }
        intentObj.slots[SLOT_PODCAST_URL] = { CONF_VALUE: podcast_url, CONF_TEXT: "Spotify" }
        intentObj.slots[SLOT_EPISODE_TITLE] = { CONF_VALUE: episode_uri, CONF_TEXT: episode_title }
        intentObj.slots[SLOT_EPISODE_URL] = { CONF_VALUE: episode_url, CONF_TEXT: "Spotify" }

        # set service name and build parameters.
        svcName:str = SERVICE_SPOTIFY_PLAYER_MEDIA_PLAY_TRACKS
        svcData:dict = \
        {
            "entity_id": playerEntityState.entity_id,
            "uris": episode_uri,
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
        responseKey = RESPONSE_PLAY_PODCAST_EPISODE
        if (podcast_name is None):
            responseKey = RESPONSE_PLAY_PODCAST
           
        # return intent response.
        return await self.ReturnResponseByKey(intentObj, intentResponse, responseKey)
