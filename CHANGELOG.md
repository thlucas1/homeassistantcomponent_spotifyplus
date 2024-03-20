## Change Log

All notable changes to this project are listed here.  

Change are listed in reverse chronological order (newest to oldest).  

<span class="changelog">

###### [ 1.0.10 ] - 2024/03/20

  * Added service `follow_artist` to add the current user as a follower of one or more artists.
  * Added service `unfollow_artist` to remove the current user as a follower of one or more artists.
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