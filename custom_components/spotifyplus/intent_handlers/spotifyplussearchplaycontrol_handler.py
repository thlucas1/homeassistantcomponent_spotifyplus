import voluptuous as vol

from homeassistant.components.media_player import MediaPlayerEntityFeature
from homeassistant.const import (
    STATE_IDLE,
    STATE_OFF,
    STATE_ON,
    STATE_PAUSED,
    STATE_PLAYING,
    STATE_UNKNOWN,
)
from homeassistant.core import State, ServiceResponse
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.intent import (
    Intent,
    IntentResponse, 
    IntentResponseErrorCode, 
)

from smartinspectpython.siauto import SILevel, SIColors

from spotifywebapipython import SpotifyMediaTypes

from ..appmessages import STAppMessages
from ..intent_loader import IntentLoader
from ..utils import get_id_from_uri
from ..const import (
    CONF_LIMIT_TOTAL_MINIMUM,  
    CONF_TEXT,
    CONF_VALUE,
    DOMAIN,
    INTENT_SEARCH_PLAY_CONTROL,
    PLATFORM_SPOTIFYPLUS,
    RESPONSE_ERROR_SEARCH_NO_CRITERIA,
    RESPONSE_ERROR_SEARCH_PLAY_CONTROL_INVALID,
    RESPONSE_PLAY_ALBUM,
    RESPONSE_PLAY_ALBUM_WITH_ARTIST,
    RESPONSE_PLAY_AUDIOBOOK,
    RESPONSE_PLAY_AUDIOBOOK_WITH_AUTHOR,
    RESPONSE_PLAY_FAVORITE_TRACKS,
    RESPONSE_PLAY_FAVORITE_TRACKS_FOR_ARTIST,
    RESPONSE_PLAY_PLAYLIST,
    RESPONSE_PLAY_PODCAST,
    RESPONSE_PLAY_PODCAST_EPISODE,
    RESPONSE_PLAY_TRACK,
    RESPONSE_PLAY_TRACK_WITH_ARTIST,
    RESPONSE_SPOTIFY_SEARCH_NO_ITEMS_ALBUM,
    RESPONSE_SPOTIFY_SEARCH_NO_ITEMS_AUDIOBOOK,
    RESPONSE_SPOTIFY_SEARCH_NO_ITEMS_PLAYLIST,
    RESPONSE_SPOTIFY_SEARCH_NO_ITEMS_PODCAST,
    RESPONSE_SPOTIFY_SEARCH_NO_ITEMS_PODCAST_EPISODE,
    RESPONSE_SPOTIFY_SEARCH_NO_ITEMS_TRACK,
    SERVICE_SPOTIFY_GET_EPISODE,
    SERVICE_SPOTIFY_GET_SHOW_EPISODES,
    SERVICE_SPOTIFY_PLAYER_MEDIA_PLAY_CONTEXT,
    SERVICE_SPOTIFY_PLAYER_MEDIA_PLAY_TRACKS,
    SERVICE_SPOTIFY_PLAYER_MEDIA_PLAY_TRACK_FAVORITES,
    SERVICE_SPOTIFY_SEARCH_ALBUMS,
    SERVICE_SPOTIFY_SEARCH_AUDIOBOOKS,
    SERVICE_SPOTIFY_SEARCH_EPISODES,
    SERVICE_SPOTIFY_SEARCH_PLAYLISTS,
    SERVICE_SPOTIFY_SEARCH_SHOWS,
    SERVICE_SPOTIFY_SEARCH_TRACKS,
    SLOT_ALBUM_TITLE,
    SLOT_ALBUM_URL,
    SLOT_AREA,
    SLOT_ARTIST_TITLE,
    SLOT_ARTIST_URL,
    SLOT_AUDIOBOOK_TITLE,
    SLOT_AUDIOBOOK_URL,
    SLOT_AUTHOR_TITLE,
    SLOT_CRITERIA_ARG_1,
    SLOT_CRITERIA_ARG_2,
    SLOT_DELAY,
    SLOT_DEVICE_NAME,
    SLOT_EPISODE_TITLE,
    SLOT_EPISODE_URL,
    SLOT_FLOOR,
    SLOT_LATEST_EPISODE,
    SLOT_LIMIT_TOTAL,
    SLOT_NAME,
    SLOT_PLAYLIST_TITLE,
    SLOT_PLAYLIST_URL,
    SLOT_PLAYER_SHUFFLE_MODE,
    SLOT_PODCAST_TITLE,
    SLOT_PODCAST_URL,
    SLOT_PREFERRED_AREA_ID,
    SLOT_PREFERRED_FLOOR_ID,
    SLOT_SEARCH_CRITERIA,
    SLOT_SPOTIFYPLUS_SEARCH_PLAY_CONTROL,
    SLOT_SPOTIFYPLUS_SEARCH_PLAY_CONTROL_MULTI,
    SLOT_SPOTIFYPLUS_SEARCH_PLAY_CONTROL_SINGLE,
    SLOT_TRACK_TITLE,
    SLOT_TRACK_URL,
    SPOTIFY_WEB_URL_PFX,
)

from .spotifyplusintenthandler import SpotifyPlusIntentHandler


