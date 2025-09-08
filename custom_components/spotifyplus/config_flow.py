"""
User interface config flow for SpotifyPlus integration.

Integrations can be set up via the user interface by adding support for a config 
flow to create a config entry. Components that want to support config entries will 
need to define a Config Flow Handler. This handler will manage the creation of 
entries from user input, discovery or other sources (like Home Assistant OS).

Config Flow Handlers control the data that is stored in a config entry. This means 
that there is no need to validate that the config is correct when Home Assistant 
starts up. It will also prevent breaking changes, because we will be able to migrate
 configuration entries to new formats if the version changes.

When instantiating the handler, Home Assistant will make sure to load all 
dependencies and install the requirements of the component.
"""
from __future__ import annotations
from collections.abc import Mapping
import logging
from typing import Any
import voluptuous as vol

from spotifywebapipython import SpotifyClient
from spotifywebapipython.models import Device, SpotifyConnectDevices

from homeassistant.components import zeroconf
from homeassistant import config_entries
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_DESCRIPTION, CONF_ID, CONF_NAME
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import config_entry_oauth2_flow, config_validation as cv, selector
from homeassistant.helpers.selector import (
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .const import (
    CONF_OPTION_ALWAYS_ON,
    CONF_OPTION_DEVICE_DEFAULT, 
    CONF_OPTION_DEVICE_LOGINID,
    CONF_OPTION_DEVICE_PASSWORD,
    CONF_OPTION_DEVICE_USERNAME,
    CONF_OPTION_SCRIPT_TURN_OFF,
    CONF_OPTION_SCRIPT_TURN_ON,
    CONF_OPTION_SOURCE_LIST_HIDE,
    CONF_OPTION_SPOTIFY_SCAN_INTERVAL,
    CONF_OPTION_TURN_OFF_AUTO_PAUSE,
    CONF_OPTION_TURN_ON_AUTO_RESUME,
    CONF_OPTION_TURN_ON_AUTO_SOURCE_SELECT,
    DEFAULT_OPTION_SPOTIFY_SCAN_INTERVAL,
    DOMAIN, 
    DOMAIN_SCRIPT,
    SPOTIFY_SCOPES
)
from .instancedata_spotifyplus import InstanceDataSpotifyPlus

# get smartinspect logger reference; create a new session for this module name.
from smartinspectpython.siauto import SIAuto, SILevel, SISession, SIColors
import logging
_logsi:SISession = SIAuto.Si.GetSession(__name__)
if (_logsi == None):
    _logsi = SIAuto.Si.AddSession(__name__, True)
_logsi.SystemLogger = logging.getLogger(__name__)


class SpotifyPlusConfigFlow(config_entry_oauth2_flow.AbstractOAuth2FlowHandler, domain=DOMAIN):
    """
    Config flow to handle SpotifyPlus OAuth2 authentication.
    """

    # integration DOMAIN (must be a local variable; can't use the constant reference).
    DOMAIN = DOMAIN

    # integration configuration entry major version number.
    VERSION = 2

    # re-authorization request entry.
    reauth_entry: ConfigEntry | None = None


    @property
    def logger(self) -> logging.Logger:
        """Return logger."""
        return logging.getLogger(__name__)


    @property
    def extra_authorize_data(self) -> dict[str, Any]:
        """
        Extra data that needs to be appended to the authorize url.
        
        Returns:
            A dictionary containing the extra data.
        """
        data:dict = \
        {
            "scope": ",".join(SPOTIFY_SCOPES),
            "show_dialog": "true"
        }
        
        _logsi.LogDictionary(SILevel.Verbose, "Configure Component extra_authorize_data - data (dictionary)", data)
        return data


    async def async_oauth_create_entry(self, data:dict[str,Any]) -> FlowResult:
        """ 
        Create an oauth config entry or update existing entry for reauth. 
        
        Args:
            data (dict):
                Configuration data for the entry (e.g. id, name, token, auth_implementation, etc).
                
        Returns:
            A `FlowResult` object that indicates the flow result.
        """
        spotifyClient:SpotifyClient = None

        try:

            # trace.
            _logsi.EnterMethod(SILevel.Debug)
            _logsi.LogDictionary(SILevel.Verbose, "ConfigFlow is starting the OAuth2 config entry flow - parameters", data, prettyPrint=True)

            try:
            
                # get shared zeroconf instance.
                _logsi.LogVerbose("Retrieving the HA shared Zeroconf instance")
                zeroconf_instance = await zeroconf.async_get_instance(self.hass)

                # create new spotify web api python client instance - "SpotifyClient()".
                # note that Spotify Connect Directory task will be disabled, since we don't need it
                # for creating the OAuth2 application credentials.
                _logsi.LogVerbose("Creating SpotifyClient instance")
                tokenStorageDir:str = "%s/.storage" % (self.hass.config.config_dir)
                tokenStorageFile:str = "%s_tokens.json" % (DOMAIN)
                spotifyClient = await self.hass.async_add_executor_job(
                    SpotifyClient, 
                    None,                   # manager:PoolManager=None,
                    tokenStorageDir,        # tokenStorageDir:str=None,
                    tokenStorageFile,       # tokenStorageFile:str=None,
                    None,                   # tokenUpdater:Callable=None,
                    zeroconf_instance,      # zeroconfClient:Zeroconf=None,
                    None,                   # spotifyConnectUsername:str=None,
                    None,                   # spotifyConnectPassword:str=None,
                    None,                   # spotifyConnectLoginId:str=None,
                    0,                      # spotifyConnectDiscoveryTimeout:float=2.0,   # 0 to disable Spotify Connect Zeroconf browsing features.
                    False,                  # spotifyConnectDirectoryEnabled:bool=True,   # disable Spotify Connect Directory Task.
                    None,                   # spotifyWebPlayerCookieSpdc:str=None,
                    None,                   # spotifyWebPlayerCookieSpkey:str=None,
                )
                _logsi.LogObject(SILevel.Verbose, "SpotifyClient instance created - object", spotifyClient)

                clientId:str = None
                tokenProfileId:str = None

                # set spotify web api token authorization from HA-managed OAuth2 session token.
                _logsi.LogVerbose("Setting SpotifyClient token authorization from OAuth2 session token")
                await self.hass.async_add_executor_job(
                    spotifyClient.SetAuthTokenFromToken, clientId, data["token"], tokenProfileId
                )

                _logsi.LogObject(SILevel.Verbose, "SpotifyClient token authorization was set - object (with AuthToken)", spotifyClient)
                _logsi.LogObject(SILevel.Verbose, "SpotifyClient UserProfile - object", spotifyClient.UserProfile)

            except Exception as ex:
            
                _logsi.LogException(None, ex)
                return self.async_abort(reason="setauthtoken_error")

            # is this a reauthentication request?
            # if so, and the unique id's are different then it's a mismatch error.
            if self.reauth_entry:
                if spotifyClient.UserProfile.Id != self.reauth_entry.data[CONF_ID]:
                    _logsi.LogWarning("Re-authenticated account id ('%s') does not match the initial authentication account id ('%s')!" % (spotifyClient.UserProfile.Id, self.reauth_entry.data[CONF_ID]))
                    return self.async_abort(reason="reauth_account_mismatch")
       
            # set configuration entry unique id (e.g. spotify profile id).
            # this value should match the value assigned in media_player `_attr_unique_id` attribute.
            await self.async_set_unique_id(spotifyClient.UserProfile.Id + "_" + DOMAIN)
            _logsi.LogVerbose("ConfigFlow assigned unique_id of '%s' for Spotify UserProfile '%s'" % (self.unique_id, spotifyClient.UserProfile.DisplayName))

            # the following code would display an error if the unique_id already exists, and
            # would force the user to modify the existing entry.
            # in our case, just overlay the configuration if unique_id is already configured.

            # # one final check to see if a configuration entry already exists for the unique id.
            # # if it IS already configured, then we will send an "already_configured" message 
            # # to the user and halt the flow to prevent a duplicate configuration entry.
            # _logsi.LogVerbose("ConfigFlow is verifying USER ENTRY device details have not already been configured: unique_id=%s, display name=%s" % (self.unique_id, spotifyClient.UserProfile.DisplayName))
            # self._abort_if_unique_id_configured()

            # set configuration data parameters.
            data[CONF_ID] = spotifyClient.UserProfile.Id
            data[CONF_NAME] = spotifyClient.UserProfile.DisplayName
            data[CONF_DESCRIPTION] = "(%s account)" % spotifyClient.UserProfile.Product.capitalize()

            # create the configuration entry.
            _logsi.LogDictionary(SILevel.Verbose, "ConfigFlow is creating a configuration entry for Spotify Id='%s', name='%s'" % (data[CONF_ID], data[CONF_NAME]), data)
            configEntry:FlowResult = self.async_create_entry(
                title=f"SpotifyPlus {data[CONF_NAME]}",
                description=data[CONF_DESCRIPTION],
                data=data
            )
            _logsi.LogDictionary(SILevel.Verbose, "ConfigFlow created configuration entry for Spotify Id='%s', name='%s'" % (data[CONF_ID], data[CONF_NAME]), data, prettyPrint=True)
            return configEntry

        except Exception as ex:
            
            # trace.
            _logsi.LogException(None, ex, logToSystemLogger=False)
            raise
        
        finally:

            # dispose of resources.
            if (spotifyClient is not None):
                spotifyClient.Dispose()

            # trace.
            _logsi.LeaveMethod(SILevel.Debug)


    async def async_step_reauth(self, entry_data:Mapping[str, Any]) -> FlowResult:
        """
        Perform reauth upon an API authentication error or migration of old entries.
        
        Args:
            entry_data (dict|None):
                A dictionary of entry data values.

        Returns:
            A `FlowResult` object that indicates the flow result.
        """
        try:

            # trace.
            _logsi.EnterMethod(SILevel.Debug)
            _logsi.LogDictionary(SILevel.Verbose, "ConfigFlow is starting the OAuth2 Re-Authentication flow - user input parameters", entry_data, prettyPrint=True)

            # get
            self.reauth_entry = self.hass.config_entries.async_get_entry(
                self.context["entry_id"]
            )

            # trace.
            if self.reauth_entry is not None:
                _logsi.LogDictionary(SILevel.Verbose, "reauth_entry Data", self.reauth_entry.data, prettyPrint=True)

            # prompt the user to re-authenticate.
            return await self.async_step_reauth_confirm()

        except Exception as ex:
            
            # trace.
            _logsi.LogException(None, ex, logToSystemLogger=False)
            raise
        
        finally:

            # trace.
            _logsi.LeaveMethod(SILevel.Debug)


    async def async_step_reauth_confirm(self, user_input:dict[str,Any]|None=None) -> FlowResult:
        """
        Dialog that informs the user that reauth is required.
        
        Args:
            user_input (dict|None):
                A dictionary of input data values the user entered on the form if
                the form was submitted, or null if the form is being shown initially.

        Returns:
            A `FlowResult` object that indicates the flow result.
        """
        try:

            # trace.
            _logsi.EnterMethod(SILevel.Debug)
            _logsi.LogDictionary(SILevel.Verbose, "ConfigFlow is confirming the OAuth2 Re-Authentication flow - user input parameters", user_input, prettyPrint=True)
            if self.reauth_entry is not None:
                _logsi.LogDictionary(SILevel.Verbose, "reauth_entry Data", self.reauth_entry.data, prettyPrint=True)

            # is this a reauthentication request?
            # if so, then it's a mismatch error.
            if self.reauth_entry:
                _logsi.LogWarning("Re-authenticated account id ('%s') mismatch detected" % self.reauth_entry.data[CONF_ID])
                return self.async_abort(reason="reauth_account_mismatch")

            # if user has not authenticated then prompt the user to authenticate.
            if user_input is None and self.reauth_entry:
                _logsi.LogVerbose("ConfigFlow is prompting user to authenticate for account id ('%s')" % self.reauth_entry.data[CONF_ID])
                return self.async_show_form(
                    step_id="reauth_confirm",
                    description_placeholders={"account": self.reauth_entry.data[CONF_ID]},
                    errors={},
                )

            # at this point, the user has been authenticated to Spotify.
            # now the user needs to pick an OAuth2 implementation (e.g. application credentials) to use.
            return await self.async_step_pick_implementation(
                user_input={"implementation": self.reauth_entry.data["auth_implementation"]}
            )

        except Exception as ex:
            
            # trace.
            _logsi.LogException(None, ex, logToSystemLogger=False)
            raise
        
        finally:

            # trace.
            _logsi.LeaveMethod(SILevel.Debug)


    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> SpotifyPlusOptionsFlow:
        """
        Get the options flow for this handler, which enables options support.

        This method is invoked when a user clicks the "Configure" button from the integration
        details page of the UI.
        """
        return SpotifyPlusOptionsFlow(config_entry)


class SpotifyPlusOptionsFlow(OptionsFlow):
    """
    Handles options flow for the component.
    
    The options flow allows a user to configure additional options for the component at any time by 
    navigating to the integrations page and clicking the Options button on the card for your component. 
    Generally speaking these configuration values are optional, whereas values in the config flow are 
    required to make the component function.
    """

    def __init__(self, entry:ConfigEntry) -> None:
        """
        Initialize options flow.
        """
        try:

            # trace.
            _logsi.EnterMethod(SILevel.Debug)
            _logsi.LogObject(SILevel.Verbose, "'%s': OptionsFlow is initializing - entry (ConfigEntry) object" % entry.title, entry)
            _logsi.LogDictionary(SILevel.Verbose, "'%s': OptionsFlow entry.data dictionary" % entry.title, entry.data)
            _logsi.LogDictionary(SILevel.Verbose, "'%s': OptionsFlow entry.options dictionary" % entry.title, entry.options)
       
            # initialize storage.
            self._entry = entry
            self._name:str = None

            # load config entry base values.
            self._name = entry.data.get(CONF_NAME, None)

            # load config entry options values.
            self._Options = dict(entry.options)
            
        except Exception as ex:
            
            # trace.
            _logsi.LogException(None, ex, logToSystemLogger=False)
            raise
        
        finally:

            # trace.
            _logsi.LeaveMethod(SILevel.Debug)


    async def async_step_init(self, user_input: None = None) -> ConfigFlowResult:
        """
        Manage the options for the custom component.

        Since we have multiple options dialog forms, we will simply return the first
        options form reference.
        """
        return await self.async_step_01_options_basic()


    async def async_step_01_options_basic(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """
        Manage the basic options for the custom component.

        Args:
            user_input (dict[str,Any]):
                User input gathered from the input form.  
                This argument defaults to None when this step is first called.  
                When the user clicks the submit button on the form, the argument will contain
                a dictionary of the data that was entered.  Home Assistant will do some basic 
                validation on your behalf based on the data schema that you defined (e.g. 
                required field, port number is within a numeric range, etc). 
                
        For a good example, look at HA demo source code:
            /home-assistant-core/homeassistant/components/demo/config_flow.py
            
        Note that the "self.hass.data[DOMAIN][entry.entry_id]" object is present in the
        OptionsFlow "async_step_init" step.  This allows you to access the client if one
        is assigned to the data area.  All you need to do is assign a reference to the 
        "entry:ConfigEntry" in the "__init__" in order to access it.  This saves you from
        instantiating a new instance of the client to retrieve settings.  
        """
        errors: dict[str, str] = {}
        
        try:

            # trace.
            _logsi.EnterMethod(SILevel.Debug)
            _logsi.LogDictionary(SILevel.Verbose, "'%s': OptionsFlow async_step_01_options_basic is starting - user_input" % self._name, user_input)

            # if not the initial entry, then save the entered options; otherwise, prepare the form.
            if user_input is not None:
            
                # update config entry options from user input values.
                self._Options[CONF_OPTION_ALWAYS_ON] = user_input.get(CONF_OPTION_ALWAYS_ON, None)
                self._Options[CONF_OPTION_DEVICE_DEFAULT] = user_input.get(CONF_OPTION_DEVICE_DEFAULT, None)
                self._Options[CONF_OPTION_SPOTIFY_SCAN_INTERVAL] = user_input.get(CONF_OPTION_SPOTIFY_SCAN_INTERVAL, DEFAULT_OPTION_SPOTIFY_SCAN_INTERVAL)
                self._Options[CONF_OPTION_SCRIPT_TURN_OFF] = user_input.get(CONF_OPTION_SCRIPT_TURN_OFF, None)
                self._Options[CONF_OPTION_SCRIPT_TURN_ON] = user_input.get(CONF_OPTION_SCRIPT_TURN_ON, None)
                self._Options[CONF_OPTION_SOURCE_LIST_HIDE] = user_input.get(CONF_OPTION_SOURCE_LIST_HIDE, None)
                self._Options[CONF_OPTION_TURN_OFF_AUTO_PAUSE] = user_input.get(CONF_OPTION_TURN_OFF_AUTO_PAUSE, True)
                self._Options[CONF_OPTION_TURN_ON_AUTO_RESUME] = user_input.get(CONF_OPTION_TURN_ON_AUTO_RESUME, True)
                self._Options[CONF_OPTION_TURN_ON_AUTO_SOURCE_SELECT] = user_input.get(CONF_OPTION_TURN_ON_AUTO_SOURCE_SELECT, True)

                # validations.
                # spotify scan interval must be in the 4 to 60 range (if specified).
                spotifyScanInterval:int = user_input.get(CONF_OPTION_SPOTIFY_SCAN_INTERVAL, DEFAULT_OPTION_SPOTIFY_SCAN_INTERVAL)
                if (spotifyScanInterval is not None) and ((spotifyScanInterval < 4) or (spotifyScanInterval > 60)):
                    errors["base"] = "spotify_scan_interval_range_invalid"

                # any validation errors?
                if "base" not in errors:
                    
                    # no - store the updated config entry options.
                    _logsi.LogDictionary(SILevel.Verbose, "'%s': OptionsFlow is updating configuration options - options" % self._name, self._Options)
                    self._Options.update(user_input)

                    # show the next configuration options form.
                    return await self.async_step_02_options_player()

            # load available spotify connect devices;
            device_list:list[str] = await self.hass.async_add_executor_job(self._GetPlayerDevicesList)

            # log device that is currently selected.
            device_default:str = self._Options.get(CONF_OPTION_DEVICE_DEFAULT, None)
            _logsi.LogVerbose("'%s': OptionsFlow option '%s' - SELECTED value: '%s'" % (self._name, CONF_OPTION_DEVICE_DEFAULT, device_default))

            # if no devices, then remove device default value.
            if (device_list is None):
                device_list = []
                _logsi.LogVerbose("'%s': OptionsFlow option '%s' - Spotify Connect device list is empty; removing default device selection" % (self._name, CONF_OPTION_DEVICE_DEFAULT))
                self._Options.pop(CONF_OPTION_DEVICE_DEFAULT, None)
                   
            # create validation schema.
            schema = vol.Schema(
                {
                    # note - DO NOT use "default" argument on the following - use "suggested_value" instead.
                    # using "default=" does not allow a null value to be selected!
                    vol.Optional(
                        CONF_OPTION_DEVICE_DEFAULT,
                        description={"suggested_value": self._Options.get(CONF_OPTION_DEVICE_DEFAULT)},
                        ): SelectSelector(
                                SelectSelectorConfig(
                                    options=device_list or [],
                                    mode=SelectSelectorMode.DROPDOWN
                        )
                    ),
                    vol.Optional(CONF_OPTION_SOURCE_LIST_HIDE, 
                                 description={"suggested_value": self._Options.get(CONF_OPTION_SOURCE_LIST_HIDE)},
                                 ): cv.string,
                    vol.Optional(CONF_OPTION_SCRIPT_TURN_ON, 
                                 description={"suggested_value": self._Options.get(CONF_OPTION_SCRIPT_TURN_ON)},
                                 ): selector.EntitySelector(selector.EntitySelectorConfig(integration=DOMAIN_SCRIPT, 
                                                            multiple=False),
                    ),
                    vol.Optional(CONF_OPTION_SCRIPT_TURN_OFF, 
                                 description={"suggested_value": self._Options.get(CONF_OPTION_SCRIPT_TURN_OFF)},
                                 ): selector.EntitySelector(selector.EntitySelectorConfig(integration=DOMAIN_SCRIPT, 
                                                            multiple=False),
                    ),
                    vol.Optional(CONF_OPTION_SPOTIFY_SCAN_INTERVAL, 
                                 description={"suggested_value": self._Options.get(CONF_OPTION_SPOTIFY_SCAN_INTERVAL)},
                                 ): cv.positive_int,
                    vol.Optional(CONF_OPTION_ALWAYS_ON, 
                                 description={"suggested_value": self._Options.get(CONF_OPTION_ALWAYS_ON)},
                                 ): cv.boolean,
                    vol.Optional(CONF_OPTION_TURN_OFF_AUTO_PAUSE, 
                                 description={"suggested_value": self._Options.get(CONF_OPTION_TURN_OFF_AUTO_PAUSE)},
                                 default=True,  # default to True if not supplied
                                 ): cv.boolean,
                    vol.Optional(CONF_OPTION_TURN_ON_AUTO_RESUME, 
                                 description={"suggested_value": self._Options.get(CONF_OPTION_TURN_ON_AUTO_RESUME)},
                                 default=True,  # default to True if not supplied
                                 ): cv.boolean,
                    vol.Optional(CONF_OPTION_TURN_ON_AUTO_SOURCE_SELECT, 
                                 description={"suggested_value": self._Options.get(CONF_OPTION_TURN_ON_AUTO_SOURCE_SELECT)},
                                 default=True,  # default to True if not supplied
                                 ): cv.boolean,
                }
            )
            
            # any validation errors? if so, then log them.
            if "base" in errors:
                _logsi.LogDictionary(SILevel.Warning, "'%s': OptionsFlow 01_options_basic contained validation errors" % self._name, errors)

            _logsi.LogVerbose("'%s': OptionsFlow is showing the 01_options_basic configuration options form" % self._name)
            return self.async_show_form(
                step_id="01_options_basic", 
                data_schema=schema, 
                description_placeholders={CONF_NAME: self._name},
                errors=errors or {},
                last_step=False,
            )

        except Exception as ex:
            
            # trace.
            _logsi.LogException(None, ex, logToSystemLogger=False)
            raise
        
        finally:

            # trace.
            _logsi.LeaveMethod(SILevel.Debug)

    
    async def async_step_02_options_player(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """
        Manage the credential options for the custom component.

        Args:
            user_input (dict[str,Any]):
                User input gathered from the input form.  
                This argument defaults to None when this step is first called.  
                When the user clicks the submit button on the form, the argument will contain
                a dictionary of the data that was entered.  Home Assistant will do some basic 
                validation on your behalf based on the data schema that you defined (e.g. 
                required field, port number is within a numeric range, etc). 
                
        For a good example, look at HA demo source code:
            /home-assistant-core/homeassistant/components/demo/config_flow.py
            
        Note that the "self.hass.data[DOMAIN][entry.entry_id]" object is present in the
        OptionsFlow "async_step_init" step.  This allows you to access the client if one
        is assigned to the data area.  All you need to do is assign a reference to the 
        "entry:ConfigEntry" in the "__init__" in order to access it.  This saves you from
        instantiating a new instance of the client to retrieve settings.  
        """
        errors: dict[str, str] = {}
        
        try:

            # trace.
            _logsi.EnterMethod(SILevel.Debug)
            _logsi.LogDictionary(SILevel.Verbose, "'%s': OptionsFlow async_step_02_options_player is starting - user_input" % self._name, user_input)

            # if not the initial entry, then save the entered options; otherwise, prepare the form.
            if user_input is not None:
            
                # update config entry options from user input values.
                self._Options[CONF_OPTION_DEVICE_LOGINID] = user_input.get(CONF_OPTION_DEVICE_LOGINID, None)
                self._Options[CONF_OPTION_DEVICE_USERNAME] = user_input.get(CONF_OPTION_DEVICE_USERNAME, None)
                self._Options[CONF_OPTION_DEVICE_PASSWORD] = user_input.get(CONF_OPTION_DEVICE_PASSWORD, None)
                
                # validations.
                # if device username was entered then device password is required.
                deviceLoginid:str = user_input.get(CONF_OPTION_DEVICE_LOGINID, None)
                deviceUsername:str = user_input.get(CONF_OPTION_DEVICE_USERNAME, None)
                devicePassword:str = user_input.get(CONF_OPTION_DEVICE_PASSWORD, None)
                if (deviceUsername is not None) and (devicePassword is None):
                    errors["base"] = "device_password_required"
                if (deviceUsername is None) and (devicePassword is not None):
                    errors["base"] = "device_username_required"

                # any validation errors? if not, then ...
                if "base" not in errors:
                    
                    # store the updated config entry options.
                    _logsi.LogDictionary(SILevel.Verbose, "'%s': OptionsFlow is updating configuration options - options" % self._name, self._Options)

                    # for the last options form, we will call "async_create_entry" to update 
                    # the options and store them to disk.
                    return self.async_create_entry(
                        title="", 
                        data=self._Options
                    )

            # log device that is currently selected.
            device_loginid:str = self._Options.get(CONF_OPTION_DEVICE_LOGINID, None)
            _logsi.LogVerbose("'%s': OptionsFlow option '%s' - value: '%s'" % (self._name, CONF_OPTION_DEVICE_LOGINID, device_loginid))
            device_username:str = self._Options.get(CONF_OPTION_DEVICE_USERNAME, None)
            _logsi.LogVerbose("'%s': OptionsFlow option '%s' - value: '%s'" % (self._name, CONF_OPTION_DEVICE_USERNAME, device_username))
                   
            # create validation schema.
            schema = vol.Schema(
                {
                    # note - DO NOT use "default" argument on the following - use "suggested_value" instead.
                    # using "default=" does not allow a null value to be selected!
                    vol.Optional(CONF_OPTION_DEVICE_LOGINID, 
                                 description={"suggested_value": self._Options.get(CONF_OPTION_DEVICE_LOGINID)},
                                 ): cv.string,
                    vol.Optional(CONF_OPTION_DEVICE_USERNAME, 
                                 description={"suggested_value": self._Options.get(CONF_OPTION_DEVICE_USERNAME)},
                                 ): cv.string,
                    vol.Optional(CONF_OPTION_DEVICE_PASSWORD, 
                                 description={"suggested_value": self._Options.get(CONF_OPTION_DEVICE_PASSWORD)},
                                 ): cv.string,
                }
            )
            
            # any validation errors? if so, then log them.
            if "base" in errors:
                _logsi.LogDictionary(SILevel.Warning, "'%s': OptionsFlow 02_options_player contained validation errors" % self._name, errors)

            _logsi.LogVerbose("'%s': OptionsFlow is showing the 02_options_player configuration options form" % self._name)
            return self.async_show_form(
                step_id="02_options_player", 
                data_schema=schema, 
                description_placeholders={CONF_NAME: self._name},
                errors=errors or {},
                last_step=True
            )
        
        except Exception as ex:
            
            # trace.
            _logsi.LogException(None, ex, logToSystemLogger=False)
            raise
        
        finally:

            # trace.
            _logsi.LeaveMethod(SILevel.Debug)

    
    def _GetPlayerDevicesList(self) -> list:
        """
        Retrieves Spotify Connect device list from the Spotify Web API.
        """
        try:

            # trace.
            _logsi.EnterMethod(SILevel.Debug)
            
            # get configuration instance data so we can reference the client instance.
            _logsi.LogVerbose("'%s': OptionsFlow is retrieving instance data" % self._name)
            data:InstanceDataSpotifyPlus = self.hass.data[DOMAIN].get(self._entry.entry_id, None)
            _logsi.LogObject(SILevel.Verbose, "'%s': OptionsFlow instance data.spotifyClient" % self._name, data.spotifyClient)
            _logsi.LogObject(SILevel.Verbose, "'%s': OptionsFlow instance data.options" % self._name, data.options)
            
            # get spotify connect player device list.
            _logsi.LogVerbose("'%s': OptionsFlow is retrieving Spotify Connect player devices" % self._name)
            devices:SpotifyConnectDevices = data.spotifyClient.GetSpotifyConnectDevices()

            # build string array of all devices.
            result:list = []
            item:Device
            for item in devices.GetDeviceList():
                result.append(item.SelectItemNameAndId)

            # trace.
            _logsi.LogArray(SILevel.Verbose, "'%s': OptionsFlow option '%s' - available values" % (self._name, CONF_OPTION_DEVICE_DEFAULT), result)
            return result
            
        except Exception as ex:
            
            _logsi.LogError("'%s': OptionsFlow could not retrieve Spotify Connect player device list: %s" % (self._name, str(ex)))
            return []
        
        finally:

            # trace.
            _logsi.LeaveMethod(SILevel.Debug)
