from __future__ import annotations

import asyncio
import copy
from dataclasses import dataclass
from pathlib import Path
import time
from typing import IO, Any, cast, Dict
import yaml

from home_assistant_intents import (
    get_languages,
)

from hassil.intents import (
    Intents,
    TextSlotList,
)
from hassil.util import merge_dict

from homeassistant.const import EVENT_CALL_SERVICE
from homeassistant.core import HomeAssistant, callback
from homeassistant.util import language as language_util
from homeassistant.util.json import JsonObjectType, json_loads_object
from homeassistant.components.conversation.const import (
    SERVICE_RELOAD as CONVERSATION_SERVICE_RELOAD, 
    DOMAIN as DOMAIN_CONVERSATION,
)

import logging
_LOGGER = logging.getLogger(__name__)

# get smartinspect logger reference; create a new session for this module name.
from smartinspectpython.siauto import SIAuto, SILevel, SISession, SIMethodParmListContext, SIColors
_logsi:SISession = SIAuto.Si.GetSession(__name__)
if (_logsi == None):
    _logsi = SIAuto.Si.AddSession(__name__, True)
_logsi.SystemLogger = _LOGGER

ERROR_SENTINEL = object()
METADATA_CUSTOM_SENTENCE = "hass_custom_sentence"
METADATA_CUSTOM_FILE = "hass_custom_file"


@dataclass(slots=True)
class LanguageIntents:
    """Loaded intents for a language."""
    intents: Intents
    intents_dict: dict[str, Any]
    intent_responses: dict[str, Any]
    error_responses: dict[str, Any]
    platform_responses: dict[str, Any]
    generic_responses: dict[str, Any]
    language_variant: str | None


def json_load(fp: IO[str]) -> JsonObjectType:
    """Wrap json_loads for get_intents."""
    return json_loads_object(fp.read())


