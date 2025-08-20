# TPLink Cloud Integration


[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg?style=flat-square&logo=homeassistantcommunitystore)](https://hacs.xyz/)
![GitHub Release](https://img.shields.io/github/v/release/iluvdata/tplink_cloud)
![Dynamic JSON Badge](https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fraw.githubusercontent.com%2Filuvdata%2Ftplink_cloud%2Frefs%2Fheads%2Fmain%2Fcustom_components%2Ftplink_cloud%2Fmanifest.json&query=%24.version&prefix=v&label=dev-version&labelColor=orange)





A custom HomeAssistant integration that allows you to integrate a few TPLink/Kasa/Tapo devices by the cloud interface.  This integration relies extensively on the base [TP-Link Smart Home](https://www.home-assistant.io/integrations/tplink/) integration as well as the underlying [python-kasa](https://github.com/python-kasa/python-kasa) library.

Configuration via Homeassistant UI.

## Rationale

This integration is antithetical to the ethos of HomeAssistant which advocates direct local control of your IoT devices.  What about devices not on your local network?  I'd still advocate accessing these devices via VPN using the core TP-Link Smart Home integration.

### Use Case

What about devices that you want to add to your HomeAssistant instance that are network where you cannot setup a VPN.  In my case devices attached to my condo utility room network? You have two solutions:
1. Connect the device via another hub like Amazon Alexa then connect your HomeAssitant to that cloud hub... Ouch.
2. Utilizing TP-Link's cloud to control the device. (Much simipiler).

## Installation with HACS

The recommended way to install this is via HACS:



[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?category=custom_respository&owner=iluvdata&repository=tplink_cloud)

#### Semi-manual install

1. Click on HACS in the Homeassistant side bar
2. Click on the three dots in the upper right-hand corner and select "Custom repositories."
3. In the form enter:

    1. Respository: `iluvdata/tplink_cloud`
    2. Select "Integration" as "Type"

## Manual Installation

Copy the `tplink_cloud` directory to the `custom_components` directory of your Homeassistant Instance.

## Configuration


Add the intergration to Home Assistant:

[![Open your Home Assistant instance and start setting up a new integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=tplink_cloud)

Enter you username and password you used to setup your device and connect to the TP-Link Cloud.  Unlike most intergrations- this integration will not store your password as the TP-Link Cloud uses access tokens.

Once connected the intergration will add ALL active cloud devices to your home assistance instance.  You should disable any device you don't want to use.  NOTE:  In the future, I may implement the ability to select which devices to add to HomeAssistant.

### Options

There are two options to configure.  The defaults should be sufficient for most use cases.
1. Device List Poll Interval.  The frequency at which the integration looks for new devices.  Default is 30 mins.  Setting this too low will get you temporarily blocked on the api.
2. Device Poll Interval.  The frequency at which device states are refreshed.  1 min is the default.  30 seconds has worked as well.  It's not clear if more frequent will result in a temporary block.

## Compatible Devices

I don't have a ton of the devices but it would seem that any device that utilizes the IoT Protocol will work as the cloud just passes through requests to and from the device.  Tested with:
* Plugs
  * HS100 hw ver 1 and 2
* Switches
  * HS200
* Bulbs
  * KS125
  * KS135

If you're interested in testing other devices I suggest using the underlying library [pykasacloud](https://github.com/iluvdata/PyKasaCloud) to first connect to the device and enabling debug logging.  If you need assistance submit an Issue on github.

## Future Directions

If there is enough interest I will approach the contributors of the python-kasa library and the core HomeAssistant integration about add cloud functionality to these integrations.

