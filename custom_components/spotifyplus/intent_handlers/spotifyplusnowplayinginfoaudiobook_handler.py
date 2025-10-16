import voluptuous as vol

from homeassistant.components.media_player import MediaPlayerEntityFeature
from homeassistant.components.media_player.const import (
    ATTR_MEDIA_ALBUM_NAME,
    ATTR_MEDIA_ARTIST,
    ATTR_MEDIA_CONTENT_ID,
    ATTR_MEDIA_TITLE,
)
from homeassistant.core import State
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import intent
from homeassistant.helpers.intent import (
    IntentHandleError,
    IntentResponse, 
    _SlotsType,
)
from homeassistant.const import (
    STATE_PAUSED,
    STATE_PLAYING,
)

from smartinspectpython.siauto import SILevel, SIColors

from spotifywebapipython.spotifymediatypes import SpotifyMediaTypes

from ..appmessages import STAppMessages
from ..utils import get_id_from_uri
from ..const import (
    ATTR_SPOTIFYPLUS_ITEM_TYPE,
    ATTR_SPOTIFYPLUS_CONTEXT_URI,
    CONF_TEXT,
    CONF_VALUE,
    INTENT_NOWPLAYING_INFO_AUDIOBOOK,
    PLATFORM_SPOTIFYPLUS,
    RESPONSE_ERROR_UNHANDLED,
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

from .spotifyplusintenthandler import SpotifyPlusIntentHandler, get_intent_response_resource


class SpotifyPlusNowPlayingInfoAudiobook_Handler(SpotifyPlusIntentHandler):
    """
    Handles intents for SpotifyPlusNowPlayingInfoAudiobook.
    """
    def __init__(self) -> None:
        """
        Initializes a new instance of the IntentHandler class.
        """
        # invoke base class method.
        super().__init__()

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


    async def async_handle(self, intentObj: intent.Intent) -> IntentResponse:
        """
        Handles the intent.

        Args:
            intentObj (Intent):
                Intent object.
        """
        playerEntityState:State = None
        slots:_SlotsType = None

        try:

            # trace.
            self.logsi.EnterMethod(SILevel.Debug, intentObj.intent_type, colorValue=SIColors.Khaki)
            self.logsi.LogVerbose(STAppMessages.MSG_INTENT_HANDLE_REQUEST % intentObj.intent_type, colorValue=SIColors.Khaki)
            self.logsi.LogObject(SILevel.Verbose, STAppMessages.MSG_INTENT_HANDLE_REQUEST_PARMS % intentObj.intent_type, intentObj, colorValue=SIColors.Khaki)
            self.logsi.LogDictionary(SILevel.Verbose, STAppMessages.MSG_INTENT_HANDLE_REQUEST_SLOTS % intentObj.intent_type, intentObj.slots, colorValue=SIColors.Khaki)

            # create intent response object.
            intentResponse:IntentResponse = intentObj.create_response()

            # invoke base class method to resolve the player entity.
            intentResponse, slots, playerEntityState = await super().async_get_matching_player_state(
                intentObj,
                intentResponse,
                slots=intentObj.slots,
                desiredFeatures=MediaPlayerEntityFeature.PLAY_MEDIA,
                desiredStates=[STATE_PLAYING, STATE_PAUSED],
                desiredStateResponseKey=RESPONSE_PLAYER_NOT_PLAYING_MEDIA,
            )

            # if media player was not resolved, then we are done;
            # note that the base class method above already called `async_set_speech` with a response.
            if playerEntityState is None:
                return intentResponse
            
            # get optional arguments (if provided).
            # n/a

            # is now playing item an audiobook?
            item_type:str = playerEntityState.attributes.get(ATTR_SPOTIFYPLUS_ITEM_TYPE)
            if (item_type != SpotifyMediaTypes.AUDIOBOOK.value):

                # no - requested info is not available.
                responseText = await get_intent_response_resource(RESPONSE_NOWPLAYING_NO_MEDIA_AUDIOBOOK, slots, intentObj, PLATFORM_SPOTIFYPLUS)
                intentResponse.async_set_speech(responseText)
                self.logsi.LogObject(SILevel.Verbose, STAppMessages.MSG_INTENT_HANDLER_RESPONSE % (intentObj.intent_type), intentResponse, colorValue=SIColors.Khaki)
                return intentResponse

            # example:
            # sp_item_type: audiobook
            # media_content_id: spotify:episode:3npL6aA9rshrP85Gl1EK1V
            # media_title: Chapter 5
            # media_artist: Terry Brooks
            # media_album_name: The Elfstones of Shannara
            # sp_context_uri: spotify:show:74aydHJKgYz3AIq3jjBSv1

            # get now playing details.
            audiobook_uri:str = playerEntityState.attributes.get(ATTR_SPOTIFYPLUS_CONTEXT_URI)
            audiobook_name:str = playerEntityState.attributes.get(ATTR_MEDIA_ALBUM_NAME)
            author_name:str = playerEntityState.attributes.get(ATTR_MEDIA_ARTIST)
            chapter_uri:str = playerEntityState.attributes.get(ATTR_MEDIA_CONTENT_ID)
            chapter_name:str = playerEntityState.attributes.get(ATTR_MEDIA_TITLE)

            # get id portion of spotify uri value.
            audiobook_id:str = get_id_from_uri(audiobook_uri)

            # update slots with returned info.
            slots[SLOT_AUDIOBOOK_TITLE] = { CONF_TEXT: audiobook_name, CONF_VALUE: audiobook_uri }
            slots[SLOT_AUDIOBOOK_URL] = { CONF_TEXT: "Spotify", CONF_VALUE: f"{SPOTIFY_WEB_URL_PFX}/{SpotifyMediaTypes.SHOW.value}/{audiobook_id}" }
            slots[SLOT_AUTHOR_TITLE] = { CONF_TEXT: author_name, CONF_VALUE: "" }
            slots[SLOT_CHAPTER_TITLE] = { CONF_TEXT: chapter_name, CONF_VALUE: chapter_uri }

            # trace.
            if (self.logsi.IsOn(SILevel.Verbose)):
                self.logsi.LogDictionary(SILevel.Verbose, STAppMessages.MSG_INTENT_HANDLER_SLOT_INFO % intentObj.intent_type, slots, colorValue=SIColors.Khaki)

            # return intent response.
            intentResponse.speech_slots = slots
            responseText = await get_intent_response_resource(RESPONSE_NOWPLAYING_INFO_AUDIOBOOK, slots, intentObj, PLATFORM_SPOTIFYPLUS)
            intentResponse.async_set_speech(responseText)
            self.logsi.LogObject(SILevel.Verbose, STAppMessages.MSG_INTENT_HANDLER_RESPONSE % (intentObj.intent_type), intentResponse, colorValue=SIColors.Khaki)
            return intentResponse

        except HomeAssistantError: raise  # pass handled exceptions on thru
        except Exception as ex:

            # log exception, but not to system logger as HA will take care of it.
            self.logsi.LogException(STAppMessages.MSG_INTENT_HANDLER_EXCEPTION % (intentObj.intent_type, str(ex)), ex, logToSystemLogger=False, colorValue=SIColors.Khaki)
            raise IntentHandleError("Intent handler error for \"%s\"" % (intentObj.intent_type), RESPONSE_ERROR_UNHANDLED)

        finally:

            # trace.
            self.logsi.LeaveMethod(SILevel.Debug, intentObj.intent_type, colorValue=SIColors.Khaki)
