"""
This is a NodeServer for CAO Gadgets Wireless Sensor Tags for Polyglot v2 written in Python3
by JimBoCA jimboca3@gmail.com
"""
import polyinterface
import sys
import time
import requests, json
from threading import Thread
from wtServer import wtSession
from wt_funcs import get_valid_node_name
from wt_nodes import wTag

LOGGER = polyinterface.LOGGER

# For even more debug... should make a setting?
DEBUG_LEVEL=1

class wTagManager(polyinterface.Node):
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
    def __init__(self, controller, address, name, mac, node_data=False, do_discover=False):
        """
        Optional.
        Super runs all the parent class necessities. You do NOT have
        to override the __init__ method, but if you do, you MUST call super.

        :param controller: Reference to the Controller class
        :param primary: Controller address
        :param address: This nodes address
        :param name: This nodes name
        """
        # Fpr our logger lines
        self.l_name = "{}:{}:{}".format(self.id,address,name)
        self.l_debug('__init__','start')
        # Save the real mac before we legalize it.
        self.ready       = False
        self.do_discover = do_discover
        self.node_data   = node_data
        self.mac         = mac
        super(wTagManager, self).__init__(controller, address, address, name)
        # These start in threads cause they take a while
        self.discover_thread = None
        self.set_url_thread = None
        self.set_url_config_st = None
        self.l_debug('__init__','done')

    def start(self):
        """
        Optional.
        This method is run once the Node is successfully added to the ISY
        and we get a return result from Polyglot. Only happens once.
        """
        self.l_info('start','...')
        self.set_st(True)
        self.set_use_tags(self.get_use_tags())
        self.start_session()
        self.l_info("start",'{0} {1}'.format(self._drivers,self.use_tags))
        self.degFC = 1 # I like F.
        # When we are added by the controller discover, then run our discover.
        if self.do_discover:
            self.discover(thread=False)
        else:
            if self.use_tags == 1:
                self.l_info("start",'Call add_existing_tags because use_tags={0}'.format(self.use_tags))
                self.add_existing_tags()
                #self.discover() # Needed to fix tag_id's
                self.query() # To get latest tag info.
        self.reportDrivers()
        self.ready = True
        self.l_info('start','done')

    def query(self):
        """
        Called by ISY to report all drivers for this node. This is done in
        the parent class, so you don't need to override this method unless
        there is a need.
        """
        if self.use_tags == 0:
            self.l_debug('query','use_tags={}'.format(self.use_tags))
            return
        mgd = self.GetTagList()
        if mgd['st']:
            self.set_st(True)
            for tag in mgd['result']:
                tag_o = self.get_tag_by_id(tag['slaveId'])
                if tag_o is None:
                    self.l_error('query','No tag with id={0}'.format(tag['slaveId']))
                else:
                    tag_o.set_from_tag_data(tag)
                    tag_o.reportDrivers()
        else:
            self.set_st(False)
        self.reportDrivers()


    def shortPoll(self):
        """
        Optional.
        This runs every 10 seconds. You would probably update your nodes either here
        or longPoll. No need to Super this method the parent version does nothing.
        The timer can be overriden in the server.json.
        """
        if not self.ready: return False
        if self.discover_thread is not None:
            if self.discover_thread.isAlive():
                self.l_debug('shortPoll','discover thread still running...')
            else:
                self.l_debug('shortPoll','discover thread is done...')
                self.discover_thread = None
        if self.set_url_thread is not None:
            if self.set_url_thread.isAlive():
                self.l_debug('shortPoll','set_url thread still running...')
            else:
                self.l_debug('shortPoll','set_url thread is done...')
                self.set_url_thread = None
        if self.discover_thread is None and self.set_url_thread is None:
            if self.set_url_config_st == False:
                # Try again...
                self.l_error('shortPoll',"Calling set_url_config since previous st={}".format(self.set_url_config_st))
                self.set_url_config()
        for tag in self.get_tags():
            tag.shortPoll()

    def longPoll(self):
        """
        Optional.
        This runs every 30 seconds. You would probably update your nodes either here
        or shortPoll. No need to Super this method the parent version does nothing.
        The timer can be overriden in the server.json.
        """
        if not self.ready: return False
        self.l_debug('longPoll','...')
        if self.st is False:
            ret = self.controller.wtServer.SelectTagManager(self.mac)
            self.set_st(ret)

    def discover(self, thread=False):
        """
        Start the discover in a thread so we don't cause timeouts :(
        """
        if thread:
            self.discover_thread = Thread(target=self._discover)
            self.discover_thread.start()
        else:
            self._discover()

    def _discover(self):
        self.l_debug('discover','use_tags={}'.format(self.use_tags))
        if self.use_tags == 0:
            return False
        ret = self.GetTagList()
        if ret['st'] is False:
            return
        index = 0
        for tag in ret['result']:
            self.l_debug('discover','Got Tag: {}'.format(tag))
            self.add_tag(tdata=tag, uom=self.get_tag_temp_unit(tag))
        self.reportDrivers() # Report now so they show up while set_url runs.
        self.set_url_config(thread=False)

    def add_existing_tags(self):
        """
        Called on startup to add the tags from the config.
        This has to loop thru the _nodes list to figure out if it's one of the
        tags for this tag manager.
        """
        self.l_debug("add_existing_tags","Looking for my tags")
        if DEBUG_LEVEL > 0: self.l_debug("add_existing_tags"," in _nodes={}".format(self.controller._nodes))
        for address in self.controller._nodes:
            if address != self.address:
                node = self.controller._nodes[address]
                # One of my tags?
                self.l_debug("add_existing_tags","check node primary={}".format(node['primary']))
                if node['primary'] == self.address:
                    self.l_info("add_existing_tags","node={0} = {1}".format(address,node))
                    self.add_tag(address=node['address'], name=node['name'], is_new=False)
        self.set_url_config()

    def add_tag(self, address=None, name=None, tag_type=None, uom=None, tdata=None, is_new=True):
        return self.controller.addNode(wTag(self.controller, self.address, address,
        name=name, tag_type=tag_type, uom=uom, tdata=tdata, is_new=is_new))

    """
    Misc functions
    """
    def get_tags(self):
        """
        Get all the active tags for this tag manager.
        """
        nodes = list()
        for address in self.controller.nodes:
            node = self.controller.nodes[address]
            #self.l_debug('get_tags','node={}'.format(node))
            if hasattr(node,'tag_id') and node.primary_n.mac == self.mac:
                nodes.append(node)
        #self.l_debug('get_tags','nodes={0}'.format(nodes))
        return nodes

    def get_tag_by_id(self,tid):
        tid = int(tid)
        for tag in self.get_tags():
            self.l_debug('get_tag_by_id','{0} address={1} id={2}'.format(tid,tag.address,tag.tag_id))
            if int(tag.tag_id) == tid:
                return tag
        return None

    """
    Wireless Tags API Communication functions
    """
    def start_session(self):
        self.session = wtSession(self,LOGGER,self.controller.wtServer,self.mac)

    # http://wirelesstag.net/ethClient.asmx?op=GetTagList
    def GetTagList(self):
        ret = self.session.api_post_d('ethClient.asmx/GetTagList',{})
        self.set_st(ret)
        if ret: return ret
        self.l_error('GetTagList',"Failed: st={}".format(ret))
        return ret

    # http://wirelesstag.net/ethClient.asmx?op=LoadEventURLConfig
    def LoadEventURLConfig(self,params):
        return self.session.api_post_d('ethClient.asmx/LoadEventURLConfig',params)

    # http://wirelesstag.net/ethClient.asmx?op=SaveEventURLConfig
    def SaveEventURLConfig(self,params):
        return self.session.api_post_d('ethClient.asmx/SaveEventURLConfig',params)

    # http://wirelesstag.net/ethClient.asmx?op=LoadTempSensorConfig
    def LoadTempSensorConfig(self,params):
        return self.session.api_post_d('ethClient.asmx/LoadTempSensorConfig',params)

    # http://wirelesstag.net/ethClient.asmx?op=RequestImmediatePostback
    def RequestImmediatePostback(self,params):
        return self.session.api_post_d('ethClient.asmx/RequestImmediatePostback',params)

    def RebootTagManager(self,tmgr_mac):
        return self.session.api_post_d('ethClient.asmx/RebootTagManager',{})

    def PingAllTags(self,tmgr_mac):
        return self.session.api_post_d('ethClient.asmx/PingAllTags',{'autoRetry':True})

    def LightOn(self,tmgr_mac,id,flash):
        return self.session.api_post_d('ethClient.asmx/LightOn',{'id': id, 'flash':flash})

    def LightOff(self,tmgr_mac,id):
        return self.session.api_post_d('ethClient.asmx/LightOff',{'id': id})

    # TODO: Cache the temp sensor config's?
    def get_tag_temp_unit(self,tag_data):
        """
        Returns the LoadTempSensorConfig temp_unit.  0 = Celcius, 1 = Fahrenheit
        """
        mgd = self.LoadTempSensorConfig({'id':tag_data['slaveId']})
        if mgd['st']:
            return mgd['result']['temp_unit']
        else:
            return -1

    """
        Call set_url_config tags so updates are pushed back to me.
        # TODO: This needs to run in a seperate thread because it can take to long.
    """
    def set_url_config(self, thread=True, force=False):
        """
        Start the set_url_config in a thread so we don't cause timeouts :(
        """
        if thread:
            if force:
                self.set_url_thread = Thread(target=self._set_url_config_true)
            else:
                self.set_url_thread = Thread(target=self._set_url_config_false)
            self.set_url_thread.start()
        else:
            self._set_url_config()

    def _set_url_config_true(self):
        self._set_url_config(force=True)

    def _set_url_config_false(self):
        self._set_url_config(force=False)

    def _set_url_config(self,force=False):
        # None means there are no tags.
        self.set_url_config_st = None
        if self.use_tags == 0:
            return False
        # Tracks our status so longPoll can auto-rerun it when necessary
        tags = self.get_tags()
        if len(tags) == 0:
            self.l_error("_set_url_config","No tags in Polyglot DB, you need to discover?")
            return False
        self.set_url_config_st = False
        for tag in tags:
            tag.set_url_config(force=force)
        self.set_url_config_st = True


    def l_info(self, name, string):
        LOGGER.info("%s:%s: %s" %  (self.l_name,name,string))

    def l_error(self, name, string):
        LOGGER.error("%s:%s: %s" % (self.l_name,name,string))

    def l_warning(self, name, string):
        LOGGER.warning("%s:%s: %s" % (self.l_name,name,string))

    def l_debug(self, name, string):
        LOGGER.debug("%s:%s: %s" % (self.l_name,name,string))

    """
    Set Functions
    """
    def set_params(self,params):
        """
        Set params from the getTagManager data
        """
        self.set_st(params['online'])

    def set_st(self,value,force=False):
        self.l_debug('set_st',"{},{}".format(value,force))
        if not force and hasattr(self,"st") and self.st == value:
            return True
        self.st = value
        if value:
            self.setDriver('ST', 1)
        else:
            self.setDriver('ST', 0)

    def get_use_tags(self):
        self.use_tags = self.getDriver('GV1')
        if self.use_tags is None: return None
        self.use_tags = int(self.use_tags)
        return self.use_tags

    def set_use_tags(self,value,force=False):
        if value is None: value = 0
        value = int(value)
        if not force and hasattr(self,"use_tags") and self.use_tags == value:
            return True
        self.use_tags = value
        self.setDriver('GV1', value)
        if self.ready and value == 1:
            self.discover()

    """
    """

    def cmd_set_use_tags(self,command):
        self.set_use_tags(command.get("value"))

    def cmd_set_url_config(self,command):
        self.set_url_config(thread=True,force=True)

    def cmd_ping_all_tags(self,command):
        self.PingAllTags()

    def cmd_reboot(self,command):
        self.RebootTagManager(self.mac)

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

    def cmd_test(self, command):
        self.l_debug('cmd_test','just a test')
        self.l_debug('cmd_test',str(self.controller.nodes['foo']))

    id = 'wTagManager'
    drivers = [
        {'driver': 'ST',  'value': 0, 'uom': 2},
        {'driver': 'GV1', 'value': 0, 'uom': 2}, # Use Tags
    ]
    commands = {
        'SET_USE_TAGS': cmd_set_use_tags,
        'QUERY': query,
        'SET_URL_CONFIG': cmd_set_url_config,
        'PING_ALL_TAGS': cmd_ping_all_tags,
        'DISCOVER': discover,
        'REBOOT': cmd_reboot,
        'TEST': cmd_test,
    }
