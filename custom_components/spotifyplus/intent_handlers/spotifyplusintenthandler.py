from abc import abstractmethod

from homeassistant.components.media_player.const import MediaPlayerState
from homeassistant.components.media_player import MediaPlayerEntityFeature
from homeassistant.core import State
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_registry import RegistryEntry
from homeassistant.helpers.template import Template
from homeassistant.helpers.intent import (
    Intent, 
    IntentError,
    IntentHandler, 
    IntentResponse, 
    IntentResponseErrorCode,
    IntentResponseType,
    MatchFailedReason,
    MatchTargetsConstraints, 
    MatchTargetsPreferences, 
    MatchTargetsResult,
    MatchFailedError,
    MatchTargetsResult,
    async_match_targets,
)

from ..appmessages import STAppMessages
from ..const import (
    ATTR_SPOTIFYPLUS_USER_PRODUCT,
    CONF_TEXT,
    CONF_VALUE,
    DOMAIN_MEDIA_PLAYER,
    PLATFORM_SPOTIFYPLUS,
    RESPONSE_ERROR_FAILED_TO_HANDLE,
    RESPONSE_PLAYER_FEATURES_NOT_SUPPORTED,
    RESPONSE_PLAYER_NOT_MATCHED,
    RESPONSE_PLAYER_NOT_MATCHED_AREA,
    RESPONSE_SPOTIFY_PREMIUM_REQUIRED,
    SLOT_AREA,
    SLOT_ERROR_FEATURES,
    SLOT_ERROR_INFO,
    SLOT_ERROR_STATES,
    SLOT_FLOOR,
    SLOT_NAME,
    SLOT_PREFERRED_AREA_ID,
    SLOT_PREFERRED_FLOOR_ID,
    SLOT_TARGET_PLAYER,
)
from ..intent_loader import (
    LanguageIntents,
    IntentLoader,
)

import logging
_LOGGER = logging.getLogger(__name__)

# get smartinspect logger reference; create a new session for this module name.
from smartinspectpython.siauto import SIAuto, SILevel, SISession, SIMethodParmListContext, SIColors
_logsi:SISession = SIAuto.Si.GetSession(__name__)
if (_logsi == None):
    _logsi = SIAuto.Si.AddSession(__name__, True)
_logsi.SystemLogger = _LOGGER


