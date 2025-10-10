"""Intents for the spotifyplus integration."""
from homeassistant.core import HomeAssistant
from homeassistant.helpers import intent
from homeassistant.helpers.intent import (
    IntentHandler, 
)

from .appmessages import STAppMessages
from .intent_handlers import *

import logging
_LOGGER = logging.getLogger(__name__)

# get smartinspect logger reference; create a new session for this module name.
from smartinspectpython.siauto import SIAuto, SILevel, SISession, SIMethodParmListContext, SIColors
_logsi:SISession = SIAuto.Si.GetSession(__name__)
if (_logsi == None):
    _logsi = SIAuto.Si.AddSession(__name__, True)
_logsi.SystemLogger = _LOGGER


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
           
        # register all intents this component provides, and their corresponding schemas.
        intentObj:IntentHandler = SpotifyPlusPlayerMediaSkipNext_Handler()
        _logsi.LogObject(SILevel.Verbose, STAppMessages.MSG_INTENT_HANDLER_REGISTER % intentObj.intent_type, intentObj, colorValue=SIColors.Khaki)
        intent.async_register(hass, intentObj)

        intentObj:IntentHandler = SpotifyPlusPlayerMediaSkipPrevious_Handler()
        _logsi.LogObject(SILevel.Verbose, STAppMessages.MSG_INTENT_HANDLER_REGISTER % intentObj.intent_type, intentObj, colorValue=SIColors.Khaki)
        intent.async_register(hass, intentObj)

        # indicate success.
        _logsi.LogVerbose("Component async_setup_intents complete", colorValue=SIColors.Khaki)
        return True

    except Exception as ex:

        # log exception, but not to system logger as HA will take care of it.
        _logsi.LogException("Component async_setup_intents exception", ex, logToSystemLogger=False)
        raise

    finally:

        # trace.
        _logsi.LeaveMethod(SILevel.Debug, colorValue=SIColors.Khaki)


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

#                 #_logsi.LogObject(SILevel.Verbose, "TODO REMOVEME Entity object: %s" % entityObj.entity_id, entityObj)

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
