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
from typing import Any
import voluptuous as vol
import ssl
import socket
import sys

from spotifywebapipython import SpotifyClient
from spotifywebapipython.models import Device, SpotifyConnectDevices

from homeassistant.components import zeroconf
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlowResult,
    OptionsFlow,
    SOURCE_REAUTH,
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
from smartinspectpython.siauto import SIAuto, SILevel, SISession, SIColors, SIMethodParmListContext
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
        
        _logsi.LogDictionary(SILevel.Verbose, "Configure Component extra_authorize_data - data (dictionary)", data, colorValue=SIColors.Tan)
        return data


    async def async_generate_authorize_url(self) -> str:
        """
        Generate a url for the user to authorize.
        
        Returns:
            A string containing the authorization url used to authenticate the user.
        """
        # verify ssl / tls setup prior to authorizing, just in case the PyOpenSSL
        # module is injected (causes Spotify authorization to fail).
        self._ssl_verify()

        # invoke base class method.
        return await super().async_generate_authorize_url()


    async def async_oauth_create_entry(self, data:dict[str,Any]) -> ConfigFlowResult:
        """ 
        Create an oauth config entry or update existing entry for reauth. 
        
        Args:
            data (dict):
                Configuration data for the entry (e.g. id, name, token, auth_implementation, etc).
                
        Returns:
            A `ConfigFlowResult` object that indicates the flow result.
        """
        spotifyClient:SpotifyClient = None

        try:

            # trace.
            _logsi.EnterMethod(SILevel.Debug, colorValue=SIColors.Tan)
            _logsi.LogDictionary(SILevel.Verbose, "ConfigFlow is starting the OAuth2 config entry flow - parameters", data, prettyPrint=True, colorValue=SIColors.Tan)

            try:
            
                # get shared zeroconf instance.
                _logsi.LogVerbose("Retrieving the HA shared Zeroconf instance", colorValue=SIColors.Tan)
                zeroconf_instance = await zeroconf.async_get_instance(self.hass)

                # create new spotify web api python client instance - "SpotifyClient()".
                # note that Spotify Connect Directory task will be disabled, since we don't need it
                # for creating the OAuth2 application credentials.
                _logsi.LogVerbose("Creating SpotifyClient instance, and retrieving account information", colorValue=SIColors.Tan)
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
                _logsi.LogObject(SILevel.Verbose, "SpotifyClient instance created - object", spotifyClient, colorValue=SIColors.Tan)

            except Exception as ex:
            
                _logsi.LogException(None, ex, colorValue=SIColors.Tan)
                return self.async_abort(reason="connection_error")

            try:
            
                clientId:str = None
                tokenProfileId:str = None

                # set spotify web api token authorization from HA-managed OAuth2 session token.
                _logsi.LogVerbose("Setting SpotifyClient token authorization from OAuth2 session token", colorValue=SIColors.Tan)
                await self.hass.async_add_executor_job(
                    spotifyClient.SetAuthTokenFromToken, clientId, data["token"], tokenProfileId
                )

                _logsi.LogObject(SILevel.Verbose, "SpotifyClient token authorization was set - object (with AuthToken)", spotifyClient, colorValue=SIColors.Tan)
                _logsi.LogObject(SILevel.Verbose, "SpotifyClient UserProfile - object", spotifyClient.UserProfile, colorValue=SIColors.Tan)

            except Exception as ex:
            
                _logsi.LogException(None, ex, colorValue=SIColors.Tan)
                return self.async_abort(reason="setauthtoken_error")

            # set configuration entry unique id (e.g. spotify profile id).
            # this value should match the value assigned in media_player `_attr_unique_id` attribute.
            await self.async_set_unique_id(spotifyClient.UserProfile.Id + "_" + DOMAIN)
            _logsi.LogVerbose("ConfigFlow assigned unique_id of '%s' for Spotify UserProfile '%s'" % (self.unique_id, spotifyClient.UserProfile.DisplayName), colorValue=SIColors.Tan)

            # is this a reauthentication request?
            # if so, then abort if the unique ID does not match the reauth / reconfigure context.
            if self.source == SOURCE_REAUTH:
                _logsi.LogVerbose("ConfigFlow re-auth source detected; checking for account mismatch using unique_id of '%s' for Spotify DisplayName '%s'" % (self.unique_id, spotifyClient.UserProfile.DisplayName), colorValue=SIColors.Tan)
                self._abort_if_unique_id_mismatch(reason="reauth_account_mismatch")
                return self.async_update_reload_and_abort(
                    self._get_reauth_entry(), title=spotifyClient.UserProfile.DisplayName, data=data
                )

            # one final check to see if a configuration entry already exists for the unique id.
            # if it IS already configured, then we will display an "already_configured" message 
            # to the user and halt the flow to prevent a duplicate configuration entry.
            # this will also prevent the HA system log warning: "Detected that custom integration
            # 'xxx'xcreates a config entry when another entry with the same unique ID exists.".
            _logsi.LogVerbose("ConfigFlow is verifying USER ENTRY device details have not already been configured: unique_id=\"%s\", display name=\"%s\"" % (self.unique_id, spotifyClient.UserProfile.DisplayName), colorValue=SIColors.Tan)
            self._abort_if_unique_id_configured(
                error="already_configured",
                description_placeholders={
                    "userinfo_name": spotifyClient.UserProfile.DisplayName,
                    "userinfo_id": spotifyClient.UserProfile.Id
                    },
            )

            # set configuration data parameters.
            data[CONF_ID] = spotifyClient.UserProfile.Id
            data[CONF_NAME] = spotifyClient.UserProfile.DisplayName
            data[CONF_DESCRIPTION] = "(%s account)" % spotifyClient.UserProfile.Product.capitalize()

            # create the configuration entry.
            _logsi.LogDictionary(SILevel.Verbose, "ConfigFlow is creating a configuration entry for Spotify Id='%s', name='%s'" % (data[CONF_ID], data[CONF_NAME]), data, colorValue=SIColors.Tan)
            configEntry:FlowResult = self.async_create_entry(
                title=f"SpotifyPlus {data[CONF_NAME]}",
                description=data[CONF_DESCRIPTION],
                data=data
            )
            _logsi.LogDictionary(SILevel.Verbose, "ConfigFlow created configuration entry for Spotify Id='%s', name='%s'" % (data[CONF_ID], data[CONF_NAME]), data, prettyPrint=True, colorValue=SIColors.Tan)
            return configEntry

        except Exception as ex:
            
            # trace.
            _logsi.LogException(None, ex, logToSystemLogger=False, colorValue=SIColors.Tan)
            raise
        
        finally:

            # dispose of resources.
            if (spotifyClient is not None):
                spotifyClient.Dispose()

            # trace.
            _logsi.LeaveMethod(SILevel.Debug, colorValue=SIColors.Tan)


    async def async_step_reauth(self, entry_data:Mapping[str, Any]) -> ConfigFlowResult:
        """
        Perform reauth upon an API authentication error or migration of old entries.
        
        Args:
            entry_data (dict|None):
                A dictionary of entry data values.

        Returns:
            A `ConfigFlowResult` object that indicates the flow result.

        Refer to the following developer guide on how to handle expired application credentials:
        - https://developers.home-assistant.io/docs/integration_setup_failures/#handling-expired-credentials
        - https://developers.home-assistant.io/docs/config_entries_config_flow_handler/#reauthentication

        ReAuth processing can be tested by calling the `entry.async_start_reauth(hass)` method
        from the __init__.py `async_setup_entry` logic (after session token is established).
        """
        try:

            # trace.
            _logsi.EnterMethod(SILevel.Debug, colorValue=SIColors.Tan)
            _logsi.LogDictionary(SILevel.Verbose, "ConfigFlow is starting the OAuth2 Re-Authentication flow - user input parameters", entry_data, prettyPrint=True, colorValue=SIColors.Tan)

            # prompt the user to re-authenticate.
            return await self.async_step_reauth_confirm()

        except Exception as ex:
            
            # trace.
            _logsi.LogException(None, ex, logToSystemLogger=False, colorValue=SIColors.Tan)
            raise
        
        finally:

            # trace.
            _logsi.LeaveMethod(SILevel.Debug, colorValue=SIColors.Tan)


    async def async_step_reauth_confirm(self, user_input:dict[str,Any]|None=None) -> ConfigFlowResult:
        """
        Dialog that informs the user that reauth is required.
        
        Args:
            user_input (dict|None):
                A dictionary of input data values the user entered on the form if
                the form was submitted, or null if the form is being shown initially.

        Returns:
            A `ConfigFlowResult` object that indicates the flow result.
        """
        try:

            # trace.
            _logsi.EnterMethod(SILevel.Debug, colorValue=SIColors.Tan)
            _logsi.LogDictionary(SILevel.Verbose, "ConfigFlow is confirming the OAuth2 Re-Authentication flow - user input parameters", user_input, prettyPrint=True, colorValue=SIColors.Tan)

            reauth_account_name = "unknown"
            reauth_account_id = "unknown"

            # get reauth config entry linked to the current context.
            reauth_entry = self._get_reauth_entry()
            if (reauth_entry is not None):

                # trace.
                if (_logsi.IsOn(SILevel.Verbose)):
                    _logsi.LogObject(SILevel.Verbose, "ConfigFlow OAuth2 Re-Authentication flow - reauth_entry object", reauth_entry, colorValue=SIColors.Tan)
                    _logsi.LogDictionary(SILevel.Verbose, "ConfigFlow OAuth2 Re-Authentication flow - reauth_entry data", reauth_entry.data, prettyPrint=True, colorValue=SIColors.Tan)

                # default reauth account information details.
                # note that there could be instances where the "id" and "name" attributes 
                # do not exist in the reauth entry data; in this case, we will use the
                # unique_id and the title instead.
                reauth_account_id = reauth_entry.data.get(CONF_ID, None) or reauth_entry.unique_id.replace("_" + DOMAIN, "")  # drop the "_spotifyplus" suffix
                reauth_account_name = reauth_entry.data.get(CONF_NAME, None) or reauth_entry.title

            # if user has not authenticated then prompt the user to authenticate.
            if user_input is None:

                _logsi.LogVerbose("ConfigFlow is prompting user to authenticate for account name \"%s\", id \"%s\"" % (reauth_account_name, reauth_account_id), colorValue=SIColors.Tan)
                return self.async_show_form(
                    step_id="reauth_confirm",
                    description_placeholders={
                        "account_id": reauth_account_id,
                        "account_name": reauth_account_name
                        },
                    errors={},
                )

            # at this point, the user has been authenticated to Spotify.
            # now the user needs to pick an OAuth2 implementation (e.g. application credentials) to use.
            return await self.async_step_pick_implementation(
                user_input={"implementation": reauth_entry.data["auth_implementation"]}
            )

        except Exception as ex:
            
            # trace.
            _logsi.LogException(None, ex, logToSystemLogger=False, colorValue=SIColors.Tan)
            raise
        
        finally:

            # trace.
            _logsi.LeaveMethod(SILevel.Debug, colorValue=SIColors.Tan)


    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> SpotifyPlusOptionsFlow:
        """
        Get the options flow for this handler, which enables options support.

        This method is invoked when a user clicks the "Configure" button from the integration
        details page of the UI.
        """
        return SpotifyPlusOptionsFlow(config_entry)


    def _ssl_verify(self) -> None:
        """
        Check if pyopenssl was injected into urllib3 by the `requests` module initialization.

        At this point, the integration has not been installed yet but is in the process of being installed.

        If pyopenssl is injected then we will log a warning as Spotify authorization will probably 
        fail with a `certificate verify failed` error when pyopenssl `do_handshake()` method is called.
        """
        apiMethodName:str = 'config_flow._ssl_verify'
        apiMethodParms:SIMethodParmListContext = None

        try:

            # if pyopenssl is injected then we will log a warning as Spotify authorization will probably 
            # fail with a `certificate verify failed` error when pyopenssl `do_handshake()` method is called.
            # in this case, the certificate chain is valid and processing successfully, but the failure
            # occurs during TLS Server Name Indication (SNI) processing.  the pyopenssl module does not
            # support TLS SNI processing.  
            
            # this is usually caused by a conflicting custom integration that is installed in HA.
            # the offending integration can usually be found by searching the HA /config/custom_components/
            # folder (and all sub-folders) for these phrases: "urllib3", "pyopenssl".  

            # try:
            #     # TEST TODO force urllib3 to use PyOpenSSL for testing.
            #     _logsi.LogWarning("TEST TODO forcing urllib3 to use PyOpenSSL for TLS verification testing", colorValue=SIColors.Red)
            #     import urllib3.contrib.pyopenssl
            #     urllib3.contrib.pyopenssl.inject_into_urllib3()
            # except Exception as ex:
            #     _logsi.LogException("TEST TODO Could not force urllib3 to use PyOpenSSL for TLS verification testing!", ex, logToSystemLogger=False, colorValue=SIColors.Red)

            # force a reference to requests, which will call `inject_into_urllib3` method
            # if the PyOpenSSL library is installed and HAS_SNI = False (SNI support disabled).
            import requests

            # is TLS SNI support enabled in Python?
            has_sni:bool = getattr(ssl, "HAS_SNI", False)

            # trace.
            apiMethodParms = _logsi.EnterMethodParmList(SILevel.Debug, apiMethodName, colorValue=SIColors.Tan)
            apiMethodParms.AppendKeyValue("Python Version", sys.version)
            apiMethodParms.AppendKeyValue("TLS SNI Support?", "ENABLED in Python" if has_sni else "DISABLED")
            apiMethodParms.AppendKeyValue("OpenSSL Version", ssl.OPENSSL_VERSION)
            apiMethodParms.AppendKeyValue("OpenSSL HAS_SNI", getattr(ssl, "HAS_SNI", False))
            apiMethodParms.AppendKeyValue("OpenSSL Default Verify Paths", ssl.get_default_verify_paths())

            is_pyopenssl:bool = False
            try:
                import urllib3.util.ssl_
                is_pyopenssl = getattr(urllib3.util.ssl_, "IS_PYOPENSSL", False)
                apiMethodParms.AppendKeyValue("urllib3 present?", "YES")
                apiMethodParms.AppendKeyValue("urllib3 Using PyOpenSSL?", is_pyopenssl)
            except Exception as e:
                apiMethodParms.AppendKeyValue("urllib3 check failed", str(e))

            try:
                import cryptography
                apiMethodParms.AppendKeyValue("Cryptography Version", cryptography.__version__)
            except Exception:
                apiMethodParms.AppendKeyValue("Cryptography", "NOT INSTALLED")

            try:
                import OpenSSL
                apiMethodParms.AppendKeyValue("pyOpenSSL Version", OpenSSL.__version__)
            except Exception:
                apiMethodParms.AppendKeyValue("pyOpenSSL", "NOT INSTALLED")

            # trace.
            _logsi.LogMethodParmList(SILevel.Verbose, "Verifying TLS and SSL authorization environment parameters", apiMethodParms, colorValue=SIColors.Tan)
            
            # log various conditions that may cause Spotify OAuth2 to fail.
            if has_sni == False:
                _logsi.LogWarning("SSL TLS SNI support is DISABLED, which may cause Spotify OAuth to fail with `certificate verify failed` errors if pyopenssl is installed!")

            if is_pyopenssl == True:

                # The following will try to prevent PyOpenSSL from overriding the Python OpenSSL stack,
                # which can be a problem when the `requests` and `urllib3` libraries are used together.
                # The `requests.__init__` method overrides the standard Python OpenSSL library with the
                # PyOpenSSL library if TLS SNI support is disabled AND the PyOpenSSL library is
                # installed; it does this by calling the `pyopenssl.inject_into_urllib3()` method.
                #
                # To restore the standard Python OpenSSL library, the `pyopenssl.extract_from_urllib3()` 
                # method can be called to remove the PyOpenSSL override.
                #
                # The PyOpenSSL library cannot be used with the Spotify Web API, as it causes all calls
                # to fail with "certificate verify failed" exceptions.  Note that the SSL certificate
                # validation works fine, but the surrounding TLS Server Name Indication is what fails.
                #
                # The standard Python OpenSSL library correctly handles the TLS SNI verification to the
                # Spotify Web API.
                try:

                    _logsi.LogWarning("pyOpenSSL has been injected into URLLIB3 by another custom component!  This could cause SSL `certificate verify failed` errors to occur due to TLS handshake failures", colorValue=SIColors.Tan)
                    _logsi.LogWarning("Extracting pyOpenSSL from URLLIB3, and restoring the standard Python OpenSSL library", colorValue=SIColors.Tan)

                    # remove PyOpenSSL from urllib3, restoring the standard Python OpenSSL library.
                    import urllib3.contrib.pyopenssl
                    urllib3.contrib.pyopenssl.extract_from_urllib3()

                except Exception as ex:

                    _logsi.LogWarning("Could not restore the standard Python OpenSSL library!  This could cause SSL `certificate verify failed` errors to occur due to TLS handshake failures! Error: %s" % str(ex), colorValue=SIColors.Red)

        except Exception as e:

            # trace.
            _logsi.LogVerbose("Could not determine OAuth2 SSL authorization environment parameters!  Error: %s" % str(e), colorValue=SIColors.Red)
            # ignore exceptions here, as they will be handled if / when authorization fails.

        finally:
        
            # trace.
            _logsi.LeaveMethod(SILevel.Debug, apiMethodName, colorValue=SIColors.Tan)


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
            if (data) and (data.spotifyClient):
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
