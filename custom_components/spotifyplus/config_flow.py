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

from spotifywebapipython import SpotifyClient

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_DESCRIPTION, CONF_ID, CONF_NAME
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import config_entry_oauth2_flow

from .const import DOMAIN, SPOTIFY_SCOPES

# get smartinspect logger reference; create a new session for this module name.
from smartinspectpython.siauto import SIAuto, SILevel, SISession, SIColors
import logging
_logsi:SISession = SIAuto.Si.GetSession(__name__)
if (_logsi == None):
    _logsi = SIAuto.Si.AddSession(__name__, True)
_logsi.SystemLogger = logging.getLogger(__name__)


class SpotifyFlowHandler(config_entry_oauth2_flow.AbstractOAuth2FlowHandler, domain=DOMAIN):
    """
    Config flow to handle Spotify OAuth2 authentication.
    """

    DOMAIN = DOMAIN
    VERSION = 1

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
        try:

            # trace.
            _logsi.EnterMethod(SILevel.Debug)
            _logsi.LogDictionary(SILevel.Verbose, "ConfigFlow is starting the OAuth2 config entry flow - parameters", data, prettyPrint=True)

            try:
            
                # create new spotify web api python client instance.
                _logsi.LogVerbose("Creating SpotifyClient instance")
                tokenStorageDir:str = "%s/custom_components/%s/data" % (self.hass.config.config_dir, DOMAIN)
                spotifyClient:SpotifyClient = await self.hass.async_add_executor_job(
                    SpotifyClient, None, tokenStorageDir, None
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

            except Exception:
            
                return self.async_abort(reason="connection_error")

            # is this a reauthentication request?
            # if so, and the unique id's are different then it's a mismatch error.
            if self.reauth_entry:
                if spotifyClient.UserProfile.Id != self.reauth_entry.data[CONF_ID]:
                    _logsi.LogWarning("Re-authenticated account id ('%s') does not match the initial authentication account id ('%s')!" % (spotifyClient.UserProfile.Id, self.reauth_entry.data[CONF_ID]))
                    return self.async_abort(reason="reauth_account_mismatch")
       
            # set configuration entry unique id (e.g. spotify profile id).
            await self.async_set_unique_id(spotifyClient.UserProfile.Id)
            _logsi.LogVerbose("ConfigFlow assigned unique_id of '%s' for Spotify UserProfile '%s'" % (self.unique_id, spotifyClient.UserProfile.DisplayName))

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
