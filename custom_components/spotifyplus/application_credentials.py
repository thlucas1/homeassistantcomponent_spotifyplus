"""Application credentials platform for spotify."""

from homeassistant.components.application_credentials import AuthorizationServer
from homeassistant.core import HomeAssistant


async def async_get_authorization_server(hass: HomeAssistant) -> AuthorizationServer:
    """
    Return authorization server.
    """
    # create a new authorization server instance for Spotify Web API usage.
    auth_server:AuthorizationServer = AuthorizationServer(
        authorize_url="https://accounts.spotify.com/authorize",
        token_url="https://accounts.spotify.com/api/token",
    )

    return auth_server