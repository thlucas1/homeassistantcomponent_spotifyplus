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

from .const import SPOTIFY_SEARCH_LIMIT_TOTAL
from .const import (
    BrowsableMedia, 
    SPOTIFY_BROWSE_LIMIT_TOTAL,
    SPOTIFY_SEARCH_LIMIT_TOTAL, 
)

# get smartinspect logger reference; create a new session for this module name.
from smartinspectpython.siauto import SIAuto, SILevel, SISession, SIMethodParmListContext, SIColors
import logging
_logsi:SISession = SIAuto.Si.GetSession(__name__)
if (_logsi == None):
    _logsi = SIAuto.Si.AddSession(__name__, True)
_logsi.SystemLogger = logging.getLogger(__name__)


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
        searchResp:SearchResponse = None

        # default search criteria type (comma-delimited string of criteria types).
        criteriaType:str = None  # will default to "track"

        # was query criteria specified?
        if (query):
        
            # was media filter class(es) specified?
            if (query.media_filter_classes):

                _logsi.LogVerbose("'%s': Filtering by media filter class: \"%s\"" % (playerName, str(query.media_filter_classes)))

                # create a comma-delimited string of criteria types.      
                mapping = {
                    MediaClass.ARTIST: SpotifyMediaTypes.ARTIST.value,
                    MediaClass.ALBUM: SpotifyMediaTypes.ALBUM.value,
                    MediaClass.TRACK: SpotifyMediaTypes.TRACK.value,
                    MediaClass.MUSIC: SpotifyMediaTypes.TRACK.value,
                    MediaClass.PLAYLIST: SpotifyMediaTypes.PLAYLIST.value,
                    MediaClass.APP: SpotifyMediaTypes.AUDIOBOOK.value,
                    MediaClass.PODCAST: SpotifyMediaTypes.SHOW.value,
                    MediaClass.EPISODE: SpotifyMediaTypes.EPISODE.value,
                }
                media_types = [
                    mapping[cls] for cls in query.media_filter_classes if cls in mapping
                ]
                criteriaType = ','.join(media_types)  # comma-delimited string of criteria types

            # was a media content type specified?
            # note that this integration does not use media content type, but rather media filter classes.
            # some generic media players use media content type though, so support it.
            elif (query.media_content_type):

                _logsi.LogVerbose("'%s': Filtering by media content type: \"%s\"" % (playerName, str(query.media_content_type)))
                criteriaType = query.media_content_type
                media_content_type = query.media_content_type
                
                # change default "music" to "track".
                if (isinstance(criteriaType,str)):
                    criteriaType = criteriaType.replace("music","track")
                    criteriaType = criteriaType.replace("MUSIC","track")

                # if searching favorites, then use the favorite-specific methods and filter the results.
                # we will load the results to a SearchResponse object so we can use the same method
                # to build the BrowseMedia object as the general Spotify search.
                if media_content_type == BrowsableMedia.SPOTIFY_USER_SAVED_ALBUMS:
                    _logsi.LogVerbose("Filtering Spotify user Album favorites")
                    media:AlbumPageSaved = client.GetAlbumFavorites(limitTotal=SPOTIFY_BROWSE_LIMIT_TOTAL, filterCriteria=query.search_query)
                    searchResp:SearchResponse = SearchResponse(query.search_query, SpotifyMediaTypes.ALBUM.value)
                    searchResp.LoadAlbumsFromAlbumPageSaved(media)
            
                elif media_content_type == BrowsableMedia.SPOTIFY_USER_FOLLOWED_ARTISTS:
                    _logsi.LogVerbose("'%s': Filtering Spotify user Artist favorites" % playerName)
                    media:ArtistPage = client.GetArtistsFollowed(limitTotal=SPOTIFY_BROWSE_LIMIT_TOTAL, filterCriteria=query.search_query)
                    searchResp:SearchResponse = SearchResponse(query.search_query, SpotifyMediaTypes.ARTIST.value)
                    searchResp.LoadArtistsFromArtistPage(media)
            
                elif media_content_type == BrowsableMedia.SPOTIFY_USER_SAVED_AUDIOBOOKS:
                    _logsi.LogVerbose("Filtering Spotify user Audiobook favorites")
                    media:AudiobookPageSimplified = client.GetAudiobookFavorites(limitTotal=SPOTIFY_BROWSE_LIMIT_TOTAL, filterCriteria=query.search_query)
                    searchResp:SearchResponse = SearchResponse(query.search_query, SpotifyMediaTypes.AUDIOBOOK.value)
                    searchResp.LoadAudiobooksFromAudiobookPageSimplified(media)
            
                elif media_content_type == BrowsableMedia.SPOTIFY_USER_PLAYLISTS:
                    _logsi.LogVerbose("'%s': Filtering Spotify user Playlist favorites" % playerName)
                    media:PlaylistPageSimplified = client.GetPlaylistFavorites(limitTotal=SPOTIFY_BROWSE_LIMIT_TOTAL, filterCriteria=query.search_query)
                    searchResp:SearchResponse = SearchResponse(query.search_query, SpotifyMediaTypes.PLAYLIST.value)
                    searchResp.LoadPlaylistsFromPlaylistPageSimplified(media)
            
                elif media_content_type == BrowsableMedia.SPOTIFY_USER_SAVED_SHOWS:
                    _logsi.LogVerbose("Filtering Spotify user Show favorites")
                    media:ShowPageSaved = client.GetShowFavorites(limitTotal=SPOTIFY_BROWSE_LIMIT_TOTAL, filterCriteria=query.search_query)
                    searchResp:SearchResponse = SearchResponse(query.search_query, SpotifyMediaTypes.SHOW.value)
                    searchResp.LoadShowsFromShowPageSaved(media)
            
                elif media_content_type == BrowsableMedia.SPOTIFY_USER_SAVED_TRACKS:
                    _logsi.LogVerbose("Filtering Spotify user Track favorites")
                    media:TrackPageSaved = client.GetTrackFavorites(limitTotal=SPOTIFY_BROWSE_LIMIT_TOTAL, filterCriteria=query.search_query)
                    searchResp:SearchResponse = SearchResponse(query.search_query, SpotifyMediaTypes.TRACK.value)
                    searchResp.LoadTracksFromTrackPageSaved(media)

                elif media_content_type == BrowsableMedia.SPOTIFY_USER_RECENTLY_PLAYED:
                    _logsi.LogVerbose("Filtering Spotify user Recently Played Tracks")
                    media:PlayHistoryPage = client.GetPlayerRecentTracks(limitTotal=SPOTIFY_BROWSE_LIMIT_TOTAL, filterCriteria=query.search_query)
                    searchResp:SearchResponse = SearchResponse(query.search_query, SpotifyMediaTypes.TRACK.value)
                    searchResp.LoadTracksFromPlayHistoryPage(media)
            
                elif media_content_type == BrowsableMedia.SPOTIFY_USER_TOP_ARTISTS:
                    _logsi.LogVerbose("Filtering Spotify user Top Artists")
                    media:ArtistPage = client.GetUsersTopArtists(limitTotal=SPOTIFY_BROWSE_LIMIT_TOTAL, filterCriteria=query.search_query)
                    searchResp:SearchResponse = SearchResponse(query.search_query, SpotifyMediaTypes.TRACK.value)
                    searchResp.LoadArtistsFromArtistPage(media)
            
                elif media_content_type == BrowsableMedia.SPOTIFY_USER_TOP_TRACKS:
                    _logsi.LogVerbose("Filtering Spotify user Top Tracks")
                    media:TrackPage = client.GetUsersTopTracks(limitTotal=SPOTIFY_BROWSE_LIMIT_TOTAL, filterCriteria=query.search_query)
                    searchResp:SearchResponse = SearchResponse(query.search_query, SpotifyMediaTypes.TRACK.value)
                    searchResp.LoadTracksFromTrackPage(media)

                elif media_content_type == BrowsableMedia.SPOTIFY_NEW_RELEASES:
                    _logsi.LogVerbose("Filtering Spotify Album New Releases")
                    media:AlbumPageSimplified = client.GetAlbumNewReleases(limitTotal=SPOTIFY_BROWSE_LIMIT_TOTAL, filterCriteria=query.search_query)
                    searchResp:SearchResponse = SearchResponse(query.search_query, SpotifyMediaTypes.TRACK.value)
                    searchResp.LoadAlbumsFromAlbumPageSimplified(media)

                if searchResp is not None:

                    # trace.
                    _logsi.LogObject(SILevel.Verbose, "Search favorites results - SearchResponse Object: Type='%s', Criteria='%s'" % (searchResp.SearchCriteriaType, searchResp.SearchCriteria), searchResp)

        # if not a favorites search, then search ALL of Spotify for the specified criteria.
        if searchResp is None:

            # search spotify.
            _logsi.LogVerbose("'%s': Searching ALL of Spotify for media: \"%s\" (type=%s)" % (playerName, query.search_query, criteriaType))
            searchResp:SearchResponse = client.Search(query.search_query, criteriaType, limitTotal=SPOTIFY_SEARCH_LIMIT_TOTAL)

        # add search results for all media types.
        _ProcessFoundItems(result, SpotifyMediaTypes.ALBUM, searchResp.Albums.Items)
        _ProcessFoundItems(result, SpotifyMediaTypes.ARTIST.value, searchResp.Artists.Items)
        _ProcessFoundItems(result, SpotifyMediaTypes.AUDIOBOOK.value, searchResp.Audiobooks.Items)
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
            media_content_type=mediaClass, # child and parent will always be the same content type
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
        result = MediaClass.APP
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
    elif (media_class_str == MediaClass.APP.value):
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
