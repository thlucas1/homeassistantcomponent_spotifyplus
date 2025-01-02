## Change Log

All notable changes to this project are listed here.  

Change are listed in reverse chronological order (newest to oldest).  

<span class="changelog">

###### [ 1.0.78 ] - 2025/01/02

  * Updated underlying `spotifywebapiPython` package requirement to version 1.0.132.  Updated `SpotifyClient` methods `PlayerActivateDevices` and `GetSpotifyConnectDevice` to rediscover the Spotify Connect Zeroconf device after a Disconnect call is issued.  It has been found that some device manufacturers (e.g. Denon) stop and restart the Zeroconf server on the device after a `resetUsers` (e.g. disconnect) call is made, which changes the IP Port number that the device listens on for incoming connections.
  * Removed the deprecated service `player_resolve_device_id` (since 2024/08/15); use the `get_spotify_connect_device` service instead.

###### [ 1.0.77 ] - 2025/01/01

  * Updated underlying `spotifywebapiPython` package requirement to version 1.0.131.  Modified `ZeroconfConnect.GetInformation` method logic to automatically retry the connection (after 250ms, 10s max) to the Spotify Connect Zeroconf device service if a "connection refused" was returned while trying to get device information.  Some Spotify Connect devices take a little bit longer to start accepting connections again after a change.

###### [ 1.0.76 ] - 2024/12/28

  * Updated logic to correctly account for idle state; the integration will go into idle state (instead of staying in paused state) after it detects that the Spotify Web API has dropped the current play state (e.g. the device disconnects from Spotify Connect).
  * Added extra state attribute: `sp_source_list_hide` - List of device names (in lower-case) to hide from the source list.
  * Updated underlying `spotifywebapiPython` package requirement to version 1.0.130.  

###### [ 1.0.75 ] - 2024/12/21

  * Added service `get_cover_image_file` to get the contents of an image url and transfer the contents to the local file system.  This service should only be used to download images for playlists that contain public domain images.  It should not be used to download copyright protected images, as that would violate the Spotify Web API Terms of Service.
  * Updated underlying `spotifywebapiPython` package requirement to version 1.0.129.  

###### [ 1.0.74 ] - 2024/12/20

  * Updated underlying `spotifywebapiPython` package requirement to version 1.0.128.  

###### [ 1.0.73 ] - 2024/12/20

  * Updated underlying `spotifywebapiPython` package requirement to version 1.0.127.  

###### [ 1.0.72 ] - 2024/12/18

  * Updated underlying `spotifywebapiPython` package requirement to version 1.0.126.  

###### [ 1.0.71 ] - 2024/12/17

  * Added extra state attribute: `sp_playing_type` - object type of the currently playing item, or null if nothing is playing.  If not null, it can be one of `track`, `episode`, `ad` or `unknown`.  This allows you to detect when an advertisement is playing for Spotify Free accounts.
  * Bypassed logic in `turn_on` service for Spotify Free account to transfer playback and resume play.  These were failing for Spotify Free accounts, since they require Premium account to execute.
  * Removed unsupported features for Spotify Free subscription: PAUSE, PLAY, PLAY_MEDIA, SELECT_SOURCE, VOLUME_MUTE, VOLUME_SET, VOLUME_STEP.  These features require Spotify premium membership.
  * Replaced caught exception calls of `raise HomeAssistantError` with `raise ServiceValidationError`, which should reduce stack traces in the logs which are not necessary.
  