class SpotifyPlusIntentHandler(IntentHandler):
    """
    Base class that handles intents for the SpotifyPlus integration.
    """
    def __init__(
        self, 
        intentLoader:IntentLoader,
        ) -> None:
        """
        Initializes a new instance of the class.

        Args:
            intentLoader (IntentLoader):
                A IntentLoader instance that loads our platform intents from custom_sentences.
        """
        # set trace reference.
        self.logsi = _logsi

        # store intent loader reference.
        self._IntentLoader = intentLoader

        # set intent handler basics.
        # these should be overridden in the inheriting class, but are here for validation.
        self.platforms = {PLATFORM_SPOTIFYPLUS}
        self.intent_type = "INTENT_TYPE_NOT_SET_IN_INHERITING_CLASS"
        self.description = "This description should be overridden in the inheriting class!"


    @abstractmethod
    async def async_HandleIntent(
        self, 
        intentObj: Intent, 
        intentResponse: IntentResponse
        ) -> IntentResponse:
        """
        Subclasses must implement this method to handle the intent.

        This method is called from the `async_handle` method, and is wrapped in a `try...except`
        block to automatically capture exceptions and return an error response.

        Args:
            intentObj (Intent):
                Intent object.
            intentResponse (IntentResponse):
                Intent response object.

        Returns:
            An IntentResponse object.
        """
        raise NotImplementedError()


    async def async_handle(
        self, 
        intentObj:Intent
        ) -> IntentResponse:
        """
        Handles the intent.

        Args:
            intentObj (Intent):
                Intent object.

        Returns:
            An IntentResponse object.
        """
        # create intent response object.
        intentResponse = intentObj.create_response()

        try:

            # trace.
            self.logsi.EnterMethod(SILevel.Debug, intentObj.intent_type, colorValue=SIColors.Khaki)
            self.logsi.LogVerbose(STAppMessages.MSG_INTENT_HANDLE_REQUEST % intentObj.intent_type, colorValue=SIColors.Khaki)
            self.logsi.LogObject(SILevel.Verbose, STAppMessages.MSG_INTENT_HANDLE_REQUEST_PARMS % intentObj.intent_type, intentObj, colorValue=SIColors.Khaki)
            self.logsi.LogDictionary(SILevel.Verbose, STAppMessages.MSG_INTENT_HANDLE_REQUEST_SLOTS % intentObj.intent_type, intentObj.slots, colorValue=SIColors.Khaki)

            # call internal method to handle the intent, and return the response.
            return await self.async_HandleIntent(intentObj, intentResponse)

        except IntentError as ex:

            # anything that inherits from IntentError: MatchFailedError, NoStatesMatchedError, etc.

            # trace.
            self.logsi.LogException(STAppMessages.MSG_INTENT_HANDLER_EXCEPTION % (intentObj.intent_type, str(ex)), ex, logToSystemLogger=False, colorValue=SIColors.Khaki)
            raise

        except Exception as ex:

            # determine type of exception.
            # if HA exception, then do not log to the system logger since HA has already done that.
            logToSystemLogger = True
            if (isinstance(ex, HomeAssistantError)):
                logToSystemLogger = False

            # trace.
            self.logsi.LogException(STAppMessages.MSG_INTENT_HANDLER_EXCEPTION % (intentObj.intent_type, str(ex)), ex, logToSystemLogger=logToSystemLogger, colorValue=SIColors.Khaki)

            # update slot error details.
            intentObj.slots[SLOT_ERROR_INFO] = { CONF_VALUE: RESPONSE_ERROR_FAILED_TO_HANDLE, CONF_TEXT: str(ex) }

            # return intent response.
            return await self.ReturnResponseByKey(intentObj, intentResponse, RESPONSE_ERROR_FAILED_TO_HANDLE, IntentResponseErrorCode.FAILED_TO_HANDLE)

        finally:

            # trace.
            self.logsi.LeaveMethod(SILevel.Debug, intentObj.intent_type, colorValue=SIColors.Khaki)


    async def async_GetMatchingPlayerState(
        self, 
        intentObj:Intent,
        intentResponse:IntentResponse,
        desiredFeatures:MediaPlayerEntityFeature=None,
        desiredStates:list[MediaPlayerState]=None,
        desiredStateResponseKey:str=None,
        requiresSpotifyPremium:bool=False,
        ) -> State | None:
        """
        Get matching player entity state, if one exists.

        Args:
            intentObj (Intent):
                Intent object.
            intentResponse (IntentResponse):
                Intent response object that will be returned if an error occurs.
            desiredFeatures (MediaPlayerEntityFeature):
                Media player Features that are required for the match (e.g. MediaPlayerEntityFeature.PLAY | MediaPlayerEntityFeature.PAUSE).
            desiredStates (list[MediaPlayerState]):
                A list of media player states that are required for the match (e.g. [STATE_PLAYING, STATE_PAUSED]).
            desiredStateResponseKey (str):
                Response message key that will be loaded and sent if the `desiredFeatures` are not supported.
            requiresSpotifyPremium (bool):
                If true, a check will be made to ensure the user is a Spotify premium member and raise an exception if not.

        Returns:
            The resolved SpotifyPlus media player entity state if one exists; otherwise, None.
        """
        methodParms:SIMethodParmListContext = None
        
        try:

            # trace.
            methodParms = _logsi.EnterMethodParmList(SILevel.Debug, colorValue=SIColors.Khaki)
            methodParms.AppendKeyValue("intent_type", intentObj.intent_type)
            methodParms.AppendKeyValue("language", intentObj.language)
            methodParms.AppendKeyValue("desiredFeatures", desiredFeatures)
            methodParms.AppendKeyValue("desiredStates", desiredStates)
            methodParms.AppendKeyValue("desiredStateResponseKey", desiredStateResponseKey)
            methodParms.AppendKeyValue("requiresSpotifyPremium", requiresSpotifyPremium)
            _logsi.LogMethodParmList(SILevel.Verbose, "Resolving matching player state for intent: \"%s\"" % (intentObj.intent_type), methodParms, colorValue=SIColors.Khaki)

            # validate slot arguments.
            if (self.logsi.IsOn(SILevel.Verbose)):
                self.logsi.LogDictionary(SILevel.Verbose, "Validating slot arguments for intent: \"%s\"" % intentObj.intent_type, intentObj.slots, colorValue=SIColors.Khaki)
            slots = self.async_validate_slots(intentObj.slots)

            # get player name / area / floor slot arguments.
            # note that HA conversation agent requires specific slot id's to perform it's magic
            # when resolving entity_id's related to the following: "name", "floor", "area".
            # if you customize outside of those values then entity matching will not work; you 
            # have to define custom lists in order for things to match!
            player_name: str | None = slots.get(SLOT_NAME, {}).get(CONF_VALUE, "")
            area_id = slots.get(SLOT_AREA, {}).get(CONF_VALUE, "")
            floor_id = slots.get(SLOT_FLOOR, {}).get(CONF_VALUE, "")

            # update target player slot in case we have any errors.
            slots[SLOT_TARGET_PLAYER] = {
                CONF_VALUE: "unknown",
                CONF_TEXT: player_name + area_id + floor_id,  # only 1 should be populated, others are empty strings.
            }

            # build matching entities criteria.
            matchConstraints = MatchTargetsConstraints(
                name=player_name,
                area_name=area_id,
                floor_name=floor_id,
                domains={DOMAIN_MEDIA_PLAYER},
                assistant=intentObj.assistant,
                #features=desiredFeatures,
                single_target=True,
            )
            if (self.logsi.IsOn(SILevel.Verbose)):
                self.logsi.LogObject(SILevel.Verbose, STAppMessages.MSG_INTENT_MATCH_CONSTRAINTS_REQ % intentObj.intent_type, matchConstraints, colorValue=SIColors.Khaki)

            # find matching entities; this will try to match a media player entity
            # to the desired spoken player name / area / floor value.
            # it seems to match on friendly name, alias(es), and exact entity id.
            matchResult:MatchTargetsResult = async_match_targets(
                intentObj.hass,
                matchConstraints,
                MatchTargetsPreferences(
                    area_id=slots.get(SLOT_PREFERRED_AREA_ID, {}).get(CONF_VALUE),
                    floor_id=slots.get(SLOT_PREFERRED_FLOOR_ID, {}).get(CONF_VALUE),
                ),
            )
            if (self.logsi.IsOn(SILevel.Verbose)):
                self.logsi.LogObject(SILevel.Verbose, STAppMessages.MSG_INTENT_MATCH_CONSTRAINTS_RSLT % (intentObj.intent_type, str(matchResult.is_match), str(matchResult.no_match_reason), str(matchResult.no_match_name)), matchResult, colorValue=SIColors.Khaki)

            playerEntityState:State = None
            playerEntity:RegistryEntry = None
            resolvedDesc:str = None

            # did we find a matching entity?
            if matchResult.is_match:

                # yes - let's verify the matched entity is an active spotifyplus media player.
                # the HA matching engine is not great at matching by platform!
                playerEntityState = matchResult.states[0]
                playerEntity = get_registry_entry_media_player(intentObj, platform=PLATFORM_SPOTIFYPLUS, entity_id=playerEntityState.entity_id)
                resolvedDesc = "MatchTargetsResult"

            else:

                # determine why contraints were not matched.
                if matchResult.no_match_reason == MatchFailedReason.AREA:

                    # media player entity not found for specified area.
                    #raise MatchFailedError(result=matchResult, constraints=matchConstraints)
                    intentResponse = await self.ReturnResponseByKey(intentObj, intentResponse, RESPONSE_PLAYER_NOT_MATCHED_AREA, IntentResponseErrorCode.NO_VALID_TARGETS)
                    return None

                elif matchResult.no_match_reason == MatchFailedReason.ASSISTANT:

                    # media player entity has not been exposed to HA Voice Assist.
                    # raise HA MatchFailedError, which will cause the `conversation.default_agent` logic
                    # to read `response: -> errors: -> no_x_exposed:` key message.
                    raise MatchFailedError(result=matchResult, constraints=matchConstraints)

                    # media player entity has not been exposed to HA Voice Assist.
                    # intentResponse = await self.ReturnResponseByKey(intentObj, intentResponse, RESPONSE_PLAYER_NOT_EXPOSED_TO_VOICE, IntentResponseErrorCode.NO_VALID_TARGETS)
                    # return None

                elif matchResult.no_match_reason == MatchFailedReason.MULTIPLE_TARGETS:

                    # if multiple targets matched, then loop through them to find the
                    # first SpotifyPlus platform.
                    for stateEntry in matchResult.states:
                        playerEntity = get_registry_entry_media_player(intentObj, platform=PLATFORM_SPOTIFYPLUS, entity_id=stateEntry.entity_id)
                        if (playerEntity):
                            playerEntityState = stateEntry
                            resolvedDesc = "MatchTargetsResult (First of Multiple)"
                            break

                else:

                    # no - search for the first active spotifyplus media player entity.
                    playerEntity = get_registry_entry_media_player(intentObj, platform=PLATFORM_SPOTIFYPLUS)
                    if (playerEntity):
                        playerEntityState = intentObj.hass.states.get(playerEntity.entity_id)
                        resolvedDesc = "RegistryEntry"

            # if player not found, then give up and inform the user.
            if (playerEntity is None):
                intentResponse = await self.ReturnResponseByKey(intentObj, intentResponse, RESPONSE_PLAYER_NOT_MATCHED, IntentResponseErrorCode.NO_VALID_TARGETS)
                return None

            # trace.
            if (self.logsi.IsOn(SILevel.Verbose)):
                self.logsi.LogObject(SILevel.Verbose, "Resolved player state for entity_id: \"%s\" (%s)" % (playerEntityState.entity_id, resolvedDesc), playerEntityState, colorValue=SIColors.Khaki)

            # update target player slot that contains the selected player info.
            # note we will use the friendly name / area / floor value supplied, 
            # and just update the entity_id value.
            slots[SLOT_TARGET_PLAYER] = {
                CONF_VALUE: playerEntityState.entity_id,
                CONF_TEXT: player_name + area_id + floor_id,  # only 1 should be populated, others are empty strings.
            }

            # update slots with target media player info.
            intentObj.slots.update(slots)
            intentResponse.speech_slots = slots

            # is spotify premium account required for this function?
            # we check this BEFORE the features supported check, otherwise it would
            # always hit the features not supported since free accounts don't support 
            # player features.  it's a more meaningful message to say that the "spotify
            # premium is required for this" versus "feature x not supported".
            if (requiresSpotifyPremium):
                account_type:str = playerEntityState.attributes.get(ATTR_SPOTIFYPLUS_USER_PRODUCT)
                if ((account_type or "").lower().find("premium") == -1):
                    intentResponse = await self.ReturnResponseByKey(intentObj, intentResponse, RESPONSE_SPOTIFY_PREMIUM_REQUIRED, IntentResponseErrorCode.NO_VALID_TARGETS)
                    return None

            # do we need to check for desired features?
            if (desiredFeatures is not None):
                
                # are all desired features supported for this player? if not, then we are done.
                if (playerEntity.supported_features & desiredFeatures) != desiredFeatures:

                    # extract and format the names of desired features.
                    featureNames = ", ".join(
                        feature.name.replace("_", " ").lower()
                        for feature in MediaPlayerEntityFeature
                        if feature & desiredFeatures
                    )

                    # media player does not support requested features.
                    intentObj.slots[SLOT_ERROR_FEATURES] = { CONF_VALUE: RESPONSE_PLAYER_FEATURES_NOT_SUPPORTED, CONF_TEXT: featureNames }
                    intentResponse = await self.ReturnResponseByKey(intentObj, intentResponse, RESPONSE_PLAYER_FEATURES_NOT_SUPPORTED, IntentResponseErrorCode.NO_VALID_TARGETS)
                    return None

            # do we need to check player state?
            if (desiredStates is not None):

                # is media player state in the desired state (e.g. playing? paused? etc)?
                if (playerEntityState.state not in desiredStates):
                    intentObj.slots[SLOT_ERROR_STATES] = { CONF_VALUE: desiredStateResponseKey, CONF_TEXT: ", ".join(lbl for lbl in desiredStates).lower() }
                    intentResponse = await self.ReturnResponseByKey(intentObj, intentResponse, desiredStateResponseKey, IntentResponseErrorCode.FAILED_TO_HANDLE)
                    return None

            # trace.
            if (self.logsi.IsOn(SILevel.Verbose)):
                self.logsi.LogDictionary(SILevel.Verbose, STAppMessages.MSG_INTENT_HANDLER_SLOT_INFO % intentObj.intent_type, intentObj.slots, colorValue=SIColors.Khaki)

            # return response and the found player entity.
            return playerEntityState

        finally:

            # trace.
            self.logsi.LeaveMethod(SILevel.Debug, colorValue=SIColors.Khaki)


    async def ReturnResponseByKey(
        self,
        intentObj:Intent,
        intentResponse:IntentResponse,
        responseKey:str,
        responseErrorCode:IntentResponseErrorCode=None,
    ) -> IntentResponse | None:
        """
        Look up a response template in `custom_sentences/<language>/*.yaml` files by a key value,
        render it (with template support), and sets the intent response to return the message.

        If the `responseErrorCode` argument is specified, the intent response is updated to return
        a response type of error, and the error code set with the `responseErrorCode` value.  
        
        In the HA Companion App Assist, the message background is red if a `responseErrorCode`
        argument value is passed; otherwise, the background is black.

        Args:
            intentObj (Intent|None):
                Intent object that is handling the request.
            intentResponse (IntentResponse):
                Intent response object.
            responseKey (str):
                Intent Response key to find; this value is case-sensitive.
            responseErrorCode (IntentResponseErrorCode)
                The IntentResponseErrorCode value to use for the response error code;
                defaults to `FAILED_TO_HANDLE` if not set.

        Returns:
            An IntentResponse object with the response.
        """
        # trace.
        if (self.logsi.IsOn(SILevel.Verbose)):
            self.logsi.LogDictionary(SILevel.Verbose, STAppMessages.MSG_INTENT_HANDLER_SLOT_INFO % intentObj.intent_type, intentObj.slots, colorValue=SIColors.Khaki)

        # if response error code set, then treat it as an error.
        if (responseErrorCode is not None):
            intentResponse.response_type = IntentResponseType.ERROR
            intentResponse.error_code = responseErrorCode

        # get the response code message text, and update the intent response.
        responseText = await self.GetIntentResponseByKey(intentObj, responseKey)
        intentResponse.async_set_speech(responseText)
        if (self.logsi.IsOn(SILevel.Verbose)):
            self.logsi.LogObject(SILevel.Verbose, STAppMessages.MSG_INTENT_HANDLER_RESPONSE % (intentObj.intent_type), intentResponse, colorValue=SIColors.Khaki)

        # return response.
        return intentResponse


    async def GetIntentResponseByKey(
        self,
        intentObj:Intent,
        responseKey:str,
    ) -> str | None:
        """
        Look up a response template in `custom_sentences/<language>/*.yaml` files by a key value
        and render it (with template support).

        Args:
            intentObj (Intent|None):
                Intent object that is handling the request.
            responseKey (str):
                Intent Response key to find; this value is case-sensitive.

        Returns:
            A rendered template string for the response key if found; otherwise, a default English 
            message stating that the response key could not be found.

        Response key templates may be nested using the following schemas.
        This is also the search prevalence heirarchy, in that the first layout that contains
        the response key will be the value that is used.
        - intent-specific: `responses -> intents -> MyIntentName -> my_message_key: "My message text"`
        - platform-specific: `responses -> MyPlatform -> my_message_key: "My message text"`
        - generic-response: `responses -> my_message_key: "My message text"`
        """
        methodParms:SIMethodParmListContext = None

        # default result if response key could not be resolved.
        result:str = "Resource message for response key \"%s\" could not be found." % responseKey
        
        try:

            # trace.
            methodParms = _logsi.EnterMethodParmList(SILevel.Debug, colorValue=SIColors.Khaki)
            methodParms.AppendKeyValue("responseKey", responseKey)
            methodParms.AppendKeyValue("intent_type", intentObj.intent_type)
            methodParms.AppendKeyValue("language", intentObj.language)
            _logsi.LogMethodParmList(SILevel.Verbose, "Loading response text for response key: \"%s\" (language=%s)" % (responseKey, intentObj.language), methodParms, colorValue=SIColors.Khaki)

            # validations.
            language = intentObj.language
            intent_type = intentObj.intent_type

            # get intent data; if none found, then return default message.
            langIntents:LanguageIntents = await self._IntentLoader.async_get_or_load_intents(language)
            if (langIntents is None):
                return result

            # search for intent response key using the following search heirarchy:
            # - intent-response:   `responses -> intents -> MyIntentName -> my_message_key: "My message text"`
            # - platform-response: `responses -> MyPlatform -> my_message_key: "My message text"`
            # - error-response:    `responses -> errors -> my_message_key: "My message text"`
            # - generic-response:  `responses -> my_message_key: "My message text"`

            # create searchable dictionarys of response data.
            intents_block = langIntents.intent_responses or {}
            platform_block = langIntents.platform_responses or {}
            error_block = langIntents.error_responses or {}
            generic_block = langIntents.generic_responses or {}

            # check for response key in each response data dictionary.
            candidates = []

            # check for response key message at the intent level (intent-response).
            if intent_type in intents_block:
                intent_dict = intents_block[intent_type] or {}
                if responseKey in intent_dict:
                    _logsi.LogDebug("Found candidate for response key (intent-response) \"%s\": \"%s\"" % (responseKey, intent_dict[responseKey]), colorValue=SIColors.Khaki)
                    candidates.append(intent_dict[responseKey])

            # check for response key message by platform (platform-response).
            if responseKey in platform_block:
                _logsi.LogDebug("Found candidate for response key (platform-response) \"%s\": \"%s\"" % (responseKey, platform_block[responseKey]), colorValue=SIColors.Khaki)
                candidates.append(platform_block[responseKey])

            # check for response key message in response errors (error-response):
            if responseKey in error_block:
                _logsi.LogDebug("Found candidate for response key (error-response) \"%s\": \"%s\"" % (responseKey, error_block[responseKey]), colorValue=SIColors.Khaki)
                candidates.append(error_block[responseKey])

            # check for response key message by simple lookup under responses (generic-response):
            if responseKey in generic_block and isinstance(generic_block[responseKey], str):
                _logsi.LogDebug("Found candidate for response key (generic-response) \"%s\": \"%s\"" % (responseKey, generic_block[responseKey]), colorValue=SIColors.Khaki)
                candidates.append(generic_block[responseKey])

            # trace.
            _logsi.LogDictionary(SILevel.Verbose,"Responses candidates dictionary", candidates, prettyPrint=True, colorValue=SIColors.Khaki)

            # did we find any matching candidates?
            if candidates:

                # render the first candidate entry found.
                template_text = candidates[0]

                # just in case there are exceptions processing the template.
                # e.g. "dict object' has no attribute 'name'" <- slot reference error.
                try:

                    # use Home Assistant Template helper to render, with access to hass template functions.
                    # provide `slots` to the template context as well (like intent scripts do).
                    tpl = Template(template_text, intentObj.hass)
                    rendered = tpl.async_render({"slots": intentObj.slots}, parse_result=False)
                    result = rendered

                except Exception as ex:

                    # trace.
                    _logsi.LogException("Intent handler GetIntentResponseByKey template render exception: %s" % (str(ex)), ex, logToSystemLogger=False, colorValue=SIColors.Khaki)

                    # ignore template render exceptions.
                    # we will use the resource message as-is, and let the user figure it out.
                    # HA will take care of logging the exception to the system log.
                    result = template_text

            # return result text.
            _logsi.LogText(SILevel.Verbose,"Response text for response key \"%s\": \"%s\"" % (responseKey, result), result, colorValue=SIColors.Khaki)
            return result

        except Exception as ex:
            
            # trace.
            _logsi.LogException("Intent handler GetIntentResponseByKey exception: %s" % (str(ex)), ex, logToSystemLogger=False, colorValue=SIColors.Khaki)

            # ignore exceptions
            return "Could not find intent resource message for response key \"%s\" (language=\"%s\", platform=\"%s\")." % (responseKey, intentObj.language, self._IntentLoader._Platform)
        
        finally:

            # trace.
            _logsi.LeaveMethod(SILevel.Debug, colorValue=SIColors.Khaki)


    async def GetTextSlotListInValue(
        self,
        intentObj:Intent,
        listName:str,
        outValue:str,
        defaultValue:str=None,
    ) -> str | None:
        """
        Queries a TextSlotList of values for the specified "out" value, returning its
        corresponding "in" value if found.

        Args:
            intentObj (Intent|None):
                Intent object that is handling the request.
            listName (str):
                Intent list name to query; must be a TextSlotList of "in" / "out" values.
            outValue (str):
                TextSlotList "out" value to find.
            defaultValue (str):
                Default value to return if TextSlotList "out" value could not be found.

        Returns:
            A TextSlotList "in" value assigned to the found "out" value if found; otherwise, None.

        This method does NOT include the built-in intent "lists", only the lists that 
        were loaded by this integration!
        """
        methodParms:SIMethodParmListContext = None
        result:str = defaultValue

        try:

            # trace.
            methodParms = _logsi.EnterMethodParmList(SILevel.Debug, colorValue=SIColors.Khaki)
            methodParms.AppendKeyValue("listName", listName)
            methodParms.AppendKeyValue("outValue", outValue)
            methodParms.AppendKeyValue("defaultValue", defaultValue)
            _logsi.LogMethodParmList(SILevel.Verbose, "Querying TextSlotList IN value for OUT value key: \"%s\"" % (outValue), methodParms, colorValue=SIColors.Khaki)

            # validations.
            if (not isinstance(intentObj, Intent)):
                return None
            if (not isinstance(listName, str)):
                return None
            if (not isinstance(outValue, str)):
                return None

            language = intentObj.language

            # get intent data; if none found, then we are done.
            langIntents:LanguageIntents = await self._IntentLoader.async_get_or_load_intents(language)
            if (langIntents is None):
                return None

            # example "lists" dictionary for "spotifyplus_playlist_names" list:
            # 'lists': {
            #     'spotifyplus_playlist_names': {
            #         'values': [{
            #                 'in': 'Daily Mix (1|One)',
            #                 'out': 'spotify:playlist:37i9dQZF1E39vTG3GurFPW'
            #             },
            #             {
            #                 'in': 'Daily Mix (2|Two)',
            #                 'out': 'spotify:playlist:37i874jngdjhg8577kjjss'
            #             }
            #         ]
            #     }
            # }

            # query the global "lists" dictionary for the specified list name, returning
            # it's underlying list of values.
            slotListValuesArray:list = langIntents.intents_dict.get("lists",{}).get(listName,{}).get("values",[])

            # trace.
            if (self.logsi.IsOn(SILevel.Verbose)):
                self.logsi.LogArray(SILevel.Verbose, "TextSlotList list of values: \"%s\"" % (listName), slotListValuesArray, colorValue=SIColors.Khaki)

            # prepare for comparison.
            outValueLower = outValue.lower()

            # check for a matching "out" key value.
            # if found, then return the "in" value.
            slotValueDict:dict = None
            for slotValueDict in slotListValuesArray:
                outValue = slotValueDict.get("out", "")
                if (outValue.lower() == outValueLower):
                    result = slotValueDict.get("in", None)
                    self.logsi.LogVerbose("Matched TextSlotList OUT value \"%s\" - IN value: \"%s\"" % (outValue, result), colorValue=SIColors.Khaki)
                    break

            # return result to caller.
            return result

        except Exception as ex:
            
            # trace.
            _logsi.LogException("Intent handler GetTextSlotListInValue exception: %s" % (str(ex)), ex, logToSystemLogger=False, colorValue=SIColors.Khaki)

            # ignore exceptions.
            return result
        
        finally:

            # trace.
            _logsi.LeaveMethod(SILevel.Debug, colorValue=SIColors.Khaki)


