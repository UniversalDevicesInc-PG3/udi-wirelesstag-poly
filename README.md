# MyNodeServer

#### TODO Before release
- Test if slaveId changes when a tag is deleted and undeleted?
   - May need to link the mac & slave id in customData
- Create C versions of all or some tags?
   - See which have temperature
- Query Tag's on startup?
- Short poll query when Motion=True to change motion
- What are the other motion settings door_open...
- Query to reset Motion when it's True?
  - Don't seem to get motion timout in updates?

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

#### Installation

Here is how you install this poly.

- Add it
- Will add message in Polyglot Web which shows a Active link to click.
  - Seems the wirelesstags certificate is not up to date, so in chrome you have to click continue anyway (unsafe) to continue :(
  - To https://www.wirelesstag.net/oauth2/authorize.aspx?...
  - With a redirect back to the nodeserver's REST Server
  - After you 'Grant' access you should see a message saying "SUCCESS, received our token, ..."
- Open Admin Console (if you already had it open, then close and re-open)
- You should now have a node for each of your tag managers
- By default the Monitor Tags for each tag manager is turned off, if you want the tags to show up in your current ISY/nodeserver, then enable it.
   - The nodeserver and tag manager must be on the same LAN since the tag mangaer sends updates directly to the nodeserver.
   - Only one nodeserver can monitor the tags if you have multiple ISY/nodeserver's.

TODO: Need to add param on tag manager to enable/disable?

#### Requirements

Here is what is required to run this poly.



