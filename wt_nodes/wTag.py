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
    def __init__(self, controller, primary, address=None, name=None, tag_type=None, uom=None, tdata=None, node_data=None):
        """
        Optional.
        Super runs all the parent class necessities. You do NOT have
        to override the __init__ method, but if you do, you MUST call super.

        :param controller: Reference to the Controller class
        :param primary: Controller address
        :param address: This nodes address
        :param name: This nodes name
        """
        self.drivers = [
            {'driver': 'ST',      'value': 0, 'uom': 2},
            {'driver': 'GPV',     'value': 0, 'uom': 56}, # tag_id
            {'driver': 'UOM',     'value': 0, 'uom': 56}, # UOM 0=C 1=F
            {'driver': 'GV1',     'value': 0, 'uom': 56}, # tag_type: 
            {'driver': 'ALARM',   'value': 0, 'uom': 25}, # evst: Event State   
            {'driver': 'CLITEMP', 'value': 0, 'uom': 'temp_uom'}, # temp:   Curent temperature (17=F 4=C)
            {'driver': 'BATLVL',  'value': 0, 'uom': 51}, # batp:   Battery percent (51=percent)
            {'driver': 'LUMIN',   'value': 0, 'uom': 36}, # lux:    Lux (36=lux)
            {'driver': 'CLIHUM',  'value': 0, 'uom': 21}, # hum:    Humidity (21 = absolute humidity)
            {'driver': 'CV',      'value': 0, 'uom': 72}, # batv:   Battery Voltag 72=Volt
            {'driver': 'GV2',     'value': 0, 'uom': 25}, # motion: Might use True, False, Open for door mode?
            {'driver': 'GV3',     'value': 0, 'uom': 56}, # orien:  Orientation
            {'driver': 'GV4',     'value': 0, 'uom': 56}, # xaxis:  X-Axis
            {'driver': 'GV5',     'value': 0, 'uom': 56}, # yasis:  Y-Axis
            {'driver': 'GV6',     'value': 0, 'uom': 56}, # zaxis:  Z-Asis
            {'driver': 'GV7',     'value': 0, 'uom': 78},  # lit:    Light 78=off/off
            {'driver': 'GV8',     'value': 0, 'uom':  2},  # oor:    OutOfRange
            {'driver': 'GV9',     'value': 0, 'uom': 25},  # tempState:  
            {'driver': 'GV10',    'value': 0, 'uom': 25},  # moisture(cap)State:  
            {'driver': 'GV11',    'value': 0, 'uom': 25}   # lightState:  
        ]

        LOGGER.debug('wTag:__init__: address={0} name={1} type={2} uom={3}'.format(address,name,tag_type,uom))

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
                    self.tag_type = driver['value']
                elif driver['driver'] == 'GPV':
                    self.tag_id   = driver['value']
                elif driver['driver'] == 'UOM':
                    self.tag_uom  = driver['value']
        elif address is None or name is None or tag_type is None:
            # It's a new tag.
            self.address = address
            if tdata is None:
                self.l_error('__init__',"address ({0}), name ({1}), and type ({2}) must be specified when tdata is None".format(address,name,tag_type))
                return False
            if uom is None:
                self.l_error('__init__',"uom ({0}) must be specified for new tags.".format(uom))
            self.is_new   = True
            self.tag_type = tdata['tagType']
            self.tag_uom  = uom
            self.tag_id   = tdata['slaveId']
            self.uuid     = tdata['uuid']
            address       = id_to_address(self.uuid)
            name          = tdata['name']
        self.name = name
        self.tdata = tdata
        #
        # C or F?
        # Fix our temp_uom in drivers
        # This won't change an existing tag, only new ones.
        #
        # TODO:  test changing it by forcing update?
        for driver in self.drivers:
            if driver['uom'] == 'temp_uom':
                # (17=F 4=C)
                driver['uom'] = 4 if self.tag_uom == 0 else 17
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
            # These stay the same across reboots as the defaul.
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
        if 'hum' in tdata:
            self.set_hum(tdata['hum'])
        if 'lit' in tdata:
            self.set_lit(tdata['lit'])
        if 'eventState' in tdata:
            self.set_evst(tdata['eventState'])
        if 'oor' in tdata:
            self.set_oor(tdata['oor'])
        if 'tempEventState' in tdata:
            self.set_tmst(tdata['tempEventState'])
        if 'capEventState' in tdata:
            self.set_msst(tdata['capEventState'])
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
        self.setDriver('CLITEMP', self.temp)
        
    def set_hum(self,value,force=False):
        value = int(value)
        if not force and hasattr(self,"hum") and self.hum == value:
            return True
        self.hum = value
        self.setDriver('CLIHUM', self.hum)
 
    def set_lit(self,value,force=False):
        value = int(value)
        if not force and hasattr(self,"lit") and self.lit == value:
            return True
        self.lit = value
        self.setDriver('GV7', value)
      
    def set_lux(self,value,force=False):
        value = int(value)
        if not force and hasattr(self,"lux") and self.lux == value:
            return True
        self.lux = value
        self.setDriver('LUMIN', self.lux)
        
    def set_batp(self,value,force=False):
        value = myfloat(value,2)
        if not force and hasattr(self,"batp") and self.batp == value:
            return True
        self.batp = value
        self.setDriver('BATLVL', self.batp)
        
    def set_batv(self,value,force=False):
        value = myfloat(value,3)
        if not force and hasattr(self,"batv") and self.batv == value:
            return True
        self.batv = value
        self.setDriver('CV', self.batv)
        
    def set_motion(self,value,force=False):
        if not force and hasattr(self,"motion") and self.motion == value:
            return True
        self.motion = value
        self.setDriver('GV2', self.motion)
        
    def set_orien(self,value,force=False):
        value = myfloat(value,1)
        if not force and hasattr(self,"orien") and self.orien == value:
            return True
        self.orien = value
        self.setDriver('GV3', self.orien)
        
    def set_xaxis(self,value,force=False):
        value = int(value)
        if not force and hasattr(self,"xaxis") and self.xaxis == value:
            return True
        self.xaxis = value
        self.setDriver('GV4', self.xaxis)
        
    def set_yaxis(self,value,force=False):
        value = int(value)
        if not force and hasattr(self,"yaxis") and self.yaxis == value:
            return True
        self.yaxis = value
        self.setDriver('GV5', self.yaxis)
        
    def set_zaxis(self,value,force=False):
        value = int(value)
        if not force and hasattr(self,"zaxis") and self.zaxis == value:
            return True
        self.zaxis = value
        self.setDriver('GV6', self.zaxis)
        
    def set_evst(self,value,force=False):
        if value is None: 
            value = 0 
        else: 
            value = int(value)
        if not force and hasattr(self,"evst") and self.evst == value: return True
        self.evst = value
        self.setDriver('ALARM', self.evst)
        
    def set_oor(self,value,force=False):
        value = int(value)
        if not force and hasattr(self,"oor") and self.oor == value:
            return True
        self.oor = value
        self.setDriver('GV7', value)
      
    def set_tmst(self,value,force=False):
        if value is None: 
            value = 0 
        else: 
            value = int(value)
        if not force and hasattr(self,"tmst") and self.tmst == value: return True
        self.tmst = value
        self.setDriver('GV9', self.evst)
        
    def set_msst(self,value,force=False):
        if value is None: 
            value = 0 
        else: 
            value = int(value)
        if not force and hasattr(self,"msst") and self.msst == value: return True
        self.msst = value
        self.setDriver('GV10', self.evst)
        
    def set_list(self,value,force=False):
        if value is None: 
            value = 0 
        else: 
            value = int(value)
        if not force and hasattr(self,"list") and self.list == value: return True
        self.list = value
        self.setDriver('GV11', self.evst)
        
    """
    """

    def cmd_set_on(self, command):
        """
        Example command received from ISY.
        Set DON on MyNode.
        Sets the ST (status) driver to 1 or 'True'
        """
        self.setDriver('ST', 1)

    def cmd_set_off(self, command):
        """
        Example command received from ISY.
        Set DOF on MyNode
        Sets the ST (status) driver to 0 or 'False'
        """
        self.setDriver('ST', 0)

    
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
        'DOF': cmd_set_off,
    }