def get_registry_entry_media_player(
    intentObj:Intent,
    platform:str=None,
    entity_id:str=None,
    ) -> RegistryEntry | None:
    """
    Retrieves a registry entry for the specified media player criteria.

    Args:
        intentObj (Intent):
            Intent instance that is calling the method.
        platform (str):
            Platform name of the media player entity to retrieve (e.g.
            "spotifyplus", "spotify", etc).
        entity_id (str):
            Entity id to retrieve

    Returns:
        A `RegistryEntry` object found in the HA entity registry.
    """
    # prepare to access the entity registry.
    er_registry = er.async_get(intentObj.hass)
    result:RegistryEntry = None

    # trace.
    _logsi.LogVerbose("Searching HA entity registry for active media player platform \"%s\", entity id: \"%s\"" % (platform, entity_id or "*any*"), colorValue=SIColors.Khaki)

    # was a specific entity supplied?
    if (entity_id):

        # yes - get the value directly.
        entityObj = er_registry.async_get(entity_id)
        if (entityObj):
            if (entityObj.domain == DOMAIN_MEDIA_PLAYER) and (entityObj.platform == platform) and (entityObj.disabled == False):
                result = entityObj

        if (result is None):
            _logsi.LogVerbose("No active HA entity registry entry found for media player platform \"%s\", entity id: \"%s\"" % (platform, entity_id), colorValue=SIColors.Khaki)
            #No active HA entity registry entry found for "spotifyplus" media player entity id: "media_player.sonos_01"

            return result

    else:

        # no - get all active media player entities for the supplied platform.
        entities = [
            entityObj for entityObj in er_registry.entities.values()
            if (entityObj.domain == DOMAIN_MEDIA_PLAYER) and (entityObj.platform == platform) and (entityObj.disabled == False)
        ]
        if entities:
            result = entities[0]
        if (result is None):
            _logsi.LogObject("No active HA entity registry entries were found for media player platform \"%s\"" % (platform), colorValue=SIColors.Khaki)
            return result

    # trace.
    _logsi.LogObject(SILevel.Verbose, "Found HA entity registry for active media player platform \"%s\", entity id: \"%s\"" % (platform, result.entity_id), result, colorValue=SIColors.Khaki)

    # return to caller.
    return result
