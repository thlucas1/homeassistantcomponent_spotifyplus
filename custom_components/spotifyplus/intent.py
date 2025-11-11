"""Intents for the spotifyplus integration."""
from typing import IO

from homeassistant.core import HomeAssistant
from homeassistant.helpers.intent import (
    IntentHandler, 
    async_register as intent_async_register,
)
from homeassistant.util.json import JsonObjectType, json_loads_object

from home_assistant_intents import (
    _DATA_DIR as HA_BUILT_IN_INTENTS_DATA_DIR, 
    get_intents,
)

from custom_components.spotifyplus.const import PLATFORM_SPOTIFYPLUS

from .appmessages import STAppMessages
from .intent_handlers import *
from .intent_loader import IntentLoader

import logging
_LOGGER = logging.getLogger(__name__)

# get smartinspect logger reference; create a new session for this module name.
from smartinspectpython.siauto import SIAuto, SILevel, SISession, SIMethodParmListContext, SIColors
_logsi:SISession = SIAuto.Si.GetSession(__name__)
if (_logsi == None):
    _logsi = SIAuto.Si.AddSession(__name__, True)
_logsi.SystemLogger = _LOGGER


def json_load(fp: IO[str]) -> JsonObjectType:
    """Wrap json_loads for get_intents."""
    return json_loads_object(fp.read())


async def async_setup_intents(hass: HomeAssistant) -> None:
    """
    Set up voice assist intents.

    Called by HA to register all intents that this integration supports.

    Args:
        hass (HomeAssistant):
            HomeAssistant instance.
    """
    try:

        # trace.
        _logsi.EnterMethod(SILevel.Debug, colorValue=SIColors.Khaki)
        _logsi.LogVerbose("Component async_setup_intents starting", colorValue=SIColors.Khaki)
        
        # get slot list of spotifyplus media player names and any defined aliases.
        #player_name_list = await async_get_slot_list_player_name(hass)

        # create intent loader instance.
        # in our case, we will only load OUR platform intent data.
        intentLoader:IntentLoader = IntentLoader(hass, PLATFORM_SPOTIFYPLUS)
                   
        # register all intents this component provides.
        register_intent_handler(hass, SpotifyPlusFavoriteAddRemove_Handler(intentLoader))
        register_intent_handler(hass, SpotifyPlusGetInfoArtistBio_Handler(intentLoader))
        register_intent_handler(hass, SpotifyPlusGetNowPlayingInfo_Handler(intentLoader))
        register_intent_handler(hass, SpotifyPlusPlayerDeckControl_Handler(intentLoader))
        register_intent_handler(hass, SpotifyPlusPlayerSetRepeatMode_Handler(intentLoader))
        register_intent_handler(hass, SpotifyPlusPlayerSetShuffleMode_Handler(intentLoader))
        register_intent_handler(hass, SpotifyPlusPlayerTransferPlayback_Handler(intentLoader))
        register_intent_handler(hass, SpotifyPlusPlayerVolumeControl_Handler(intentLoader))
        register_intent_handler(hass, SpotifyPlusPlaylistCreate_Handler(intentLoader))
        register_intent_handler(hass, SpotifyPlusSearchPlayControl_Handler(intentLoader))

        # start listening for conversation.reload service call events.
        await intentLoader.async_register_cache_reload_listener()

        # # trace.
        # # log information about built-in intents for this language variant.
        # if (_logsi.IsOn(SILevel.Verbose)):
        #     try:
        #         _logsi.LogVerbose("Component - loading HA built-in intents from data path: \"%s\"" % HA_BUILT_IN_INTENTS_DATA_DIR, colorValue=SIColors.Khaki)
        #         language_variant = hass.config.language or "en"
        #         lang_variant_intents = await hass.async_add_executor_job(
        #             get_intents, language_variant, json_load
        #         )
        #         if lang_variant_intents:
        #             _logsi.LogDictionary(SILevel.Verbose, "Component - HA built-in intents (dictionary)", lang_variant_intents, prettyPrint=True, colorValue=SIColors.Khaki)
        #         else:
        #             _logsi.LogVerbose("Component - HA built-in intents not found for language variant: \"%s\"" % language_variant, colorValue=SIColors.Khaki)
        #     except Exception as ex:
        #         # log exception, but not to system logger as HA will take care of it.
        #         _logsi.LogException("Could not load HA built-in intents!", ex, logToSystemLogger=False, colorValue=SIColors.Khaki)

        # indicate success.
        _logsi.LogVerbose("Component async_setup_intents complete", colorValue=SIColors.Khaki)
        return True

    except Exception as ex:

        # log exception, but not to system logger as HA will take care of it.
        _logsi.LogException("Component async_setup_intents exception", ex, logToSystemLogger=False, colorValue=SIColors.Khaki)
        raise

    finally:

        # trace.
        _logsi.LeaveMethod(SILevel.Debug, colorValue=SIColors.Khaki)


