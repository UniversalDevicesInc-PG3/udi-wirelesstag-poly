
"""
Tag Names are not included because the spaces or other characters are
not properly transalted. Also, same for last which contains a space :(

Load all with http://wirelesstag.net/ethClient.asmx?op=LoadEventURLConfig

"""
wt_params = {

    # When tag sends a temperature/humidity/brightness update -
    # {0}: Tag name, {1}: Tag ID, {2}: temperature in °C, {3}: humidity/moisture (%), {4}: brightness (lux), {5}: timestamp
    # {7}: signal strength (dBm), {8}: transmit power (1~255)"
    'update': 'name={0}&tagid={1}&temp={2}&hum={3}&lux={4}&ts={5}&batv={6}&signaldBm={7}&txpwr={8}',

    # When lost link to a tag -
    # {0}: Tag name, {1}: Time since last update, {2}: Tag ID, {3}: timestamp
    # Can't include last, it has a space :(
    #wtHandler:log_messagecode 400, message Bad request syntax ('GET /oor?tmgr_mac=0E994A04A300&tagid=3&last=23 minutes&ts=2018-03-04T20:46:18+00:00 HTTP/1.1')
    'oor':    'name={0}&tagid={2}&ts={3}',

    # When re-established link to a tag
    # {0}: Tag name, {1}: Time since last update (lost link duration), {2}: Tag ID, {3}: timestamp
    'back_in_range': 'name={0}&tagid={2}&ts={3}',

    # When motion is detected - {0}: Tag name,
    # (For motion tag {1}: Orientation change, {2}: x axis reading, {3}: y axis, {4}; z axis, {5}: tag ID, {6}: timestamp)
    # (for PIR {1}: timestamp, {2}: tag ID)
    'motion_detected': 'name={0}&tagid={5}&orien={1}&xaxis={2}&yaxis={3}&zaxis={4}&ts={6}',

    # When motion detector times out
    # {0}: Tag name, {1}: timestamp, {2}: tag ID
    'motion_timedout': 'name={0}&tagid={2}&ts={1}',

    # When door is opened
    # {0}: Tag name, {1}: Orientation change since armed, {2}: x axis reading, {3}: y axis, {4}; z axis, {5}: Tag ID, {6}: timestamp
    'door_opened': 'name={0}&tagid={5}&orien={1}&xaxis={2}&yaxis={3}&zaxis={4}&ts={6}',

    # When door is closed
    # {0}: Tag name, {1}: Orientation change since armed, {2}: x axis reading, {3}: y axis, {4}; z axis, {5}: Tag ID, {6}: timestamp
    'door_closed': 'name={0}&tagid={5}&orien={1}&xaxis={2}&yaxis={3}&zaxis={4}&ts={6}',

    # When door is open for too long
    # {0}: Tag name, {1}: Orientation change since armed, {2}: How long, {3}: Tag ID
    'door_open_toolong': 'name={0}&tagid={3}&ochg={1}&hlong={2}',

    # When temperature is too high - {0}: Tag name, {1}: Temperature in °F, {2}: Temperature in °C, {3}: Tag ID, {4}: timestamp
    'temp_toohigh': 'name={0}&tagid={3}&tempf={1}&tempc={2}&ts={4}',

    # When temperature is too low
    # {0}: Tag name, {1}: Temperature in °F, {2}: Temperature in °C, {3}: Tag ID, {4}: timestamp
    'temp_toolow': 'name={0}&tagid={3}&tempf={1}&tempc={2}&ts={4}',

    # When temperature returned to normal
    # {0}: Tag name, {1}: Temperature in °F, {2}: Temperature in °C, {3}: Tag ID, {4}: timestamp
    'temp_normal': 'name={0}&tagid={3}&tempf={1}&tempc={2}&ts={4}',

    #
    # NOTE: Below 3 are not as documented, if APi is fixed then swap back 1 & 2
    #
    # When it's too bright
    # {0}: Tag name, {1}: Tag ID, {2}: Brightness in lux, {3}: timestamp
    'too_bright': 'name={0}&tagid={2}&lux={1}&ts={3}',

    # When it's too dark
    # {0}: Tag name, {1}: Tag ID, {2}: Brightness in lux, {3}: timestamp
    'too_dark': 'name={0}&tagid={2}&lux={1}&ts={3}',

    # When brightness returned to normal
    # {0}: Tag name, {1}: Tag ID, {2}: Brightness in lux, {3}: timestamp
    'light_normal': 'name={0}&tagid={2}&lux={1}&ts={3}',

    # When tag battery is low
    # {0}: Tag name, {1}: latest battery voltage, {2}: configured low battery warning threshold, {3}: Tag ID,{4}: timestamp
    'low_battery': 'name={0}&volt={1}&thrs={2}&tagid={3}&ts={4}',

    # When moisture level is too high
    # {0}: Tag name, {1}: moisture level in %, {2}: Tag ID, {3}: timestamp
    'too_humid': 'name={0}&hum={1}&tagid={2}&ts={3}',

    # When moisture level is too low
    # {0}: Tag name, {1}: moisture level in %, {2}: Tag ID, {3}: timestamp
    'too_dry': 'name={0}&hum={1}&tagid={2}&ts={3}',

    # When moisture level returned to normal
    # {0}: Tag name, {1}: moisture level in %, {2}: Tag ID, {3}: timestamp
    'cap_normal': 'name={0}&hum={1}&tagid={2}&ts={3}',

    # When detected water - {0}: Tag name, {1}: Tag ID, {2}: timestamp
    'water_detected': 'name={0}&tagid={1}&ts={2}',

    # When no longer detected water
    # {0}: Tag name, {1}: Tag ID, {2}: timestamp
    'water_dried': 'name={0}&tagid={1}&ts={2}',

    # Carried away
    # No docs? Not in WebUI Assuming {0}: Tag name, {1}: Tag ID, {2}: timestamp
    'carried_away': 'name={0}&tagid={1}&ts={2}',

    # In Free Fall
    # No doc?  Not in WebUI? {0}: Tag name, {1}: Tag ID, {2}: timestamp
    'in_free_fall': 'name={0}&tagid={1}&ts={2}',

    # VOC No docs for these either
    'voc_normal': 'name={0}&tagid={1}&2={2}&3={3}&4={4}&5={5}&6={6}',
    'too_smelly': 'name={0}&tagid={1}&2={2}&3={3}&4={4}&5={5}&6={6}',
    'too_fresh':  'name={0}&tagid={1}&2={2}&3={3}&4={4}&5={5}&6={6}'

 }