###### [ 1.0.70 ] - 2024/12/12

  * Added [configuration option](https://github.com/thlucas1/homeassistantcomponent_spotifyplus/wiki/Device-Configuration-Options#spotify-polling-scan-interval) to specify the Spotify polling scan interval.  This option specifies the polling scan interval (in seconds) used to query Spotify Player playstate.

###### [ 1.0.69 ] - 2024/12/09

  * Updated code when calling the spotifywebapiPython `GetPlaylist` method to not log exception information if the call fails.  This was causing exceptions to be logged when trying to retrieve details for Spotify-owned algorithmic playlist details; the call now fails due to the unannounced Spotify Web API changes that were made by the Spotify Developer Team on 2024/11/27.  Note that the call works fine for user-defined playlists.
  * The `media_playlist` extended attribute will now display `Unknown` if the currently playing context is a Spotify-owned algorithmic playlist (e.g. "Daily Mix 1", etc). It will display the correct playlist name if the currently playing context is a user-defined playlist.  
  * The `sp_playlist_name` extended attribute will now display `Unknown` if the currently playing context is a Spotify-owned algorithmic playlist (e.g. "Daily Mix 1", etc).  It will display the correct playlist name if the currently playing context is a user-defined playlist.  
  * Updated service `turn_on` to first check if the previously selected source is active or not; if so, then play is resumed immediately; if not, then a `source_select` is performed to activate the selected source.
  * Updated underlying `spotifywebapiPython` package requirement to version 1.0.125.  

###### [ 1.0.68 ] - 2024/12/06

  * Updated service `player_transfer_playback` to resume play if `play=True` and `force_activate_device=True`.  If forcefully activating a device, then we need to resume play manually if `play=True` was specified; this is due to the device losing its current status since it was being forcefully activated (e.g. disconnected and reconnected).
  * Updated underlying `spotifywebapiPython` package requirement to version 1.0.123.

###### [ 1.0.67 ] - 2024/12/02

  * Updated underlying `spotifywebapiPython` package requirement to version 1.0.122.
  * The above `spotifywebapiPython` package will now return an exception due to the functions being deprecated by the Spotify development team.  More information can be found on the [Spotify Developer Forum Blog post](https://developer.spotify.com/blog/2024-11-27-changes-to-the-web-api) that was conveyed on November 27, 2024.  The following methods will now raise a `SpotifyApiError` exception due to the Spotify development team changes: `GetArtistRelatedArtists`, `GetTrackRecommendations`, `GetTrackAudioFeatures`, `GetFeaturedPlaylists`, `GetCategoryPlaylists`, `GetGenres`.  The following properties were also marked as deprecated for the same reason: `TrackSimplified.PreviewUrl`.
  * Due to the above changes made by Spotify, any Algorithmic and Spotify-owned editorial playlists are no longer accessible or have more limited functionality.  This means that you can no longer obtain details via the `SpotifyClient.GetPlaylist` and `SpotifyClient.GetPlaylistItems` methods for Spotify-owned / generated content (e.g. "Made For You", etc).  A `404 - Not Found` error will be returned when trying to retrieve information for these playlist types.

###### [ 1.0.66 ] - 2024/11/20

  * Added service `get_playlist_cover_image` to get the current image associated with a specific playlist.
  * Added service `get_playlists_for_user` to get a list of the playlists owned or followed by a Spotify user.
  * Added service `player_media_pause` to pause media play for the specified Spotify Connect device.
  * Added service `player_media_resume` to resume media play for the specified Spotify Connect device.
  * Added service `player_media_skip_next` to skip to next track in the user's queue for the specified Spotify Connect device.
  * Added service `player_media_skip_previous` to skip to previous track in the user's queue for the specified Spotify Connect device.
  * Updated service `playlist_items_add` to return a result property that contains a snapshot ID for the updated playlist.
  * Updated service `playlist_items_clear` to return a result property that contains a snapshot ID for the updated playlist.
  * Updated service `playlist_items_remove` to return a result property that contains a snapshot ID for the updated playlist.
  * Added service `playlist_items_reorder` to reorder items in a user's playlist.
  * Added service `playlist_items_replace` to replace one or more items in a user's playlist. Replacing items in a playlist will overwrite its existing items. This service can also be used to clear a playlist.
  * Added service `check_users_following` to check to see if the current user is following one or more users.
  * Updated service `zeroconf_device_connect` to add the `delay` argument.
  * Updated service `zeroconf_device_disconnect` to add the `delay` argument.
  * Updated underlying `spotifywebapiPython` package requirement to version 1.0.121.

###### [ 1.0.65 ] - 2024/11/15

  * Updated underlying `spotifywebapiPython` package requirement to version 1.0.119.

###### [ 1.0.64 ] - 2024/11/03

  * Added service `add_player_queue_items` to add one or more items to the end of the user's current Spotify Player playback queue. 
  * Added service `get_artist_related_artists` to get Spotify catalog information about artists similar to a given artist.  Similarity is based on analysis of the Spotify community's listening history.
  * Added service `get_artist_top_tracks` to get Spotify catalog information about an artist's top tracks by country.
  * Added service `get_audiobook` to get Spotify catalog information for a single audiobook.  Audiobooks are only available within the US, UK, Canada, Ireland, New Zealand and Australia markets.
  * Updated underlying `spotifywebapiPython` package requirement to version 1.0.114.

###### [ 1.0.63 ] - 2024/10/31

  * Updated underlying `spotifywebapiPython` package requirement to version 1.0.113.

###### [ 1.0.62 ] - 2024/10/27

  * Added service `get_track_recommendations` to get track recommendations for specified criteria.
  * Added the following extra state attribute: `sp_track_is_explicit` - denotes the nowplaying track contains explicit lyrics (true) or not (false).

###### [ 1.0.61 ] - 2024/10/22

  * Added service `get_audiobook_chapters` to get Spotify catalog information about an audiobook's chapters.
  * Added service `get_chapter` to get Spotify catalog information about a single audiobook chapter.
  * Added service `check_playlist_followers` to check to see if the current user is following a specified playlist.
  * Added service `get_album_tracks` to get Spotify catalog information about an album's tracks.  
  * Added service `get_artist_info` to get artist about information from the Spotify Artist Biography page for the specified Spotify artist ID.
  * Added service `get_playlist_items` to get full details of the items of a playlist owned by a Spotify user.
  * Updated service `get_spotify_connect_devices` to return a `SpotifyConnectDevices` instead of a list of `Device` instances.  This contains more detailed information about the device, as well as when the list was last refreshed from real-time queries.
  * Updated underlying `spotifywebapiPython` package requirement to version 1.0.112.

###### [ 1.0.60 ] - 2024/10/04

  * Added service `player_media_seek` to seek to the given absolute or relative position in the user's currently playing track for the specified Spotify Connect device.
  * Updated service `get_show_favorites` to include the `exclude_audiobooks` argument, which allows you to limit the results to only podcast items (by default).  For some reason, the Spotify Web API returns both audiobook and podcast items.
  * Updated Spotify Connect device processing to only require the userid and password configuration options when authenticating to devices that require user and password values.  Some devices only require a loginid value (e.g. spotifyd, Spotify Connect AddOn, librespot, Sonos, etc).  The user should not have to specify userid and password options if they are not required!
  * Updated service description strings to correct HASSFest validation errors on GitHub.
  * Updated underlying `spotifywebapiPython` package requirement to version 1.0.106.

###### [ 1.0.59 ] - 2024/09/28

  * Added support for devices that utilize spotifyd / librespot.  See the [wiki documentation](https://github.com/thlucas1/homeassistantcomponent_spotifyplus/wiki/Device-Configuration-Options#librespot-and-spotifyd-device-support) for more information on how to configure support for spotifyD / librespot applications.
  * Corrected the `media_content_id` attribute value when content is played on a Sonos device.  Prior to this fix, the value was loaded from the Sonos Soco API `get_current_track_info.uri` value that contained the `x-sonos-vli` value (e.g. `x-sonos-vli:RINCON_38420B909DC801400:2,spotify:e934941535d7b182815bf688490ce8a8`).  The `media_content_id` attribute value now contains a true Spotify URI value (e.g. `spotify:track:6kYyS9g4WJeRzTYqsmcMmM`).
  * Added the following extra state attribute: `sp_device_is_brand_sonos` - denotes the source device is a Sonos brand device (true) or not (false).
  * Added service `get_track` to get Spotify catalog information for a single track identified by its unique Spotify ID.
  * Added service `get_episode` to get Spotify catalog information for a single episode identified by its unique Spotify ID.
  * Added `SoCo` requirements.
  * Updated underlying `spotifywebapiPython` package requirement to version 1.0.101.

###### [ 1.0.58 ] - 2024/09/25

  * Added the following extra state attribute: `sp_item_type` - denotes the type of episode being played: `podcast` or `audiobook`.
  * Updated underlying `spotifywebapiPython` package requirement to version 1.0.99.

###### [ 1.0.57 ] - 2024/09/20

  * Added service `get_audiobook_favorites` to get a list of the audiobooks saved in the current Spotify user's 'Your Library'.
  * Added service `get_episode_favorites` to get a list of the episodes saved in the current Spotify user's 'Your Library'.
  * Updated underlying `spotifywebapiPython` package requirement to version 1.0.97.

###### [ 1.0.56 ] - 2024/09/19

  * Updated underlying `spotifywebapiPython` package requirement to version 1.0.96.

###### [ 1.0.55 ] - 2024/09/16

  * Added service `check_album_favorites` to check if one or more albums (or the currently playing album) exists in the current user's 'Your Library' favorites.
  * Added service `check_artists_following` to check if one or more artists (or the currently playing artist) exists in the current user's 'Your Library' favorites.
  * Added service `check_audiobook_favorites` to check if one or more audiobooks (or the currently playing audiobook) exists in the current user's 'Your Library' favorites.
  * Added service `check_episode_favorites` to check if one or more episodes (or the currently playing episode) exists in the current user's 'Your Library' favorites.
  * Added service `check_show_favorites` to check if one or more shows (or the currently playing show) exists in the current user's 'Your Library' favorites.
  * Added service `check_track_favorites` to check if one or more tracks (or the currently playing track) exists in the current user's 'Your Library' favorites.
  * Added service `get_tracks_audio_features` to get audio features for multiple tracks based on their Spotify IDs.
  * Updated service `follow_playlist` to make the `playlistId` argument optional; if not supplied, the currently playing playlist id value is used instead.
  * Updated service `get_album` to make the `albumId` argument optional; if not supplied, the currently playing album id value is used instead.
  * Updated service `get_artist` to make the `artistId` argument optional; if not supplied, the currently playing artist id value is used instead.
  * Updated service `get_artist_albums` to make the `artistId` argument optional; if not supplied, the currently playing artist id value is used instead.
  * Updated service `get_playlist` to make the `playlistId` argument optional; if not supplied, the currently playing playlist id value is used instead.
  * Updated service `get_show` to make the `showId` argument optional; if not supplied, the currently playing show id value is used instead.
  * Updated service `get_show_episodes` to make the `showId` argument optional; if not supplied, the currently playing show id value is used instead.
  * Updated service `unfollow_playlist` to make the `playlistId` argument optional; if not supplied, the currently playing playlist id value is used instead.
  * Added the following extra state attributes: `sp_playlist_name`, `sp_playlist_uri`, `sp_user_country`, `sp_user_display-name`, `sp_user_email`, `sp_user_id`, `sp_user_product`, `sp_user_uri`.
  * Updated underlying `spotifywebapiPython` package requirement to version 1.0.95.

###### [ 1.0.54 ] - 2024/08/22

  * Updated `config_flow` to correct a bug in the token authorization process that was introduced in v1.0.52 with the Token Cache file location change.  This was preventing new instances of the integration to be setup due to `connection_error` exceptions in the Spotify OAuth2 authorization method.
  * Updated `media_player.select_source` service to correctly process the state of the player so that the player resume playing on the target source.  Prior to this fix, play was not resumed (e.g. still paused) on the target source.

###### [ 1.0.53 ] - 2024/08/20

  * Added `DefaultDeviceId` processing to set the default device id (or name) to use for player transport methods (e.g. play, pause, skip, etc) that do not specify a device id and there is no active Spotify player detected.  This should avoid the `No Active Device` exceptions returned from the Spotify Web API when playback transport methods are called after long pauses of inactivity.
  * Updated underlying `spotifywebapiPython` package requirement to version 1.0.88.

###### [ 1.0.52 ] - 2024/08/19

  * Changed storage location of authorization Token Cache file to prevent data loss on version updates.  The file was moved from `\config\custom_components\spotifyplus\data\tokens.json` to `\config\.storage\spotifyplus_tokens.json`, which will allow it to persist between version updates.  Note that you can simply copy the Token Cache file from the old location to the new location prior to this update, so that you don't have to re-run the AuthTokenGenerator.py script again.
  * Added service `remove_audiobook_favorites` to remove one or more audiobooks (or the currently playing audiobook) from the current user's 'Your Library' favorites.
  * Added service `remove_episode_favorites` to remove one or more show episodes (or the currently playing episode) from the current user's 'Your Library' favorites.
  * Added service `remove_show_favorites` to remove one or more shows (or the currently playing show) from the current user's 'Your Library' favorites.
  * Added service `save_audiobook_favorites` to save one or more audiobooks (or the currently playing audiobook) to the current user's 'Your Library' favorites.
  * Added service `save_episode_favorites` to save one or more show episodes (or the currently playing episode) to the current user's 'Your Library' favorites.
  * Added service `save_show_favorites` to save one or more shows (or the currently playing show) to the current user's 'Your Library' favorites.
  * Updated underlying `spotifywebapiPython` package requirement to version 1.0.86.

###### [ 1.0.51 ] - 2024/08/18

  * Updated service `player_transfer_playback` to check Sonos transport status after transferring playback to the target device, and play / pause the transport as designated by the `play` argument.

###### [ 1.0.50 ] - 2024/08/18

  * Updated service `select_source` to refresh the Spotify Connect device list prior to selecting the new source.
  * Updated service `player_transfer_playback` to refresh the Spotify Connect device list prior to transferring playback to the target device.
  * Updated underlying `spotifywebapiPython` package requirement to version 1.0.84.

###### [ 1.0.49 ] - 2024/08/16

  * Updated service `zeroconf_device_connect` to correctly process Spotify Connect requests for token type `authorization_code` devices.  This requires you to setup a seperate OAuth2 authorization access token outside of Home Assistant in order to activate these devices.  This (currently) only affects Sonos devices, as they are the only manufacturer (that I am aware of) that implements the `authorization_code` token type.  More information can be found in the [wiki documentation](https://github.com/thlucas1/homeassistantcomponent_spotifyplus/wiki/Device-Configuration-Options#oauth2-token-for-tokentypeauthorization_code-devices).
  * Added service `get_spotify_connect_device` to get information about a specific Spotify Connect player device, and (optionally) activate the device if it requires it.
  * Updated service `player_resolve_device_id` with deprecated status, as the `get_spotify_connect_device` service offers the same (and more) functionality.
  * Updated service descriptions for services that specify a `limit` argument.
  * Added `sortResult` argument to the various services that return lists that can be sorted.  If True (default), result items are sorted by name prior to returning to the caller; otherwise, results are left in the order that the Spotify Web API returned them.
  * Updated underlying `spotifywebapiPython` package requirement to version 1.0.83.

###### [ 1.0.48 ] - 2024/08/10

  * Updated service `player_media_play_track_favorites` to transfer the Spotify users track favorites (200 max) to the Sonos device and play them from a local queue.  See the [Sonos Limitations](https://github.com/thlucas1/homeassistantcomponent_spotifyplus/wiki/Spotify-Connect-Brand-Notes#sonos) wiki documentation for further details about Sonos-related issues.

###### [ 1.0.47 ] - 2024/08/05

  * Added configuration option to hide specified device names from the HA media player UI source list.

###### [ 1.0.46 ] - 2024/08/04

  * Updated service `player_transfer_playback` to transfer the Spotify users queue (20 items max) to the Sonos device (instead of just the currently playing track).  See the [Sonos Limitations](https://github.com/thlucas1/homeassistantcomponent_spotifyplus/wiki/Spotify-Connect-Brand-Notes#sonos) wiki documentation for further details about Sonos-related issues.

###### [ 1.0.45 ] - 2024/07/30

  * Updated service `player_transfer_playback` to support Sonos devices with some limitations; see the [Sonos Limitations](https://github.com/thlucas1/homeassistantcomponent_spotifyplus/wiki/Spotify-Connect-Brand-Notes#sonos) wiki documentation for further details.
  * Updated service `player_media_play_context` and `player_media_play_tracks` to support Sonos devices with some limitations; see the [Sonos Limitations](https://github.com/thlucas1/homeassistantcomponent_spotifyplus/wiki/Spotify-Connect-Brand-Notes#sonos) wiki documentation for further details.
  * Fixed a bug in the `player_transfer_playback` service that was not transferring control to offline Spotify Connect devices.

###### [ 1.0.44 ] - 2024/07/24

  * Updated service `player_set_shuffle_mode` to correctly set shuffle mode for Sonos devices.
  * Updated service `player_set_repeat_mode` to correctly set repeat mode for Sonos devices.
  * Updated service `player_set_volume_level` to correctly set volume level for Sonos devices.

###### [ 1.0.43 ] - 2024/07/23

  * Updated service `player_media_play_context` to correctly default the `position_ms` and `offset_position` argument values.  This was causing the playlist to always start at the first track if the `offset_position` argument value was not supplied.  This manifested itself when shuffle was enabled, as the playlist should have started at a random track and was not doing so.
  * Updated service `player_media_play_tracks` to correctly default the `position_ms` argument value.

###### [ 1.0.42 ] - 2024/07/23

  * Added service `player_set_repeat_mode` that sets repeat mode for the specified Spotify Connect device.
  * Added service `player_set_shuffle_mode` that sets shuffle mode for the specified Spotify Connect device.
  * Added service `player_set_volume_level` that sets volume level for the specified Spotify Connect device.

###### [ 1.0.41 ] - 2024/07/18

  * Added support for Sonos device control and status updates via the Python [SoCo (Sonos Controller) API](https://docs.python-soco.com/en/latest/) package.  These changes will allow you to control playback, obtain current status, and transfer Spotify Connect Player control to / from the device.  Note that this works best when the device is controlled by the various Spotify Applications (e.g. Desktop, Mobile, and Web).  Sonos devices that are controlled by the Sonos Applications can behave erratically when controlled by SpotifyPlus.  More information on why that is can be found on the [Spotify Connect Brand Notes](https://github.com/thlucas1/homeassistantcomponent_spotifyplus/wiki/Spotify-Connect-Brand-Notes) wiki documentation page.
  * Updated underlying `spotifywebapiPython` package requirement to version 1.0.76.

###### [ 1.0.40 ] - 2024/07/02

  * Updated underlying `spotifywebapiPython` package requirement to version 1.0.73.
  * Updated `SpotifyClient.GetSpotifyConnectDevices` to gracefully handle device unavailable scenarios.  It will try to reach the device by its direct HostIpAddress first; if that fails, then it will try to reach the device by its Server alias; if that fails, then it will log a warning that the device could not be reached and press on.
  * Updated `ZeroconfConnect.Disconnect` to check for an invalid JSON response. It has been found that some devices (Sonos, etc) do not return a proper JSON response for the `resetUsers` action.  If a JSON response was not returned, then it will treat the http status code as the response code; if it's not a 200, then it will raise an exception.

###### [ 1.0.39 ] - 2024/06/28

  * Updated underlying `spotifywebapiPython` package requirement to version 1.0.72.

###### [ 1.0.38 ] - 2024/06/27

  * Corrected various services that use float values that were incorrectly defined as strings by the service schema.
  * Updated underlying `spotifywebapiPython` package requirement to version 1.0.71.

###### [ 1.0.37 ] - 2024/06/27

  * Updated underlying `spotifywebapiPython` package requirement to version 1.0.70.

###### [ 1.0.36 ] - 2024/06/26

  * Added support for Spotify Connect LoginID specification in configuration options.
  * Updated underlying `spotifywebapiPython` package requirement to version 1.0.69.

###### [ 1.0.35 ] - 2024/06/26

  * Updated underlying `spotifywebapiPython` package requirement to version 1.0.68.

###### [ 1.0.34 ] - 2024/06/25

  * Updated underlying `spotifywebapiPython` package requirement to version 1.0.67.

###### [ 1.0.33 ] - 2024/06/25

  * Updated underlying `spotifywebapiPython` package requirement to version 1.0.66.
  * The underlying `spotifywebapiPython` update changes the way the Spotify Connect Zeroconf API processes the `status` and `spotifyError` response values.  Some Spotify Connect devices return them as strings, while other return them as numerics.  Spotify Zeroconf API specifically says they should be returned as integer values.

###### [ 1.0.32 ] - 2024/06/25

  * Updated underlying `spotifywebapiPython` package requirement to version 1.0.65.
  * The underlying `spotifywebapiPython` update changes the way the Spotify Connect Zeroconf API `addUser` call is processed to account for "ERROR-INVALID-PUBLICKEY" statuses returned for some devices.  This will retry the connection request with the PublicKey value returned from the initial request.

###### [ 1.0.31 ] - 2024/06/24

  * Updated underlying `spotifywebapiPython` package requirement to version 1.0.64.
  * The underlying `spotifywebapiPython` update changes the way Spotify Connect Zeroconf API return codes are processed.  It now processes the Spotify Zeroconf API status code from the JSON response instead of processing the HTTP request status code.  It has been found that some Spotify Connect manufacturers return different HTTP status codes than other manufacturers; but the Spotify Connect `status`, `statusString` and `spotifyError` JSON properties seem to be consistent across the board.
  * The underlying `spotifywebapiPython` update also filters out duplicate Spotify Connect Device entries for devices that have been grouped together.  For example, the "Bose-ST10-1" and "Bose-ST10-2" are grouped as a stereo pair; there will be two Zeroconf discovery result entries with different instance names, but their Zeroconf getInfo endpoint url will be the same.  This was causing two entries to appear in the device list, when there should have been only one.

###### [ 1.0.30 ] - 2024/06/22

  * Updated `config_flow` to utilize the HA shared Zeroconf instance.
  * Updated underlying `spotifywebapiPython` package requirement to version 1.0.62.
  * The underlying `spotifywebapiPython` update fixes a potential memory leak with the Zeroconf discovery process.

###### [ 1.0.29 ] - 2024/06/21

  * Fixed a bug due to `SpotifyConnect` addon not properly returning a "Content-Type: application/json" header in it's Spotify Zeroconf API responses.  This was causing an error in the SpotifyPlus integration when trying to retrieve the Spotify Connect device list, and returning errors in the configuration options form.
  * Updated underlying `spotifywebapiPython` package requirement to version 1.0.61.

###### [ 1.0.28 ] - 2024/06/19

  * Added service `get_spotify_connect_devices` that gets information about all available Spotify Connect player devices.
  * Added service `get_player_now_playing` that gets object properties currently being played on the user's Spotify account.
  * Added service `player_activate_devices` that activates all static Spotify Connect player devices, and (optionally) switches the active user context to the current user context.
  * Added service `player_resolve_device_id` that resolves a Spotify Connect device identifier from a specified device id, name, alias id, or alias name.  This will ensure that the device id can be found on the network, as well as connect to the device if necessary with the current user context. 
  * Added service `get_player_playback_state` that gets information about the user's current playback state, including track or episode, progress, and active device.
  * Added extra state attribute `media_context_content_id` that contains the Context Content ID of current playing context if one is active; otherwise, None.
  * Updated underlying `spotifywebapiPython` package requirement to version 1.0.59.

###### [ 1.0.27 ] - 2024/06/12

  * Added extra state attribute `media_playlist_content_id` that contains the Content ID of current playing playlist context if one is active; otherwise, None.
  * Added property `media_player.media_playlist_content_id` that contains the Content ID of current playing playlist context if one is active; otherwise, None.
  * Added property `media_player.media_playlist_content_type` that contains the Content Type of current playing playlist if one is playing; otherwise, None.
  * Added property `media_player.media_playlist_description` that contains the Description of current playing playlist if one is playing; otherwise, None.
  * Added property `media_player.media_playlist_image_url` that contains the Image URL of current playing playlist if one is playing; otherwise, None.
  * Updated `use_ssl` description on all of the Zeroconf Device services.

###### [ 1.0.26 ] - 2024/06/10

  * Added service `zeroconf_device_connect` that calls the `addUser` Spotify Zeroconf API endpoint to issue a call to SpConnectionLoginBlob.  If successful, the associated device id is added to the Spotify Connect active device list for the specified user account.
  * Added service `zeroconf_device_disconnect` that calls the `resetUsers` Spotify Zeroconf API endpoint to issue a call to SpConnectionLogout.  The currently logged in user (if any) will be logged out of Spotify Connect, and the device id removed from the active Spotify Connect device list.
  * Removed service `zeroconf_device_resetusers` and replaced it with `zeroconf_device_disconnect`.
  * Updated underlying `spotifywebapiPython` package requirement to version 1.0.48.

###### [ 1.0.25 ] - 2024/06/08

  * Updated underlying `spotifywebapiPython` package requirement to version 1.0.47.

###### [ 1.0.25 ] - 2024/06/08

  * Fixed a bug that was causing `ValueError: list.remove(x): x not in list` exceptions to be raised whenever the user changed configuration options for a service.  This started appearing with the HA 2024.6.1 release.

###### [ 1.0.24 ] - 2024/06/07

  * Updated underlying `spotifywebapiPython` package requirement to version 1.0.46.
  * Added the following requirements to manifest.json so that any dependency `ResolutionImpossible` errors can be quickly identified: 'oauthlib>=3.2.2', 'platformdirs>=4.1.0', 'requests>=2.31.0', 'requests_oauthlib>=1.3.1', 'zeroconf>=0.132.2'.  This bug bit me in the HA 2024.6.1 release when the HA devs upgraded the `requests` dependency to 2.32.3!  The System log was showing that the `spotifywebapiPython` library was the invalid dependency, but it was not - the REAL culprit was the `requests` dependency!

###### [ 1.0.23 ] - 2024/06/07

  * Re-updated underlying `spotifywebapiPython` package requirement to version 1.0.45.

###### [ 1.0.22 ] - 2024/06/07

  * Re-updated underlying `spotifywebapiPython` package requirement to version 1.0.44.

###### [ 1.0.21 ] - 2024/06/07

  * Fixed a bug that caused player state to return an error every 30 seconds when playing the Spotify DJ playlist.  As the Spotify Web API does not support retrieving the DJ playlist (`spotify:playlist:37i9dQZF1EYkqdzj48dyYq`), it simply returns a manually built representation of the Spotify DJ playlist with limited properties populated (uri, id, name, description, etc).  Note that Spotify DJ support is not supported (as of 2024/06/07) by the Spotify Web API (this includes starting play, retrieving playlist details, retrieving playlist items, etc).
  * Added service `zeroconf_discover_devices` to discover Spotify Connect devices on the local network via the ZeroConf (aka MDNS) service, and return details about each device. 
  * Added service `zeroconf_device_getinfo` to retrieve Spotify Connect device information from the Spotify Zeroconf API `getInfo` endpoint.
  * Added service `zeroconf_device_resetusers` to reset users for a Spotify Connect device by calling the Spotify Zeroconf API `resetUsers` endpoint.
  * Updated underlying `spotifywebapiPython` package requirement to version 1.0.44.

###### [ 1.0.20 ] - 2024/06/06

  * Changed all `media_player.schedule_update_ha_state(force_refresh=True)` calls to `schedule_update_ha_state(force_refresh=False)` to improve performance.  Suggested by @bdraco, along with an explanation of why.  Thanks @bdraco!
  * Changed logic to call `session.hass.config_entries.async_update_entry` via a `hass.add_job` call instead of calling directly.  This fixes the issue of `Detected that custom integration 'spotifyplus' calls hass.config_entries.async_update_entry from a thread other than the event loop, which may cause Home Assistant to crash or data to corrupt` that was introduced with HA 2024.6 release.
  * Changed logic to access local file system files via a `hass.async_add_executor_job` call.  This fixes the issue of `Detected blocking call to open inside the event loop by custom integration 'X' ...` that was introduced with HA 2024.6 release.

###### [ 1.0.19 ] - 2024/05/03

  * Changed all `media_player.async_write_ha_state()` calls to `schedule_update_ha_state(force_refresh=True)` calls due to HA 2024.5 release requirements.  This fixes the issue of "Failed to call service X. Detected that custom integration 'Y' calls async_write_ha_state from a thread at Z. Please report it to the author of the 'Y' custom integration.".
  * Added more information to system health display (version, integration configs, etc).
  * Updated Python version from 3.11 to 3.12.3 due to HA 2024.5 release requirements.

###### [ 1.0.18 ] - 2024/04/25

  * Updated various `media_player` services that control playback to verify a Spotify Connect Player device is active.  If there is no active device, or the default device was specified (e.g. "*"), then we will force the configuration option default device to be used and transfer playback to it.  If an active device was found, then we will use it without transferring playback for services that do not specify a `deviceId` argument.  For services that can supply a `deviceId` argument, we will issue a transfer playback command if a device id (or name) was specified.

###### [ 1.0.17 ] - 2024/04/21

  * Added device name support to the following custom services that take a Spotify Connect Player `deviceId` argument for player functions.  You can now specify either a device id or device name in the `deviceId` argument to target a specific Spotify Connect Player device.  Services updated were: `player_media_play_context`, `player_media_play_track_favorites`, `player_media_play_tracks`, `player_transfer_playback`.
  * Updated underlying `spotifywebapiPython` package requirement to version 1.0.43.

###### [ 1.0.16 ] - 2024/04/21

  * Added extra state attribute `spotifyplus_device_id` that lists the Spotify Connect Player device id that is in use.
  * Added extra state attribute `spotifyplus_device_name` that lists the Spotify Connect Player device name that is in use.
  * Refer to the [wiki documentation](https://github.com/thlucas1/homeassistantcomponent_spotifyplus/wiki/Media-Player-Service-Enhancements#state-custom-variables) page for more details about custom state variables.

###### [ 1.0.15 ] - 2024/04/05

  * Added `MediaPlayerEntityFeature.VOLUME_MUTE` support to handle volume mute requests.
  * Added `MediaPlayerEntityFeature.VOLUME_STEP` support to handle volume step requests.
  * Updated Media Browser logic to return an empty `BrowseMedia` object when ignoring Sonos-Card 'favorites' node requests, as a null object was causing numerous `Browse Media should use new BrowseMedia class` log warnings.
  * Updated underlying `spotifywebapiPython` package requirement to version 1.0.42.

###### [ 1.0.14 ] - 2024/04/04

  * Added service `player_media_play_track_favorites` to play all track favorites for the current user.
  * Increased all browse media limits from 50 items to 150 items.
  * Updated Media Browser logic to ignore Sonos-Card 'favorites' node requests, as there is no Spotify direct equivalent.
  * Updated underlying `spotifywebapiPython` package requirement to version 1.0.41.

###### [ 1.0.13 ] - 2024/03/28

  * Updated `_CallScriptPower` method to use the script uniqueid value (instead of the entity_id value) when calling the `turn_on` and `turn_off` scripts.

###### [ 1.0.12 ] - 2024/03/27

  * Updated underlying `spotifywebapiPython` package requirement to version 1.0.40.
  * Added service `turn_on` and `turn_off` support for the player.  Playback control is transferred to the player after turning on.  Configuration options support the execution of scripts to allow external devices to be powered on and off.  Refer to the [wiki documentation](https://github.com/thlucas1/homeassistantcomponent_spotifyplus/wiki/Media-Player-Service-Enhancements#turn-on--off) on how to configure this feature.
  * Added support for media controls to properly function when the Spotify Connect Player loses the active device reference.  For example, when the player goes into an `idle` state due to player pausing for extended period of time, you can now resume play without having to re-select the source (avoids `No active playback device found` errors).

###### [ 1.0.11 ] - 2024/03/24

  * Updated media_player SCAN_INTERVAL to 1 second to inform HA of Spotify status updates in near real time (e.g. pause, resume, next track, etc).
  * Updated `media_player.update` logic to only call the spotifywebapiPython `SpotifyClient.GetPlayerNowPlaying` every 30 seconds OR if a player command is issued (e.g. pause, play, next / previous track, seek, volume, etc) OR if the current track is nearing the end of play (e.g. next track in a playlist or queue).
  * This update adds a few more calls to the Spotify Web API, but not many.  The trade-off is near real-time updates of player status.
  * Added service `follow_playlist` to add the current user as a follower of a playlist.
  * Added service `unfollow_playlist` to remove the current user as a follower of a playlist
  * Added service `follow_users` to add the current user as a follower of one or more users.
  * Added service `unfollow_users` to remove the current user as a follower of one or more users.

###### [ 1.0.10 ] - 2024/03/20

  * Added service `follow_artists` to add the current user as a follower of one or more artists.
  * Added service `unfollow_artists` to remove the current user as a follower of one or more artists.
  * Added service `save_album_favorites` to save one or more items to the current user's album favorites.
  * Added service `remove_album_favorites` to remove one or more items from the current user's album favorites.
  * Updated underlying `spotifywebapiPython` package requirement to version 1.0.37.
  * Updated service `playlist_create` to add the `image_path` argument to allow a cover art image to be assigned when a playlist is created.
  * Updated service `playlist_change` to add the `image_path` argument to allow a cover art image to be updated when a playlist details are updated.

###### [ 1.0.9 ] - 2024/03/19

  * Added service `playlist_create` to create a new Spotify playlist.
  * Added service `playlist_change` to change the details for an existing Spotify playlist.
  * Added service `playlist_cover_image_add` to replace the image displayed for a specified playlist ID.
  * Added service `playlist_items_clear` to remove (clear) all items from a user's playlist.
  * Added service `playlist_items_remove` to remove one or more items from a user's playlist.
  * Added service `save_track_favorites` to save one or more items to the current user's track favorites.
  * Added service `remove_track_favorites` to remove one or more items from the current user's track favorites.
  * Updated `media_player.play_media` method to better support `play_media` service enqueue features.
  * Updated underlying `spotifywebapiPython` package requirement to version 1.0.36.

###### [ 1.0.8 ] - 2024/03/15

  * Added service `playlist_items_add` to add one or more items to a user's playlist.  Items are added in the order they are listed in the `uris` argument.

###### [ 1.0.7 ] - 2024/03/07

  * Updated service `service_spotify_player_media_play_context` to pause the Spotify Connect device before switching play context, and resuming after.
  * Updated service `service_spotify_player_media_play_tracks` to pause the Spotify Connect device before switching play context, and resuming after.
  * Updated media_player to inform HA of manual status updates as they happen (e.g. pause, resume, next track, etc).

###### [ 1.0.6 ] - 2024/03/05

  * Updated service `player_transfer_playback` schema to make the `device_id` argument optional instead of required.  This allows the active spotify connect player to be used (if desired) when transferring playback.
  * commented out the `ignore: "brands"` in validate.yaml, as brands have been added for the integration.

###### [ 1.0.5 ] - 2024/03/02

  * Added configuration option `default_device` to allow a user to specify a default Spotify Connect device to use when one is not active.
  * Added service `player_media_play_context` to start playing one or more tracks of the specified context on a Spotify Connect device.
  * Added service `player_media_play_tracks` to start playing one or more tracks on a Spotify Connect device.
  * Added service `player_transfer_playback` to transfer playback to a new Spotify Connect device and optionally begin playback.
  * Updated underlying `spotifywebapiPython` package requirement to version 1.0.33.

###### [ 1.0.4 ] - 2024/03/01

  * Added service `search_albums` to search the Spotify catalog for matching album criteria.
  * Added service `search_artists` to search the Spotify catalog for matching artist criteria.
  * Added service `search_audiobooks` to search the Spotify catalog for matching audiobook criteria.
  * Added service `search_episodes` to search the Spotify catalog for matching episode criteria.
  * Added service `search_shows` to search the Spotify catalog for matching show (aka podcast) criteria.
  * Added service `search_tracks` to search the Spotify catalog for matching track criteria.
  * Updated underlying `spotifywebapiPython` package requirement to version 1.0.32.

###### [ 1.0.3 ] - 2024/02/28

  * Updated service `get_show_episodes` to include the `limit_total` argument.
  * Added service `get_player_queue_info` to retrieve the player queue information.
  * Added service `get_player_devices` to retrieve player device list.

###### [ 1.0.2 ] - 2024/02/28

  * Updated underlying `spotifywebapiPython` package requirement to version 1.0.31.

###### [ 1.0.1 ] - 2024/02/25

  * Version 1 initial release.

</span>