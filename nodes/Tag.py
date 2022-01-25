"""
This is a NodeServer for CAO Gadgets Wireless Sensor Tags for Polyglot v2 written in Python3
by JimBoCA jimboca3@gmail.com
"""

from udi_interface import Node,LOGGER
import sys
import time
import re
from wt_funcs import id_to_address,myfloat,CtoF
from wt_params import wt_params

DLEV = 0

class Tag(Node):

    def __init__(self, controller, primary, address=None, name=None,
                 tag_type=None, uom=None, tdata=None, is_new=True):
        LOGGER.debug('address={0} name={1} type={2} uom={3}'.format(address,name,tag_type,uom))
        tag_id = None
         # So logger calls won't crash
        self.address = address
        self.id = 'wTag' # Until we figure out the uom
        self.type = 'wTag'
        self.name = name
        self.is_new = is_new
        self.node_set_url = False
        # Have to set this to call getDriver
        self.controller = controller
        self.primary_n = controller.poly.getNode(primary)
        if is_new:
            # It's a new tag.
            self.address = address
            if tdata is None:
                LOGGER.error("New node address ({0}), name ({1}), and type ({2}) must be specified when tdata is None".format(address,name,tag_type))
                return False
            if uom is None:
                LOGGER.error("uom ({0}) must be specified for new tags.".format(uom))
            LOGGER.debug('New node {}'.format(tdata))
            tag_type      = tdata['tagType']
            self.tag_uom  = uom
            tag_id        = tdata['slaveId']
            self.uuid     = tdata['uuid']
            address       = id_to_address(self.uuid)
            name          = tdata['name']
        else:
            #
            # An existing node,
            LOGGER.debug('Existing node...')
            # We need to pull info from existing tags to know what they are.
            node_data = self.controller.poly.db_getNodeDrivers(address)
            LOGGER.debug(f"node_data={node_data}")
            dv = dict()
            for driver in node_data:
                dv[driver['driver']] = driver['value']
            if 'UOM' in dv:
                self.tag_uom = dv['UOM']
            else:
                LOGGER.error('No tag_uom (UOM)')
                self.tag_uom = -1
            # tag_id = GPV
            if 'GPV' in dv:
                tag_id = dv['GPV']
            else:
                LOGGER.error('No tag_id (GPV) in node_data={0}'.format(node_data))
                return False
            # tag_type = GV1
            if 'GV1' in dv:
                tag_type = dv['GV1']
            else:
                LOGGER.error('No tag_type (GV1) in node_data={0}'.format(node_data))
                return False
        tag_id = int(tag_id)
        tag_type = int(tag_type)
        self.name = name
        self.tdata = tdata
        self.tag_id = tag_id
        self.tag_type = tag_type
        LOGGER.info('type={} uom={} id={} address={} name={}'.format(self.tag_type,self.tag_uom,self.tag_id,address,name))
        #
        # C or F?
        # Fix our temp_uom in drivers
        # This won't change an existing tag, only new ones.
        #
        # TODO:  test changing it by forcing update?
        temp_uom = 4 if self.tag_uom == 0 else 17
        dv = [
            {'driver': 'ST',      'value': 0, 'uom': 2},
             # tag_id
            {'driver': 'GPV',     'value': self.tag_id, 'uom': 56},
            # UOM 0=C 1=F
            {'driver': 'UOM',     'value': 0, 'uom': 56},
            # tag_type:
            {'driver': 'GV1',     'value': self.tag_type, 'uom': 56},
            # temp:   Curent temperature (17=F 4=C)
            {'driver': 'CLITEMP', 'value': 0, 'uom': temp_uom},
            # batv:   Battery Voltag 72=Volt
            {'driver': 'CV',      'value': 0, 'uom': 72},
            # lit:    Light
            # fan:    Honeywell Fan State
            {'driver': 'GV7',     'value': 0, 'uom': 25},
            # tempState:
            {'driver': 'GV9',     'value': 0, 'uom': 25},
            # time:
            {'driver': 'GV13',     'value': 0, 'uom': 25},
            # seconds since update
            {'driver': 'GV14',     'value': 0, 'uom': 25},
        ]
        if (not (tag_type == 102 or tag_type == 107)):
            # batp:   Battery percent (51=percent)
            dv.append({'driver': 'BATLVL',  'value': 0, 'uom': 51})
        if (tag_type == 12 or tag_type == 13 or tag_type == 21 or tag_type == 26
            or tag_type == 32 or tag_type == 52 or tag_type == 62 or
            tag_type == 72):
            # evst: Event State
            dv.append({'driver': 'ALARM',   'value': 0, 'uom': 25})
        if (tag_type == 13 or tag_type == 26 or tag_type == 107):
            # lux:    Lux (36=lux)
            dv.append({'driver': 'LUMIN',   'value': 0, 'uom': 36})
        if (tag_type == 13 or tag_type == 21 or tag_type == 26 or tag_type == 32
            or tag_type == 52 or tag_type == 62 or tag_type == 72
            or tag_type == 102 or tag_type == 107):
            # hum:    Humidity (21 = absolute humidity)
            dv.append({'driver': 'CLIHUM',  'value': 0, 'uom': 22})
        if (tag_type == 12 or tag_type == 13 or tag_type == 21 or tag_type == 26):
            # motion:
            dv.append({'driver': 'GV2',     'value': 0, 'uom': 25})
        if (tag_type == 12 or tag_type == 13 or tag_type == 21):
            # orien:  Orientation
            dv.append({'driver': 'GV3',     'value': 0, 'uom': 56})
            # xaxis:  X-Axis
            dv.append({'driver': 'GV4',     'value': 0, 'uom': 56})
            # yasis:  Y-Axis
            dv.append({'driver': 'GV5',     'value': 0, 'uom': 56})
            # zaxis:  Z-Axis
            dv.append({'driver': 'GV6',     'value': 0, 'uom': 56})
        if (tag_type == 12 or tag_type == 13 or tag_type == 21 or tag_type == 26
            or tag_type == 32 or tag_type == 52 or tag_type == 72
            or tag_type == 102 or tag_type == 107):
            # oor:    OutOfRange
            dv.append({'driver': 'GV8',     'value': 0, 'uom':  2})
            # signaldBm:
            dv.append({'driver': 'CC',     'value': 0, 'uom':  56})
        if (tag_type == 13 or tag_type == 21 or tag_type == 26
            or tag_type == 32 or tag_type == 52 or tag_type == 62
            or tag_type == 72 or tag_type == 107):
            # moisture(cap)State:
            dv.append({'driver': 'GV10',    'value': 0, 'uom': 25})
        if (tag_type == 13 or tag_type == 26 or tag_type == 107):
            # lightState:
            dv.append({'driver': 'GV11',    'value': 0, 'uom': 25})
        if (tag_type == 32):
            # TODO: Only 32 has water sensor?
            dv.append({'driver': 'GV12',  'value': 1, 'uom': 25})
        if (tag_type == 42):
            # TODO: Only 42 has chip temperature
            dv.append({'driver': 'GV15',  'value': 0, 'uom': temp_uom})
        self.drivers = dv
        uomS = "C" if self.tag_uom == 0 else "F"
        self.id = 'wTag' + str(self.tag_type) + uomS
        self.address = address
        controller.poly.subscribe(controller.poly.START,             self.handler_start, address) 
        #LOGGER.info('super id={} controller{} primary={} address={} name={} type={} id={} uom={}'.format(Tag,controller,primary,address,name,self.tag_type,self.tag_id,self.tag_uom))
        super(Tag, self).__init__(controller.poly, primary, address, name)
        LOGGER.debug('done')

    def handler_start(self):
        """
        Optional.
        This method is run once the Node is successfully added to the ISY
        and we get a return result from Polyglot. Only happens once.
        """
        # Always set driver from tag type
        self.set_tag_type(self.tag_type)
        self.set_tag_id(self.tag_id)
        self.set_tag_uom(self.tag_uom)
        if self.tdata is not None:
            self.set_from_tag_data(self.tdata)
        self.set_time_now()
        if self.controller.update_profile:
            # Drivers were updated, need to query
            self.query()
        else:
            # Otherwise just report previous values
            self.reportDrivers()

    def shortPoll(self):
        self.set_seconds()

    def query(self):
        """
        Called by ISY to report all drivers for this node. This is done in
        the parent class, so you don't need to override this method unless
        there is a need.
        """
        # This askes for the sensor to report
        mgd = self.primary_n.RequestImmediatePostback({'id':self.tag_id})
        if mgd['st']:
            self.set_from_tag_data(mgd['result'])
            self.reportDrivers()

    def set_url_config(self,force=False):
        if self.controller.wtServer is False:
            LOGGER.error("Unable to set URL Config because main server was not started")
            return False
        # If we haven't tried to set this nodes url's or it failed, the reset it.
        url = self.controller.wtServer.listen_url
        if not self.node_set_url or force:
            mgd = self.primary_n.LoadEventURLConfig({'id':self.tag_id})
            LOGGER.debug('{0}'.format(mgd))
            if mgd['st'] is False:
                self.node_set_url = False
            else:
                #{'in_free_fall': {'disabled': True, 'nat': False, 'verb': None, 'url': 'http://', 'content': None}
                newconfig = dict()
                for key, value in mgd['result'].items():
                    if key != '__type':
                        if key in wt_params:
                            param = wt_params[key]
                        else:
                            LOGGER.error("Unknown tag param '{0}' it will be ignored".format(key))
                            param = False
                        # Just skip for now
                        if param is not False:
                            # for PIR and ALS {1}: timestamp, {2}: tag ID)
                            if key == 'motion_detected' and (self.tag_type == 72 or self.tag_type == 26):
                                param = 'name={0}&tagid={2}&ts={1}'
                            LOGGER.debug("key={0} value={1}".format(key,value))
                            value['disabled'] = False
                            value['url'] = '{0}/{1}?tmgr_mac={2}&{3}'.format(url,key,self.primary_n.mac,param)
                            value['nat'] = True
                            newconfig[key] = value
                res = self.primary_n.SaveEventURLConfig({'id':self.tag_id, 'config': newconfig, 'applyAll': False})
                self.node_set_url = res['st']

    def get_handler(self,command,params):
        """
        This is called by the controller get_handler after parsing the node_data
        """
        LOGGER.debug('command={} params={}'.format(command,params))
        if command == '/update':
            #tagname=Garage Freezer&tagid=0&temp=-21.4213935329179&hum=0&lux=0&ts=2018-02-15T11:18:02+00:00 HTTP/1.1" 400 -
            pass
        elif command == '/motion_detected':
            self.set_motion(1)
        elif command == '/motion_timedout':
            self.set_motion(0)
        elif command == '/door_opened':
            self.set_motion(2)
        elif command == '/door_closed':
            self.set_motion(4)
        elif command == '/door_open_toolong':
            self.set_motion(2)
        elif command == '/oor':
            self.set_oor(1)
        elif command == '/back_in_range':
            self.set_oor(0)
        elif command == '/temp_normal':
            self.set_tmst(1)
        elif command == '/temp_toohigh':
            self.set_tmst(2)
        elif command == '/temp_toolow':
            self.set_tmst(3)
        elif command == '/too_humid':
            self.set_cpst(4)
        elif command == '/too_dry':
            self.set_cpst(3)
        elif command == '/cap_normal':
            self.set_cpst(2)
        elif command == '/water_detected':
            self.set_wtst(2)
        elif command == '/water_dried':
            self.set_wtst(1)
        elif command == '/low_battery':
            self.set_batl(1)
        elif command == '/too_bright':
            self.set_list(4)
        elif command == '/too_dark':
            self.set_list(3)
        elif command == '/light_normal':
            self.set_list(2)
        else:
            LOGGER.error("Unknown command '{0}'".format(command))
        if 'temp' in params:
            # This is always C ?
            if self.tag_uom == 0:
                self.set_temp(params['temp'])
            else:
                self.set_temp(CtoF(params['temp']))
        elif self.tag_uom == 0:
            if 'tempc' in params:
                self.set_temp(params['tempc'])
        elif self.tag_uom == 1:
            if 'tempf' in params:
                self.set_temp(params['tempf'])
        if 'hum' in params:
            # hum is used for chip_temp on tag type 42, all others is humidity
            if self.tag_type == 42:
                # This is always C
                if self.tag_uom == 0:
                    self.set_chip_temp(params['hum'])
                else:
                    self.set_chip_temp(CtoF(params['hum']))
            else:
                self.set_hum(params['hum'])
        if 'lux' in params:
            self.set_lux(params['lux'])
        if 'orien' in params:
            self.set_orien(params['orien'])
        if 'xaxis' in params:
            self.set_xaxis(params['xaxis'])
        if 'yaxis' in params:
            self.set_yaxis(params['yaxis'])
        if 'zaxis' in params:
            self.set_zaxis(params['zaxis'])
        if 'batv' in params:
            self.set_batv(params['batv'])
        self.set_time_now()
        return True

    """
    Set Functions
    """
    def set_from_tag_data(self,tdata):
        LOGGER.debug('{}'.format(tdata))
        if 'alive' in tdata:
            self.set_alive(tdata['alive'])
        if 'temperature' in tdata:
            # This is always C ?
            if self.tag_uom == 0:
                self.set_temp(tdata['temperature'])
            else:
                self.set_temp(CtoF(tdata['temperature']))
        if 'batteryVolt' in tdata:
            self.set_batv(tdata['batteryVolt'])
        if 'batteryRemaining' in tdata:
            self.set_batp(float(tdata['batteryRemaining']) * 100)
        if 'lux' in tdata:
            self.set_lux(tdata['lux'])
        if 'cap' in tdata:
            # cap is used for chip_temp on tag type 42, all others is humidity
            if self.tag_type == 42:
                # This is always C
                if self.tag_uom == 0:
                    self.set_chip_temp(tdata['cap'])
                else:
                    self.set_chip_temp(CtoF(tdata['cap']))
            else:
                self.set_hum(tdata['cap'])
        if self.tag_type == 62:
            if 'thermostat' in tdata and tdata['thermostat'] is not None and 'fanOn' in tdata['thermostat']:
                self.set_fan(tdata['thermostat']['fanOn'])
        else:
            if 'lit' in tdata:
                self.set_lit(tdata['lit'])
        if 'eventState' in tdata:
            self.set_evst(tdata['eventState'])
        # Used to be oor, not it's OutOfRange ?
        if 'OutOfRange' in tdata:
            self.set_oor(tdata['OutOfRange'])
        if 'oor' in tdata:
            self.set_oor(tdata['oor'])
        if 'signaldBm' in tdata:
            self.set_signaldbm(tdata['signaldBm'])
        if 'tempEventState' in tdata:
            self.set_tmst(tdata['tempEventState'])
        if 'capEventState' in tdata:
            self.set_cpst(tdata['capEventState'])
        if 'lightEventState' in tdata:
            self.set_list(tdata['lightEventState'])
        # This is the last time the tag manager has heard from the tag?
        if 'lastComm' in tdata:
            self.set_time(tdata['lastComm'],wincrap=True)
            self.set_seconds()

    # This is the tag_type number, we don't really need to show it, but
    # we need the info when recreating the tags from the config.
    def set_tag_type(self,value):
        LOGGER.debug('GV1 to {0}'.format(value))
        self.tag_type = value
        self.setDriver('GV1', value)

    def set_tag_id(self,value):
        LOGGER.debug('GPV to {0}'.format(value))
        self.tag_id = value
        self.setDriver('GPV', value)

    def set_tag_uom(self,value):
        LOGGER.debug('UOM to {0}'.format(value))
        self.tag_uom = value
        self.setDriver('UOM', value)

    def set_alive(self,value):
        LOGGER.debug('{0}'.format(value))
        self.setDriver('ST', int(value))

    def set_temp(self,value):
        LOGGER.debug('{0}'.format(value))
        self.setDriver('CLITEMP', myfloat(value,1))

    def set_chip_temp(self,value):
        LOGGER.debug('{0}'.format(value))
        self.setDriver('GV15', myfloat(value,1))

    def set_hum(self,value):
        LOGGER.debug('{0}'.format(value))
        self.setDriver('CLIHUM', myfloat(value,1))

    def set_lit(self,value):
        LOGGER.debug('{0}'.format(value))
        self.setDriver('GV7', int(value))

    def get_lit(self):
        LOGGER.debug('')
        return self.getDriver('GV7')

    def set_fan(self,value):
        LOGGER.debug('{0}'.format(value))
        self.setDriver('GV7', int(value))

    def set_lux(self,value):
        LOGGER.debug('{0}'.format(value))
        self.setDriver('LUMIN', myfloat(value,2))

    def set_batp(self,value,force=False):
        LOGGER.debug('{0}'.format(value))
        self.setDriver('BATLVL', myfloat(value,2))

    def set_batv(self,value):
        LOGGER.debug('{0}'.format(myfloat(value,3)))
        self.setDriver('CV', myfloat(value,3))

    def set_batl(self,value,force=False):
        # TODO: Implement battery low!
        return
        self.setDriver('CV', value)

    def set_motion(self,value=None):
        LOGGER.debug('{0}'.format(value))
        value = int(value)
        # Not all have motion, but that's ok, just sent it.
        self.setDriver('GV2', value)
        if value == 0: # False
            self.set_evst(1,andMotion=False) # Armed
        elif value == 1: # True
            self.set_evst(5,andMotion=False) # Detected Movement
        if value == 2: # Door Open
            self.set_evst(3,andMotion=False) # Opened
        elif value == 3: # Open too long
            self.set_evst(3,andMotion=False) # Opened
        elif value == 4: # Closed
            self.set_evst(4,andMotion=False) # Closed

    def set_orien(self,value):
        LOGGER.debug('{0}'.format(value))
        self.setDriver('GV3', myfloat(value,1))

    def set_xaxis(self,value):
        LOGGER.debug('{0}'.format(value))
        self.setDriver('GV4', int(value))

    def set_yaxis(self,value):
        LOGGER.debug('{0}'.format(value))
        self.setDriver('GV5', int(value))

    def set_zaxis(self,value):
        LOGGER.debug('{0}'.format(value))
        self.setDriver('GV6', int(value))

    def set_evst(self,value,andMotion=True):
        LOGGER.debug('{0}'.format(value))
        self.setDriver('ALARM', int(value))
        # eventState 1=Armed, so no more motion
        if andMotion and int(value) == 1:
            self.set_motion(0)

    def set_oor(self,value):
        LOGGER.debug('{0}'.format(value))
        self.setDriver('GV8', int(value))

    def set_signaldbm(self,value):
        LOGGER.debug('{0}'.format(value))
        self.setDriver('CC', int(value))

    def set_tmst(self,value):
        LOGGER.debug('{0}'.format(value))
        self.setDriver('GV9', int(value))

    def set_cpst(self,value):
        LOGGER.debug('{0}'.format(value))
        self.setDriver('GV10', int(value))

    def set_list(self,value):
        LOGGER.debug('{0}'.format(value))
        self.setDriver('GV11', int(value))

    def set_wtst(self,value):
        LOGGER.debug('{0}'.format(value))
        # Force to 1, Dry state on initialization since polyglot ignores the init value
        value = int(value)
        if value == 0: value = 1
        self.setDriver('GV12', int(value))

    def set_time_now(self):
        self.set_time(int(time.time()))
        self.set_seconds()

    def set_time(self,value,wincrap=False):
        LOGGER.debug('{0},{1}'.format(value,wincrap))
        value = int(value)
        if wincrap:
            # Convert windows timestamp to unix :(
            # https://stackoverflow.com/questions/10411954/convert-windows-timestamp-to-date-using-php-on-a-linux-box
            value = int(value / 10000000 - 11644477200)
            LOGGER.debug('{0}'.format(value))
        self.time = value
        self.setDriver('GV13', self.time)

    def set_seconds(self,force=True):
        if not hasattr(self,"time"): return False
        time_now = int(time.time())
        if DLEV > 0: LOGGER.debug('time_now    {}'.format(time_now))
        if DLEV > 0: LOGGER.debug('last_time - {}'.format(self.time))
        if self.time == 0:
            value = -1
        else:
            value = time_now - self.time
        if DLEV > 0:
            LOGGER.debug('          = {}'.format(value))
        else:
            LOGGER.debug('{}'.format(value))
        self.setDriver('GV14', value)

    """
    """

    def cmd_set_light(self,command):
        value = int(command.get("value"))
        # Save current value, and change it.
        slit = self.get_lit()
        self.set_lit(value)
        if value == 0:
            ret = self.primary_n.LightOff(self.primary_n.mac,self.tag_id)
        elif value == 1:
            ret = self.primary_n.LightOn(self.primary_n.mac,self.tag_id,False)
        elif value == 2:
            ret = self.primary_n.LightOn(self.primary_n.mac,self.tag_id,True)
        if ret['st']:
            self.set_from_tag_data(ret['result'])
        else:
            # Command failed, restore status
            self.set_lit(slit)

    def cmd_set_url_config(self,command):
        self.set_url_config(force=True)

    commands = {
        'QUERY': query,
        'SET_LIGHT': cmd_set_light,
        'SET_URL_CONFIG': cmd_set_url_config,
    }
