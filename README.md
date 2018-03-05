[![Build Status](https://travis-ci.org/jimboca/udi-camera-poly.svg?branch=master)](https://travis-ci.org/jimboca/udi-camera-poly)

# udi-WirelessTags-polyglot

This is the Wireless Tags Poly for the [Universal Devices ISY994i](https://www.universal-devices.com/residential/ISY) [Polyglot interface](http://www.universal-devices.com/developers/polyglot/docs/) with  [Polyglot V2](https://github.com/Einstein42/udi-polyglotv2)
to support [CAO Gadgets Wireless Sensor Tags](http://wirelesstag.net/)

(c) JimBoCA aka Jim Searle
MIT license.

## Support

This is discussed on the forum post [Polglot V2 CAO Wireless Tags Nodeserver](https://forum.universal-devices.com/topic/23724-polglot-v2-cao-wireless-tags-nodeserver/)  You can ask questions on that post, or file an issue here on github if you like https://github.com/jimboca/udi-wirelesstag-poly/issues

## How it works

This nodeserver starts a background process which implements a minimal REST
server to handle data coming from the tag manager.  All communication from
the tag manager to the REST server is on the local network, so no port
forwarding is necessary.

The Tag Manager node created in the ISY has a "Monitor Tags" option, which by default
is disabled in case you have multiple ISY's.  It should only be enabled on the ISY
that is on the same LAN as the Tag Manger.  When this option is enabled, the nodeserver
updates all the Tag URL's so any updates are pushed to the REST server.

The authorization for communicating with your tag manager account handled
by OAuth2 so no passwords are necessary. When the nodeserver is started up for
the first time you will be asked to give permission.

If the Tag Manager is configured for Fahrenheit then all temperatures should be
shown in Fahrenheit, same with Celsius, although that has not been tested yet.

## IP Address

The code tries to figure out the machines IP address for starting the local REST server.
This should always work, unless you have multiple network interfaces.  We will need to
allow users to set the IP Address manually if this happens.

# Node Types

## WirelessTagsController

The is the main controller node for Polyglot.

### Drivers

* Node Server Online
  * Indicates that the nodeserver is running.
* Version Major
  * The first two digits of version of this node server
* Version Minor
  * The last digit of the version of this node server
* Communicating
  * Node server communicating with WirelessTags server
* OAUTH2
  * Status of OAuth2 authoization to access the tag managers
* Debug Mode
  * The Logger debug level
* Short Poll
  * The seconds between each short poll.  This updates the "Seconds since update" value of each Tag
* Long Poll
  * What is run in long poll?
* Listen Port
  * The port the REST server is running on, this should match the URL's in the tag manager

## Tag Manager

There is one node create for each of your Tag Managers

### Drivers

* Status
  * Indicates if the tag manager is online.
* Monitor Tags
  * Enable if the Tag Manager's tags should be added to the current ISY.  This is False by default in case you have multiple ISY's and Tag Managers

### Commands

* Query
  * Queries all Tags, but only requests the data Cached in the Tag Manager so it may not be the latest.
* Ping All Tags
  * Request all Tags to report back their latest data, so only run when necessary since it will use Tag battery power.
* Reboot Tag Manager
  * Only works with newer Tag Managers which are greater than version 6.
* Discover
  * Look for all Tags registered in the Tag Manager, this is run by default when "Monitor Tags" is changed from False to True.

## Tags

### Supported Sensors Types

This node server is intended to eventually support all Wireless Tags used by the
ISY Community.

The list of all sensors is at
http://wirelesstag.net/kumoapp/17/tags-kumosensors-kumostats

The list at this time is in the following table, and support level is denoted
with:
  - 1 = I have one, so should be fully working
  - 2 = I don't have one, hopefully it should work
  - 3 = Has been verified by another user to be working
  - 4 = No intention of supporting at this time
  - 5 = New, have not determined if it will be supported

| Name                                             | Type | Support |
| ------------------------------------------------ | ---- | ------- |
| Motion Sensor Tag (8-bit temperature)            | 12   | 1       |
| Motion Sensor Tag (13-bit temperature+humidity)  | 13   | 2       |
| Motion Sensor Tag Pro                            | 21   | 2       |
| Motion Sensor Tag Pro ALS (Ambient Light Sensor) | 26   | 2       |
| Water/Soil moisture sensor                       | 32   | 1       |
| Door/window (reed) KumoSensor                    | 52   | 2       |
| Kumostat/Nest Thremostat                         | 62   | 4       |
| Infra-Red (PIR) KumoSensor                       | 72   | 2       |
| WeMo Switches/Maker/LED                          | 82   | 4       |
| Webcams (Dropcam)                                | 92   | 4       |

#### Supported Drivers

The supported drivers that are used from the [GetTagList](http://wirelesstag.net/ethClient.asmx?op=GetTagList)
data is shown in the following table along with information passed back from the [LoadEventURLConfig](http://wirelesstag.net/ethClient.asmx?op=LoadEventURLConfig)

| Driver   | NLS   | Name             | 12 | 13 | 21 | 26 | 32 | 52 | 62 | 72 | 82 | 92 | Notes |
| -------- | ----- | ---------------- | -- | -- | -- | -- | -- | -- | -- | -- | -- | -- | ----- |
| UOM      | CORF  | degree           | X  | X  | X  | X  | X  | X  | X  | X  | X  | X  |       |
| GPV      | INT   | tagType          | X  | X  | X  | X  | X  | X  | X  | X  | X  | X  |       |
| GV1      | INT   | TagId (slaveId)  | X  | X  | X  | X  | X  | X  | X  | X  | X  | X  |       |
| ST       | BOOL  | alive            | X  | X  | X  | X  | X  | X  | X  | X  | X  | X  |       |
| CV       | FLOAT | batteryVolt      | X  | X  | X  | X  | X  | X  | X  | X  | X  | X  |       |
| GV7      | BONOFF| lit              | X  | X  | X  | X  | X  | X  | X  | X  | X  | X  |       |
| ALARM    | EVST  | eventState       | X  | X  | X  | X  |    | X  |    | X  |    |    |       |
| GV9      | TMST  | tempEventState   | X  | X  | X  | X  | X  | X  | X  | X  | X  | X  |       |
| GV8      | BOOL  | oor              | X  | X  | X  | X  | X  | X  |    | X  |    |    | Out Of Range |
| LUMIN    | FLOAT | lux              |    |    |    | X  |    |    |    |    |    |    |       |
| CLITEMP  | FLOAT | temperature      | X  | X  | X  | X  | X  | X  | X  | X  | X  | X  |       |
| CLIHUM   | FLOAT | cap              |    | X  | X  | X  | X  | X  | X  | X  |    |    |       |
| GV10     | CPST  | CapEventState    |    | X  | X  | X  | X  | X  |    | X  |    |    |       |
| GV11     | LIST  | lightEventState  |    |    |    | X  |    |    |    |    |    |    |       |
| BATLVL   | FLOAT | batteryRemaining | X  | X  | X  | X  | X  | X  | X  | X  | X  | X  |       |
| GV2      | BOOL  | motion           | X  | X  | X  |    |    |    |    |    |    |    |   N1  |
| GV3      | FLOAT | orien            | X  | X  | X  |    |    |    |    |    |    |    |   N1  |
| GV4      | FLOAT | xaxis            | X  | X  | X  |    |    |    |    |    |    |    |   N1  |
| GV5      | FLOAT | yaxis            | X  | X  | X  |    |    |    |    |    |    |    |   N1  |
| GV6      | FLOAT | zaxis            | X  | X  | X  |    |    |    |    |    |    |    |   N1  |
| NS1      | FLOAT | lowTH            | X  | X  | X  | X  | X  | X  | X  | X  | X  | X  |       |
| NS1      | FLOAT | highTH           | X  | X  | X  | X  | X  | X  | X  | X  | X  | X  |       |
| NS1      | FLOAT | rssi             | X  | X  | X  | X  | X  | X  | X  | X  | X  | X  |       |
| NS1      | FLOAT | txpwr            | X  | X  | X  | X  | X  | X  | X  | X  | X  | X  |       |


  - NA1 = Not Applicable, since it's available in eventState?
  - NS1 = Not Supported, likely to be added.
  - NS2 = Not Supported, part of Kumostat, which nobody is using?
  - N1 = Only updated on change, so not intially populated.

#### NLS entries

| Name | # | Text       |
| ---- | - | ---------- |
| CORF | 0 | Celsius    |
|      | 1 | Fahrenheit |
| EVST | 0 | Disarmed   |
|      | 1 | Armed      |
|      | 2 | Moved      |
|      | 3 | Opened     |
|      | 4 | Closed     |
|      | 5 | DetectedMovement  |
|      | 6 | TimedOut          |
|      | 7 | Stabilizing       |
|      | 8 | CarriedAway       |
|      | 9 | InFreeFall        |
| BONOFF | 0 | Off             |
|        | 1 | On              |
| TMST | 0 | Disarmed          |
|      | 1 | Normal            |
|      | 2 | Too High          |
|      | 3 | Too Low           |
|      | 4 | Threshold Pending |
| CPST | 0 | Not Applicable    |
|      | 1 | Disarmed          |
|      | 2 | Normal            |
|      | 3 | Too Dry           |
|      | 4 | Too Humid         |
|      | 5 | Threshold Pending |
|      | 6 | Water Detected    |
| LIST | 0 | Not Applicable    |
|      | 1 | Disarmed          |
|      | 2 | Normal            |
|      | 3 | Too Dark          |
|      | 4 | Too Bright        |
|      | 5 | Threshold Pending |

### Commands

* Query
  * Requests the Tag to post back with it's data.  May take a few seconds to show up

## Installation

1. Backup Your ISY in case of problems!
   * Really, do the backup, please
2. Go to the Polyglot Store in the UI and install WirelessTags.
3. Add WirelessTags NodeServer in Polyglot
4. Once it starts up, you should see a message in Polyglot Web which shows a "Active" link to click.
    * Seems the wirelesstags certificate is not up to date, so in chrome you may have to click continue anyway (unsafe) selection :(
    * The link points to https://www.wirelesstag.net/oauth2/authorize.aspx?... with necessary info
    * Including a redirect back to the nodeserver's REST Server
    * After you 'Grant' access you should see a message saying "SUCCESS, received our token, ..." in your web browser
5. Open Admin Console (if you already had it open, then close and re-open)
6. You should now have a node for each of your tag managers
7. By default the "Monitor Tags" for each tag manager is turned off, if you want the tags to show up in your current ISY/nodeserver, then enable it.
    * The nodeserver and tag manager must be on the same LAN since the tag mangaer sends updates directly to the nodeserver.
    * Only one nodeserver can monitor the tags if you have multiple ISY/nodeserver's.
    * This could be fixed by using Kumoapps, but not sure if it's necessary
8. Once Monitor tags is enabled, you should see the tags be added to the ISY.
    * Review the nodeserver log if they don't all show up, it may take a minute or so.

  ## Requirements
1. [Polyglot V2](https://github.com/UniversalDevicesInc/polyglot-v2) >= 2.1.0
1. When using a RaspberryPi it should be run on Raspian Stretch
  To check your version: ```cat /etc/os-release```
  and the first line should look like ```PRETTY_NAME="Raspbian GNU/Linux 9 (stretch)"```
  It is possible to upgrade from Jessie to Stretch, but I would recommend just
  re-imaging the SD card.  Some helpful links:
    * https://www.raspberrypi.org/blog/raspbian-stretch/
    * https://linuxconfig.org/raspbian-gnu-linux-upgrade-from-jessie-to-raspbian-stretch-9
1. This has only been tested with ISY 5.0.11 so it is not confirmed to work with any prior version.

## TODO

See [Github Issues](https://github.com/jimboca/udi-wirelesstag-poly/issues)

## Upgrading

### From the store

1. Open the Polyglot web page, go to nodeserver store and click "Update" for "WirelessTags".
    * You can always answer "No" when asked to install profile.  The nodeserver will handle this for you.
2. Go to the WirelessTags Control Page, and click restart

### The manual way

1. ```cd ~/.polyglot/nodeservers/WirelessTag```
2. ```git pull```
3. Open the polyglot web page, and restart the node server
4. If you had the Admin Console open, then close and re-open.


## Release Notes

  Please make sure to yes to the Update Profile question when upgrading if the Profile Update version has changed from the current version you are using.

  - 0.0.18 03/04/2018
    - Another fix for get_network_ip that should now work on MacOS
    - https://github.com/jimboca/udi-wirelesstag-poly/issues/14
  - 0.0.17 03/04/2018
    - Fixed bug where tag_id's don't get properly set. ALL USERS: Please select the WirelessTagsController and run a discover after updating and restarting the node server.
    - Added more info to Tag Type 62
    - Changed how to figure out the local IP address, thanks @xKing. See IP Address section above
    - Changed Humidity to prec=1
    - Profile Version: 0.0.17
  - 0.0.16 03/03/2018
    - Attempt to fix issue with restart for multiple Tag Managers
    - https://github.com/jimboca/udi-wirelesstag-poly/issues/12
    - Profile Version: 0.0.16
  - 0.0.15 03/03/2018
    - https://github.com/jimboca/udi-wirelesstag-poly/issues/11
    - https://github.com/jimboca/udi-wirelesstag-poly/issues/12
    - Profile Update: 0.0.15
  - 0.0.14 03/03/2018
    - https://github.com/jimboca/udi-wirelesstag-poly/issues/10
  - 0.0.13 03/03/2018
    - Fix race condition when starting up causing error in set_seconds
    - Change URL's to not pass tag name since they are not properly encoded, adding passing of tag manager mac to identify tags on multiple tag managers.
      - If you previously added tags that had spaces in the names, then delete them from inside the Polyglot -> WirelessTag -> Nodes page and run discover again.
    - It should work much better with multiple tag managers, but there may still be some issues. Will review the code more and test further.
  - 0.0.12 03/02/2018
    - https://github.com/jimboca/udi-wirelesstag-poly/issues/1
    - Added a lot to documentation
    - Profile Update: 0.0.12
  - 0.0.11 03/02/2018
    - Add Seconds Since Update
    - Fixed setting logging/debug moe
    - Profile Update: 0.0.11
  - 0.0.10 03/02/2018
    - Really add "Last Update" to all tags
    - Profile Update: 0.0.10
  - 0.0.9 03/02/2018
      - Add "Last Update" to all tags
      - Profile Update: 0.0.9
  - 0.0.8 03/01/2018
    - Add "Last Update" seconds since epoch time of last update sent from the tag
    - Allow hum to be a float
    - Profile Update: 0.0.8
  - 0.0.7 02/27/2018
    - Catch missing tag id in node_data
  - 0.0.6 02/27/2018
    - Fixed initial Wet State to be Dry on startup if it's NA
    - Added requests to requirements
  - 0.0.5 02/27/2018
    - Fixed BATLVL Editor so tag conditions show up in programs
    - Added 'Set Light', but it doesn't actually work yet
  - 0.0.4 02/27/2018
    - First release
  - 0.0.3 02/22/2018
    - Still not released, see TODO list
