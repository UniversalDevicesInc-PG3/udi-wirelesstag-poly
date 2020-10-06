[![Build Status](https://travis-ci.org/jimboca/udi-camera-poly.svg?branch=master)](https://travis-ci.org/jimboca/udi-camera-poly)

# udi-WirelessTags-polyglot

This is the Wireless Tags Poly for the [Universal Devices ISY994i](https://www.universal-devices.com/residential/ISY) [Polyglot interface](http://www.universal-devices.com/developers/polyglot/docs/) with  [Polyglot V2](https://github.com/Einstein42/udi-polyglotv2)
to support [CAO Gadgets Wireless Sensor Tags](http://wirelesstag.net/)

(c) JimBoCA aka Jim Searle
MIT license.

## Support

This is discussed on the forum post [Polglot V2 CAO Wireless Tags Nodeserver](https://forum.universal-devices.com/topic/23724-polglot-v2-cao-wireless-tags-nodeserver/)  You can ask questions on that post, or file an issue here on github if you like https://github.com/jimboca/udi-wirelesstag-poly/issues

If you are going to purchase a Tag Manager or Tags, please use [My Referral Link](https://goo.gl/rXAGk9)

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
| Outdoor Probe/Thermocouple                       | 42   | 3       |
| Door/window (reed) KumoSensor                    | 52   | 2       |
| Kumostat/Nest Thremostat                         | 62   | 4       |
| Infra-Red (PIR) KumoSensor                       | 72   | 2       |
| WeMo Switches/Maker/LED                          | 82   | 4       |
| Webcams (Dropcam)                                | 92   | 4       |
| External Power Sensor (USB) Basic                | 102  | 1       |
| External Power Sensor (USB) Precision            | 107  | 1       |

#### Supported Drivers

The supported drivers that are used from the [GetTagList](http://wirelesstag.net/ethClient.asmx?op=GetTagList)
data is shown in the following table along with information passed back from the [LoadEventURLConfig](http://wirelesstag.net/ethClient.asmx?op=LoadEventURLConfig)
Tag 102 is the new external batter tag, which is currently not in their documentation

| Driver   | NLS   | Name                 | 12 | 13 | 21 | 42 | 26 | 32 | 52 | 62 | 72 | 82 | 92 | 102 | 107 | Notes |
| -------- | ----- | -------------------- | -- | -- | -- | -- | -- | -- | -- | -- | -- | -- | -- | --- | --- | ----- |
| UOM      | CORF  | degree               | X  | X  | X  | X  | X  | X  | X  | X  | X  | X  | X  |  X  |  X  |       |
| GPV      | INT   | tagType              | X  | X  | X  | X  | X  | X  | X  | X  | X  | X  | X  |  X  |  X  |       |
| GV1      | INT   | TagId (slaveId)      | X  | X  | X  | X  | X  | X  | X  | X  | X  | X  | X  |  X  |  X  |       |
| ST       | BOOL  | alive                | X  | X  | X  | X  | X  | X  | X  | X  | X  | X  | X  |  X  |  X  |       |
| CV       | FLOAT | batteryVolt          | X  | X  | X  | X  | X  | X  | X  | X  | X  | X  | X  |  X  |  X  |       |
| GV7      | BONOFF| lit                  | X  | X  | X  | X  | X  | X  | X  | X  | X  | X  | X  |  X  |  X  |       |
| ALARM    | EVST  | eventState           | X  | X  | X  | X  | X  |    | X  |    | X  |    |    |  X  |  X  |       |
| GV9      | TMST  | tempEventState       | X  | X  | X  | X  | X  | X  | X  | X  | X  | X  | X  |  X  |  X  |       |
| GV8      | BOOL  | oor                  | X  | X  | X  |    | X  | X  | X  |    | X  |    |    |  X  |  X  | Out Of Range |
| LUMIN    | FLOAT | lux                  |    |    |    |    | X  |    |    |    |    |    |    |     |  X  |       |
| CLITEMP  | FLOAT | temperature          | X  | X  | X  | X  | X  | X  | X  | X  | X  | X  | X  |  X  |  X  |       |
| CLIHUM   | FLOAT | cap                  |    | X  | X  |    | X  | X  | X  | X  | X  |    |    |  X  |  X  |       |
| GV10     | CPST  | CapEventState        |    | X  | X  |    | X  | X  | X  |    | X  |    |    |  X  |  X  |       |
| GV11     | LIST  | lightEventState      |    |    |    |    | X  |    |    |    |    |    |    |     |  X  |       |
| GV12     | WTST  | water detected/dried |    |    |     |   |    |  X |    |    |    |    |    |     |     |   N1  |
| BATLVL   | FLOAT | batteryRemaining     | X  | X  | X  | X  | X  | X  | X  | X  | X  | X  | X  |     |     |       |
| GV2      | BOOL  | motion               | X  | X  | X  |    |    |    |    |    |    |    |    |     |  X  |   N1  |
| GV3      | FLOAT | orien                | X  | X  | X  |    |    |    |    |    |    |    |    |     |     |   N1  |
| GV4      | FLOAT | xaxis                | X  | X  | X  |    |    |    |    |    |    |    |    |     |     |   N1  |
| GV5      | FLOAT | yaxis                | X  | X  | X  |    |    |    |    |    |    |    |    |     |     |   N1  |
| GV6      | FLOAT | zaxis                | X  | X  | X  |    |    |    |    |    |    |    |    |     |     |   N1  |
| NS1      | FLOAT | lowTH                | X  | X  | X  |    | X  | X  | X  | X  | X  | X  | X  |  X  |  X  |       |
| NS1      | FLOAT | highTH               | X  | X  | X  |    | X  | X  | X  | X  | X  | X  | X  |  X  |  X  |       |
| NS1      | FLOAT | rssi                 | X  | X  | X  |    | X  | X  | X  | X  | X  | X  | X  |  X  |  X  |       |
| NS1      | FLOAT | txpwr                | X  | X  | X  |    | X  | X  | X  | X  | X  | X  | X  |  X  |  X  |       |
| GV13     | INT   | time                 | X  | X  | X  | X  | X  | X  | X  | X  | X  | X  | X  |  X  |  X  |   N2  |
| GV14     | INT   | seconds since update | X  | X  |  X | X  | X  | X  | X  | X  | X  | X  | X  |  X  |  X  |   N2  |
| GV15     | FLOAT | chip temperature     |    |    |    | X  |    |    |    |    |    |    |    |     |     |       |


  - NA1 = Not Applicable, since it's available in eventState?
  - NS1 = Not Supported, likely to be added.
  - NS2 = Not Supported, part of Kumostat, which nobody is using?
  - N1 = Only updated on change, so not populated on restart
  - N2 = Time is UNIX epoch time of last update, seconds since update is the number of seconds since an update was seen from the tag and is updated each shortPoll run. So it won't be updated if the nodeserver dies! (which of course never happens)

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

## Switching C or F Mode

You can reconfigure a Tag to report in C or F mode at https://my.wirelesstag.net by clicking the
temperature on the Tag, then change to C/F and save, which will change all tags on that tag manager.
However this will not change them in the ISY, you need to select the Tag Manager in
the ISY Admin Console and click discover.  This can take a few minutes, but eventually you should
see the node identifier change from (F) or (C) at the end, and the Temperature display will show
C or F appropriately.

Due to node types changing, you may have to go to each program referencing a node, select the
tag reference in the program, click update, and save.

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
3. ```./install.sh```
4. Open the polyglot web page, and restart the node server
5. If you had the Admin Console open, then close and re-open.


## Release Notes

If you are going to purchase a Tag Manager or Tags, please use [My Referral Link](https://goo.gl/XVcSKZ)

If you have issues, please create an issue https://github.com/jimboca/udi-wirelesstag-poly/issues  If you have questions please use the forum.
  - 2.0.24 10/06/2020
    - Fix Battery Voltage editor to show volts, and now it can be set to a variable. After updating nodeserver, restart then close admin console if you have it open first.  The variable should be set to Precision=3 and if you have any programs currently referencing Battery Voltage in the if/then/else you will need to Update that line and save it.  
  - 2.0.23 09/30/2020
    - Increase allowable lux to 100000
  - 2.0.22 09/30/2020
    - [Fix setting Battery Voltage from Tag Manager update command](https://github.com/jimboca/udi-wirelesstag-poly/issues/37)
  - 2.0.21 08/10/2020
    - Fix for not setting Out Of Range on startup.
  - 2.0.20 08/09/2020
    - Fixed crashed caused by "Set Light" command.
  - 2.0.17: 06/11/2020
    - Use hum from updates for [Add probe (tagType=42) chip temperature](https://github.com/jimboca/udi-wirelesstag-poly/issues/35)
  - 2.0.16: 06/09/2020
    - Blindly trying to get this working [Add probe (tagType=42) chip temperature](https://github.com/jimboca/udi-wirelesstag-poly/issues/35)
  - 2.0.15: 06/08/2020
    - [Add probe (tagType=42) chip temperature](https://github.com/jimboca/udi-wirelesstag-poly/issues/35)
  - 2.0.14: 03/05/2020
    - Fixed motion detection for tag type 26 ALS, which looks like a PIR
\   - Motion timeout still not working
  - 2.0.13: 12/23/2019
    - Removed eventState from tags 102 and 107 since they don't support motion events
    - Fixed moisture state to report for tags 107
    - Added lightstate to 26 and 107
  - 2.0.12: 12/21/2019
    - Add new tag 107, untested since I don't have one yet
  - 2.0.11: 10/28/2019
    - Skip unknown params for now
  - 2.0.10: 10/18/2019
    - Fixed BATLVL not reporting
  - 2.0.9: 09/14/2019
    - Adding missing name for External Power Sensor
  - 2.0.8: 09/12/2019
    - First attempt at adding new External Battery Tag which I can't test.
  - 2.0.7: 03/03/2019
    - Fixed Tag 26 C nodedef
  - 2.0.6  03/02/2019
    - [Tags in Celcius still show temp in Fahrenheit](https://github.com/jimboca/udi-wirelesstag-poly/issues/32)
    - [See Switching C or F Mode](#switching-c-or-f-mode)
  - 2.0.5 07/22/2018
    - Fix crash bug in shortPoll that only happens if tag manager is not properly selected the first try.
  - 2.0.4  07/11/2018
    - Add better icons from @xKing. Profile should automatically reload, but if you don't see the new icons then select the WirelessTagsConroller and "Install Profile" then restart admin console.
  - 2.0.3  07/10/2018
    - Changed from http to https, thanks @xKing for the change
    - Increased post timeout from 15 to 60 for when the tag server is slow
  - 2.0.2  05/03/2018
    - Fix when query is run to report all nodes
    - New version of polyinterface will fix issue with Notice's not going away
    - Added Heartbeat https://github.com/jimboca/udi-wirelesstag-poly/issues/6
  - 2.0.1  04/17/2018
    - Fix initialization of Short Poll, Long Poll, Debug Mode, on controller, and Monitor Tags of TagManager nodes.
  - 2.0.0  03/22/2018
    - Why jump to 2.0.0?  Because it's Polyglot V2, should have started with that :)
    - And the big addition of what should now be proper support for multiple Tag Managers https://github.com/jimboca/udi-wirelesstag-poly/issues/26
    - Profile updates for Honeywell thermostats https://github.com/jimboca/udi-wirelesstag-poly/issues/14
    - Add Set URL Config buttons https://github.com/jimboca/udi-wirelesstag-poly/issues/25
    - Program Tag URL individually https://github.com/jimboca/udi-wirelesstag-poly/issues/23 and fix for PIR sensor type 72
    - Typo in Wireless Tag type 62 in Wireless Tag node server https://github.com/jimboca/udi-wirelesstag-poly/issues/21
    - Add carried_away and in_free_fall params https://github.com/jimboca/udi-wirelesstag-poly/issues/19
    - Properly initialize params https://github.com/jimboca/udi-wirelesstag-poly/issues/22
    - All driver values now persist https://github.com/jimboca/udi-wirelesstag-poly/issues/13
  - 0.0.25 03/15/2018
    - Add lock sending Tag Manager specific commands.  Seems to resolve all issues with multiple tag managers.
    - Fix typo https://github.com/jimboca/udi-wirelesstag-poly/issues/21
    - Add carried_away and in_free_fall https://github.com/jimboca/udi-wirelesstag-poly/issues/19
  - 0.0.24 03/14/2018
    - Tag 42 - Outdoor Probe/Thermocouple added.  Thanks to https://github.com/mayermd
  - 0.0.23 03/12/2018
    - Remove moisture from 26 and 52
    - Fix lux for all
    - Add tag id to device display for debugging
  - 0.0.22 03/08/2018
    - Bad bug in 0.0.21 causing infinite loop
  - 0.0.21 03/08/2018
    - Change eventState along with Motion, may get rid of Motion driver if this works properly.
  - 0.0.20 03/08/2018
    - Fix setting for Humidity, Out Of Range and Light for all Tags
    - Change temperature to precision=2
  - 0.0.19 03/07/2018
    - Last Update Time and Seconds since update are properly tracked across nodeserver restarts using info from Tag Manager
    - Tag Status is properly set based on 'alive' property from Tag Manager
    - Aded signaldBm to all tags https://github.com/jimboca/udi-wirelesstag-poly/issues/16
    - Simplified all get/set methods so changes can be tracked better in logs for debugging.
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
