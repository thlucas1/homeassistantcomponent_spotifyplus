# SpotifyPlus

[![GitHub Release][releases-shield]][releases] [![License][license-shield]](LICENSE) [![docs][docs-shield]][docs] [![hacs][hacs-shield]][hacs]

![Project Maintenance][maintenance-shield] [![BuyMeCoffee][buymecoffee-shield]][buymecoffee]

_Home Assistant Integration to integrate with [spotifyplus][spotifyplus]._  
Extended support for the Spotify Connect media player for use in Home Assistant.

This integration will set up the following platforms.

Platform | Description
-- | --
`media_player` | Media Player Entity.

## Features

The following Home Assistant media_player Platform services are supplied by this integration.
- BROWSE_MEDIA
- MEDIA_ENQUEUE
- NEXT_TRACK
- PAUSE
- PLAY
- PLAY_MEDIA
- PREVIOUS_TRACK
- REPEAT_SET
- SEEK
- SELECT_SOURCE
- SHUFFLE_SET
- TURN_OFF
- TURN_ON
- VOLUME_MUTE
- VOLUME_SET
- VOLUME_STEP

Check out the [Media Player Service Enhancements wiki](https://github.com/thlucas1/homeassistantcomponent_spotifyplus/wiki/Media-Player-Service-Enhancements) page for detailed explanations and YAML examples of the media player service enhancements provided by this integration.

## Custom Services

This integration provides 99% of the services offered by the Spotify Web API.  
Check out the [Services Provided wiki](https://github.com/thlucas1/homeassistantcomponent_spotifyplus/wiki/Services-Provided) page for detailed explanations and YAML examples.

## HACS Installation Instructions

Use the following link to open (and add) the custom repository in HACS:  

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=thlucas1&repository=homeassistantcomponent_spotifyplus&category=Integration)

If the above does not work for you, then use the following steps to add the custom repository manually.
- go to HACS main menu.
- click on the 3-dot overflow menu in the upper right, and select `custom repositories` item.
- copy / paste `https://github.com/thlucas1/homeassistantcomponent_spotifyplus` in the Repository textbox and select `Integration` for the category entry.
- click on `Add` to add the custom repository.
- you can then click on the SpotifyPlus repository entry (you may need to filter your list first to find the new entry).

Note at this point you have only added the repository to the HACS Repository List.  Now it's time to actually download the contents of the repository itself.  You should now be displaying the repository details, which will also display a `Download` button (lower right corner) that can be used to download the repository contents.  
 
- click on `download` to start the download. It will install the spotifyplus integration to your config/custom_components directory.
- restart HA to start using the component.

## Manual Installation

- Using the tool of choice open the directory (folder) for your HA configuration (where you find `configuration.yaml`).
- If you do not have a `custom_components` directory (folder) there, you need to create it.
- In the `custom_components` directory (folder) create a new folder called `spotifyplus`.
- Download _all_ the files from the `custom_components/spotifyplus/` directory (folder) in this repository.
- Place the files you downloaded in the new directory (folder) you created.
- Restart Home Assistant.
- In the HA UI go to "Configuration" -> "Integrations" click "+" and search for "SpotifyPlus"

## Configuration 

[Integration configuration](https://github.com/thlucas1/homeassistantcomponent_spotifyplus/wiki/Installation-Instructions#configuration) is mostly done in the UI, but a configuration file is required for specific device functionality (e.g. Sonos, Chromecast, etc).

<!---->

## Advanced Logging Support

The SmartInspectPython package (installed with this integration) can be used to easily debug the integration.
Note that the standard Home Assistant logger is also supported, but does not provide as much information as the SmartInspect logger.

Check out the [SmartInspect Logging Configuration wiki page](https://github.com/thlucas1/homeassistantcomponent_spotifyplus/wiki/SmartInspect-Logging-Configuration) for more information on how to configure and enable / disable advanced logging.

## Reporting a Problem

Submit a [Bug Report](https://github.com/thlucas1/homeassistantcomponent_spotifyplus/issues/new?labels=bug&template=bug.yml) to bring the issue to my attention. I receive a notification when a new issue is opened, and will do my best to address it in a prompt and professional manner.

## Request a New Feature

Do you have an idea for a new feature that could be added to the integration?  Submit a [Enhancement Request](https://github.com/thlucas1/homeassistantcomponent_spotifyplus/issues/new?labels=enhancement&template=enhancement.yml) to get your idea into the queue. I receive a notification when a new request is opened, and will do my best to turn your idea into the latest and greatest feature.

***

[spotifyplus]: https://github.com/thlucas1/homeassistantcomponent_spotifyplus

[releases-shield]: https://img.shields.io/github/release/thlucas1/homeassistantcomponent_spotifyplus.svg?style=for-the-badge
[releases]: https://github.com/thlucas1/homeassistantcomponent_spotifyplus/releases
[license-shield]: https://img.shields.io/github/license/thlucas1/homeassistantcomponent_spotifyplus.svg?style=for-the-badge
[docs]: https://github.com/thlucas1/homeassistantcomponent_spotifyplus/wiki
[docs-shield]: https://img.shields.io/badge/Docs-Wiki-blue.svg?style=for-the-badge
[hacs]: https://github.com/hacs/integration
[hacs-shield]: https://img.shields.io/badge/HACS-Default-41BDF5.svg?style=for-the-badge

[maintenance-shield]: https://img.shields.io/badge/maintainer-Todd%20Lucas%20%40thlucas1-blue.svg?style=for-the-badge
[buymecoffee]: https://www.buymeacoffee.com/thlucas1
[buymecoffee-shield]: https://img.shields.io/badge/buy%20me%20a%20coffee-donate-yellow.svg?style=for-the-badge
