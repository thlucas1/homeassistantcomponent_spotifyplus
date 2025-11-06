import voluptuous as vol

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
    IntentResponseErrorCode, 
)

from smartinspectpython.siauto import SILevel, SIColors

from spotifywebapipython import SpotifyMediaTypes

from ..appmessages import STAppMessages
from ..intent_loader import IntentLoader
from ..utils import get_id_from_uri
from ..const import (
    ATTR_SPOTIFYPLUS_ARTIST_URI,
    ATTR_SPOTIFYPLUS_CONTEXT_URI,
    ATTR_SPOTIFYPLUS_ITEM_TYPE,
    ATTR_SPOTIFYPLUS_PLAYLIST_NAME,
    ATTR_SPOTIFYPLUS_PLAYLIST_URI,
    ATTR_SPOTIFYPLUS_TRACK_URI_ORIGIN,
    CONF_ADD,
    CONF_REMOVE,
    CONF_TEXT,
    CONF_VALUE,
    DOMAIN,
    INTENT_FAVORITE_ADD_REMOVE,
    PLATFORM_SPOTIFYPLUS,
    RESPONSE_ERROR_MEDIA_TYPE_INVALID,
    RESPONSE_FAVORITE_OPERATION_INVALID,
    RESPONSE_FAVORITE_ADD_REMOVE_ALBUM_OK,
    RESPONSE_FAVORITE_ADD_REMOVE_ARTIST_OK,
    RESPONSE_FAVORITE_ADD_REMOVE_AUDIOBOOK_OK,
    RESPONSE_FAVORITE_ADD_REMOVE_PLAYLIST_OK,
    RESPONSE_FAVORITE_ADD_REMOVE_PODCAST_OK,
    RESPONSE_FAVORITE_ADD_REMOVE_PODCAST_EPISODE_OK,
    RESPONSE_FAVORITE_ADD_REMOVE_TRACK_OK,
    RESPONSE_NOWPLAYING_NO_MEDIA_ALBUM,
    RESPONSE_NOWPLAYING_NO_MEDIA_ARTIST,
    RESPONSE_NOWPLAYING_NO_MEDIA_AUDIOBOOK,
    RESPONSE_NOWPLAYING_NO_MEDIA_PLAYLIST,
    RESPONSE_NOWPLAYING_NO_MEDIA_PODCAST,
    RESPONSE_NOWPLAYING_NO_MEDIA_PODCAST_EPISODE,
    RESPONSE_NOWPLAYING_NO_MEDIA_TRACK,
    RESPONSE_PLAYER_NOT_PLAYING_MEDIA,
    SERVICE_SPOTIFY_SAVE_ALBUM_FAVORITES,
    SERVICE_SPOTIFY_REMOVE_ALBUM_FAVORITES,
    SERVICE_SPOTIFY_FOLLOW_ARTISTS,
    SERVICE_SPOTIFY_UNFOLLOW_ARTISTS,
    SERVICE_SPOTIFY_SAVE_AUDIOBOOK_FAVORITES,
    SERVICE_SPOTIFY_REMOVE_AUDIOBOOK_FAVORITES,
    SERVICE_SPOTIFY_SAVE_EPISODE_FAVORITES,
    SERVICE_SPOTIFY_REMOVE_EPISODE_FAVORITES,
    SERVICE_SPOTIFY_FOLLOW_PLAYLIST,
    SERVICE_SPOTIFY_UNFOLLOW_PLAYLIST,
    SERVICE_SPOTIFY_SAVE_SHOW_FAVORITES,
    SERVICE_SPOTIFY_REMOVE_SHOW_FAVORITES,
    SERVICE_SPOTIFY_SAVE_TRACK_FAVORITES,
    SERVICE_SPOTIFY_REMOVE_TRACK_FAVORITES,
    SLOT_AREA,
    SLOT_ALBUM_TITLE,
    SLOT_ARTIST_TITLE,
    SLOT_ARTIST_URL,
    SLOT_AUDIOBOOK_TITLE,
    SLOT_AUDIOBOOK_URL,
    SLOT_AUTHOR_TITLE,
    SLOT_CHAPTER_TITLE,
    SLOT_EPISODE_TITLE,
    SLOT_EPISODE_URL,
    SLOT_FAVORITE_OPERATOR,
    SLOT_FLOOR,
    SLOT_IS_PUBLIC,
    SLOT_NAME,
    SLOT_PLAYLIST_TITLE,
    SLOT_PLAYLIST_URL,
    SLOT_PODCAST_TITLE,
    SLOT_PODCAST_URL,
    SLOT_PREFERRED_AREA_ID,
    SLOT_PREFERRED_FLOOR_ID,
    SLOT_SPOTIFYPLUS_MEDIA_TYPE,
    SLOT_TRACK_TITLE,
    SLOT_TRACK_URL,
    SPOTIFY_WEB_URL_PFX,
)

