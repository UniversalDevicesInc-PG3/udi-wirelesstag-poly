"""
This is a NodeServer for CAO Gadgets Wireless Sensor Tags for Polyglot v2 written in Python3
by JimBoCA jimboca3@gmail.com
"""
import polyinterface
import sys
import time
from threading import Thread
from wt_funcs import get_valid_node_name
from wt_params import wt_params
from wt_nodes import wTag

LOGGER = polyinterface.LOGGER

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
        # Save the real mac before we legalize it.
        self.ready       = False
        self.do_discover = do_discover
        self.node_data   = node_data
        self.mac         = mac
        super(wTagManager, self).__init__(controller, address, address, name)
        # These start in threads cause they take a while
        self.discover_thread = None
        self.set_url_thread = None

    def start(self):
        """
        Optional.
        This method is run once the Node is successfully added to the ISY
        and we get a return result from Polyglot. Only happens once.
        """
        self.l_info('start','...')
        self.set_st(True)
        if self.node_data is False:
            # New node, set the defaults.
            self.set_use_tags(0)
        else:
            self.set_use_tags(self.getDriver('GV1'))
            self.l_info("start",'{0} {1}'.format(self._drivers,self.use_tags))
        self.degFC = 1 # I like F.
        # When we are added by the controller discover, then run our discover.
        if self.do_discover:
            self.discover()
        else:
            self.add_existing_tags()
        self.query()
        self.ready = True
        self.l_info('start','done')

    def query(self):
        """
        Called by ISY to report all drivers for this node. This is done in
        the parent class, so you don't need to override this method unless
        there is a need.
        """
        self.reportDrivers()

    def shortPoll(self):
        """
        Optional.
        This runs every 10 seconds. You would probably update your nodes either here
        or longPoll. No need to Super this method the parent version does nothing.
        The timer can be overriden in the server.json.
        """
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

    def longPoll(self):
        """
        Optional.
        This runs every 30 seconds. You would probably update your nodes either here
        or shortPoll. No need to Super this method the parent version does nothing.
        The timer can be overriden in the server.json.
        """
        self.l_debug('longPoll','...')

    def discover(self):
        """
        Start the discover in a thread so we don't cause timeouts :(
        """
        self.discover_thread = Thread(target=self._discover)
        self.discover_thread.start()

    def _discover(self):
        self.l_debug('discover','use_tags={}'.format(self.use_tags))
        if self.use_tags == 0:
            return False
        ret = self.get_tag_list()
        if ret['st'] is False:
            return
        index = 0
        for tag in ret['result']:
            self.l_debug('discover','Got Tag: {}'.format(tag))
            self.add_tag(tdata=tag)
        self.set_url_config(thread=False)

    def add_existing_tags(self):
        """
        Called on startup to add the tags from the config
        """
        for address in self.controller._nodes:
            node = self.controller._nodes[address]
            if node['address'] != self.address and node['node_def_id'] != 'wtController':
                self.l_info("add_existing_tags","node={0} = {1}".format(address,node))
                self.add_tag(address=node['address'], name=node['name'], node_data=node)
        self.set_url_config()

    def add_tag(self, address=None, name=None, tag_type=None, tdata=None, node_data=None):
        self.controller.addNode(wTag(self.controller, self.address, address, name=name, tag_type=tag_type, tdata=tdata, node_data=node_data))

    def get_tags(self):
        nodes = list()
        for address in self.controller.nodes:
            node = self.controller.nodes[address]
            if hasattr(node,'tag_id'):
                nodes.append(node)
        return nodes

    """
    Misc functions
    """

    """
        Call set_url_config tags so updates are pushed back to me.
        # TODO: This needs to run in a seperate thread because it can take to long.
    """
    def set_url_config(self, thread=True):
        """
        Start the set_url_config in a thread so we don't cause timeouts :(
        """
        if thread:
            self.set_url_thread = Thread(target=self._set_url_config)
            self.set_url_thread.start()
        else:
            self._set_url_config()

    def _set_url_config(self):
        if self.use_tags == 0:
            return False
        tags = self.get_tags()
        def_param = '0={0}&1={1}&2={2}'
        mgd = self.controller.wtServer.LoadEventURLConfig({'id':tags[0].tag_id})
        self.l_debug('set_url_config','{0}'.format(mgd))
        if mgd['st'] is False:
            return False
        else:
            url = self.controller.wtServer.listen_url
            #{'in_free_fall': {'disabled': True, 'nat': False, 'verb': None, 'url': 'http://', 'content': None}
            newconfig = dict()
            for key, value in mgd['result'].items():
                if key != '__type':
                    if key in wt_params:
                        param = wt_params[key]
                    else:
                        self.l_error('set_url_config',"Unknown tag param '{0}'".format(key))
                        param = def_param
                    self.l_debug('set_url_config',"key={0} value={1}".format(key,value))
                    value['disabled'] = False
                    value['url'] = '{0}/{1}?{2}'.format(url,key,param)
                    value['nat'] = True
                    newconfig[key] = value
            # Changed to applyAll True for now?
            res = self.controller.wtServer.SaveEventURLConfig({'id':tags[0].tag_id, 'config': newconfig, 'applyAll': True})

    def get_tag_list(self):
        ret = self.controller.wtServer.SelectTagManager(self.mac)
        if ret['st'] is False:
            self.set_st(False)
            self.l_error('get_tag_list',"Unable to select tag manager: {}".format(self.mac))
        else:
            ret = self.controller.wtServer.GetTagList()
            if ret['st'] is False:
                self.set_st(False)
                self.l_error('get_tag_list',"Unable to select get tags")
            else:
                self.set_st(True)
        return ret

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
    def set_params(self,params):
        """
        Set params from the getTagManager data
        """
        self.set_st(params['online'])

    def set_st(self,value,force=False):
        if not force and hasattr(self,"st") and self.st == value:
            return True
        self.st = value
        if value:
            self.setDriver('ST', 1)
        else:
            self.setDriver('ST', 0)

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

    
    id = 'wTagManager'
    drivers = [
        {'driver': 'ST',  'value': 0, 'uom': 2},
        {'driver': 'GV1', 'value': 1, 'uom': 2}  # Use Tags
    ]
    commands = {
        'SET_USE_TAGS': cmd_set_use_tags,
        'DON': cmd_set_on,
        'DOF': cmd_set_off,
    }
