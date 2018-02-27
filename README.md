[![Build Status](https://travis-ci.org/jimboca/udi-camera-poly.svg?branch=master)](https://travis-ci.org/jimboca/udi-camera-poly)

# udi-WirelessTags-polyglot

This is the Wireless Tags Poly for the [Universal Devices ISY994i](https://www.universal-devices.com/residential/ISY) [Polyglot interface](http://www.universal-devices.com/developers/polyglot/docs/) with  [Polyglot V2](https://github.com/Einstein42/udi-polyglotv2)
to support [CAO Gadgets Wireless Sensor Tags](http://wirelesstag.net/)

(c) JimBoCA aka Jim Searle
MIT license.

## How it works

This nodeserver starts a backgroud process which implements a minimal REST
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

## Supported Sensors

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

### Supported Drivers

The supported drivers that are used from the [GetTagList](http://wirelesstag.net/ethClient.asmx?op=GetTagList)
data is shown in the following table along with information passed back from the [LoadEventURLConfig](http://wirelesstag.net/ethClient.asmx?op=LoadEventURLConfig)

| Driver   | NLS   | Name             | 12 | 13 | 21 | 26 | 32 | 52 | 62 | 72 | 82 | 92 | Notes |
| -------- | ----- | ---------------- | -- | -- | -- | -- | -- | -- | -- | -- | -- | -- | ----- |
| UOM      | CORF  | degree           | X  | X  | X  | X  | X  | X  | X  | X  | X  | X  |       | From Tag Manager
| GPV      | INT   | tagType          | X  | X  | X  | X  | X  | X  | X  | X  | X  | X  |       |
| GV1      | INT   | TagId (slaveId)  | X  | X  | X  | X  | X  | X  | X  | X  | X  | X  |       |
| ST       | BOOL  | alive            | X  | X  | X  | X  | X  | X  | X  | X  | X  | X  |       |
| CV       | FLOAT | batteryVolt      | X  | X  | X  | X  | X  | X  | X  | X  | X  | X  |       |
| GV7      | BONOFF| lit              | X  | X  | X  | X  | X  | X  | X  | X  | X  | X  |       |
| ALARM    | EVST  | eventState       | X  | X  | X  | X  |    | X  |    | X  |    |    |       |
| GV9      | TMST  | tempEventState   | X  | X  | X  | X  | X  | X  | X  | X  | X  | X  |       |
| GV8      | BOOL  | OutOfRange       | X  | X  | X  | X  | X  | X  |    | X  |    |    | Out Of Range |
| LUMIN    | FLOAT | lux              |    |    |    | X  |    |    |    |    |    |    |       |
| CLITEMP  | FLOAT | temperature      | X  | X  | X  | X  | X  | X  | X  | X  | X  | X  |       |
| CLIHUM   | FLOAT | cap              |    | X  | X  | X  | X  | X  | X  | X  |    |    |       |
| GV10     | CPST  | CapEventState    |    | X  | X  | X  | X  | X  | X  | X  |    |    |       |
| GV11     | LIST  | lightEventState  |    |    |    | X  |    |    |    |    |    |    |       |
| BATLVL   | FLOAT | batteryRemaining | X  | X  | X  | X  | X  | X  | X  | X  | X  | X  |       |
| GV2      | BOOL  | motion           | X  | X  | X  |    |    |    |    |    |    |    |       |
| GV3      | FLOAT | orien            | X  | X  | X  |    |    |    |    |    |    |    |       |
| GV4      | FLOAT | xaxis            | X  | X  | X  |    |    |    |    |    |    |    |       |
| GV5      | FLOAT | yaxis            | X  | X  | X  |    |    |    |    |    |    |    |       |
| GV6      | FLOAT | zaxis            | X  | X  | X  |    |    |    |    |    |    |    |       |
| NS1      | FLOAT | lowTH            | X  | X  | X  | X  | X  | X  | X  | X  | X  | X  |       |
| NS1      | FLOAT | highTH           | X  | X  | X  | X  | X  | X  | X  | X  | X  | X  |       |
| NS1      | FLOAT | rssi             | X  | X  | X  | X  | X  | X  | X  | X  | X  | X  |       |
| NS1      | FLOAT | txpwr            | X  | X  | X  | X  | X  | X  | X  | X  | X  | X  |       |


  - NA1 = Not Applicable, since it's available in eventState?
  - NS1 = Not Supported, likely to be added.
  - NS2 = Not Supported, part of Kumostat, which nobody is using?

### NLS entries

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
| LIST | 0 | Not Applicable    |
|      | 1 | Disarmed          |
|      | 2 | Normal            |
|      | 3 | Too Dark          |
|      | 4 | Too Bright        |
|      | 5 | Threshold Pending |



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

## Upgrading

1. Open the Polyglot web page, go to nodeserver store and click "Update" for "WirelessTags".
2. Go to the WirelessTags Control Page, and click restart

## Release Notes

  - 0.0.3 02/22/2018
     - Still not released, see TODO list below.

## TODO Before release
- Update code and documentation from using kumoapp events to http://wirelesstag.net/apidoc.html
- Add last update time from ts? Or do a heartbeat?
- Triple check all F nodedef's have proper Drivers
- Test that C works?  Can I switch mine to C?
- Only add necessary drivers based on tag_type in wTag
- What happens when authorization expires?
- What happens when authorization is removed?
- Really test sensor changes when I am home
  - Humidity & water detected.
  - Out of Range
  - Online
- Test if slaveId changes when a tag is deleted and undeleted?
   - May need to link the mac & slave id in customData
- Query Tag's on startup?  Don't think this is necessary?  Just means some data will not be populated.
- Short poll query when Motion=True to change motion
- What are the other motion settings door_open...
- Query to reset Motion when it's True?
  - Don't seem to get motion timeout in updates?
- Finish handling all GET commands, only update is currently handled?

```
2018-02-16 20:44:03,737 ERROR    wtController:get_handler: Unknown command '/too_humid'
2018-02-16 20:44:03,738 ERROR    get_handler: code=500 message=Command /too_humid failed
2018-02-16 20:44:03,739 INFO     wtHandler:log_message"GET /too_humid?tagname=WaterSensor&mois=38&tagid=1&ts=2018-02-16T20:43:59+00:00 HTTP/1.1" 500 -
2018-02-16 20:44:10,642 DEBUG    get_handler: command=/cap_normal
2018-02-16 20:44:10,643 DEBUG    wtController:get_handler: processing command=/cap_normal params={'tagname': 'WaterSensor', 'mois': '2', 'ts': '2018-02-16T20:44:06 00:00', 'tagid': '1'}
2018-02-16 20:44:10,644 ERROR    wtController:get_handler: Unknown command '/cap_normal'
2018-02-16 20:44:10,645 ERROR    get_handler: code=500 message=Command /cap_normal failed
2018-02-16 20:44:10,646 INFO     wtHandler:log_message"GET /cap_normal?tagname=WaterSensor&mois=2&tagid=1&ts=2018-02-16T20:44:06+00:00 HTTP/1.1" 500 -
2018-02-16 20:44:43,516 DEBUG    get_handler: command=/water_detected
2018-02-16 20:44:43,518 DEBUG    wtController:get_handler: processing command=/water_detected params={'tagname': 'WaterSensor', 'mois': '1', 'ts': '2018-02-16T20:44:38 00:00'}
2018-02-16 20:44:43,519 ERROR    wtController:get_handler: Unknown command '/water_detected'
2018-02-16 20:44:43,520 ERROR    get_handler: code=500 message=Command /water_detected failed
2018-02-16 20:44:43,521 INFO     wtHandler:log_message"GET /water_detected?tagname=WaterSensor&mois=1&ts=2018-02-16T20:44:38+00:00 HTTP/1.1" 500 -
2018-02-16 20:44:56,046 DEBUG    get_handler: command=/water_dried
2018-02-16 20:44:56,047 DEBUG    wtController:get_handler: processing command=/water_dried params={'tagname': 'WaterSensor', 'mois': '1', 'ts': '2018-02-16T20:44:51 00:00'}
2018-02-16 20:44:56,048 ERROR    wtController:get_handler: Unknown command '/water_dried'
2018-02-16 20:44:56,049 ERROR    get_handler: code=500 message=Command /water_dried failed
```
