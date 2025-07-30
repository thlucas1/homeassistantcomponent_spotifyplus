"""Support for Spotify media searching."""
from __future__ import annotations
import logging

from spotifywebapipython import SpotifyClient, SpotifyMediaTypes
from spotifywebapipython.models import *

from homeassistant.components.media_player import (
    BrowseMedia,
    MediaClass,
    SearchMediaQuery,
    SearchMedia,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import IntegrationError

# get smartinspect logger reference; create a new session for this module name.
from smartinspectpython.siauto import SIAuto, SILevel, SISession, SIMethodParmListContext, SIColors
import logging
_logsi:SISession = SIAuto.Si.GetSession(__name__)
if (_logsi == None):
    _logsi = SIAuto.Si.AddSession(__name__, True)
_logsi.SystemLogger = logging.getLogger(__name__)


SPOTIFY_SEARCH_LIMIT_TOTAL = 10
""" Max number of items to return (for each type) from a search request (5). """


def search_media_node(
    hass:HomeAssistant,
    client:SpotifyClient,
    playerName:str,
    query: SearchMediaQuery,
    ) -> SearchMedia:
    """
    Searches the Spotify catalog for the requested criteria, and returns a list of
    BrowseMedia items with the results.
    
    Args:
        hass (HomeAssistant):
            HomeAssistant instance.
        client (SpotifyClient):
            The SpotifyClient instance that will make calls to the device
            to retrieve the data for display in the media browser.
        playerName (str):
            Name of the media player that is calling this method (for tracing purposes).
        query (SearchMediaQuery):
            Search media query criteria to search for.
            Note that `media_filter_classes` can also be passed as a dictionary of values,
            which differs from the method signature which indicates a `list[MediaClass]`.

    Returns:
        A `SearchMedia` object that contains the search results.
    """
    methodParms:SIMethodParmListContext = None
        
    try:

        # trace.
        methodParms = _logsi.EnterMethodParmList(SILevel.Debug)
        methodParms.AppendKeyValue("playerName", playerName)
        methodParms.AppendKeyValue("query", query)
        methodParms.AppendKeyValue("query.media_content_id", query.media_content_id)
        methodParms.AppendKeyValue("query.media_content_type", query.media_content_type)
        methodParms.AppendKeyValue("query.media_filter_classes", query.media_filter_classes)
        methodParms.AppendKeyValue("query.search_query", query.search_query)
        _logsi.LogMethodParmList(SILevel.Verbose, "'%s': Preparing to search for media" % (playerName), methodParms)
        
        result:list[BrowseMedia] = []

        # map MediaClass to SpotifyMediaTypes.
        mapping = {
            MediaClass.ARTIST: SpotifyMediaTypes.ARTIST.value,
            MediaClass.ALBUM: SpotifyMediaTypes.ALBUM.value,
            MediaClass.TRACK: SpotifyMediaTypes.TRACK.value,
            MediaClass.MUSIC: SpotifyMediaTypes.TRACK.value,
            MediaClass.PLAYLIST: SpotifyMediaTypes.PLAYLIST.value,
            MediaClass.DIRECTORY: SpotifyMediaTypes.AUDIOBOOK.value,
            MediaClass.PODCAST: SpotifyMediaTypes.SHOW.value,
            MediaClass.EPISODE: SpotifyMediaTypes.EPISODE.value,
        }
        media_types = [
            mapping[cls] for cls in query.media_filter_classes if cls in mapping
        ]
        criteriaType:str = ','.join(media_types)  # comma-delimited string of criteria types

        # search spotify.
        _logsi.LogVerbose("'%s': Searching for media: \"%s\"" % (playerName, query.search_query))
        searchResp:SearchResponse = client.Search(query.search_query, criteriaType, limitTotal=SPOTIFY_SEARCH_LIMIT_TOTAL)

        # add search results for all media types.
        _ProcessFoundItems(result, SpotifyMediaTypes.ALBUM, searchResp.Albums.Items)
        _ProcessFoundItems(result, SpotifyMediaTypes.ARTIST, searchResp.Artists.Items)
        _ProcessFoundItems(result, SpotifyMediaTypes.AUDIOBOOK, searchResp.Audiobooks.Items)
        _ProcessFoundItems(result, SpotifyMediaTypes.EPISODE, searchResp.Episodes.Items)
        _ProcessFoundItems(result, SpotifyMediaTypes.PLAYLIST, searchResp.Playlists.Items)
        _ProcessFoundItems(result, SpotifyMediaTypes.SHOW, searchResp.Shows.Items)
        _ProcessFoundItems(result, SpotifyMediaTypes.TRACK, searchResp.Tracks.Items)

        # return search results.
        return SearchMedia(result=result)

    except Exception as ex:
            
        # trace.
        _logsi.LogException("'%s': SearchMedia search_media_node exception: %s" % (playerName, str(ex)), ex, logToSystemLogger=False)
        raise IntegrationError(str(ex)) from ex
        
    finally:

        # trace.
        _logsi.LeaveMethod(SILevel.Debug)


def _ProcessFoundItems(
    result:list[BrowseMedia],
    spotifyMediaType:SpotifyMediaTypes,
    items:list[SearchResultBase],
    ) -> None:
    """
    Builds a BrowseMedia object for each search result returned, and appends 
    them to the result collection.
    
    Args:
        result (list[BrowseMedia]):
            List of BrowseMedia items to append results to.
        spotifyMediaType (str):
            Spotify media type.
        items (list[SearchResultBase]):
            List of matching search items found.
    """
    # track and episode media items cannot be expanded (only played);
    # other media types can be expanded to display child items (e.g. Album, Artist, Playlist, etc).
    canExpand:bool = spotifyMediaType not in [
        SpotifyMediaTypes.TRACK,
        SpotifyMediaTypes.EPISODE,
    ]

    # get HA media class for Spotify media type.
    mediaClass:str = _GetMediaClassFromSpotifyMediaType(spotifyMediaType) or MediaClass.DIRECTORY
        
    # process found items.
    item:SearchResultBase
    for item in items:

        # build BrowseMedia object for found item.
        browseMedia:BrowseMedia = BrowseMedia(
            can_expand=canExpand,
            can_play=True,
            children=None,
            children_media_class=None,
            media_class=mediaClass,
            media_content_id=item.Uri,
            media_content_type=item.Type,
            thumbnail=item.ImageUrl,
            title=item.Name
            )

        # trace.
        _logsi.LogObject(SILevel.Verbose, "Search BrowseMedia Object: Type='%s', Id='%s', Title='%s'" % (browseMedia.media_content_type, browseMedia.media_content_id, browseMedia.title), browseMedia)

        # append object to results.
        result.append(browseMedia)


def _GetMediaClassFromSpotifyMediaType(media_type:str) -> MediaClass|None:
    """
    Get the appropriate HA media class for a given Spotify media type.
    """
    result:MediaClass = None

    if (media_type == SpotifyMediaTypes.TRACK.value):
        result = MediaClass.TRACK
    elif (media_type == SpotifyMediaTypes.ALBUM.value):
        result = MediaClass.ALBUM
    elif (media_type == SpotifyMediaTypes.ARTIST.value):
        result = MediaClass.ARTIST
    elif (media_type == SpotifyMediaTypes.PLAYLIST.value):
        result = MediaClass.PLAYLIST
    elif (media_type == SpotifyMediaTypes.SHOW.value):
        result = MediaClass.PODCAST
    elif (media_type == SpotifyMediaTypes.AUDIOBOOK.value):
        result = MediaClass.DIRECTORY
    elif (media_type == SpotifyMediaTypes.EPISODE.value):
        result = MediaClass.EPISODE
    
    return result


def _GetSpotifyMediaTypeFromMediaClass(media_class:str|MediaClass) -> SpotifyMediaTypes|None:
    """
    Get the appropriate Spotify media type for a given HA media class.
    """
    result:SpotifyMediaTypes = None
    media_class_str = str(media_class)

    if (media_class_str == MediaClass.ALBUM.value):
        result = SpotifyMediaTypes.ALBUM
    elif (media_class_str == MediaClass.ARTIST.value):
        result = SpotifyMediaTypes.ARTIST
    elif (media_class_str == MediaClass.DIRECTORY.value):
        result = SpotifyMediaTypes.AUDIOBOOK
    elif (media_class_str == "audiobook"):
        result = SpotifyMediaTypes.AUDIOBOOK
    elif (media_class_str == MediaClass.EPISODE.value):
        result = SpotifyMediaTypes.EPISODE.value
    elif (media_class_str == MediaClass.PLAYLIST.value):
        result = SpotifyMediaTypes.PLAYLIST
    elif (media_class_str == MediaClass.PODCAST.value):
        result = SpotifyMediaTypes.SHOW
    elif (media_class_str == MediaClass.TRACK.value):
        result = SpotifyMediaTypes.TRACK

    return result
