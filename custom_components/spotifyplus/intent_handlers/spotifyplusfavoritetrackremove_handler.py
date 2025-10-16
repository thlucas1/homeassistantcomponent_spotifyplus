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
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import intent
from homeassistant.helpers.intent import (
    IntentHandleError,
    IntentResponse, 
    _SlotsType,
)

from smartinspectpython.siauto import SILevel, SIColors

from spotifywebapipython import SpotifyMediaTypes

from ..appmessages import STAppMessages
from ..utils import get_id_from_uri
from ..const import (
    ATTR_SPOTIFYPLUS_ITEM_TYPE,
    ATTR_SPOTIFYPLUS_ARTIST_URI,
    ATTR_SPOTIFYPLUS_TRACK_URI_ORIGIN,
    CONF_TEXT,
    CONF_VALUE,
    DOMAIN,
    INTENT_FAVORITE_TRACK_REMOVE,
    PLATFORM_SPOTIFYPLUS,
    RESPONSE_ERROR_UNHANDLED,
    RESPONSE_NOWPLAYING_NO_MEDIA_TRACK,
    RESPONSE_PLAYER_NOT_PLAYING_MEDIA,
    SERVICE_SPOTIFY_REMOVE_TRACK_FAVORITES,
    SLOT_AREA,
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

from .spotifyplusintenthandler import SpotifyPlusIntentHandler, get_intent_response_resource


class SpotifyPlusFavoriteTrackRemove_Handler(SpotifyPlusIntentHandler):
    """
    Handles intents for SpotifyPlusFavoriteTrackRemove.
    """
    def __init__(self) -> None:
        """
        Initializes a new instance of the IntentHandler class.
        """
        # invoke base class method.
        super().__init__()

        # set intent handler basics.
        self.description = "Removes the currently playing track from Spotify user track favorites."
        self.intent_type = INTENT_FAVORITE_TRACK_REMOVE
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
            vol.Optional(SLOT_TRACK_TITLE): cv.string,
            vol.Optional(SLOT_TRACK_URL): cv.string,
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

            # is now playing item a track?
            item_type:str = playerEntityState.attributes.get(ATTR_SPOTIFYPLUS_ITEM_TYPE)
            if (item_type != SpotifyMediaTypes.TRACK.value):

                # no - requested info is not available.
                responseText = await get_intent_response_resource(RESPONSE_NOWPLAYING_NO_MEDIA_TRACK, slots, intentObj, PLATFORM_SPOTIFYPLUS)
                intentResponse.async_set_speech(responseText)
                self.logsi.LogObject(SILevel.Verbose, STAppMessages.MSG_INTENT_HANDLER_RESPONSE % (intentObj.intent_type), intentResponse, colorValue=SIColors.Khaki)
                return intentResponse

            # get now playing details.
            artist_name:str = playerEntityState.attributes.get(ATTR_MEDIA_ARTIST)
            artist_uri:str = playerEntityState.attributes.get(ATTR_SPOTIFYPLUS_ARTIST_URI)
            track_name:str = playerEntityState.attributes.get(ATTR_MEDIA_TITLE)
            track_uri:str = playerEntityState.attributes.get(ATTR_SPOTIFYPLUS_TRACK_URI_ORIGIN)

            # get id portion of spotify uri value.
            artist_id:str = get_id_from_uri(artist_uri)
            track_id:str = get_id_from_uri(track_uri)

            # update slots with returned info.
            slots[SLOT_ARTIST_TITLE] = { CONF_TEXT: artist_name, CONF_VALUE: artist_uri }
            slots[SLOT_ARTIST_URL] = { CONF_TEXT: "Spotify", CONF_VALUE: f"{SPOTIFY_WEB_URL_PFX}/{SpotifyMediaTypes.ARTIST.value}/{artist_id}" }
            slots[SLOT_TRACK_TITLE] = { CONF_TEXT: track_name, CONF_VALUE: track_uri }
            slots[SLOT_TRACK_URL] = { CONF_TEXT: "Spotify", CONF_VALUE: f"{SPOTIFY_WEB_URL_PFX}/{SpotifyMediaTypes.TRACK.value}/{track_id}" }

            # trace.
            if (self.logsi.IsOn(SILevel.Verbose)):
                self.logsi.LogDictionary(SILevel.Verbose, STAppMessages.MSG_INTENT_HANDLER_SLOT_INFO % intentObj.intent_type, slots, colorValue=SIColors.Khaki)

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
           
            # trace.
            if (self.logsi.IsOn(SILevel.Verbose)):
                self.logsi.LogDictionary(SILevel.Verbose, STAppMessages.MSG_INTENT_HANDLER_SLOT_INFO % intentObj.intent_type, slots, colorValue=SIColors.Khaki)

            # return intent response.
            intentResponse.speech_slots = slots
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
