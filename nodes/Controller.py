
from udi_interface import Node,LOGGER,Custom,LOG_HANDLER
import sys,time,logging,json
from threading import Thread
from copy import deepcopy

from nodes import TagManager
from wtServer import wtServer
from wt_funcs import get_server_data,get_valid_node_name,get_profile_info

# old
nodedef = 'node_def_id'
# new
#nodedef = 'nodedef'

class Controller(Node):

    def __init__(self, poly, primary, address, name):
        LOGGER.info('HarmonyController: Initializing')
        super(Controller, self).__init__(poly, primary, address, name)
        # These start in threads cause they take a while
        self.ready = False
        self.oauth2_code = False
        self.discover_thread = None
        self.wtServer = False
        # TODO: Always true, should read from customData and check profile version like PG2 version did?
        self.update_profile = True
        self.n_queue = []
        self.Notices         = Custom(poly, 'notices')
        self.Data            = Custom(poly, 'customdata')
        self.Params          = Custom(poly, 'customparams')
        self.Notices         = Custom(poly, 'notices')
        #self.TypedParameters = Custom(poly, 'customtypedparams')
        #self.TypedData       = Custom(poly, 'customtypeddata')
        poly.subscribe(poly.START,             self.handler_start, address) 
        poly.subscribe(poly.POLL,              self.handler_poll)
        poly.subscribe(poly.DISCOVER,          self.discover)
        poly.subscribe(poly.STOP,              self.handler_stop)
        poly.subscribe(poly.CUSTOMPARAMS,      self.handler_params)
        self.config_st = False
        #poly.subscribe(poly.CUSTOMDATA,        self.handler_data)
        #poly.subscribe(poly.CUSTOMTYPEDPARAMS, self.handler_typed_params)
        #poly.subscribe(poly.CUSTOMTYPEDDATA,   self.handler_typed_data)
        poly.subscribe(poly.LOGLEVEL,          self.handler_log_level)
        poly.subscribe(poly.CONFIGDONE,        self.handler_config_done)
        poly.subscribe(poly.ADDNODEDONE,       self.node_queue)
        self.client_secret = None
        self.client_id = None
        self.got_nsdata = False
        poly.subscribe(poly.CUSTOMNS,          self.handler_nsdata)
        poly.ready()
        poly.addNode(self, conn_status="ST")

    '''
    node_queue() and wait_for_node_event() create a simple way to wait
    for a node to be created.  The nodeAdd() API call is asynchronous and
    will return before the node is fully created. Using this, we can wait
    until it is fully created before we try to use it.
    '''
    def node_queue(self, data):
        self.n_queue.append(data['address'])

    def wait_for_node_done(self):
        while len(self.n_queue) == 0:
            time.sleep(0.1)
        self.n_queue.pop()

    def add_node(self,node):
        anode = self.poly.addNode(node)
        LOGGER.debug(f'got {anode}')
        self.wait_for_node_done()
        if anode is None:
            LOGGER.error('Failed to add node address')
        return anode

    def handler_start(self):
        LOGGER.info('enter')
        self.poly.Notices.clear()
        #serverdata = self.poly.get_server_data(check_profile=False)
        LOGGER.info(f"Started WirelessTag NodeServer {self.poly.serverdata['version']}")
        #
        # Always need to start the REST server
        #
        self.wtServer = wtServer(LOGGER,self.client_id,self.client_secret,self.get_handler,self.oauth2_code)
        try:
            self.wtServer.start()
        except KeyboardInterrupt:
            # TODO: Should we set a flag so poll can just restart the server, instead of exiting?
            logger.info('Exiting from keyboard interupt')
            sys.exit()
        if self.wtServer.st:
            self.set_port(self.wtServer.listen_port,True)
        else:
            self.set_port(-1)
        #self.setDriver('GV1', self.serverdata['version_major'])
        #self.setDriver('GV2', self.serverdata['version_minor'])
        # TODO: Get working again: Short Poll
        #val = self.getDriver('GV6')
        #LOGGER.debug("shortPoll={0} GV6={1}".format(self.polyConfig['shortPoll'],val))
        #if val is None or int(val) == 0:
        #    val = self.polyConfig['shortPoll']
        #self.set_short_poll(val)
        # Long Poll
        #val = self.getDriver('GV7')
        #LOGGER.debug("longPoll={0} GV7={1}".format(self.polyConfig['longPoll'],val))
        #if val is None or int(val) == 0:
        #    val = self.polyConfig['longPoll']
        #self.set_long_poll(val)
        self.hb = 0
        self.heartbeat()
        self.add_existing_tag_managers()
        self.query()
        self.ready = True
        LOGGER.info('done')

    def handler_config_done(self):
        LOGGER.info('enter')
        LOGGER.info('done')

    def handler_poll(self, polltype):
        if polltype == 'longPoll':
            self.longPoll()
        elif polltype == 'shortPoll':
            self.shortPoll()

    def shortPoll(self):
        if self.discover_thread is not None:
            if self.discover_thread.isAlive():
                LOGGER.debug('discover thread still running...')
            else:
                LOGGER.debug('discover thread is done...')
                self.discover_thread = None
        # Call short poll on the tags managers
        for node in self.poly.nodes():
            if node.id == 'wTagManager':
                node.shortPoll()

    def longPoll(self):
        LOGGER.debug('ready={}'.format(self.ready))
        if not self.ready: return False
        # For now just pinging the server to make sure it's alive
        self.is_signed_in()
        if not self.comm: return self.comm
        # Call long poll on the tags managers
        for node in self.poly.nodes():
            if node.id == 'wTagManager':
                node.longPoll()
        self.heartbeat()

    def heartbeat(self):
        LOGGER.debug('hb={}'.format(self.hb))
        if self.hb == 0:
            self.reportCmd("DON",2)
            self.hb = 1
        else:
            self.reportCmd("DOF",2)
            self.hb = 0

    def query(self):
        if not self.authorized('query') : return False
        self.is_signed_in()
        self.reportDrivers();
        # Don't do this on initial startup!
        for node in self.poly.nodes():
            node.reportDrivers()

    def add_existing_tag_managers(self):
        """
        Called on startup to add the tags from the config
        We can't rely on discover at startup in case the server is down, we need to add the ones we know about.
        """
        for node in self.poly.db_getNodeDrivers(''):
            if 'nodeDefId' in node:
                if node['nodeDefId'] == 'wTagManager':
                    LOGGER.info(f'node={node}')
                    address = node['address']
                    self.add_node(TagManager(self, address, node['name'], address.upper(), node_data=node))
            else:
                LOGGER.error('node has no {0}? node={1}'.format(nodedef,node))

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
        mgd = self.get_tag_managers()
        if not 'macs' in self.Data:
            self.Data['macs'] = dict()
        if mgd['st']:
            for mgr in mgd['result']:
                LOGGER.debug("TagManager={0}".format(mgr))
                address = mgr['mac'].lower()
                node = self.get_node(address)
                if node is None:
                    self.add_node(TagManager(self, address, mgr['name'], mgr['mac'], do_discover=True))
                else:
                    LOGGER.info('Running discover on {0}'.format(node))
                    node.discover(thread=False)

    def delete(self):
        LOGGER.info('Oh God I\'m being deleted. Nooooooooooooooooooooooooooooooooooooooooo.')

    def handler_stop(self):
        LOGGER.debug('NodeServer stopped.')

    """
    This handle's all the 'get's from the tag URL calling.
    """
    def get_handler(self,command,params):
        LOGGER.debug('processing command={0} params={1}'.format(command,params))
        if command == '/code':
            self.Params['oauth2_code'] = params['oauth2_code']
            self.discover()
            return
        tnode = None
        if not 'tagid' in params:
            LOGGER.error('tagid not in params? command={0} params={1}'.format(command,params))
            return False
        if not 'tmgr_mac' in params:
            LOGGER.error('tmgr_mac not in params? command={0} params={1}'.format(command,params))
            return False
        for node in self.poly.nodes():
            if hasattr(node,'tag_id') and int(node.tag_id) == int(params['tagid']) and node.primary_n.mac == params['tmgr_mac']:
                tnode = node
        if tnode is None:
            LOGGER.error("Did not find node for tag manager '{0}' with id '{1}'".format(params['tmgr_mac'],params['tagid']))
            for node in self.poly.nodes():
                if hasattr(node,'tag_id'):
                    LOGGER.debug(' tmgr_mac={0} tagid={1}'.format(node.primary_n.mac,node.tag_id))
            return False
        #LOGGER.debug('calling node={0} command={1} params={2}'.format(node.address,command,params))
        return node.get_handler(command,params)

    """
     Misc funcs
    """
    def authorized(self,name):
        if self.wtServer.oauth2_code == False:
            self.set_auth(False)
            LOGGER.error("Not able to {0} oauth2_code={1}".format(name,self.wtServer.oauth2_code))
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
        LOGGER.debug('{0}'.format(st))
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
        LOGGER.info("adress={0}".format(address))
        for node in self.poly.nodes():
            #LOGGER.debug("node={0}".format(node))
            if node.address == address:
                return node
        return None

    #def handler_data(self,data):
    #    LOGGER.debug('enter: Loading data')
    #    self.Data.load(data)
    #    LOGGER.debug(f'Data={self.Data}')

    def handler_nsdata(self, key, data):
        LOGGER.debug(f"key={key} data={data}")
        if 'nsdata' in key:
            LOGGER.info('Got nsdata update {}'.format(data))
            try:
                #jdata = json.loads(data)
                self.client_id     = data['client_id']
                self.client_secret = data['client_secret']
            except:
                LOGGER.error(f'failed to parse nsdata={data}',exc_info=True)
                self.client_id = None
                self.client_secret = None
                self.got_nsdata = False
                return
            self.got_nsdata = True

    def handler_params(self,params):
        LOGGER.debug(f'enter: Loading params {params}')
        self.Params.load(params)
        self.poly.Notices.clear()
        """
        Check all user params are available and valid
        """
        # Assume it's good unless it's not
        config_st = True
        #
        # Check for oauth2_code
        #
        if 'oauth2_code' in self.Params.keys():
            value = self.Params['oauth2_code']
        else:
            LOGGER.error(f"oauth2_code not defined, assuming False")
            value = False

        if value is False or value == "false" or value == "":
            value = False
            self.set_auth(False)
            self.set_comm(False)
        else:
            self.set_auth(True)
            self.set_comm(True)
        self.oauth2_code = value
        LOGGER.debug(f'oauth2_code={self.oauth2_code}')
        #
        # Wait for server to start up.
        #
        count = 10
        while self.wtServer is False and count > 0:
            LOGGER.warning("Waiting for REST Server {self.wtServer} to startup {count}...")
            time.sleep(1)
            count -= 1
        if self.wtServer is False:
            LOGGER.error(f"Timeout waiting for REST Server {self.wtServer} to startup")
        if self.client_id is None:
                self.Notices['authorize'] = "ERROR: Unable to authorize, no client id returned in Node Server Data.  Check Log for ERROR"
        else:
            if self.oauth2_code is False:
                if self.wtServer is not False:
                    self.auth_url      = "https://www.mytaglist.com/oauth2/authorize.aspx?client_id={0}".format(self.client_id)
                    self.Notices['authorize'] = 'Click <a target="_blank" href="{0}&redirect_uri={1}/code">Authorize</a> to link your CAO Wireless Sensor Tags account'.format(self.auth_url,self.wtServer.url)
                else:
                    self.Notices['authorize'] = "No Authorization, and no REST Server running, this should not be possible!"
        self.config_st = config_st
        LOGGER.debug(f'exit: config_st={config_st}')

    def set_url_config(self):
        # TODO: Should loop over tag managers, and call set_url_config on the tag manager
        for node in self.poly.nodes():
            LOGGER.debug("id={}".format(node.id))
            if not (node.id == 'wtController' or node.id == 'wTagManager'):
                node.set_url_config()

    def handler_log_level(self,level):
        LOGGER.info(f'enter: level={level}')
        if level['level'] < 10:
            LOGGER.info("Setting basic config to DEBUG...")
            LOG_HANDLER.set_basic_config(True,logging.DEBUG)
            slevel = logging.DEBUG
        else:
            LOGGER.info("Setting basic config to WARNING...")
            LOG_HANDLER.set_basic_config(True,logging.WARNING)
            slevel = logging.WARNING
        #logging.getLogger('requests').setLevel(slevel)
        #logging.getLogger('urllib3').setLevel(slevel)
        LOGGER.info(f'exit: slevel={slevel}')

    """
    Set Functions
    """
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

    def cmd_set_short_poll(self,command):
        val = command.get('value')
        LOGGER.info(val)
        self.set_short_poll(val)

    def cmd_set_long_poll(self,command):
        val = int(command.get('value'))
        LOGGER.info(val)
        self.set_long_poll(val)


    def cmd_install_profile(self,command):
        LOGGER.info("installing...")
        self.poly.installprofile()

    """
    Node Definitions
    """
    id = 'wtController'
    commands = {
        'SET_SHORTPOLL': cmd_set_short_poll,
        'SET_LONGPOLL':  cmd_set_long_poll,
        'QUERY': query,
        'DISCOVER': discover,
        'INSTALL_PROFILE': cmd_install_profile
    }
    drivers = [
        {'driver': 'ST',  'value': 1, 'uom': 2},
        {'driver': 'GV3', 'value': 0, 'uom': 2},  # auth: Authorized (we have valid oauth2 token)
        {'driver': 'GV4', 'value': 0, 'uom': 2},  # comm: Communicating
        {'driver': 'GV6', 'value': 5, 'uom': 56}, # shortpoll
        {'driver': 'GV7', 'value': 60, 'uom': 56},  # longpoll
        {'driver': 'GV8', 'value': 0, 'uom': 56} # port: REST Server Listen port
    ]