
import polyinterface
import sys,time,logging
from threading import Thread
from copy import deepcopy

from wt_nodes import wTagManager
from wtServer import wtServer
from wt_funcs import get_server_data,get_valid_node_name,get_profile_info

LOGGER = polyinterface.LOGGER
# old
nodedef = 'node_def_id'
# new
#nodedef = 'nodedef'

class wtController(polyinterface.Controller):
    client_id     = "3b08b242-f0f8-41c0-ba29-6b0478cd0b77"
    client_secret = "0b947853-1676-4a63-a384-72769c88f3b1"
    auth_url      = "https://www.wirelesstag.net/oauth2/authorize.aspx?client_id={0}".format(client_id)
    """
    The Controller Class is the primary node from an ISY perspective. It is a Superclass
    of polyinterface.Node so all methods from polyinterface.Node are available to this
    class as well.

    Class Variables:
    self.nodes: Dictionary of nodes. Includes the Controller node. Keys are the node addresses
    self.name: String name of the node
    self.address: String Address of Node, must be less than 14 characters (ISY limitation)
    self.polyConfig: Full JSON config dictionary received from Polyglot for the controller Node
    self.added: Boolean Confirmed added to ISY as primary node
    self.config: Dictionary, this node's Config

    Class Methods (not including the Node methods):
    start(): Once the NodeServer config is received from Polyglot this method is automatically called.
    addNode(polyinterface.Node, update = False): Adds Node to self.nodes and polyglot/ISY. This is called
        for you on the controller itself. Update = True overwrites the existing Node data.
    updateNode(polyinterface.Node): Overwrites the existing node data here and on Polyglot.
    delNode(address): Deletes a Node from the self.nodes/polyglot and ISY. Address is the Node's Address
    longPoll(): Runs every longPoll seconds (set initially in the server.json or default 10 seconds)
    shortPoll(): Runs every shortPoll seconds (set initially in the server.json or default 30 seconds)
    query(): Queries and reports ALL drivers for ALL nodes to the ISY.
    getDriver('ST'): gets the current value from Polyglot for driver 'ST' returns a STRING, cast as needed
    runForever(): Easy way to run forever without maxing your CPU or doing some silly 'time.sleep' nonsense
                  this joins the underlying queue query thread and just waits for it to terminate
                  which never happens.
    """
    def __init__(self, polyglot):
        """
        Optional.
        Super runs all the parent class necessities. You do NOT have
        to override the __init__ method, but if you do, you MUST call super.
        """
        self.ready = False
        self.discover_thread = None
        self.serverdata = get_server_data(LOGGER)
        self.l_info('init','Initializing VERSION=%s' % (self.serverdata['version']))
        super(wtController, self).__init__(polyglot)
        self.name = 'WirelessTagsController'
        self.address = 'wtcontroller'
        self.primary = self.address


    def start(self):
        """
        Optional.
        Polyglot v2 Interface startup done. Here is where you start your integration.
        This will run, once the NodeServer connects to Polyglot and gets it's config.
        In this example I am calling a discovery method. While this is optional,
        this is where you should start. No need to Super this method, the parent
        version does nothing.
        """
        self.l_info('start','WirelessSensorTags Polyglot...')
        self.load_params()
        self.wtServer = wtServer(LOGGER,self.client_id,self.client_secret,self.get_handler,self.oauth2_code)
        try:
            self.wtServer.start()
        except KeyboardInterrupt:
            # TODO: Should we set a flag so poll can just restart the server, instead of exiting?
            logger.info('Exiting from keyboard interupt')
            sys.exit()
        self.setDriver('GV1', self.serverdata['version_major'])
        self.setDriver('GV2', self.serverdata['version_minor'])
        self.debug_mode     = self.getDriver('GV5')
        # Short Poll
        val = self.getDriver('GV6')
        self.l_debug("start","shortPoll={0} GV6={1}".format(self.polyConfig['shortPoll'],val))
        if val is None or int(val) == 0:
            val = self.polyConfig['shortPoll']
            self.setDriver('GV6',val)
        else:
            self.polyConfig['shortPoll'] = int(val)
        self.short_poll = val
        # Long Poll
        val = self.getDriver('GV7')
        self.l_debug("start","longPoll={0} GV7={1}".format(self.polyConfig['longPoll'],val))
        if val is None or int(val) == 0:
            val = self.polyConfig['longPoll']
            self.setDriver('GV7',val)
        else:
            self.polyConfig['longPoll'] = int(val)
        self.long_poll = val
        if self.wtServer.st:
            self.set_port(self.wtServer.listen_port,True)
        else:
            self.set_port(-1)
        self.save_params()
        self.check_profile()
        self.add_existing_tag_managers()
        self.query()
        self.ready = True
        self.l_info('start','done')

    def check_profile(self):
        self.profile_info = get_profile_info(LOGGER)
        # Set Default profile version if not Found
        cdata = deepcopy(self.polyConfig['customData'])
        self.l_info('check_profile','profile_info={0} customData={1}'.format(self.profile_info,cdata))
        if not 'profile_info' in cdata:
            cdata['profile_info'] = { 'version': 0 }
        if self.profile_info['version'] == cdata['profile_info']['version']:
            self.update_profile = False
        else:
            self.update_profile = True
            self.poly.installprofile()
        self.l_info('check_profile','update_profile={}'.format(self.update_profile))
        cdata['profile_info'] = self.profile_info
        self.saveCustomData(cdata)

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
        # Call short poll on the tags managers
        for address in self.nodes:
            if self.nodes[address].id == 'wTagManager':
                self.nodes[address].shortPoll()


    def longPoll(self):
        """
        Optional.
        This runs every 30 seconds. You would probably update your nodes either here
        or shortPoll. No need to Super this method the parent version does nothing.
        The timer can be overriden in the server.json.
        """
        self.l_debug('longPoll','ready={}'.format(self.ready))
        if not self.ready: return False
        # For now just pinging the serverto make sure it's alive
        self.is_signed_in()
        if not self.comm: return self.comm
        # Call long poll on the tags managers
        for address in self.nodes:
            if self.nodes[address].id == 'wTagManager':
                self.nodes[address].longPoll()

    def query(self):
        """
        Optional.
        By default a query to the control node reports the FULL driver set for ALL
        nodes back to ISY. If you override this method you will need to Super or
        issue a reportDrivers() to each node manually.
        """
        if not self.authorized('query') : return False
        self.is_signed_in()
        self.reportDrivers;
        # Don't do this on initial startup!
        #for node in self.nodes:
            #self.nodes[node].reportDrivers()

    def add_existing_tag_managers(self):
        """
        Called on startup to add the tags from the config
        We can't rely on discover at startup in case the server is down, we need to add the ones we know about.
        """
        for address in self.controller._nodes:
            node = self.controller._nodes[address]
            if nodedef in node:
                if node[nodedef] == 'wTagManager':
                    self.l_info('add_existing_tag_managers','node={0} update={1}'.format(node,self.update_profile))
                    self.addNode(wTagManager(self, address, node['name'], address.upper(), node_data=node),update=self.update_profile)
            else:
                self.l_error('add_existing_tag_managers','node has no {0}? node={1}'.format(nodedef,node))

    def discover(self, *args, **kwargs):
        """
        Start the discover in a thread so we don't cause timeouts :(
        """
        self.discover_thread = Thread(target=self._discover)
        self.discover_thread.start()

    def _discover(self):
        """
        Example
        Do discovery here. Does not have to be called discovery. Called from example
        controller start method and from DISCOVER command recieved from ISY as an exmaple.
        """
        if not self.authorized('discover') : return False
        self.set_auth(True)
        self.save_params()
        mgd = self.get_tag_managers()
        if not 'macs' in self.polyConfig['customData']:
            self.polyConfig['customData']['macs'] = dict()
        if mgd['st']:
            for mgr in mgd['result']:
                self.l_debug("discover","TagManager={0}".format(mgr))
                address = mgr['mac'].lower()
                node = self.get_node(address)
                if node is None:
                    self.addNode(wTagManager(self, address, mgr['name'], mgr['mac'], do_discover=True))
                else:
                    self.l_info('discover','Running discover on {0}'.format(node))
                    node.discover(thread=False)

    def delete(self):
        """
        Example
        This is sent by Polyglot upon deletion of the NodeServer. If the process is
        co-resident and controlled by Polyglot, it will be terminiated within 5 seconds
        of receiving this message.
        """
        LOGGER.info('Oh God I\'m being deleted. Nooooooooooooooooooooooooooooooooooooooooo.')

    def stop(self):
        LOGGER.debug('NodeServer stopped.')

    def set_all_logs(self,level):
        LOGGER.setLevel(level)
        logging.getLogger('requests').setLevel(level)
        logging.getLogger('urllib3').setLevel(level)

    """
    This handle's all the 'get's from the tag URL calling.
    """
    def get_handler(self,command,params):
        self.l_debug('get_handler','processing command={0} params={1}'.format(command,params))
        if command == '/code':
            return self.set_oauth2(params['oauth2_code'])
        node = None
        if not 'tagid' in params:
            self.l_error('get_handler','tagid not in params? command={0} params={1}'.format(command,params))
            return False
        if not 'tmgr_mac' in params:
            self.l_error('get_handler','tmgr_mac not in params? command={0} params={1}'.format(command,params))
            return False
        for address in self.nodes:
            tnode = self.nodes[address]
            if hasattr(tnode,'tag_id') and int(tnode.tag_id) == int(params['tagid']) and tnode.primary_n.mac == params['tmgr_mac']:
                node = self.nodes[address]
        if node is None:
            self.l_error('get_handler',"Did not find node for tag manager '{0}' with id '{1}'".format(params['tmgr_mac'],params['tagid']))
            for address in self.nodes:
                tnode = self.nodes[address]
                if hasattr(tnode,'tag_id'):
                    self.l_debug('get_handler',' tmgr_mac={0} tagid={1}'.format(tnode.primary_n.mac,tnode.tag_id))
            return False
        return node.get_handler(command,params)

    """
     Misc funcs
    """
    def authorized(self,name):
        if self.wtServer.oauth2_code == False:
            self.set_auth(False)
            self.l_error('authorized',"Not able to {0} oauth2_code={1}".format(name,self.wtServer.oauth2_code))
            return False
        return True

    def is_signed_in(self):
        if not self.authorized('is_signed_in'):
            return False
        mgd = self.wtServer.IsSignedIn()
        if 'result' in mgd:
            st = mgd['result']
            self.set_comm(True)
        else:
            st = False
            # Didn't even get a response.
            self.set_comm(st)
        self.l_debug('is_signed_in','{0}'.format(st))
        self.set_auth(st)
        return st

    def get_tag_managers(self):
        if not self.authorized('get_tag_managers') : return { 'st': False }
        mgd = self.wtServer.GetTagManagers()
        self.set_comm(mgd['st'])
        return mgd

    def get_node(self,address):
        """
        Returns a node that already exists in the controller.
        Use self.poly.getNode to look for node's in config, not this method.
        """
        self.l_info('get_node',"adress={0}".format(address))
        for node in self.nodes:
            #self.l_debug('get_node',"node={0}".format(node))
            if self.nodes[node].address == address:
                return self.nodes[node]
        return None

    def load_params(self):
        if 'oauth2_code' in self.polyConfig['customParams']:
            self.set_oauth2(self.polyConfig['customParams']['oauth2_code'],save=False)
        else:
            self.l_error('load_params',"oauth2_code not defined in customParams, please authorize")
            self.set_oauth2(False)
            st = False

    def save_params(self):
        # Make sure latest code is in the params
        self.addCustomParam({'oauth2_code': self.oauth2_code})
        self.removeNoticesAll()
        if self.oauth2_code == False:
            if hasattr(self,'wtServer'):
                self.addNotice('Click <a target="_blank" href="{0}&redirect_uri={1}/code">Authorize</a> to link your CAO Wireless Sensor Tags account'.format(self.auth_url,self.wtServer.url))
            else:
                self.addNotice("No Athorization, and no REST Server running, this should not be possible!")

    def set_url_config(self):
        # TODO: Should loop over tag managers, and call set_url_config on the tag manager
        for address in self.nodes:
            self.l_debug('set_url_config',"id={}".format(self.nodes[address].id))
            if not (self.nodes[address].id == 'wtController' or self.nodes[address].id == 'wTagManager'):
                self.nodes[address].set_url_config()

    def l_info(self, name, string):
        LOGGER.info("%s:%s: %s" %  (self.id,name,string))

    def l_error(self, name, string):
        LOGGER.error("%s:%s: %s" % (self.id,name,string))

    def l_warning(self, name, string):
        LOGGER.warning("%s:%s: %s" % (self.id,name,string))

    def l_debug(self, name, string):
        LOGGER.debug("%s:%s: %s" % (self.id,name,string))

    """
    Set Functions
    """
    def set_oauth2(self,value,save=True):
        if not hasattr(self,"oauth2_code"): self.oauth2_code = False
        if self.oauth2_code != value:
            self.oauth2_code = value
            if (save):
                self.save_params()
                self.discover()
        if value is False:
            self.set_auth(False)
            self.set_comm(False)
        else:
            self.set_auth(True)
            self.set_comm(True)
        return True


    def set_debug_mode(self,level):
        if level is None:
            level = 0
        else:
            level = int(level)
        self.debug_mode = level
        self.setDriver('GV5', level)
        # 0=All 10=Debug are the same because 0 (NOTSET) doesn't show everything.
        if level == 0 or level == 10:
            self.set_all_logs(logging.DEBUG)
        elif level == 20:
            self.set_all_logs(logging.INFO)
        elif level == 30:
            self.set_all_logs(logging.WARNING)
        elif level == 40:
            self.set_all_logs(logging.ERROR)
        elif level == 50:
            self.set_all_logs(logging.CRITICAL)
        else:
            self.l_error("set_debug_level","Unknown level {0}".format(level))

    def set_short_poll(self,val):
        if val is None or int(val) < 5:
            val = 5
        self.short_poll = int(val)
        self.setDriver('GV6', self.short_poll)
        self.polyConfig['shortPoll'] = val

    def set_long_poll(self,val):
        if val is None or int(val) < 60:
            val = 60
        self.long_poll = int(val)
        self.setDriver('GV7', self.long_poll)
        self.polyConfig['longPoll'] = val


    def set_auth(self,value,force=False):
        if not force and hasattr(self,"auth") and self.auth == value:
            return True
        self.auth = value
        if value:
            self.setDriver('GV3', 1)
        else:
            self.setDriver('GV3', 0)

    def set_comm(self,value,force=False):
        if not force and hasattr(self,"comm") and self.comm == value:
            return True
        self.comm = value
        if value:
            self.setDriver('GV4', 1)
        else:
            self.setDriver('GV4', 0)

    def set_port(self,value,force=False):
        if not force and hasattr(self,"port") and self.port == value:
            return True
        self.port = value
        self.setDriver('GV8', value)

    """
    Command Functions
    """
    def cmd_set_debug_mode(self,command):
        val = command.get('value')
        self.l_info("cmd_set_debug_mode",val)
        self.set_debug_mode(val)

    def cmd_set_short_poll(self,command):
        val = command.get('value')
        self.l_info("cmd_set_short_poll",val)
        self.set_short_poll(val)

    def cmd_set_long_poll(self,command):
        val = int(command.get('value'))
        self.l_info("cmd_set_long_poll",val)
        self.set_long_poll(val)


    def cmd_install_profile(self,command):
        self.l_info("cmd_install_profile","installing...")
        self.poly.installprofile()

    """
    Node Definitions
    """
    id = 'wtController'
    commands = {
        'SET_DM': cmd_set_debug_mode,
        'SET_SHORTPOLL': cmd_set_short_poll,
        'SET_LONGPOLL':  cmd_set_long_poll,
        'QUERY': query,
        'DISCOVER': discover,
        'INSTALL_PROFILE': cmd_install_profile
    }
    drivers = [
        {'driver': 'ST',  'value': 0, 'uom': 2},
        {'driver': 'GV1', 'value': 0, 'uom': 56}, # vmaj: Version Major
        {'driver': 'GV2', 'value': 0, 'uom': 56}, # vmin: Version Minor
        {'driver': 'GV3', 'value': 0, 'uom': 2},  # auth: Authorized (we have valid oauth2 token)
        {'driver': 'GV4', 'value': 0, 'uom': 2},  # comm: Communicating
        {'driver': 'GV5', 'value': 0, 'uom': 25}, # Debug (Log) Mode
        {'driver': 'GV6', 'value': 5, 'uom': 56}, # shortpoll
        {'driver': 'GV7', 'value': 60, 'uom': 56},  # longpoll
        {'driver': 'GV8', 'value': 0, 'uom': 56} # port: REST Server Listen port
    ]