class IntentLoader():
    """
    Intent loader class.
    """

    def __init__(
        self, 
        hass:HomeAssistant,
        platform:str=None,
        ) -> None:
        """
        Initialize a new instance of the class.

        Args:
            hass (HomeAssistant):
                Hass instance.
            platform (str):
                Specify a platform prefix to only load `custom_sentences` files that
                begin with the specified platform name.
        """
        self.hass = hass
        self._LangIntents:dict[str, LanguageIntents | object] = {}
        self._LoadIntentsLock = asyncio.Lock()
        self._Platform:str = platform
        self.unsubscribe_event = None


    @property
    def supported_languages(self) -> list[str]:
        """Return a list of supported languages."""
        return get_languages()


    async def async_clear_cache(
        self, 
        ) -> None:
        """
        Clears the cache of any loaded intents.
        """
        try:

            # anything in the cache? if not, then there's nothing to do.
            if (self._LangIntents == {}):
                _logsi.LogVerbose("Intent cache is already empty; nothing to do", colorValue=SIColors.Khaki)
                return

            # let's prepare to load the intent data;
            # set a lock in case we get multiple requests at the same time.
            _logsi.LogVerbose("Acquiring lock prior to clearing cache", colorValue=SIColors.Khaki)
            async with self._LoadIntentsLock:

                # clear the cache.
                self._LangIntents.clear()

                # trace.
                _logsi.LogVerbose("Intent cache has been cleared", colorValue=SIColors.Khaki)

        except Exception as ex:

            # log exception, but not to system logger as HA will take care of it.
            _logsi.LogException("Component async_clear_cache exception", ex, logToSystemLogger=False, colorValue=SIColors.Khaki)
            raise


    async def async_get_or_load_intents(
        self, 
        language:str=None,
        ) -> LanguageIntents | None:
        """
        Gets the cached intent data for the specified language.

        Args:
            language (str):
                Language indicator, used to find the language-specific folder under the 
                custom_sentences base folder.

        Returns:
            A LanguageIntents instance if intent data was found; otherwise, None.

        For the first call of this method, the intents are loaded from disk for the
        specified language (in a thread-safe manner). 

        For subsequent calls, the cached intent list is returned.

        The intent cache is cleared and reloaded if the conversation "reload" service 
        is called.
        """
        try:

            # validations.
            if (not isinstance(language, str)) or (len(language.strip()) == 0):
                language = self.hass.config.language or "en"

            # if we already loaded intents, then return the cached data.
            if lang_intents := self._LangIntents.get(language):
                if lang_intents is ERROR_SENTINEL:
                    return None
                return cast(LanguageIntents, lang_intents)

            # trace.
            _logsi.LogVerbose("Intents first-time load detected; calling load intents (language=%s)" % (language), colorValue=SIColors.Khaki)

            # let's prepare to load the intent data;
            # set a lock in case we get multiple requests at the same time.
            _logsi.LogVerbose("Acquiring lock prior to loading intents", colorValue=SIColors.Khaki)
            async with self._LoadIntentsLock:

                # was another request waiting while we were loading?
                # if so, then there is no need to load it again.
                if lang_intents := self._LangIntents.get(language):
                    if lang_intents is ERROR_SENTINEL:
                        return None
                    return cast(LanguageIntents, lang_intents)

                # get start time so we can see how long it takes to load.
                start = time.monotonic()

                # load the intents from custom sentences.
                result = await self.hass.async_add_executor_job(
                    self._load_intent_definitions, language
                )

                # if we didn't find anything, then set result to an empty object.
                # this denotes that we tried to load the intent data and it did not return
                # anything, so that we don't try to load it again on the next request.
                # otherwise, store the loaded intent data under the language-specific key.
                if result is None:
                    self._LangIntents[language] = ERROR_SENTINEL
                else:
                    self._LangIntents[language] = result

                # trace.
                _logsi.LogVerbose("Full intent load completed (language=%s) in %.2f seconds" % (language, (time.monotonic() - start)), colorValue=SIColors.Khaki)

                # return result.
                return result

        except Exception as ex:

            # log exception, but not to system logger as HA will take care of it.
            _logsi.LogException("Component async_get_or_load_intents exception", ex, logToSystemLogger=False, colorValue=SIColors.Khaki)
            raise


    async def async_get_intent_list_byname(
        self, 
        language:str=None,
        listName:str=None,
        ) -> Dict[str, TextSlotList] | None:
        """
        Gets the specified intent list name definition.

        Args:
            language (str):
                Language indicator, used to find the language-specific folder under the 
                custom_sentences base folder.
            listName (str):
                Name of the specific list to retrieve; if null, ALL lists are returned.

        Returns:
            A dictionary of intent list data if found; otherwise, None.
        """
        try:

            # get intent cache; return null if intents could not be loaded.
            langIntents:LanguageIntents = await self.async_get_or_load_intents(language)
            if langIntents is None:
                return None

            # if list name not supplied, then return ALL lists.
            if (listName is None):
                return langIntents.intents.slot_lists
            else:
                return langIntents.intents.slot_lists.get(listName, None)

        except Exception as ex:

            # log exception, but not to system logger as HA will take care of it.
            _logsi.LogException("Component async_get_intent_list exception", ex, logToSystemLogger=False, colorValue=SIColors.Khaki)
            raise


    def _load_intent_definitions(
        self,
        language:str=None,
        ) -> LanguageIntents | None:
        """
        Loads language-specific intent template definitions from `custom_sentences/<lang>/*.yaml` 
        files (if found).

        Must run inside executor!

        Args:
            language (str):
                Language indicator, used to find the language-specific folder under the 
                custom_sentences base folder.

        Returns:
            A LanguageIntents object with loaded intent data if found; otherwise, None.

        Response key templates may be nested using the following schemas:
        - standard layout: `responses -> intents -> MyIntentName -> my_message_key: "My message text"`
        - platform layout: `responses -> MyPlatform -> my_message_key: "My message text"`
        - flatfile layout: `responses -> my_message_key: "My message text"`
        """
        methodParms:SIMethodParmListContext = None
        
        try:

            # trace.
            methodParms = _logsi.EnterMethodParmList(SILevel.Debug, colorValue=SIColors.Khaki)
            methodParms.AppendKeyValue("language", str(language))
            methodParms.AppendKeyValue("platform", self._Platform)
            _logsi.LogMethodParmList(SILevel.Verbose, "Component _load_intent_definitions starting", methodParms, colorValue=SIColors.Khaki)

            intents_dict: dict[str, Any] = {}
            supported_langs = set(get_languages())

            # choose a language variant upfront and commit to it.
            lang_matches = language_util.matches(language, supported_langs)
            if not lang_matches:
                _logsi.LogWarning("Unable to find supported language variant for \"%s\"" % language)
                return None

            language_variant = lang_matches[0]

            # # load built-in intents and responses for this language variant.
            # lang_variant_intents = get_intents(language_variant, json_load=json_load)

            # if lang_variant_intents:
            #     # merge sentences into existing dictionary
            #     # overriding because source dict is empty
            #     intents_dict = lang_variant_intents

            #     _LOGGER.debug(
            #         "Loaded built-in intents for language=%s (%s)",
            #         language,
            #         language_variant,
            #     )

            # check for custom sentences in "<config>/custom_sentences/<language>/" path.
            custom_sentences_dir = Path(
                self.hass.config.path("custom_sentences", language_variant)
            )
            _logsi.LogVerbose("Checking custom_sentences directory: \"%s\"" % custom_sentences_dir, colorValue=SIColors.Khaki)

            # is this a directory?
            if custom_sentences_dir.is_dir():

                # check for platform prefix file limiting.
                platformPfx = ""
                if self._Platform is not None:
                    platformPfx = f"{self._Platform}_"
                    _logsi.LogVerbose("Limiting custom_sentences files by platform prefix: \"%s\"" % platformPfx, colorValue=SIColors.Khaki)

                # create file search pattern.
                fileSearchPattern = f"{platformPfx}*.yaml"
                _logsi.LogVerbose("Searching custom_sentences directory (and sub-directories) for this file pattern: \"%s\"" % fileSearchPattern, colorValue=SIColors.Khaki)

                # process all found files in the directory, including sub-directories.
                for custom_sentences_path in sorted(custom_sentences_dir.rglob(fileSearchPattern)):

                    # if processing only our platform files, then disacrd files that aren't ours.
                    # this assumes that our files are prefixed by the platform name (e.g. "/spotifyplus_IntentNamexxx.yaml").
                    # TODO should not need this, as the rglob takes care of filtering out unwanted files!
                    #fnameCompare = custom_sentences_path.name.lower()
                    # if (self._Platform is not None) and (not fnameCompare.startswith(self._Platform)):
                    #     _logsi.LogDebug("Discarding non-platform custom_sentences file: %s" % custom_sentences_path, colorValue=SIColors.Khaki)
                    #     continue

                    # process the file.
                    _logsi.LogVerbose("Loading custom_sentences file: %s" % custom_sentences_path, colorValue=SIColors.Khaki)
                    with custom_sentences_path.open(encoding="utf-8") as custom_sentences_file:

                        # merge custom sentences.
                        if not isinstance(
                            custom_sentences_yaml := yaml.safe_load(custom_sentences_file),
                            dict,
                        ):
                            _logsi.LogWarning("Custom sentences file does not match expected format: \"%s\"" % custom_sentences_file.name)
                            continue

                        # add metadata so we can identify custom sentences in the debugger.
                        custom_intents_dict = custom_sentences_yaml.get("intents", {})
                        for intent_dict in custom_intents_dict.values():
                            intent_data_list = intent_dict.get("data", [])
                            for intent_data in intent_data_list:
                                sentence_metadata = intent_data.get("metadata", {})
                                sentence_metadata[METADATA_CUSTOM_SENTENCE] = True
                                sentence_metadata[METADATA_CUSTOM_FILE] = str(
                                    custom_sentences_path.relative_to(
                                        custom_sentences_dir.parent
                                    )
                                )
                                intent_data["metadata"] = sentence_metadata

                        # merge dictionary into base dictionary.
                        merge_dict(intents_dict, custom_sentences_yaml)

            # if no custom sentences defined then we are done.
            if not intents_dict:
                _logsi.LogVerbose("Could not find custom_sentences files for language=\"%s\", platform=\"%s\"" % (language, self._Platform), colorValue=SIColors.Khaki)
                return None

            # load intent objects from dictionary format.
            intents = Intents.from_dict(intents_dict)

            # load responses.
            responses_dict = intents_dict.get("responses", {})
            intent_responses = responses_dict.get("intents", {})
            platform_responses = responses_dict.get(self._Platform, {})
            error_responses = responses_dict.get("errors", {})
            
            # remove any child dictionary items from generic.
            generic_responses = copy.deepcopy(intents_dict.get("responses", {}))
            for key in [k for k, v in generic_responses.items() if isinstance(v, dict)]:
                del generic_responses[key]

            # trace.
            if (_logsi.IsOn(SILevel.Verbose)):
                _logsi.LogDictionary(SILevel.Verbose, "Component intents information: %s (%s) - all (dictionary)" % (self._Platform, language_variant), intents_dict, prettyPrint=True, colorValue=SIColors.Khaki)
                _logsi.LogDictionary(SILevel.Verbose, "Component intents information: %s (%s) - responses (dictionary)" % (self._Platform, language_variant), responses_dict, prettyPrint=True, colorValue=SIColors.Khaki)
                _logsi.LogDictionary(SILevel.Verbose, "Component intents information: %s (%s) - intent_responses (dictionary)" % (self._Platform, language_variant), intent_responses, prettyPrint=True, colorValue=SIColors.Khaki)
                _logsi.LogDictionary(SILevel.Verbose, "Component intents information: %s (%s) - platform_responses (dictionary)" % (self._Platform, language_variant), platform_responses, prettyPrint=True, colorValue=SIColors.Khaki)
                _logsi.LogDictionary(SILevel.Verbose, "Component intents information: %s (%s) - error_responses (dictionary)" % (self._Platform, language_variant), error_responses, prettyPrint=True, colorValue=SIColors.Khaki)
                _logsi.LogDictionary(SILevel.Verbose, "Component intents information: %s (%s) - generic_responses (dictionary)" % (self._Platform, language_variant), generic_responses, prettyPrint=True, colorValue=SIColors.Khaki)
                _logsi.LogDictionary(SILevel.Verbose, "Component intents information: %s (%s) - intents slot_lists (dictionary)" % (self._Platform, language_variant), intents.slot_lists, prettyPrint=True, colorValue=SIColors.Khaki)
                _logsi.LogDictionary(SILevel.Verbose, "Component intents information: %s (%s) - intents expansion_rules (dictionary)" % (self._Platform, language_variant), intents.expansion_rules, prettyPrint=True, colorValue=SIColors.Khaki)
                _logsi.LogDictionary(SILevel.Verbose, "Component intents information: %s (%s) - intents skip_words (dictionary)" % (self._Platform, language_variant), intents.skip_words, prettyPrint=True, colorValue=SIColors.Khaki)

            # return results.
            result = LanguageIntents(
                intents,
                intents_dict,
                intent_responses,
                error_responses,
                platform_responses,
                generic_responses,
                language_variant,
            )

            # trace.
            _logsi.LogVerbose("Component _load_intent_definitions complete", colorValue=SIColors.Khaki)
            return result

        except Exception as ex:

            # log exception, but not to system logger as HA will take care of it.
            _logsi.LogException("Component _load_intent_definitions exception", ex, logToSystemLogger=False, colorValue=SIColors.Khaki)
            raise

        finally:

            # trace.
            _logsi.LeaveMethod(SILevel.Debug, colorValue=SIColors.Khaki)


    async def async_register_cache_reload_listener(
        self, 
        ) -> None:
        """
        Registers an event listener that listens for `conversation.reload` service calls,
        so that our cache will also be reloaded on the next access call.
        """

        @callback
        async def _handle_call_service_event(event):
            """ Called when a "call_service" event is detected. """

            # get event data.
            data = event.data
            domain = data.get("domain")
            service = data.get("service")

            # trace.
            #_logsi.LogDictionary(SILevel.Verbose, "Call Service detected: domain=\"%s\", service=\"%s\"" % (domain, service), event, prettyPrint=True, colorValue=SIColors.Red)

            # was the "conversation.reload" service called?
            if domain == DOMAIN_CONVERSATION and service == CONVERSATION_SERVICE_RELOAD:

                _logsi.LogDictionary(SILevel.Verbose, "Intent Loader detected a Conversation integration Reload event", event, prettyPrint=True, colorValue=SIColors.Khaki)

                # clear our intent cache, so it will be reloaded next time.
                await self.async_clear_cache()

        # listen for all call service events, and store unsubscribe function.
        self.unsubscribe_event = self.hass.bus.async_listen(EVENT_CALL_SERVICE, _handle_call_service_event)

        # trace.
        _logsi.LogVerbose("Intent Loader registered the conversation reload event listener", colorValue=SIColors.Khaki)


    async def async_unregister_cache_reload_listener(
        self, 
        ) -> None:
        """
        Unregisters an event listener that listens for `conversation.reload` service calls.
        """
        # did we register an event listener? if so, then call it's unregister function.
        if self.unsubscribe_event:
            self.unsubscribe_event()  # <-- stop listening
            _logsi.LogVerbose("Unregistered the conversation reload event listener", colorValue=SIColors.Khaki)