from .spotifyplusintenthandler import SpotifyPlusIntentHandler


class SpotifyPlusFavoriteAddRemove_Handler(SpotifyPlusIntentHandler):
    """
    Handles intents for SpotifyPlusFavoriteAddRemove.
    """
    def __init__(self, intentLoader:IntentLoader) -> None:
        """
        Initializes a new instance of the IntentHandler class.
        """
        # invoke base class method.
        super().__init__(intentLoader)

        # set intent handler basics.
        self.description = "Add / Remove the currently playing context type to / from Spotify user favorites."
        self.intent_type = INTENT_FAVORITE_ADD_REMOVE
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
            vol.Optional(SLOT_FAVORITE_OPERATOR): cv.string,
            vol.Optional(SLOT_SPOTIFYPLUS_MEDIA_TYPE): cv.string,
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
        favorite_operator:str = intentObj.slots.get(SLOT_FAVORITE_OPERATOR, {}).get(CONF_VALUE, "").lower()
        media_type:str = intentObj.slots.get(SLOT_SPOTIFYPLUS_MEDIA_TYPE, {}).get(CONF_VALUE, "").lower()

        # validations.
        if (favorite_operator not in [CONF_ADD, CONF_REMOVE]):        
            return await self.ReturnResponseByKey(intentObj, intentResponse, RESPONSE_FAVORITE_OPERATION_INVALID, IntentResponseErrorCode.FAILED_TO_HANDLE)

        # process based on media type.
        if (media_type == SpotifyMediaTypes.ALBUM.value):
            return await self.async_ProcessAlbum(intentObj, intentResponse, playerEntityState, favorite_operator)

        elif (media_type == SpotifyMediaTypes.ARTIST.value):
            return await self.async_ProcessArtist(intentObj, intentResponse, playerEntityState, favorite_operator)

        elif (media_type == SpotifyMediaTypes.AUDIOBOOK.value):
            return await self.async_ProcessAudiobook(intentObj, intentResponse, playerEntityState, favorite_operator)

        elif (media_type == SpotifyMediaTypes.PLAYLIST.value):
            return await self.async_ProcessPlaylist(intentObj, intentResponse, playerEntityState, favorite_operator)

        elif (media_type == SpotifyMediaTypes.PODCAST.value):
            return await self.async_ProcessPodcast(intentObj, intentResponse, playerEntityState, favorite_operator)

        elif (media_type == SpotifyMediaTypes.EPISODE.value):
            return await self.async_ProcessPodcastEpisode(intentObj, intentResponse, playerEntityState, favorite_operator)

        elif (media_type == SpotifyMediaTypes.TRACK.value):
            return await self.async_ProcessTrack(intentObj, intentResponse, playerEntityState, favorite_operator)

        else:
            return await self.ReturnResponseByKey(intentObj, intentResponse, RESPONSE_ERROR_MEDIA_TYPE_INVALID, IntentResponseErrorCode.FAILED_TO_HANDLE)


    async def async_ProcessAlbum(
        self, 
        intentObj: Intent, 
        intentResponse: IntentResponse,
        playerEntityState: State,
        favorite_operator: str,
        ) -> IntentResponse:
        """
        Handles the intent.

        Args:
            intentObj (Intent):
                Intent object.
            intentResponse (IntentResponse)
                Intent response object.
            playerEntityState (State):
                Target player entity state.
            favorite_operator (str):
                Favorite operator (e.g. add, remove).

        Returns:
            An IntentResponse object.
        """
        # is now playing item a track? if not, then we are done.
        item_type:str = playerEntityState.attributes.get(ATTR_SPOTIFYPLUS_ITEM_TYPE)
        if (item_type != SpotifyMediaTypes.TRACK.value):
            return await self.ReturnResponseByKey(intentObj, intentResponse, RESPONSE_NOWPLAYING_NO_MEDIA_ALBUM)

        # get now playing details.
        artist_name:str = playerEntityState.attributes.get(ATTR_MEDIA_ARTIST)
        artist_uri:str = playerEntityState.attributes.get(ATTR_SPOTIFYPLUS_ARTIST_URI)
        album_name:str = playerEntityState.attributes.get(ATTR_MEDIA_ALBUM_NAME)

        # get id portion of spotify uri value.
        artist_id:str = get_id_from_uri(artist_uri)

        # update slots with returned info.
        intentObj.slots[SLOT_ARTIST_TITLE] = { CONF_VALUE: artist_uri, CONF_TEXT: artist_name }
        intentObj.slots[SLOT_ARTIST_URL] = { CONF_VALUE: f"{SPOTIFY_WEB_URL_PFX}/{SpotifyMediaTypes.ARTIST.value}/{artist_id}", CONF_TEXT: "Spotify" }
        intentObj.slots[SLOT_ALBUM_TITLE] = { CONF_VALUE: "", CONF_TEXT: album_name }

        # trace.
        if (self.logsi.IsOn(SILevel.Verbose)):
            self.logsi.LogDictionary(SILevel.Verbose, STAppMessages.MSG_INTENT_HANDLER_SLOT_INFO % intentObj.intent_type, intentObj.slots, colorValue=SIColors.Khaki)

        # add / remove the favorite.
        if (favorite_operator == CONF_ADD):

            # set service name and build parameters.
            svcName:str = SERVICE_SPOTIFY_SAVE_ALBUM_FAVORITES
            svcData:dict = \
            {
                "entity_id": playerEntityState.entity_id,
            }

        elif (favorite_operator == CONF_REMOVE):

            # set service name and build parameters.
            svcName:str = SERVICE_SPOTIFY_REMOVE_ALBUM_FAVORITES
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
        
        # return intent response.
        return await self.ReturnResponseByKey(intentObj, intentResponse, RESPONSE_FAVORITE_ADD_REMOVE_ALBUM_OK)


    async def async_ProcessArtist(
        self, 
        intentObj: Intent, 
        intentResponse: IntentResponse,
        playerEntityState: State,
        favorite_operator: str,
        ) -> IntentResponse:
        """
        Handles the intent.

        Args:
            intentObj (Intent):
                Intent object.
            intentResponse (IntentResponse)
                Intent response object.
            playerEntityState (State):
                Target player entity state.
            favorite_operator (str):
                Favorite operator (e.g. add, remove).

        Returns:
            An IntentResponse object.
        """
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
        intentObj.slots[SLOT_ARTIST_TITLE] = { CONF_VALUE: artist_uri, CONF_TEXT: artist_name }
        intentObj.slots[SLOT_ARTIST_URL] = { CONF_VALUE: f"{SPOTIFY_WEB_URL_PFX}/{SpotifyMediaTypes.ARTIST.value}/{artist_id}", CONF_TEXT: "Spotify" }

        # trace.
        if (self.logsi.IsOn(SILevel.Verbose)):
            self.logsi.LogDictionary(SILevel.Verbose, STAppMessages.MSG_INTENT_HANDLER_SLOT_INFO % intentObj.intent_type, intentObj.slots, colorValue=SIColors.Khaki)

        # add / remove the favorite.
        if (favorite_operator == CONF_ADD):

            # set service name and build parameters.
            svcName:str = SERVICE_SPOTIFY_FOLLOW_ARTISTS
            svcData:dict = \
            {
                "entity_id": playerEntityState.entity_id,
            }

        elif (favorite_operator == CONF_REMOVE):

            # set service name and build parameters.
            svcName:str = SERVICE_SPOTIFY_UNFOLLOW_ARTISTS
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
           
        # return intent response.
        return await self.ReturnResponseByKey(intentObj, intentResponse, RESPONSE_FAVORITE_ADD_REMOVE_ARTIST_OK)


    async def async_ProcessAudiobook(
        self, 
        intentObj: Intent, 
        intentResponse: IntentResponse,
        playerEntityState: State,
        favorite_operator: str,
        ) -> IntentResponse:
        """
        Handles the intent.

        Args:
            intentObj (Intent):
                Intent object.
            intentResponse (IntentResponse)
                Intent response object.
            playerEntityState (State):
                Target player entity state.
            favorite_operator (str):
                Favorite operator (e.g. add, remove).

        Returns:
            An IntentResponse object.
        """
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

        # add / remove the favorite.
        if (favorite_operator == CONF_ADD):

            # set service name and build parameters.
            svcName:str = SERVICE_SPOTIFY_SAVE_AUDIOBOOK_FAVORITES
            svcData:dict = \
            {
                "entity_id": playerEntityState.entity_id,
            }

        elif (favorite_operator == CONF_REMOVE):

            # set service name and build parameters.
            svcName:str = SERVICE_SPOTIFY_REMOVE_AUDIOBOOK_FAVORITES
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
           
        # return intent response.
        return await self.ReturnResponseByKey(intentObj, intentResponse, RESPONSE_FAVORITE_ADD_REMOVE_AUDIOBOOK_OK)


    async def async_ProcessPlaylist(
        self, 
        intentObj: Intent, 
        intentResponse: IntentResponse,
        playerEntityState: State,
        favorite_operator: str,
        ) -> IntentResponse:
        """
        Handles the intent.

        Args:
            intentObj (Intent):
                Intent object.
            intentResponse (IntentResponse)
                Intent response object.
            playerEntityState (State):
                Target player entity state.
            favorite_operator (str):
                Favorite operator (e.g. add, remove).

        Returns:
            An IntentResponse object.
        """
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
        intentObj.slots[SLOT_PLAYLIST_TITLE] = { CONF_VALUE: playlist_uri, CONF_TEXT: playlist_name }
        intentObj.slots[SLOT_PLAYLIST_URL] = { CONF_VALUE: f"{SPOTIFY_WEB_URL_PFX}/{SpotifyMediaTypes.PLAYLIST.value}/{playlist_id}", CONF_TEXT: "Spotify" }

        # trace.
        if (self.logsi.IsOn(SILevel.Verbose)):
            self.logsi.LogDictionary(SILevel.Verbose, STAppMessages.MSG_INTENT_HANDLER_SLOT_INFO % intentObj.intent_type, intentObj.slots, colorValue=SIColors.Khaki)

        # add / remove the favorite.
        if (favorite_operator == CONF_ADD):

            # set service name and build parameters.
            svcName:str = SERVICE_SPOTIFY_FOLLOW_PLAYLIST
            svcData:dict = \
            {
                "entity_id": playerEntityState.entity_id,
                "public": is_public
            }

        elif (favorite_operator == CONF_REMOVE):

            # set service name and build parameters.
            svcName:str = SERVICE_SPOTIFY_UNFOLLOW_PLAYLIST
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
           
        # return intent response.
        return await self.ReturnResponseByKey(intentObj, intentResponse, RESPONSE_FAVORITE_ADD_REMOVE_PLAYLIST_OK)


    async def async_ProcessPodcast(
        self, 
        intentObj: Intent, 
        intentResponse: IntentResponse,
        playerEntityState: State,
        favorite_operator: str,
        ) -> IntentResponse:
        """
        Handles the intent.

        Args:
            intentObj (Intent):
                Intent object.
            intentResponse (IntentResponse)
                Intent response object.
            playerEntityState (State):
                Target player entity state.
            favorite_operator (str):
                Favorite operator (e.g. add, remove).

        Returns:
            An IntentResponse object.
        """
        # is now playing item an podcast? if not, then we are done.
        item_type:str = playerEntityState.attributes.get(ATTR_SPOTIFYPLUS_ITEM_TYPE)
        if (item_type != SpotifyMediaTypes.PODCAST.value):
            return await self.ReturnResponseByKey(intentObj, intentResponse, RESPONSE_NOWPLAYING_NO_MEDIA_PODCAST)

        # get now playing details.
        podcast_uri:str = playerEntityState.attributes.get(ATTR_SPOTIFYPLUS_CONTEXT_URI)
        podcast_name:str = playerEntityState.attributes.get(ATTR_MEDIA_ALBUM_NAME)

        # get id portion of spotify uri value.
        podcast_id:str = get_id_from_uri(podcast_uri)

        # update slots with returned info.
        intentObj.slots[SLOT_PODCAST_TITLE] = { CONF_VALUE: podcast_uri, CONF_TEXT: podcast_name }
        intentObj.slots[SLOT_PODCAST_URL] = { CONF_VALUE: f"{SPOTIFY_WEB_URL_PFX}/{SpotifyMediaTypes.SHOW.value}/{podcast_id}", CONF_TEXT: "Spotify" }

        # trace.
        if (self.logsi.IsOn(SILevel.Verbose)):
            self.logsi.LogDictionary(SILevel.Verbose, STAppMessages.MSG_INTENT_HANDLER_SLOT_INFO % intentObj.intent_type, intentObj.slots, colorValue=SIColors.Khaki)

        # add / remove the favorite.
        if (favorite_operator == CONF_ADD):

            # set service name and build parameters.
            svcName:str = SERVICE_SPOTIFY_SAVE_SHOW_FAVORITES
            svcData:dict = \
            {
                "entity_id": playerEntityState.entity_id,
            }

        elif (favorite_operator == CONF_REMOVE):

            # set service name and build parameters.
            svcName:str = SERVICE_SPOTIFY_REMOVE_SHOW_FAVORITES
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
           
        # return intent response.
        return await self.ReturnResponseByKey(intentObj, intentResponse, RESPONSE_FAVORITE_ADD_REMOVE_PODCAST_OK)


    async def async_ProcessPodcastEpisode(
        self, 
        intentObj: Intent, 
        intentResponse: IntentResponse,
        playerEntityState: State,
        favorite_operator: str,
        ) -> IntentResponse:
        """
        Handles the intent.

        Args:
            intentObj (Intent):
                Intent object.
            intentResponse (IntentResponse)
                Intent response object.
            playerEntityState (State):
                Target player entity state.
            favorite_operator (str):
                Favorite operator (e.g. add, remove).

        Returns:
            An IntentResponse object.
        """
        # is now playing item an podcast? if not, then we are done.
        item_type:str = playerEntityState.attributes.get(ATTR_SPOTIFYPLUS_ITEM_TYPE)
        if (item_type != SpotifyMediaTypes.PODCAST.value):
            return await self.ReturnResponseByKey(intentObj, intentResponse, RESPONSE_NOWPLAYING_NO_MEDIA_PODCAST_EPISODE)

        # get now playing details.
        podcast_uri:str = playerEntityState.attributes.get(ATTR_SPOTIFYPLUS_CONTEXT_URI)
        podcast_name:str = playerEntityState.attributes.get(ATTR_MEDIA_ALBUM_NAME)
        episode_name:str = playerEntityState.attributes.get(ATTR_MEDIA_TITLE)
        episode_uri:str = playerEntityState.attributes.get(ATTR_MEDIA_CONTENT_ID)

        # get id portion of spotify uri value.
        podcast_id:str = get_id_from_uri(podcast_uri)
        episode_id:str = get_id_from_uri(episode_uri)

        # update slots with returned info.
        intentObj.slots[SLOT_PODCAST_TITLE] = { CONF_VALUE: podcast_uri, CONF_TEXT: podcast_name }
        intentObj.slots[SLOT_PODCAST_URL] = { CONF_VALUE: f"{SPOTIFY_WEB_URL_PFX}/{SpotifyMediaTypes.SHOW.value}/{podcast_id}", CONF_TEXT: "Spotify" }
        intentObj.slots[SLOT_EPISODE_TITLE] = { CONF_VALUE: episode_uri, CONF_TEXT: episode_name }
        intentObj.slots[SLOT_EPISODE_URL] = { CONF_VALUE: f"{SPOTIFY_WEB_URL_PFX}/{SpotifyMediaTypes.EPISODE.value}/{episode_id}", CONF_TEXT: "Spotify" }

        # trace.
        if (self.logsi.IsOn(SILevel.Verbose)):
            self.logsi.LogDictionary(SILevel.Verbose, STAppMessages.MSG_INTENT_HANDLER_SLOT_INFO % intentObj.intent_type, intentObj.slots, colorValue=SIColors.Khaki)

        # add / remove the favorite.
        if (favorite_operator == CONF_ADD):

            # set service name and build parameters.
            svcName:str = SERVICE_SPOTIFY_SAVE_EPISODE_FAVORITES
            svcData:dict = \
            {
                "entity_id": playerEntityState.entity_id,
            }

        elif (favorite_operator == CONF_REMOVE):

            # set service name and build parameters.
            svcName:str = SERVICE_SPOTIFY_REMOVE_EPISODE_FAVORITES
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
           
        # return intent response.
        return await self.ReturnResponseByKey(intentObj, intentResponse, RESPONSE_FAVORITE_ADD_REMOVE_PODCAST_EPISODE_OK)


    async def async_ProcessTrack(
        self, 
        intentObj: Intent, 
        intentResponse: IntentResponse,
        playerEntityState: State,
        favorite_operator: str,
        ) -> IntentResponse:
        """
        Handles the intent.

        Args:
            intentObj (Intent):
                Intent object.
            intentResponse (IntentResponse)
                Intent response object.
            playerEntityState (State):
                Target player entity state.
            favorite_operator (str):
                Favorite operator (e.g. add, remove).

        Returns:
            An IntentResponse object.
        """
        # is now playing item a track? if not, then we are done.
        item_type:str = playerEntityState.attributes.get(ATTR_SPOTIFYPLUS_ITEM_TYPE)
        if (item_type != SpotifyMediaTypes.TRACK.value):
            return await self.ReturnResponseByKey(intentObj, intentResponse, RESPONSE_NOWPLAYING_NO_MEDIA_TRACK)

        # get now playing details.
        artist_name:str = playerEntityState.attributes.get(ATTR_MEDIA_ARTIST)
        artist_uri:str = playerEntityState.attributes.get(ATTR_SPOTIFYPLUS_ARTIST_URI)
        track_name:str = playerEntityState.attributes.get(ATTR_MEDIA_TITLE)
        track_uri:str = playerEntityState.attributes.get(ATTR_SPOTIFYPLUS_TRACK_URI_ORIGIN)

        # get id portion of spotify uri value.
        artist_id:str = get_id_from_uri(artist_uri)
        track_id:str = get_id_from_uri(track_uri)

        # update slots with returned info.
        intentObj.slots[SLOT_ARTIST_TITLE] = { CONF_VALUE: artist_uri, CONF_TEXT: artist_name }
        intentObj.slots[SLOT_ARTIST_URL] = { CONF_VALUE: f"{SPOTIFY_WEB_URL_PFX}/{SpotifyMediaTypes.ARTIST.value}/{artist_id}", CONF_TEXT: "Spotify" }
        intentObj.slots[SLOT_TRACK_TITLE] = { CONF_VALUE: track_uri, CONF_TEXT: track_name }
        intentObj.slots[SLOT_TRACK_URL] = { CONF_VALUE: f"{SPOTIFY_WEB_URL_PFX}/{SpotifyMediaTypes.TRACK.value}/{track_id}", CONF_TEXT: "Spotify" }

        # trace.
        if (self.logsi.IsOn(SILevel.Verbose)):
            self.logsi.LogDictionary(SILevel.Verbose, STAppMessages.MSG_INTENT_HANDLER_SLOT_INFO % intentObj.intent_type, intentObj.slots, colorValue=SIColors.Khaki)

        # add / remove the favorite.
        if (favorite_operator == CONF_ADD):

            # set service name and build parameters.
            svcName:str = SERVICE_SPOTIFY_SAVE_TRACK_FAVORITES
            svcData:dict = \
            {
                "entity_id": playerEntityState.entity_id,
            }

        elif (favorite_operator == CONF_REMOVE):

            # set service name and build parameters.
            svcName:str = SERVICE_SPOTIFY_REMOVE_TRACK_FAVORITES
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

        # return intent response.
        return await self.ReturnResponseByKey(intentObj, intentResponse, RESPONSE_FAVORITE_ADD_REMOVE_TRACK_OK)