class SpotifyPlusSearchPlayControl_Handler(SpotifyPlusIntentHandler):
    """
    Handles intents for SpotifyPlusSearchPlayControl.
    """
    def __init__(self, intentLoader:IntentLoader) -> None:
        """
        Initializes a new instance of the IntentHandler class.
        """
        # invoke base class method.
        super().__init__(intentLoader)

        # set intent handler basics.
        self.description = "Controls media search and play functions."
        self.intent_type = INTENT_SEARCH_PLAY_CONTROL
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
            vol.Optional(SLOT_SPOTIFYPLUS_SEARCH_PLAY_CONTROL_MULTI): cv.string,
            vol.Optional(SLOT_SPOTIFYPLUS_SEARCH_PLAY_CONTROL_SINGLE): cv.string,
            vol.Optional(SLOT_DELAY, default=0.50): vol.Any(None, vol.All(vol.Coerce(float), vol.Range(min=0, max=10.0))),
            vol.Optional(SLOT_DEVICE_NAME): cv.string,
            vol.Optional(SLOT_CRITERIA_ARG_1): cv.string,
            vol.Optional(SLOT_CRITERIA_ARG_2): cv.string,
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
        # get optional arguments (if provided).
        search_play_control_text:str = intentObj.slots.get(SLOT_SPOTIFYPLUS_SEARCH_PLAY_CONTROL_SINGLE, {}).get(CONF_TEXT, None)
        search_play_control:str = intentObj.slots.get(SLOT_SPOTIFYPLUS_SEARCH_PLAY_CONTROL_SINGLE, {}).get(CONF_VALUE, None)
        if (search_play_control is None):
            search_play_control_text:str = intentObj.slots.get(SLOT_SPOTIFYPLUS_SEARCH_PLAY_CONTROL_MULTI, {}).get(CONF_TEXT, None)
            search_play_control:str = intentObj.slots.get(SLOT_SPOTIFYPLUS_SEARCH_PLAY_CONTROL_MULTI, {}).get(CONF_VALUE, None)

        # update slot with returned info.
        intentObj.slots[SLOT_SPOTIFYPLUS_SEARCH_PLAY_CONTROL] = { CONF_VALUE: search_play_control, CONF_TEXT: search_play_control_text }

        # process based on media type.
        if (search_play_control == "artist_album"):
            return await self.async_ProcessArtistAlbum(intentObj, intentResponse)

        elif (search_play_control == "artist_track"):
            return await self.async_ProcessArtistTrack(intentObj, intentResponse)

        elif (search_play_control == "album"):
            return await self.async_ProcessAlbum(intentObj, intentResponse)

        elif (search_play_control == "audiobook"):
            return await self.async_ProcessAudiobook(intentObj, intentResponse)

        elif (search_play_control == "playlist"):
            return await self.async_ProcessPlaylist(intentObj, intentResponse)

        elif (search_play_control == "podcast"):
            return await self.async_ProcessPodcast(intentObj, intentResponse)

        elif (search_play_control == "podcast_episode"):
            return await self.async_ProcessPodcastEpisode(intentObj, intentResponse)

        elif (search_play_control == "track"):
            return await self.async_ProcessTrack(intentObj, intentResponse)

        elif (search_play_control in ["favorite_tracks","favorite_tracks_artist"]):
            return await self.async_ProcessFavoriteTracks(intentObj, intentResponse)

        else:
            return await self.ReturnResponseByKey(intentObj, intentResponse, RESPONSE_ERROR_SEARCH_PLAY_CONTROL_INVALID, IntentResponseErrorCode.FAILED_TO_HANDLE)


    async def async_ProcessAlbum(
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
            album_name = intentObj.slots.get(SLOT_CRITERIA_ARG_1, {}).get(CONF_TEXT, None)
            album_uri = intentObj.slots.get(SLOT_CRITERIA_ARG_1, {}).get(CONF_VALUE, None)
            delay = intentObj.slots.get(SLOT_DELAY, {}).get(CONF_VALUE, None)
            device_name = intentObj.slots.get(SLOT_DEVICE_NAME, {}).get(CONF_VALUE, None)
            player_shuffle_mode = intentObj.slots.get(SLOT_PLAYER_SHUFFLE_MODE, {}).get(CONF_VALUE, "on")

            # update slots with returned info.
            intentObj.slots[SLOT_ALBUM_TITLE] = { CONF_VALUE: album_uri, CONF_TEXT: album_name }

            # was a uri supplied?
            if (album_uri) and (album_uri.startswith(f"spotify:{SpotifyMediaTypes.ALBUM.value}")):

                # if a uri was supplied, then it's from a pre-configured list of values; in this case,
                # we will bypass the search since it's (assumed to be) a valid uri value.

                # get id portion of spotify uri value.
                album_id:str = get_id_from_uri(album_uri)

                # load returned info that we care about.
                album_title = album_name
                album_url = f"{SPOTIFY_WEB_URL_PFX}/{SpotifyMediaTypes.ALBUM.value}/{album_id}"

                # artist variables are unknwon, since only the album name / uri were supplied.
                artist_name = None
                artist_title = artist_name
                artist_url = SPOTIFY_WEB_URL_PFX
                artist_uri = None

            else:

                # if no search criteria then we are done.
                if (album_name is None):
                    return await self.ReturnResponseByKey(intentObj, intentResponse, RESPONSE_ERROR_SEARCH_NO_CRITERIA, IntentResponseErrorCode.FAILED_TO_HANDLE)

                # set service name and build parameters.
                svcName:str = SERVICE_SPOTIFY_SEARCH_ALBUMS
                svcData:dict = \
                {
                    "entity_id": playerEntityState.entity_id,
                    "criteria": album_name,
                    "limit_total": CONF_LIMIT_TOTAL_MINIMUM,
                    "include_external": "audio"
                }

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
                self.logsi.LogDictionary(SILevel.Verbose, "SERVICE_SPOTIFY_SEARCH_ALBUMS result", search_result, prettyPrint=True, colorValue=SIColors.Khaki)

                # if no matching items, then return appropriate response.
                items_count:int = search_result.get("result",{}).get("items_count", 0)
                if (items_count == 0):
                    return await self.ReturnResponseByKey(intentObj, intentResponse, RESPONSE_SPOTIFY_SEARCH_NO_ITEMS_TRACK)

                # load returned info that we care about.
                album_title:str = search_result.get("result",{}).get("items")[0].get("name", "unknown")
                album_uri:str = search_result.get("result",{}).get("items")[0].get("uri", "unknown")
                album_url:str = search_result.get("result",{}).get("items")[0].get("external_urls", {}).get("spotify", SPOTIFY_WEB_URL_PFX)

                artist_name:str = search_result.get("result",{}).get("items")[0].get("artists")[0].get("name", "unknown")
                artist_title:str = search_result.get("result",{}).get("items")[0].get("artists")[0].get("name", "unknown")
                artist_uri:str = search_result.get("result",{}).get("items")[0].get("artists")[0].get("uri", "unknown")
                artist_url:str = search_result.get("result",{}).get("items")[0].get("artists")[0].get("external_urls", {}).get("spotify", SPOTIFY_WEB_URL_PFX)

            # update slots with returned info.
            intentObj.slots[SLOT_ARTIST_TITLE] = { CONF_VALUE: artist_uri, CONF_TEXT: artist_title }
            intentObj.slots[SLOT_ARTIST_URL] = { CONF_VALUE: artist_url, CONF_TEXT: "Spotify" }
            intentObj.slots[SLOT_ALBUM_TITLE] = { CONF_VALUE: album_uri, CONF_TEXT: album_title }
            intentObj.slots[SLOT_ALBUM_URL] = { CONF_VALUE: album_url, CONF_TEXT: "Spotify" }

            # set service name and build parameters.
            svcName:str = SERVICE_SPOTIFY_PLAYER_MEDIA_PLAY_CONTEXT
            svcData:dict = \
            {
                "entity_id": playerEntityState.entity_id,
                "context_uri": album_uri,
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
            responseKey = RESPONSE_PLAY_ALBUM_WITH_ARTIST
            if (artist_name is None):
                responseKey = RESPONSE_PLAY_ALBUM
           
            # return intent response.
            return await self.ReturnResponseByKey(intentObj, intentResponse, responseKey)

        finally:

            # trace.
            self.logsi.LeaveMethod(SILevel.Debug, colorValue=SIColors.Khaki)


    async def async_ProcessArtistAlbum(
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
            album_name = intentObj.slots.get(SLOT_CRITERIA_ARG_1, {}).get(CONF_TEXT, None)
            album_uri = intentObj.slots.get(SLOT_CRITERIA_ARG_1, {}).get(CONF_VALUE, None)
            artist_name = intentObj.slots.get(SLOT_CRITERIA_ARG_2, {}).get(CONF_TEXT, None)
            artist_uri = intentObj.slots.get(SLOT_CRITERIA_ARG_2, {}).get(CONF_VALUE, None)
            player_shuffle_mode = intentObj.slots.get(SLOT_PLAYER_SHUFFLE_MODE, {}).get(CONF_VALUE, "on")

            # update slots with returned info.
            intentObj.slots[SLOT_ARTIST_TITLE] = { CONF_VALUE: artist_uri, CONF_TEXT: artist_name }
            intentObj.slots[SLOT_ALBUM_TITLE] = { CONF_VALUE: album_uri, CONF_TEXT: album_name }

            # was a uri supplied?
            if (album_uri) and (album_uri.startswith(f"spotify:{SpotifyMediaTypes.ALBUM.value}")):

                # if a uri was supplied, then it's from a pre-configured list of values; in this case,
                # we will bypass the search since it's (assumed to be) a valid uri value.

                # get id portion of spotify uri value.
                album_id:str = get_id_from_uri(album_uri)

                # load returned info that we care about.
                album_title = album_name
                album_url = f"{SPOTIFY_WEB_URL_PFX}/{SpotifyMediaTypes.ALBUM.value}/{album_id}"

                # artist variables are unknwon, since only the album name / uri were supplied.
                artist_title = artist_name
                artist_url = SPOTIFY_WEB_URL_PFX

            else:

                # if no search criteria then we are done.
                if (album_name is None) and (artist_name is None):
                    return await self.ReturnResponseByKey(intentObj, intentResponse, RESPONSE_ERROR_SEARCH_NO_CRITERIA, IntentResponseErrorCode.FAILED_TO_HANDLE)

                # format criteria if searching by artist.
                artist_criteria = ""
                if artist_name is not None:
                    artist_criteria = f" artist:{artist_name}" 

                # set service name and build parameters.
                svcName:str = SERVICE_SPOTIFY_SEARCH_ALBUMS
                svcData:dict = \
                {
                    "entity_id": playerEntityState.entity_id,
                    "criteria": album_name + artist_criteria,
                    "limit_total": CONF_LIMIT_TOTAL_MINIMUM,
                    "include_external": "audio"
                }

                # update slots with search criteria.
                intentObj.slots[SLOT_SEARCH_CRITERIA] = { CONF_VALUE: "", CONF_TEXT: svcData["criteria"] }

                # search spotify catalog for matching album name.
                self.logsi.LogVerbose(STAppMessages.MSG_SERVICE_EXECUTE % (svcName, playerEntityState.entity_id), colorValue=SIColors.Khaki)
                search_result:ServiceResponse = await intentObj.hass.services.async_call(
                    DOMAIN,
                    svcName,
                    svcData,
                    blocking=True,
                    context=intentObj.context,
                    return_response=True,
                )
                self.logsi.LogDictionary(SILevel.Verbose, "SERVICE_SPOTIFY_SEARCH_ALBUMS result", search_result, prettyPrint=True, colorValue=SIColors.Khaki)

                # if no matching items, then return appropriate response.
                items_count:int = search_result.get("result",{}).get("items_count", 0)
                if (items_count == 0):
                    return await self.ReturnResponseByKey(intentObj, intentResponse, RESPONSE_SPOTIFY_SEARCH_NO_ITEMS_ALBUM)

                # load returned info that we care about.
                album_title:str = search_result.get("result",{}).get("items")[0].get("name", "unknown")
                album_uri:str = search_result.get("result",{}).get("items")[0].get("uri", "unknown")
                album_url:str = search_result.get("result",{}).get("items")[0].get("external_urls", {}).get("spotify", SPOTIFY_WEB_URL_PFX)

                artist_title:str = search_result.get("result",{}).get("items")[0].get("artists")[0].get("name", "unknown")
                artist_uri:str = search_result.get("result",{}).get("items")[0].get("artists")[0].get("uri", "unknown")
                artist_url:str = search_result.get("result",{}).get("items")[0].get("artists")[0].get("external_urls", {}).get("spotify", SPOTIFY_WEB_URL_PFX)

            # update slots with returned info.
            intentObj.slots[SLOT_ARTIST_TITLE] = { CONF_VALUE: artist_uri, CONF_TEXT: artist_title }
            intentObj.slots[SLOT_ARTIST_URL] = { CONF_VALUE: artist_url, CONF_TEXT: "Spotify" }
            intentObj.slots[SLOT_ALBUM_TITLE] = { CONF_VALUE: album_uri, CONF_TEXT: album_title }
            intentObj.slots[SLOT_ALBUM_URL] = { CONF_VALUE: album_url, CONF_TEXT: "Spotify" }

            # set service name and build parameters.
            svcName:str = SERVICE_SPOTIFY_PLAYER_MEDIA_PLAY_CONTEXT
            svcData:dict = \
            {
                "entity_id": playerEntityState.entity_id,
                "context_uri": album_uri,
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
            responseKey = RESPONSE_PLAY_ALBUM_WITH_ARTIST
            if (artist_name is None):
                responseKey = RESPONSE_PLAY_ALBUM
           
            # return intent response.
            return await self.ReturnResponseByKey(intentObj, intentResponse, responseKey)

        finally:

            # trace.
            self.logsi.LeaveMethod(SILevel.Debug, colorValue=SIColors.Khaki)


    async def async_ProcessArtistTrack(
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
            artist_name = intentObj.slots.get(SLOT_CRITERIA_ARG_2, {}).get(CONF_TEXT, None)
            artist_uri = intentObj.slots.get(SLOT_CRITERIA_ARG_2, {}).get(CONF_VALUE, None)
            track_name = intentObj.slots.get(SLOT_CRITERIA_ARG_1, {}).get(CONF_TEXT, None)
            track_uri = intentObj.slots.get(SLOT_CRITERIA_ARG_1, {}).get(CONF_VALUE, None)
            player_shuffle_mode = intentObj.slots.get(SLOT_PLAYER_SHUFFLE_MODE, {}).get(CONF_VALUE, "on")

            # update slots with returned info.
            intentObj.slots[SLOT_ARTIST_TITLE] = { CONF_VALUE: artist_uri, CONF_TEXT: artist_name }
            intentObj.slots[SLOT_TRACK_TITLE] = { CONF_VALUE: track_uri, CONF_TEXT: track_name }

            # was a uri supplied?
            if (track_uri) and (track_uri.startswith(f"spotify:{SpotifyMediaTypes.TRACK.value}")):

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

                # if no search criteria then we are done.
                if (track_name is None) and (artist_name is None):
                    return await self.ReturnResponseByKey(intentObj, intentResponse, RESPONSE_ERROR_SEARCH_NO_CRITERIA, IntentResponseErrorCode.FAILED_TO_HANDLE)

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
                    "limit_total": CONF_LIMIT_TOTAL_MINIMUM,
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

        finally:

            # trace.
            self.logsi.LeaveMethod(SILevel.Debug, colorValue=SIColors.Khaki)


    async def async_ProcessAudiobook(
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
            audiobook_name = intentObj.slots.get(SLOT_CRITERIA_ARG_1, {}).get(CONF_TEXT, None)
            audiobook_uri = intentObj.slots.get(SLOT_CRITERIA_ARG_1, {}).get(CONF_VALUE, None)
            player_shuffle_mode = intentObj.slots.get(SLOT_PLAYER_SHUFFLE_MODE, {}).get(CONF_VALUE, "on")

            # update slots with returned info.
            intentObj.slots[SLOT_AUDIOBOOK_TITLE] = { CONF_VALUE: audiobook_uri, CONF_TEXT: audiobook_name }

            # was a uri supplied?
            if (audiobook_uri) and (audiobook_uri.startswith(f"spotify:{SpotifyMediaTypes.SHOW.value}")):

                # if a uri was supplied, then it's from a pre-configured list of values; in this case,
                # we will bypass the search since it's (assumed to be) a valid uri value.

                # get id portion of spotify uri value.
                audiobook_id:str = get_id_from_uri(audiobook_uri)

                # load returned info that we care about.
                audiobook_title = audiobook_name
                audiobook_url = f"{SPOTIFY_WEB_URL_PFX}/{SpotifyMediaTypes.SHOW.value}/{audiobook_id}"
                author_title = None

            else:

                # if no search criteria then we are done.
                if (audiobook_name is None):
                    return await self.ReturnResponseByKey(intentObj, intentResponse, RESPONSE_ERROR_SEARCH_NO_CRITERIA, IntentResponseErrorCode.FAILED_TO_HANDLE)

                # set service name and build parameters.
                svcName:str = SERVICE_SPOTIFY_SEARCH_AUDIOBOOKS
                svcData:dict = \
                {
                    "entity_id": playerEntityState.entity_id,
                    "criteria": audiobook_name,
                    "limit_total": CONF_LIMIT_TOTAL_MINIMUM,
                    "include_external": "audio"
                }

                # update slots with search criteria.
                intentObj.slots[SLOT_SEARCH_CRITERIA] = { CONF_VALUE: "", CONF_TEXT: svcData["criteria"] }

                # search spotify catalog for matching audiobook name.
                self.logsi.LogVerbose(STAppMessages.MSG_SERVICE_EXECUTE % (svcName, playerEntityState.entity_id), colorValue=SIColors.Khaki)
                search_result:ServiceResponse = await intentObj.hass.services.async_call(
                    DOMAIN,
                    svcName,
                    svcData,
                    blocking=True,
                    context=intentObj.context,
                    return_response=True,
                )
                self.logsi.LogDictionary(SILevel.Verbose, "SERVICE_SPOTIFY_SEARCH_AUDIOBOOKS result", search_result, prettyPrint=True, colorValue=SIColors.Khaki)

                # if no matching items, then return appropriate response.
                items_count:int = search_result.get("result",{}).get("items_count", 0)
                if (items_count == 0):
                    return await self.ReturnResponseByKey(intentObj, intentResponse, RESPONSE_SPOTIFY_SEARCH_NO_ITEMS_AUDIOBOOK)

                # load returned info that we care about.
                audiobook_title:str = search_result.get("result",{}).get("items")[0].get("name", "unknown")
                audiobook_uri:str = search_result.get("result",{}).get("items")[0].get("uri", "unknown")
                audiobook_url:str = search_result.get("result",{}).get("items")[0].get("external_urls", {}).get("spotify", SPOTIFY_WEB_URL_PFX)

                author_title:str = search_result.get("result",{}).get("items")[0].get("authors")[0].get("name", "unknown")

            # update slots with returned info.
            intentObj.slots[SLOT_AUDIOBOOK_TITLE] = { CONF_VALUE: audiobook_uri, CONF_TEXT: audiobook_title }
            intentObj.slots[SLOT_AUDIOBOOK_URL] = { CONF_VALUE: audiobook_url, CONF_TEXT: "Spotify" }
            intentObj.slots[SLOT_AUTHOR_TITLE] = { CONF_VALUE: author_title, CONF_TEXT: author_title }

            # set service name and build parameters.
            svcName:str = SERVICE_SPOTIFY_PLAYER_MEDIA_PLAY_CONTEXT
            svcData:dict = \
            {
                "entity_id": playerEntityState.entity_id,
                "context_uri": audiobook_uri,
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
            responseKey = RESPONSE_PLAY_AUDIOBOOK_WITH_AUTHOR
            if (author_title is None):
                responseKey = RESPONSE_PLAY_AUDIOBOOK
           
            # return intent response.
            return await self.ReturnResponseByKey(intentObj, intentResponse, responseKey)

        finally:

            # trace.
            self.logsi.LeaveMethod(SILevel.Debug, colorValue=SIColors.Khaki)


    async def async_ProcessPlaylist(
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
            playlist_name = intentObj.slots.get(SLOT_CRITERIA_ARG_1, {}).get(CONF_TEXT, None)
            playlist_uri = intentObj.slots.get(SLOT_CRITERIA_ARG_1, {}).get(CONF_VALUE, None)
            player_shuffle_mode = intentObj.slots.get(SLOT_PLAYER_SHUFFLE_MODE, {}).get(CONF_VALUE, "on")

            # update slots with returned info.
            intentObj.slots[SLOT_PLAYLIST_TITLE] = { CONF_VALUE: playlist_uri, CONF_TEXT: playlist_name }

            # was a uri supplied?
            if (playlist_uri) and (playlist_uri.startswith(f"spotify:{SpotifyMediaTypes.PLAYLIST.value}")):

                # if a uri was supplied, then it's from a pre-configured list of values; in this case,
                # we will bypass the search since it's (assumed to be) a valid uri value.

                # get id portion of spotify uri value.
                playlist_id:str = get_id_from_uri(playlist_uri)

                # load returned info that we care about.
                playlist_title = playlist_name
                playlist_url = f"{SPOTIFY_WEB_URL_PFX}/{SpotifyMediaTypes.PLAYLIST.value}/{playlist_id}"

            else:

                # if no search criteria then we are done.
                if (playlist_name is None):
                    return await self.ReturnResponseByKey(intentObj, intentResponse, RESPONSE_ERROR_SEARCH_NO_CRITERIA, IntentResponseErrorCode.FAILED_TO_HANDLE)

                # set service name and build parameters.
                svcName:str = SERVICE_SPOTIFY_SEARCH_PLAYLISTS
                svcData:dict = \
                {
                    "entity_id": playerEntityState.entity_id,
                    "criteria": playlist_name,
                    "limit_total": CONF_LIMIT_TOTAL_MINIMUM,
                    "include_external": "audio"
                }

                # update slots with search criteria.
                intentObj.slots[SLOT_SEARCH_CRITERIA] = { CONF_VALUE: "", CONF_TEXT: svcData["criteria"] }

                # search spotify catalog for matching playlist name.
                self.logsi.LogVerbose(STAppMessages.MSG_SERVICE_EXECUTE % (svcName, playerEntityState.entity_id), colorValue=SIColors.Khaki)
                search_result:ServiceResponse = await intentObj.hass.services.async_call(
                    DOMAIN,
                    svcName,
                    svcData,
                    blocking=True,
                    context=intentObj.context,
                    return_response=True,
                )
                self.logsi.LogDictionary(SILevel.Verbose, "SERVICE_SPOTIFY_SEARCH_PLAYLISTS result", search_result, prettyPrint=True, colorValue=SIColors.Khaki)

                # if no matching items, then return appropriate response.
                items_count:int = search_result.get("result",{}).get("items_count", 0)
                if (items_count == 0):
                    return await self.ReturnResponseByKey(intentObj, intentResponse, RESPONSE_SPOTIFY_SEARCH_NO_ITEMS_PLAYLIST)

                # load returned info that we care about.
                playlist_title:str = search_result.get("result",{}).get("items")[0].get("name", "unknown")
                playlist_uri:str = search_result.get("result",{}).get("items")[0].get("uri", "unknown")
                playlist_url:str = search_result.get("result",{}).get("items")[0].get("external_urls", {}).get("spotify", SPOTIFY_WEB_URL_PFX)

            # update slots with returned info.
            intentObj.slots[SLOT_PLAYLIST_TITLE] = { CONF_VALUE: playlist_uri, CONF_TEXT: playlist_title }
            intentObj.slots[SLOT_PLAYLIST_URL] = { CONF_VALUE: playlist_url, CONF_TEXT: "Spotify" }

            # set service name and build parameters.
            svcName:str = SERVICE_SPOTIFY_PLAYER_MEDIA_PLAY_CONTEXT
            svcData:dict = \
            {
                "entity_id": playerEntityState.entity_id,
                "context_uri": playlist_uri,
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
           
            # return intent response.
            return await self.ReturnResponseByKey(intentObj, intentResponse, RESPONSE_PLAY_PLAYLIST)

        finally:

            # trace.
            self.logsi.LeaveMethod(SILevel.Debug, colorValue=SIColors.Khaki)


    async def async_ProcessPodcast(
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
            latest_episode = intentObj.slots.get(SLOT_LATEST_EPISODE, {}).get(CONF_VALUE, None)
            podcast_name = intentObj.slots.get(SLOT_CRITERIA_ARG_1, {}).get(CONF_TEXT, None)
            podcast_uri = intentObj.slots.get(SLOT_CRITERIA_ARG_1, {}).get(CONF_VALUE, None)
            player_shuffle_mode = intentObj.slots.get(SLOT_PLAYER_SHUFFLE_MODE, {}).get(CONF_VALUE, "on")

            # update slots with returned info.
            intentObj.slots[SLOT_PODCAST_TITLE] = { CONF_VALUE: podcast_uri, CONF_TEXT: podcast_name }

            # was a uri supplied?
            if (podcast_uri) and (podcast_uri.startswith(f"spotify:{SpotifyMediaTypes.SHOW.value}")):

                # if a uri was supplied, then it's from a pre-configured list of values; in this case,
                # we will bypass the search since it's (assumed to be) a valid uri value.

                # get id portion of spotify uri value.
                podcast_id:str = get_id_from_uri(podcast_uri)

                # load returned info that we care about.
                # note that the title will be the slot list text value, as the SERVICE_SPOTIFY_GET_SHOW_EPISODES
                # call does not return show information.
                podcast_title = podcast_name
                podcast_url = f"{SPOTIFY_WEB_URL_PFX}/{SpotifyMediaTypes.SHOW.value}/{podcast_id}"

            else:

                # if no search criteria then we are done.
                if (podcast_name is None):
                    return await self.ReturnResponseByKey(intentObj, intentResponse, RESPONSE_ERROR_SEARCH_NO_CRITERIA, IntentResponseErrorCode.FAILED_TO_HANDLE)

                # set service name and build parameters.
                svcName:str = SERVICE_SPOTIFY_SEARCH_SHOWS
                svcData:dict = \
                {
                    "entity_id": playerEntityState.entity_id,
                    "criteria": podcast_name,
                    "limit_total": CONF_LIMIT_TOTAL_MINIMUM,
                    "include_external": "audio"
                }

                # update slots with search criteria.
                intentObj.slots[SLOT_SEARCH_CRITERIA] = { CONF_VALUE: "", CONF_TEXT: svcData["criteria"] }

                # search spotify catalog for matching podcast name.
                self.logsi.LogVerbose(STAppMessages.MSG_SERVICE_EXECUTE % (svcName, playerEntityState.entity_id), colorValue=SIColors.Khaki)
                search_result:ServiceResponse = await intentObj.hass.services.async_call(
                    DOMAIN,
                    svcName,
                    svcData,
                    blocking=True,
                    context=intentObj.context,
                    return_response=True,
                )
                self.logsi.LogDictionary(SILevel.Verbose, "SERVICE_SPOTIFY_SEARCH_SHOWS result", search_result, prettyPrint=True, colorValue=SIColors.Khaki)

                # if no matching items, then return appropriate response.
                items_count:int = search_result.get("result",{}).get("items_count", 0)
                if (items_count == 0):
                    return await self.ReturnResponseByKey(intentObj, intentResponse, RESPONSE_SPOTIFY_SEARCH_NO_ITEMS_PODCAST)

                # load returned info that we care about.
                podcast_title:str = search_result.get("result",{}).get("items")[0].get("name", "unknown")
                podcast_uri:str = search_result.get("result",{}).get("items")[0].get("uri", "unknown")
                podcast_url:str = search_result.get("result",{}).get("items")[0].get("external_urls", {}).get("spotify", SPOTIFY_WEB_URL_PFX)

                # get id portion of spotify uri value.
                podcast_id:str = get_id_from_uri(podcast_uri)

            # update slots with returned info.
            intentObj.slots[SLOT_PODCAST_TITLE] = { CONF_VALUE: podcast_uri, CONF_TEXT: podcast_title }
            intentObj.slots[SLOT_PODCAST_URL] = { CONF_VALUE: podcast_url, CONF_TEXT: "Spotify" }

            # # are we playing the latest episode?  
            # # if so, then get the latest episode data.
            # # if not, then last played episode will resume where it left off.
            # if (latest_episode == "on"):

            #     # trace.
            #     self.logsi.LogVerbose("Playing latest podcast episode", colorValue=SIColors.Khaki)

            #     # set service name and build parameters.
            #     svcName:str = SERVICE_SPOTIFY_GET_SHOW_EPISODES
            #     svcData:dict = \
            #     {
            #         "entity_id": playerEntityState.entity_id,
            #         "show_id": podcast_id,
            #         "limit_total": 1,
            #     }

            #     # get latest podcast episode data.
            #     self.logsi.LogVerbose(STAppMessages.MSG_SERVICE_EXECUTE % (svcName, playerEntityState.entity_id), colorValue=SIColors.Khaki)
            #     search_result:ServiceResponse = await intentObj.hass.services.async_call(
            #         DOMAIN,
            #         svcName,
            #         svcData,
            #         blocking=True,
            #         context=intentObj.context,
            #         return_response=True,
            #     )
            #     self.logsi.LogDictionary(SILevel.Verbose, "SERVICE_SPOTIFY_GET_SHOW_EPISODES result", search_result, prettyPrint=True, colorValue=SIColors.Khaki)

            #     # if no matching items, then return appropriate response.
            #     items_count:int = search_result.get("result",{}).get("items_count", 0)
            #     if (items_count == 0):
            #         return await self.ReturnResponseByKey(intentObj, intentResponse, RESPONSE_SPOTIFY_SEARCH_NO_ITEMS_PODCAST_EPISODE)

            #     # load returned info that we care about.
            #     episode_title:str = search_result.get("result",{}).get("items")[0].get("name", "unknown")
            #     episode_uri:str = search_result.get("result",{}).get("items")[0].get("uri", "unknown")
            #     episode_url:str = search_result.get("result",{}).get("items")[0].get("external_urls", {}).get("spotify", SPOTIFY_WEB_URL_PFX)

            #     # update slots with returned info.
            #     intentObj.slots[SLOT_EPISODE_TITLE] = { CONF_VALUE: episode_uri, CONF_TEXT: episode_title }
            #     intentObj.slots[SLOT_EPISODE_URL] = { CONF_VALUE: episode_url, CONF_TEXT: "Spotify" }

            #     # set service name and build parameters.
            #     svcName:str = SERVICE_SPOTIFY_PLAYER_MEDIA_PLAY_TRACKS
            #     svcData:dict = \
            #     {
            #         "entity_id": playerEntityState.entity_id,
            #         "uris": episode_uri,
            #         "shuffle": True if player_shuffle_mode == "on" else False,
            #         "device_id": device_name,
            #         "delay": delay,
            #     }

            #     # play the media.
            #     self.logsi.LogVerbose(STAppMessages.MSG_SERVICE_EXECUTE % (svcName, playerEntityState.entity_id), colorValue=SIColors.Khaki)
            #     await intentObj.hass.services.async_call(
            #         DOMAIN,
            #         svcName,
            #         svcData,
            #         blocking=True,
            #         context=intentObj.context,
            #         return_response=False,
            #     )
           
            #     # return intent response.
            #     return await self.ReturnResponseByKey(intentObj, intentResponse, RESPONSE_PLAY_PODCAST_EPISODE)

            # else:

            #     # trace.
            #     self.logsi.LogVerbose("Resuming play of podcast episode last played", colorValue=SIColors.Khaki)

            # set service name and build parameters.
            svcName:str = SERVICE_SPOTIFY_PLAYER_MEDIA_PLAY_CONTEXT
            svcData:dict = \
            {
                "entity_id": playerEntityState.entity_id,
                "context_uri": podcast_uri,
                "shuffle": True if player_shuffle_mode == "on" else False,
                "device_id": device_name,
                "delay": delay,
                "play_show_latest_episode": True if latest_episode == "on" else False,
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
           
            # return intent response.
            return await self.ReturnResponseByKey(intentObj, intentResponse, RESPONSE_PLAY_PODCAST)

        finally:

            # trace.
            self.logsi.LeaveMethod(SILevel.Debug, colorValue=SIColors.Khaki)


    async def async_ProcessPodcastEpisode(
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
            podcast_name = intentObj.slots.get(SLOT_CRITERIA_ARG_2, {}).get(CONF_TEXT, None)
            podcast_uri = intentObj.slots.get(SLOT_CRITERIA_ARG_2, {}).get(CONF_VALUE, None)
            episode_name = intentObj.slots.get(SLOT_CRITERIA_ARG_1, {}).get(CONF_TEXT, None)
            episode_uri = intentObj.slots.get(SLOT_CRITERIA_ARG_1, {}).get(CONF_VALUE, None)
            player_shuffle_mode = intentObj.slots.get(SLOT_PLAYER_SHUFFLE_MODE, {}).get(CONF_VALUE, "on")

            # update slots with returned info.
            intentObj.slots[SLOT_PODCAST_TITLE] = { CONF_VALUE: podcast_uri, CONF_TEXT: podcast_name }
            intentObj.slots[SLOT_EPISODE_TITLE] = { CONF_VALUE: episode_uri, CONF_TEXT: episode_name }

            # was a uri supplied?
            if (episode_uri) and (episode_uri.startswith(f"spotify:{SpotifyMediaTypes.EPISODE.value}")):

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

                # if no search criteria then we are done.
                if (episode_name is None) and (podcast_name is None):
                    return await self.ReturnResponseByKey(intentObj, intentResponse, RESPONSE_ERROR_SEARCH_NO_CRITERIA, IntentResponseErrorCode.FAILED_TO_HANDLE)

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
                    "limit_total": CONF_LIMIT_TOTAL_MINIMUM,
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

        finally:

            # trace.
            self.logsi.LeaveMethod(SILevel.Debug, colorValue=SIColors.Khaki)


    async def async_ProcessTrack(
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
            track_name = intentObj.slots.get(SLOT_CRITERIA_ARG_1, {}).get(CONF_TEXT, None)
            track_uri = intentObj.slots.get(SLOT_CRITERIA_ARG_1, {}).get(CONF_VALUE, None)
            delay = intentObj.slots.get(SLOT_DELAY, {}).get(CONF_VALUE, None)
            device_name = intentObj.slots.get(SLOT_DEVICE_NAME, {}).get(CONF_VALUE, None)
            player_shuffle_mode = intentObj.slots.get(SLOT_PLAYER_SHUFFLE_MODE, {}).get(CONF_VALUE, "on")

            # update slots with returned info.
            intentObj.slots[SLOT_TRACK_TITLE] = { CONF_VALUE: track_uri, CONF_TEXT: track_name }

            # was a uri supplied?
            if (track_uri) and (track_uri.startswith(f"spotify:{SpotifyMediaTypes.TRACK.value}")):

                # if a uri was supplied, then it's from a pre-configured list of values; in this case,
                # we will bypass the search since it's (assumed to be) a valid uri value.

                # get id portion of spotify uri value.
                track_id:str = get_id_from_uri(track_uri)

                # load returned info that we care about.
                track_title = track_name
                track_url = f"{SPOTIFY_WEB_URL_PFX}/{SpotifyMediaTypes.TRACK.value}/{track_id}"

                # artist variables are unknwon, since only the track name / uri were supplied.
                artist_name = None
                artist_title = artist_name
                artist_url = SPOTIFY_WEB_URL_PFX
                artist_uri = None

            else:

                # if no search criteria then we are done.
                if (track_name is None):
                    return await self.ReturnResponseByKey(intentObj, intentResponse, RESPONSE_ERROR_SEARCH_NO_CRITERIA, IntentResponseErrorCode.FAILED_TO_HANDLE)

                # set service name and build parameters.
                svcName:str = SERVICE_SPOTIFY_SEARCH_TRACKS
                svcData:dict = \
                {
                    "entity_id": playerEntityState.entity_id,
                    "criteria": track_name,
                    "limit_total": CONF_LIMIT_TOTAL_MINIMUM,
                    "include_external": "audio"
                }

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

                artist_name:str = search_result.get("result",{}).get("items")[0].get("artists")[0].get("name", "unknown")
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

        finally:

            # trace.
            self.logsi.LeaveMethod(SILevel.Debug, colorValue=SIColors.Khaki)


    async def async_ProcessFavoriteTracks(
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
            artist_name = intentObj.slots.get(SLOT_CRITERIA_ARG_1, {}).get(CONF_TEXT, None)
            artist_uri = intentObj.slots.get(SLOT_CRITERIA_ARG_1, {}).get(CONF_VALUE, None)
            player_shuffle_mode = intentObj.slots.get(SLOT_PLAYER_SHUFFLE_MODE, {}).get(CONF_VALUE, "on")
            limit_total = intentObj.slots.get(SLOT_LIMIT_TOTAL, {}).get(CONF_VALUE, None)

            artist_title = artist_name

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
                "filter_artist": artist_uri or "",  # will be a uri if slot artist_names list used; otherwise, just artist text or none.
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

        finally:

            # trace.
            self.logsi.LeaveMethod(SILevel.Debug, colorValue=SIColors.Khaki)
