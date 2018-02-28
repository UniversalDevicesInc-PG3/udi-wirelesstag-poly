"""
This is a NodeServer for CAO Gadgets Wireless Sensor Tags for Polyglot v2 written in Python3
by JimBoCA jimboca3@gmail.com
"""
import polyinterface
import sys
import time
import re
from copy import deepcopy
from wt_funcs import id_to_address,myfloat

LOGGER = polyinterface.LOGGER

class wTag(polyinterface.Node):
    """
    This is the class that all the Nodes will be represented by. You will add this to
    Polyglot/ISY with the controller.addNode method.

    Class Variables:
    self.primary: String address of the Controller node.
    self.parent: Easy access to the Controller Class from the node itself.
    self.address: String address of this Node 14 character limit. (ISY limitation)
    self.added: Boolean Confirmed added to ISY

    Class Methods:
    start(): This method is called once polyglot confirms the node is added to ISY.
    setDriver('ST', 1, report = True, force = False):
        This sets the driver 'ST' to 1. If report is False we do not report it to
        Polyglot/ISY. If force is True, we send a report even if the value hasn't changed.
    reportDrivers(): Forces a full update of all drivers to Polyglot/ISY.
    query(): Called when ISY sends a query request to Polyglot for this specific node
    """
    def __init__(self, controller, primary, address=None, name=None,
                 tag_type=None, uom=None, tdata=None, node_data=None):
        """
        Optional.
        Super runs all the parent class necessities. You do NOT have
        to override the __init__ method, but if you do, you MUST call super.

        :param controller: Reference to the Controller class
        :param primary: Controller address
        :param address: This nodes address
        :param name: This nodes name
        """
        LOGGER.debug('wTag:__init__: address={0} name={1} type={2} uom={3}'.format(address,name,tag_type,uom))
        tag_id = None

        # Remove spaces from names since that messes with our return urls.
        if name is not None:
            name = re.sub(r"\s+", '', name)
        if node_data is not None:
            # An existing node,
            self.is_new = False
            # We need to pull tag_type from GV1 for existing tags.
            self.tag_uom = -1 # Should never happen, just need for old data added before it existed.
            for driver in node_data['drivers']:
                if driver['driver'] == 'GV1':
                    tag_type = driver['value']
                elif driver['driver'] == 'GPV':
                    tag_id   = driver['value']
                elif driver['driver'] == 'UOM':
                    self.tag_uom  = driver['value']
            if tag_id is None:
                self.l_error('__init__','No tag_id in node_data={0}'.format(node_data))
                return False
        elif address is None or name is None or tag_type is None:
            # It's a new tag.
            self.address = address
            if tdata is None:
                self.l_error('__init__',"address ({0}), name ({1}), and type ({2}) must be specified when tdata is None".format(address,name,tag_type))
                return False
            if uom is None:
                self.l_error('__init__',"uom ({0}) must be specified for new tags.".format(uom))
            self.is_new   = True
            tag_type = tdata['tagType']
            self.tag_uom  = uom
            tag_id   = tdata['slaveId']
            self.uuid     = tdata['uuid']
            address       = id_to_address(self.uuid)
            name          = tdata['name']
        tag_id = int(tag_id)
        tag_type = int(tag_type)
        self.name = name
        self.tdata = tdata
        self.tag_id = tag_id
        self.tag_type = tag_type
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
            {'driver': 'GPV',     'value': 0, 'uom': 56},
            # UOM 0=C 1=F
            {'driver': 'UOM',     'value': 0, 'uom': 56},
            # tag_type:
            {'driver': 'GV1',     'value': 0, 'uom': 56},
            # temp:   Curent temperature (17=F 4=C)
            {'driver': 'CLITEMP', 'value': 0, 'uom': temp_uom},
            # batp:   Battery percent (51=percent)
            {'driver': 'BATLVL',  'value': 0, 'uom': 51},
            # batv:   Battery Voltag 72=Volt
            {'driver': 'CV',      'value': 0, 'uom': 72},
            # lit:    Light 78=off/on
            {'driver': 'GV7',     'value': 0, 'uom': 25},
            # tempState:
            {'driver': 'GV9',     'value': 0, 'uom': 25},
        ]

        if (tag_type == 12 or tag_type == 13 or tag_type == 21 or tag_type == 26
            or tag_type == 32 or tag_type == 52 or tag_type == 62 or
            tag_type == 72):
            # evst: Event State
            dv.append({'driver': 'ALARM',   'value': 0, 'uom': 25})
        if (tag_type == 26):
            # lux:    Lux (36=lux)
            dv.append({'driver': 'LUMIN',   'value': 0, 'uom': 36})
        if (tag_type == 13 or tag_type == 21 or tag_type == 26 or tag_type == 32
            or tag_type == 52 or tag_type == 62 or tag_type == 72):
            # hum:    Humidity (21 = absolute humidity)
            dv.append({'driver': 'CLIHUM',  'value': 0, 'uom': 21})
        if (tag_type == 32):
            # TODO: Only 32 has water sensor?
            dv.append({'driver': 'GV12',  'value': 1, 'uom': 25})
        if (tag_type == 12 or tag_type == 13 or tag_type == 21):
            # motion: Might use True, False, Open for door mode?
            dv.append({'driver': 'GV2',     'value': 0, 'uom': 25})
            # orien:  Orientation
            dv.append({'driver': 'GV3',     'value': 0, 'uom': 56})
            # xaxis:  X-Axis
            dv.append({'driver': 'GV4',     'value': 0, 'uom': 56})
            # yasis:  Y-Axis
            dv.append({'driver': 'GV5',     'value': 0, 'uom': 56})
            # zaxis:  Z-Asis
            dv.append({'driver': 'GV6',     'value': 0, 'uom': 56})
        if (tag_type == 12 or tag_type == 13 or tag_type == 21 or tag_type == 26
            or tag_type == 32 or tag_type == 52 or tag_type == 72):
            # oor:    OutOfRange
            dv.append({'driver': 'GV8',     'value': 0, 'uom':  2})
        if (tag_type == 13 or tag_type == 21 or tag_type == 26
            or tag_type == 32 or tag_type == 52 or tag_type == 62
            or tag_type == 72):
            # moisture(cap)State:
            dv.append({'driver': 'GV10',    'value': 0, 'uom': 25})
        if (tag_type == 26):
            # lightState:
            dv.append({'driver': 'GV11',    'value': 0, 'uom': 25})

        self.drivers = dv

        uomS = "C" if self.tag_uom == 0 else "F"
        self.id = 'wTag' + str(self.tag_type) + uomS
        self.address = address
        self.l_info('__init__','address={0} name={1} type={2} id={3} uom={4}'.format(address,name,self.tag_type,self.tag_id,self.tag_uom))
        super(wTag, self).__init__(controller, primary, address, name)

    def start(self):
        """
        Optional.
        This method is run once the Node is successfully added to the ISY
        and we get a return result from Polyglot. Only happens once.
        """
        self.setDriver('ST', 1)
        self.primary_n = self.controller.nodes[self.primary]
        # Always set driver from tag type
        self.set_tag_type(self.tag_type,True)
        self.set_tag_id(self.tag_id,True)
        self.set_tag_uom(self.tag_uom,True)
        if self.tdata is not None:
            self.set_from_tag_data(self.tdata)
        else:
            # These stay the same across reboots as the default.
            self.set_temp(self.getDriver('CLITEMP'),True,False)
            self.set_hum(self.getDriver('CLIHUM'),True)
            self.set_lux(self.getDriver('LUMIN'),True)
            self.set_batp(self.getDriver('BATLVL'),True)
            self.set_batv(self.getDriver('CV'),True)
            self.set_motion(self.getDriver('GV2'),True)
            self.set_orien(self.getDriver('GV3'),True)
            self.set_xaxis(self.getDriver('GV4'),True)
            self.set_yaxis(self.getDriver('GV5'),True)
            self.set_zaxis(self.getDriver('GV6'),True)
            self.set_lit(self.getDriver('GV7'),True)
            self.set_evst(self.getDriver('ALARM'),True)
            self.set_oor(self.getDriver('GV8'),True)
            self.set_tmst(self.getDriver('GV9'),True)
            self.set_cpst(self.getDriver('GV10'),True)
            self.set_list(self.getDriver('GV11'),True)
            self.set_wtst(self.getDriver('GV12'),True)
        self.reportDrivers()


    def query(self):
        """
        Called by ISY to report all drivers for this node. This is done in
        the parent class, so you don't need to override this method unless
        there is a need.
        """
        # Polyglot bug?  We have to set every driver before calling reportDrivers?
        #self.set_tag_type(self.tag_type,True)
        #self.set_tag_id(self.tag_id,True)
        #self.set_tag_uom(self.tag_uom,True)
        # This askes for the sensor to report
        mgd = self.controller.wtServer.RequestImmediatePostback({'id':self.tag_id})
        if mgd['st']:
            self.set_from_tag_data(mgd['result'])
            self.reportDrivers()

    def l_info(self, name, string):
        LOGGER.info("%s:%s:%s:%s: %s" %  (self.id,self.address,self.name,name,string))

    def l_error(self, name, string):
        LOGGER.error("%s:%s:%s:%s: %s" % (self.id,self.address,self.name,name,string))

    def l_warning(self, name, string):
        LOGGER.warning("%s:%s:%s:%s: %s" % (self.id,self.address,self.name,name,string))

    def l_debug(self, name, string):
        LOGGER.debug("%s:%s:%s:%s: %s" % (self.id,self.address,self.name,name,string))

    def get_handler(self,command,params):
        """
        This is called by the controller get_handler after parsing the node_data
        """
        if command == '/update':
            #tagname=Garage Freezer&tagid=0&temp=-21.4213935329179&hum=0&lux=0&ts=2018-02-15T11:18:02+00:00 HTTP/1.1" 400 -
            pass
        if command == '/motion_detected':
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
            self.l_error('get_handler',"Unknown command '{0}'".format(command))
        if 'tempc' in params and self.tag_uom == 0:
            self.set_temp(params['tempc'],convert=False)
        if 'tempf' in params and self.tag_uom == 1:
            self.set_temp(params['tempf'],convert=False)
        if 'temp' in params:
            self.set_temp(params['temp'])
        if 'hum' in params:
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
        return True

    """
    Set Functions
    """
    def set_from_tag_data(self,tdata):
        if 'temperature' in tdata:
            self.set_temp(tdata['temperature'])
        if 'batteryVolt' in tdata:
            self.set_batv(tdata['batteryVolt'])
        if 'batteryRemaining' in tdata:
            self.set_batp(float(tdata['batteryRemaining']) * 100)
        if 'lux' in tdata:
            self.set_lux(tdata['lux'])
        if 'cap' in tdata:
            self.set_hum(tdata['cap'])
        if 'lit' in tdata:
            self.set_lit(tdata['lit'])
        if 'eventState' in tdata:
            self.set_evst(tdata['eventState'])
        if 'oor' in tdata:
            self.set_oor(tdata['oor'])
        if 'tempEventState' in tdata:
            self.set_tmst(tdata['tempEventState'])
        if 'capEventState' in tdata:
            self.set_cpst(tdata['capEventState'])
        if 'lightEventState' in tdata:
            self.set_list(tdata['lightEventState'])

    # This is the tag_type number, we don't really need to show it, but
    # we need the info when recreating the tags from the config.
    def set_tag_type(self,value,force=False):
        if not force and hasattr(self,"tag_type") and self.tag_type == value:
            return True
        self.l_debug('set_tag_type','GV1 to {0}'.format(value))
        self.tag_type = value
        self.setDriver('GV1', value)

    def set_tag_id(self,value,force=False):
        if not force and hasattr(self,"tag_id") and self.tag_id == value:
            return True
        self.tag_id = value
        self.setDriver('GPV', value)

    def set_tag_uom(self,value,force=False):
        if not force and hasattr(self,"tag_uom") and self.tag_uom == value:
            return True
        self.tag_uom = value
        self.setDriver('UOM', value)

    def set_temp(self,value,force=False,convert=True):
        value = myfloat(value,2)
        if convert and self.primary_n.degFC == 1:
            # Convert C to F
            value = myfloat(float(value) * 1.8 + 32.0,2)
        if not force and hasattr(self,"temp") and self.temp == value:
            return True
        self.temp = value
        self.setDriver('CLITEMP', value)

    def set_hum(self,value,force=False):
        if value is None: return
        value = int(value)
        if not force and hasattr(self,"hum") and self.hum == value:
            return True
        self.hum = value
        self.setDriver('CLIHUM', value)

    def set_lit(self,value,force=False):
        value = int(value)
        if not force and hasattr(self,"lit") and self.lit == value:
            return True
        self.lit = value
        self.setDriver('GV7', value)

    def set_lux(self,value,force=False):
        if value is None: return
        value = int(value)
        if not force and hasattr(self,"lux") and self.lux == value:
            return True
        self.lux = value
        self.setDriver('LUMIN', value)

    def set_batp(self,value,force=False):
        value = myfloat(value,2)
        if not force and hasattr(self,"batp") and self.batp == value:
            return True
        self.batp = value
        self.setDriver('BATLVL', value)

    def set_batv(self,value,force=False):
        value = myfloat(value,3)
        if not force and hasattr(self,"batv") and self.batv == value:
            return True
        self.batv = value
        self.setDriver('CV', value)

    def set_motion(self,value,force=False):
        if value is None: return
        if not force and hasattr(self,"motion") and self.motion == value:
            return True
        self.motion = value
        self.setDriver('GV2', value)

    def set_orien(self,value,force=False):
        if value is None: return
        value = myfloat(value,1)
        if not force and hasattr(self,"orien") and self.orien == value:
            return True
        self.orien = value
        self.setDriver('GV3', value)

    def set_xaxis(self,value,force=False):
        if value is None: return
        value = int(value)
        if not force and hasattr(self,"xaxis") and self.xaxis == value:
            return True
        self.xaxis = value
        self.setDriver('GV4', value)

    def set_yaxis(self,value,force=False):
        if value is None: return
        value = int(value)
        if not force and hasattr(self,"yaxis") and self.yaxis == value:
            return True
        self.yaxis = value
        self.setDriver('GV5', value)

    def set_zaxis(self,value,force=False):
        if value is None: return
        value = int(value)
        if not force and hasattr(self,"zaxis") and self.zaxis == value:
            return True
        self.zaxis = value
        self.setDriver('GV6', value)

    def set_evst(self,value,force=False):
        if value is None: return
        value = int(value)
        if not force and hasattr(self,"evst") and self.evst == value: return True
        self.evst = value
        self.setDriver('ALARM', value)
        # eventState 1=Armed, so no more motion
        if value == 1:
            self.set_motion(0)

    def set_oor(self,value,force=False):
        if value is None: return
        value = int(value)
        if not force and hasattr(self,"oor") and self.oor == value:
            return True
        self.oor = value
        self.setDriver('GV7', value)

    def set_tmst(self,value,force=False):
        if value is None: return
        value = int(value)
        if not force and hasattr(self,"tmst") and self.tmst == value: return True
        self.tmst = value
        self.setDriver('GV9', value)

    def set_cpst(self,value,force=False):
        self.l_debug('set_cpst','{0},{1}'.format(value,force))
        if value is None: return
        value = int(value)
        if not force and hasattr(self,"cpst") and self.cpst == value: return True
        self.cpst = value
        self.setDriver('GV10', value)

    def set_list(self,value,force=False):
        if value is None: return
        value = int(value)
        if not force and hasattr(self,"list") and self.list == value: return True
        self.list = value
        self.setDriver('GV11', value)

    def set_wtst(self,value,force=False):
        self.l_debug('set_wtst','{0},{1}'.format(value,force))
        if value is None: return
        value = int(value)
        # Force to 1, Dry state on initialization since polyglot ignores the init value
        if value == 0: value = 1
        if not force and hasattr(self,"wtst") and self.wtst == value: return True
        self.wtst = value
        self.setDriver('GV12', value)

    """
    """

    def cmd_set_light(self,command):
        value = command.get("value")
        self.l_error('Need to implement turning setting light to {0}'.format(value))

    """
    {"d":[
    {
      "__type":"MyTagList.Tag2",
      "managerName":"Rangwood",
      "mac":"0E994A04A300",
      "dbid":1,
      "mirrors":[],
      "notificationJS":"",
      "name":"Garage Freezer",
      "uuid":"7911937f-c758-4b88-a33a-0761ed284f29",
      "comment":"",
      "slaveId":0,
      "tag_type":12,
      "lastComm":131628820472086602,
      "alive":true,
      "signaldBm":-64,
      "batteryVolt":3.3048022377777824,
      "beeping":false,
      "lit":false,
      "migrationPending":false,
      "beepDurationDefault":15,
      "eventState":0,
      "tempEventState":1,
      "OutOfRange":false,
      "lux":0,
      "temperature":-21.421393532917921,
      "tempCalOffset":0,
      "capCalOffset":0,
      "image_md5":null,
      "cap":0,
      "capRaw":0,
      "az2":0,
      "capEventState":0,
      "lightEventState":0,
      "shorted":false,
      "thermostat":null,
      "playback":null,
      "postBackInterval":3600,
      "rev":12,
      "version1":1,
      "freqOffset":12828,
      "freqCalApplied":0,
      "reviveEvery":4,
      "oorGrace":2,
      "LBTh":2.5,
      "enLBN":true,
      "txpwr":204,
      "rssiMode":false,
      "ds18":false,
      "v2flag":16,
      "batteryRemaining":1.13 # = 113% ?
    }]}
    """

    commands = {
        'QUERY': query,
        'SET_LIGHT': cmd_set_light,
    }
