from typing import Tuple
import os
import yaml

from homeassistant.components.media_player.const import MediaPlayerState
from homeassistant.components.media_player import MediaPlayerEntity, MediaPlayerEntityFeature
from homeassistant.core import HomeAssistant, State
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_registry import RegistryEntry
from homeassistant.helpers.template import Template
from homeassistant.helpers.intent import (
    Intent, 
    IntentHandler, 
    IntentResponse, 
    IntentResponseErrorCode,
    MatchFailedReason,
    MatchTargetsConstraints, 
    MatchTargetsPreferences, 
    MatchTargetsResult,
    _SlotsType,
    MatchTargetsResult,
    async_match_targets,
)

from ..appmessages import STAppMessages
from ..const import (
    CONF_AREA,
    CONF_FLOOR,
    CONF_NAME,
    CONF_TARGET_PLAYER,
    CONF_TEXT,
    CONF_VALUE,
    DOMAIN_MEDIA_PLAYER,
    PLATFORM_SPOTIFYPLUS,
    RESPONSE_PLAYER_FEATURES_NOT_SUPPORTED,
    RESPONSE_PLAYER_NOT_EXPOSED_TO_VOICE,
    RESPONSE_PLAYER_NOT_MATCHED,
    RESPONSE_PLAYER_NOT_MATCHED_AREA,
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
    def __init__(self) -> None:
        """
        Initializes a new instance of the class.
        """
        # set trace reference.
        self.logsi = _logsi

        # set intent handler basics.
        # these should be overridden in the inheriting class, but are here for validation.
        self.platforms = {PLATFORM_SPOTIFYPLUS}
        self.intent_type = "INTENT_TYPE_NOT_SET_IN_INHERITING_CLASS"
        self.description = "This description should be overridden in the inheriting class!"


    async def async_get_matching_player_state(
        self, 
        intentObj:Intent,
        intentResponse:IntentResponse,
        slots:_SlotsType,
        desiredFeatures:MediaPlayerEntityFeature,
        desiredStates:list[MediaPlayerState],
        desiredStateResponseKey:str,
        ) -> Tuple[IntentResponse, _SlotsType, MediaPlayerEntity | None]:
        """
        Resolve matching player entity state.
        """
        try:

            # trace.
            self.logsi.EnterMethod(SILevel.Debug, colorValue=SIColors.Khaki)

            # validate slot arguments.
            if (self.logsi.IsOn(SILevel.Verbose)):
                self.logsi.LogDictionary(SILevel.Verbose, "Validating slot arguments for intent: \"%s\"" % intentObj.intent_type, slots, colorValue=SIColors.Khaki)
            slots = self.async_validate_slots(intentObj.slots)

            # get player name / area / floor slot arguments.
            # note that HA conversation agent requires specific slot id's to perform it's magic
            # when resolving entity_id's related to the following: "name", "floor", "area".
            # if you customize outside of those values then entity matching will not work; you 
            # have to define custom lists in order for things to match!
            player_name: str | None = slots.get(CONF_NAME, {}).get(CONF_VALUE, "")
            area_id = slots.get(CONF_AREA, {}).get(CONF_VALUE, "")
            floor_id = slots.get(CONF_FLOOR, {}).get(CONF_VALUE, "")

            # update target player slot in case we have any errors.
            slots[CONF_TARGET_PLAYER] = {
                CONF_TEXT: player_name + area_id + floor_id,  # only 1 should be populated, others are empty strings.
                CONF_VALUE: "unknown"
            }

            # build matching entities criteria.
            matchConstraints = MatchTargetsConstraints(
                name=player_name,
                area_name=area_id,
                floor_name=floor_id,
                domains={DOMAIN_MEDIA_PLAYER},
                assistant=intentObj.assistant,
                features=desiredFeatures,
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
                    area_id=slots.get("preferred_area_id", {}).get(CONF_VALUE),
                    floor_id=slots.get("preferred_floor_id", {}).get(CONF_VALUE),
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
                if matchResult.no_match_reason == MatchFailedReason.FEATURE:

                    # no - media player does not support requested features.
                    responseText = await get_intent_response_resource(RESPONSE_PLAYER_FEATURES_NOT_SUPPORTED, slots, intentObj, PLATFORM_SPOTIFYPLUS)
                    intentResponse.async_set_error(IntentResponseErrorCode.NO_VALID_TARGETS, responseText)
                    self.logsi.LogObject(SILevel.Verbose, STAppMessages.MSG_INTENT_HANDLER_RESPONSE % (intentObj.intent_type), intentResponse, colorValue=SIColors.Khaki)
                    return (intentResponse, slots, None)

                elif matchResult.no_match_reason == MatchFailedReason.AREA:

                    # no - media player entity not found for specified area.
                    responseText = await get_intent_response_resource(RESPONSE_PLAYER_NOT_MATCHED_AREA, slots, intentObj, PLATFORM_SPOTIFYPLUS)
                    intentResponse.async_set_error(IntentResponseErrorCode.NO_VALID_TARGETS, responseText)
                    self.logsi.LogObject(SILevel.Verbose, STAppMessages.MSG_INTENT_HANDLER_RESPONSE % (intentObj.intent_type), intentResponse, colorValue=SIColors.Khaki)
                    return (intentResponse, slots, None)

                elif matchResult.no_match_reason == MatchFailedReason.ASSISTANT:

                    # no - media player entity has not been exposed to HA Voice Assist.
                    responseText = await get_intent_response_resource(RESPONSE_PLAYER_NOT_EXPOSED_TO_VOICE, slots, intentObj, PLATFORM_SPOTIFYPLUS)
                    intentResponse.async_set_error(IntentResponseErrorCode.NO_VALID_TARGETS, responseText)
                    self.logsi.LogObject(SILevel.Verbose, STAppMessages.MSG_INTENT_HANDLER_RESPONSE % (intentObj.intent_type), intentResponse, colorValue=SIColors.Khaki)
                    return (intentResponse, slots, None)

                else:

                    # no - search for the first active spotifyplus media player entity.
                    playerEntity = get_registry_entry_media_player(intentObj, platform=PLATFORM_SPOTIFYPLUS)
                    if (playerEntity):
                        playerEntityState = intentObj.hass.states.get(playerEntity.entity_id)
                        resolvedDesc = "RegistryEntry"

            # if player not found, then give up and inform the user.
            if (playerEntity is None):
                responseText = await get_intent_response_resource(RESPONSE_PLAYER_NOT_MATCHED, slots, intentObj, PLATFORM_SPOTIFYPLUS)
                intentResponse.async_set_error(IntentResponseErrorCode.NO_VALID_TARGETS, responseText)
                self.logsi.LogObject(SILevel.Verbose, STAppMessages.MSG_INTENT_HANDLER_RESPONSE % (intentObj.intent_type), intentResponse, colorValue=SIColors.Khaki)
                return (intentResponse, slots, None)

            # trace.
            if (self.logsi.IsOn(SILevel.Verbose)):
                self.logsi.LogObject(SILevel.Verbose, "Resolved player state for entity_id: \"%s\" (%s)" % (playerEntityState.entity_id, resolvedDesc), playerEntityState, colorValue=SIColors.Khaki)

            # update target player slot that contains the selected player info.
            # note we will use the friendly name / area / floor value supplied, 
            # and just update the entity_id value.
            slots[CONF_TARGET_PLAYER] = {
                CONF_TEXT: player_name + area_id + floor_id,  # only 1 should be populated, others are empty strings.
                CONF_VALUE: playerEntityState.entity_id
            }

            # update speech slots with target media player info.
            intentResponse.speech_slots = slots

            # trace.
            if (self.logsi.IsOn(SILevel.Verbose)):
                self.logsi.LogDictionary(SILevel.Verbose, "Current slot values for intent: \"%s\"" % intentObj.intent_type, slots, colorValue=SIColors.Khaki)

            # is media player state in the desired state (e.g. playing? paused? etc)?
            if (playerEntityState.state not in desiredStates):
                responseText = await get_intent_response_resource(desiredStateResponseKey, slots, intentObj, PLATFORM_SPOTIFYPLUS)
                intentResponse.async_set_speech(responseText)
                self.logsi.LogObject(SILevel.Verbose, STAppMessages.MSG_INTENT_HANDLER_RESPONSE % (intentObj.intent_type), intentResponse, colorValue=SIColors.Khaki)
                return (intentResponse, slots, None)

            # return response and the found player entity.
            return (intentResponse, slots, playerEntityState)

        finally:

            # trace.
            self.logsi.LeaveMethod(SILevel.Debug, colorValue=SIColors.Khaki)


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


async def get_intent_response_resource(
    response_key:str,
    slots:dict=None,
    intentObj:Intent=None,
    platform:str=None,
    platform_files_only:bool=True,
    hass:HomeAssistant=None,
    intent_name:str=None,
    lang:str=None,
) -> str | None:
    """
    Look up a response template in `custom_sentences/<lang>/*.yaml` files by a key value
    and render it (with slot support).

    Args:
        response_key (str):
            Response key to find.
            This value is case-sensitive.
        slots (dict):
            Slots data to provide to the template engine for overriding resource message key values.
        intentObj (Intent|None):
            Intent object; if None, then the remaining arguments must be supplied.
        platform (str):
            Platform name.
        platform_files_only (bool):
            If true, limits file processing to file names that start with the `platform` argument value;
            otherwise, false to process all found files.
        hass (HomeAssistant):
            Hass instance used to retrieve the language indicator and process template functions.
            Defaults to intentObj.hass if not supplied.
        intent_name (str):
            Parent intent name, if response key is for a specific intent.
            This value is case-sensitive.
            Defaults to intentObj.intent_type if not supplied.
        lang (str):
            Language indicator, used to find the language-specific folder under the 
            custom_sentences base folder.

    Returns the rendered string, or a default English message if not found.

    Response key templates may be nested using the following schemas.
    This is also the search prevalence heirarchy, in that the first layout that contains
    the response key will be the value that is used.
    - standard layout: `responses -> intents -> MyIntentName -> my_message_key: "My message text"`
    - platform layout: `responses -> MyPlatform -> my_message_key: "My message text"`
    - flatfile layout: `responses -> my_message_key: "My message text"`
    """
    methodParms:SIMethodParmListContext = None

    # default result if response key could not be resolved.
    result:str = "Resource message for response key \"%s\" could not be found." % response_key
        
    try:

        # if intent object supplied, then default other input parameters from it's settings.
        if intentObj:
            if hass is None:
                hass = intentObj.hass
            if intent_name is None:
                intent_name = intentObj.intent_type
            if lang is None:
                lang = intentObj.language
            if platform is None:
                if isinstance(intentObj.platform, list):
                    platform = intentObj.platform[0]
                else:
                    platform = intentObj.platform

        # trace.
        methodParms = _logsi.EnterMethodParmList(SILevel.Debug, colorValue=SIColors.Khaki)
        methodParms.AppendKeyValue("response_key", response_key)
        methodParms.AppendKeyValue("intent_name", intent_name)
        methodParms.AppendKeyValue("platform", platform)
        methodParms.AppendKeyValue("lang", lang)
        methodParms.AppendKeyValue("slots", str(slots))
        methodParms.AppendKeyValue("platform_files_only", platform_files_only)
        _logsi.LogMethodParmList(SILevel.Verbose, "Loading response text for response key: \"%s\" (lang=%s)" % (response_key, lang), methodParms, colorValue=SIColors.Khaki)
        
        # validations.
        if (not isinstance(platform_files_only, bool)):
            platform_files_only = False

        # formulate custom sentences folder location.
        lang = lang or hass.config.language or "en"
        base_dir = hass.config.path(f"custom_sentences/{lang}")

        # is folder path really a folder? if not, then we are done.
        # note - use `async_add_executor_job` so we don't block the HA event loop.
        if not await hass.async_add_executor_job(os.path.isdir, base_dir):
            return "Resource message folder \"%s\" could not be read." % base_dir

        def _load_yaml_files():
            responses = []
            for fname in sorted(os.listdir(base_dir)):
                fnameCompare = fname.lower()
                if (not fnameCompare.endswith((".yaml", ".yml"))):
                    continue
                if (platform_files_only) and (not fnameCompare.startswith(platform)):
                    continue
                path = os.path.join(base_dir, fname)
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        data = yaml.safe_load(f) or {}
                        responses.append({ 
                            "path": path,
                            "data": data
                        })
                except Exception:
                    continue
            return responses

        # load all yaml files from the language-specific custom_sentences folder.
        # note - use `async_add_executor_job` so we don't block the HA event loop.
        all_data = await hass.async_add_executor_job(_load_yaml_files)

        # process all files in the custom_sentences folder.
        for file_entry in all_data:

            # responses may be nested using the following schemas:
            # - standard layout: `responses -> intents -> MyIntentName -> my_message_key: "My message text"`
            # - platform layout: `responses -> MyPlatform -> my_message_key: "My message text"`
            # - flatfile layout: `responses -> my_message_key: "My message text"`
            # this is also the search prevalence heirarchy, in that the first layout that contains
            # the response key will be the value that is used.

            # create searchable dictionarys of response data.
            file_path = file_entry.get("path")
            responses_root = file_entry.get("data",{}).get("responses") or {}
            intents_block = responses_root.get("intents") or {}
            platform_block = responses_root.get(platform or "") or {}

            # trace.
            _logsi.LogVerbose("Processing custom_sentences file: \"%s\"" % file_path, colorValue=SIColors.Khaki)
            #_logsi.LogDictionary(SILevel.Debug,"Responses root dictionary", responses_root, prettyPrint=True, colorValue=SIColors.Khaki)
            #_logsi.LogDictionary(SILevel.Debug,"Intents block dictionary", intents_block, prettyPrint=True, colorValue=SIColors.Khaki)
            #_logsi.LogDictionary(SILevel.Debug,"Platform block dictionary", platform_block, prettyPrint=True, colorValue=SIColors.Khaki)

            # check for response key in each layout type.
            candidates = []

            # check for standard layout:
            if intent_name in intents_block:
                intent_dict = intents_block[intent_name] or {}
                if response_key in intent_dict:
                    _logsi.LogDebug("Found candidate for response key (intent-specific) \"%s\": \"%s\"" % (response_key, intent_dict[response_key]), colorValue=SIColors.Khaki)
                    candidates.append(intent_dict[response_key])

            # check for platform layout:
            if response_key in platform_block:
                _logsi.LogDebug("Found candidate for response key (platform-specific) \"%s\": \"%s\"" % (response_key, platform_block[response_key]), colorValue=SIColors.Khaki)
                candidates.append(platform_block[response_key])

            # check for flatfile layout:
            if response_key in responses_root and isinstance(responses_root[response_key], str):
                _logsi.LogDebug("Found candidate for response key (intent-agnostic) \"%s\": \"%s\"" % (response_key, responses_root[response_key]), colorValue=SIColors.Khaki)
                candidates.append(responses_root[response_key])

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
                    tpl = Template(template_text, hass)
                    rendered = tpl.async_render({"slots": slots}, parse_result=False)
                    result = rendered

                except Exception as ex:

                    # trace.
                    _logsi.LogException("Intent get_intent_response_resource template render exception: %s" % (str(ex)), ex, logToSystemLogger=False, colorValue=SIColors.Khaki)

                    # ignore template render exceptions.
                    # we will use the resource message as-is, and let the user figure it out.
                    # HA will take care of logging the exception to the system log.
                    result = template_text

                # found result; stop processing response files.
                break

        # return result text.
        _logsi.LogText(SILevel.Verbose,"Response text for response key \"%s\": \"%s\"" % (response_key, result), result, colorValue=SIColors.Khaki)
        return result

    except Exception as ex:
            
        # trace.
        _logsi.LogException("Intent get_intent_response_resource exception: %s" % (str(ex)), ex, logToSystemLogger=False, colorValue=SIColors.Khaki)

        # ignore exceptions
        return "Resource message resolution error for response key \"%s\"." % response_key
        
    finally:

        # trace.
        _logsi.LeaveMethod(SILevel.Debug, colorValue=SIColors.Khaki)