def register_intent_handler(
    hass: HomeAssistant,
    intentObj:IntentHandler,
    ) -> None:
    """
    Registers a voice assist intent, and trace logs the object.
    """
    # register single intent this component provides.
    _logsi.LogObject(SILevel.Verbose, STAppMessages.MSG_INTENT_HANDLER_REGISTER % intentObj.intent_type, intentObj, colorValue=SIColors.Khaki)
    intent_async_register(hass, intentObj)


# async def async_get_slot_list_player_name(
#     hass: HomeAssistant, 
#     ) -> object:
#     """
#     Builds a slot list of spotifyplus media player names and any defined aliases
#     made via the HA Voice Assist UI.
#     """
#     try:

#         # trace.
#         _logsi.EnterMethod(SILevel.Debug, colorValue=SIColors.Khaki)
#         _logsi.LogVerbose("Component async_get_list_player_name starting", colorValue=SIColors.Khaki)

#         # prepare to access the entity registry.
#         er = async_get(hass)

#         slot_values: list[dict[str, Any]] = []

#         # process all registry entities for spotifyplus media_player names and aliases.
#         entityObj:RegistryEntry
#         for entityObj in er.entities.values():

#             # is this a spotifyplus media player?
#             if (entityObj.domain == DOMAIN_MEDIA_PLAYER) and (entityObj.platform == PLATFORM_SPOTIFYPLUS) and (entityObj.disabled == False):

#                 #_logsi.LogObject(SILevel.Verbose, "Entity object: %s" % entityObj.entity_id, entityObj)

#                 entity_id = entityObj.entity_id
#                 friendly_name = entityObj.name or entityObj.original_name

#                 # include entity id without the underscores.
#                 slot_entry = {
#                     "in": entityObj.entity_id.split(".")[1].replace("_"," "),
#                     "out": entity_id,
#                 }
#                 slot_values.append(slot_entry)
#                 _logsi.LogDictionary(SILevel.Verbose, "Adding entity id without the underscores: %s = %s" % (entity_id, slot_entry["in"]), slot_entry, colorValue=SIColors.Khaki)

#                 # include primary name.
#                 if friendly_name:
#                     slot_entry = {
#                         "in": friendly_name.lower(),
#                         "out": entity_id,
#                     }
#                     if slot_entry not in slot_values:
#                         slot_values.append(slot_entry)
#                         _logsi.LogDictionary(SILevel.Verbose, "Adding entity primary name: %s = %s" % (entity_id, slot_entry["in"]), slot_entry, colorValue=SIColors.Khaki)

#                 # include aliases defined in voice assist ui.
#                 if hasattr(entityObj, "aliases") and entityObj.aliases:
#                     for alias in entityObj.aliases:
#                         slot_entry = {
#                             "in": alias.lower(),
#                             "out": entity_id,
#                         }
#                         if slot_entry not in slot_values:
#                             slot_values.append(slot_entry)
#                             _logsi.LogDictionary(SILevel.Verbose, "Adding entity voice ui alias: %s = %s" % (entity_id, slot_entry["in"]), slot_entry, colorValue=SIColors.Khaki)

#         # trace.
#         _logsi.LogArray(SILevel.Verbose, "Component async_get_list_player_name result (array)", slot_values, colorValue=SIColors.Khaki)

#         # return value to caller.
#         return {
#             "player_name": {   # slot name
#                 "values": slot_values
#             }
#         }

#     except Exception as ex:

#         # log exception, but not to system logger as HA will take care of it.
#         _logsi.LogException("Component async_get_list_player_name exception", ex, logToSystemLogger=False)
#         # ignore exceptions

#     finally:

#         # trace.
#         _logsi.LeaveMethod(SILevel.Debug, colorValue=SIColors.Khaki)

