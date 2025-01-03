
from udi_interface import Node,LOGGER,Custom,LOG_HANDLER
import sys,time,logging,json
from threading import Thread,Lock
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
        LOGGER.info('WirelessTag Controller: Initializing')
        super(Controller, self).__init__(poly, primary, address, name)
        # These start in threads cause they take a while
        self.ready = False
        self.oauth2_code = False
        self.discover_thread = None
        self.wtServer = False
        self.first_run = True
        self.tag_managers_by_mac = dict()
        self.warnings = dict()
        # TODO: Always true, should read from customData and check profile version like PG2 version did?
        self.update_profile = True
        self.type = self.id
        self.queue_lock = Lock() # Lock for syncronizing acress threads
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
        poly.subscribe(poly.CUSTOMDATA,        self.handler_data)
        #poly.subscribe(poly.CUSTOMTYPEDPARAMS, self.handler_typed_params)
        #poly.subscribe(poly.CUSTOMTYPEDDATA,   self.handler_typed_data)
        poly.subscribe(poly.LOGLEVEL,          self.handler_log_level)
        poly.subscribe(poly.CONFIG,            self.handler_config)
        poly.subscribe(poly.CONFIGDONE,        self.handler_config_done)
        poly.subscribe(poly.ADDNODEDONE,       self.node_dequeue)
        self.client_id              = None
        self.client_secret          = None
        self.handler_start_st       = None
        self.handler_config_done_st = None
        self.handler_params_st      = None
        self.handler_data_st        = None
        self.handler_nsdata_st      = None
        poly.subscribe(poly.CUSTOMNS,          self.handler_nsdata)
        poly.ready()
        poly.addNode(self, conn_status="ST")

    '''
    node_queue() and wait_for_node_event() create a simple way to wait
    for a node to be created.  The nodeAdd() API call is asynchronous and
    will return before the node is fully created. Using this, we can wait
    until it is fully created before we try to use it.
    '''
    def node_dequeue(self, data):
        LOGGER.debug(f'locking: data={data}')
        self.queue_lock.acquire()
        if self.n_queue.count(data['address']) > 0:
            self.n_queue.remove(data['address'])
        self.queue_lock.release()
        LOGGER.debug('lock released')

    def add_node(self,node):
        LOGGER.debug(f'adding node node={node.address} {node.name}')
        self.queue_lock.acquire()
        ret = False

        # See if it's already being added or exists
        if self.n_queue.count(node.address) > 0:
            LOGGER.error(f"Already waiting for node {node.address} name={node.name} to be added.")
            self.queue_lock.release()
        else:
            ret = self.poly.getNode(node.address)
            if ret is not None:
                # This happens when discover is run, so not an error
                LOGGER.debug(f"Node {node.address} name={node.name} already exists.")
                self.queue_lock.release()
            else:
                # Queue it up and add it
                self.n_queue.append(node.address)
                self.queue_lock.release()
                ret = self.poly.addNode(node)
                LOGGER.debug(f'got {ret}')
                if ret is None:
                    self.node_dequeue({'address': node.address})
                    LOGGER.error(r'Failed to add {node.address} name={node.name}')
                else:
                    cnt = 0
                    while self.n_queue.count(node.address) > 0:
                        cnt += 1
                       # Warn every 5 seconds, and die after 60?
                        if cnt % 50 == 0:
                            LOGGER.warning(f"Waiting for {node.address} add to complete. Queued for {cnt / 10} seconds...")
                        if cnt > 6000:
                            LOGGER.error(f"TIMEOUT waiting for {node.address} add to complete...")
                            return False
                        time.sleep(0.1)
                        # See if we need to check for node name changes
                        cname = self.poly.getNodeNameFromDb(node.address)
                        if cname is not None and cname != node.name:
                            self.rename_node(node,cname)

        LOGGER.debug(f'returning {ret}')
        return ret

    def rename_node(self,node,cname):
        LOGGER.debug(f"enter: node.name={node.name} cname={cname}")
        ret = False
        if self.change_node_names:
            LOGGER.warning(f"Existing node name '{node.name}' for {node.address} does not match requested name '{cname}', changing to match")
            try:
                self.poly.renameNode(node.address,cname)
            except:
                LOGGER.error(f'renameNode error, which is a known issue with PG3x Version <= 3.2.7', exc_info=True)
                ret = True
            if node.name in self.warnings:
                del self.warnings[node.name]
        else:
            if not node.name in self.warnings:
                LOGGER.warning(f"Existing node name '{cname}' for {node.address} does not match requested name '{node.name}', NOT changing to match. Set change_node_names=true to enable")
                self.warnings[node.name] = True
        LOGGER.debug(f'returning {ret}')
        return ret

    def delete_node(self,node):
        if self.delete_nodes:
            self.del_node(node)
        else:
            LOGGER.warning(f"Not deleting node set Configuration to true will make it happen on next query")

    def del_node(self,node):
        LOGGER.warning(f'deleting node node={node.address} {node.name}')
        if self.poly.getNode(node.address) is None:
            LOGGER.error(f'Node {node.address} does not exist?')
        else:
            self.poly.delNode(node.address)

    def handler_start(self):
        LOGGER.info('enter')
        self.poly.Notices.clear()
        # Current interface is not updated profile as needed, so just do it always :(
        LOGGER.debug("updating profile...")
        self.poly.updateProfile()
        # Start a heartbeat right away
        self.hb = 0
        self.heartbeat()

        LOGGER.info(f"Started WirelessTag NodeServer {self.poly.serverdata['version']}")
        cnt = 10
        while (self.handler_params_st is None or self.handler_config_done_st is None
            or self.handler_nsdata_st is None or self.handler_data_st is None) and cnt > 0:
            LOGGER.warning(f'Waiting for all to be loaded config={self.handler_config_done_st} params={self.handler_params_st} data={self.handler_data_st} nsdata={self.handler_nsdata_st}... cnt={cnt}')
            time.sleep(1)
            cnt -= 1
        if cnt == 0:
            LOGGER.error(f'Timed out waiting for all to be loaded config={self.handler_config_done_st} params={self.handler_params_st} data={self.handler_data_st} nsdata={self.handler_nsdata_st}... cnt={cnt}')
            exit
        elif cnt < 10:
            # Tell them it's all ok since above warning can cause confusion.
            LOGGER.warning('All config data loaded, continuing...')
        #
        # Always need to start the REST server
        #
        self.rest_start()
        #
        # All good?
        #
        if self.wtServer is False:
            self.Notices['auth'] = f"REST Server ({self.wtServer}) not running. check Log for ERROR"
        elif self.client_id is None:
            self.Notices['auth'] = "Unable to authorize, no client id returned in Node Server Data.  Check Log for ERROR"
        elif self.oauth2_code is False:
            self.auth_url      = "https://www.mytaglist.com/oauth2/authorize.aspx?client_id={0}".format(self.client_id)
            self.Notices['auth'] = 'Click <a target="_blank" href="{0}&redirect_uri={1}/code">Authorize</a> to link your CAO Wireless Sensor Tags account'.format(self.auth_url,self.wtServer.url)
        else:
            self.Notices.delete('auth')

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

        self.add_existing_tag_managers()
        self.query()
        self.ready = True
        LOGGER.info('done')

    def handler_config(self,data):
        LOGGER.info(f'enter data={data}')
        self.handler_config_st = True
        LOGGER.info('done')

    def handler_config_done(self):
        LOGGER.info('enter')
        self.handler_config_done_st = True
        LOGGER.info('done')

    def handler_poll(self, polltype):
        if polltype == 'longPoll':
            self.longPoll()
        elif polltype == 'shortPoll':
            self.shortPoll()

    def shortPoll(self):
        if self.discover_thread is not None:
            if self.discover_thread.is_alive():
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
        self.heartbeat()
        # For now just pinging the server to make sure it's alive
        self.is_signed_in()
        if not self.comm: return self.comm
        self.set_tag_managers_st()
        # Call long poll on the tags managers
        for node in self.poly.nodes():
            if node.id == 'wTagManager':
                node.longPoll()

    def heartbeat(self):
        LOGGER.debug('hb={}'.format(self.hb))
        if self.hb == 0:
            self.reportCmd("DON",2)
            self.hb = 1
        else:
            self.reportCmd("DOF",2)
            self.hb = 0

    def set_tag_managers_st(self):
       # Check tag manager online status?
        mgd = self.get_tag_managers()
        LOGGER.debug("TagManagers={0}".format(mgd))
        for node in self.poly.nodes():
            if node.id == 'wTagManager':
                st = False
                # Find this one in the list
                if mgd['st']:
                    for mgr in mgd['data']:
                        if node.address == mgr['mac'].lower():
                            st = mgr['online']
                node.set_st(st)

    def query(self):
        if not self.authorized('query') : return False
        self.is_signed_in()
        self.set_tag_managers_st()
        self.reportDrivers()

    def query_all(self,cmd=None):
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
        self.set_tag_managers_st()

    def discover(self, do_discover=True):
        """
        Start the discover in a thread so we don't cause timeouts :(
        """
        self.discover_thread = Thread(target=self._discover(do_discover))
        self.discover_thread.start()

    def _discover(self,do_discover=True):
        """
        Example
        Do discovery here. Does not have to be called discovery. Called from example
        controller start method and from DISCOVER command recieved from ISY as an exmaple.
        """
        if not self.authorized('discover') : return False
        self.set_auth(True)
        if not 'macs' in self.Data:
            self.Data['macs'] = dict()
        #
        # Get the tag managers
        #
        mgd = self.get_tag_managers()
        if not mgd['st']: return False
        mgrs = mgd['data']
        #
        # Do cleanup first
        #
        #LOGGER.warning("delete_nodes={0}".format(self.delete_nodes))
        #if self.delete_nodes:
        #    LOGGER.warning("Checking for nodes to delete...")
        #    macs = dict()
        #    for mgr in mgrs:
        #        macs[mgr['mac'].lower()] = mgr
        #    # First look for Tag Managers that no longer exist
        #    for node in self.poly.getNodesFromDb():
        #        if 'nodeDefId' in node:
        #            if node['nodeDefId'] == 'wTagManager' and not node['address'] in macs:
        #                LOGGER.warning("Need to delete TagManager node name {0} address {1}".format(node.name,node.address))
        #
        # Add what we found
        #
        for mgr in mgrs:
            LOGGER.debug("TagManager={0}".format(mgr))
            address = mgr['mac'].lower()
            # See if it already exists
            node = self.get_node(address)
            if node is None:
                node = self.add_node(TagManager(self, address, mgr['name'], mgr['mac'], online=mgr['online'], do_discover=do_discover))
            else:
                node.set_st(mgr['online'])
                # See if we need to check for node name changes
                if mgr['name'] != node.name:
                    self.rename_node(node,mgr['name'])
                LOGGER.info('Running discover on {0}'.format(node))
                node.discover(thread=False)

    def delete(self):
        LOGGER.info('Oh God I\'m being deleted. Nooooooooooooooooooooooooooooooooooooooooo.')

    def handler_stop(self):
        LOGGER.debug('NodeServer stopping')
        self.rest_stop()
        LOGGER.debug('NodeServer stopped')
        self.poly.stop()

    def rest_start(self):

        # use previously saved nsdata if necessary, in case of network glitch.
        if self.client_id is None:
            if 'client_id' in self.Data:
                LOGGER.warning("Using previously saved client_id...")
                self.client_id = self.Data['client_id']
            elif 'client_id' in self.Params:
                LOGGER.warning("Using Params client_id...")
                self.client_id = self.Params['client_id']
        if self.client_secret is None:
            if 'client_secret' in self.Data:
                LOGGER.warning("Using previously saved client_secret...")
                self.client_secret = self.Data['client_secret']
            elif 'client_secret' in self.Params:
                LOGGER.warning("Using Params client_secret...")
                self.client_secret = self.Params['client_secret']

        if self.client_id is None or self.client_secret is None:
            msg = f"Unable to start server, no NSDATA returned client_id={self.client_id} client_secret={self.client_secret}"
            LOGGER.error(msg)
            self.Notices['rest_start'] = msg
            return False
        self.Notices.delete('rest_start')

        # Save to data if necessary
        if not 'client_id' in self.Data or self.Data['client_id'] != self.client_id:
            self.Data['client_id'] = self.client_id
        if not 'client_secret' in self.Data or self.Data['client_secret'] != self.client_secret:
            self.Data['client_secret'] = self.client_secret

        #
        # Start it up...
        #
        self.wtServer = wtServer(LOGGER,self.client_id,self.client_secret,self.get_handler,self.oauth2_code)
        try:
            self.wtServer.start()
        except:
            LOGGER.error('Failed to start REST Server...')
        if self.wtServer.st:
            self.set_port(self.wtServer.listen_port,True)
        else:
            self.set_port(-1)
        return

    def rest_stop(self):
        if self.wtServer is not False and self.wtServer.st:
            self.wtServer.stop()

    def rest_restart(self):
        self.rest_stop()
        self.rest_start()

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
            if node.type == 'wTag' and int(node.tag_id) == int(params['tagid']) and node.primary_n.mac == params['tmgr_mac']:
                LOGGER.info(f"Update for Tag {node.name} {node.address} (node.tagid={node.tag_id} node.pmac={node.primary_n.mac})")
                tnode = node
        if tnode is None:
            LOGGER.error("Did not find node for tag manager '{0}' with id '{1}'".format(params['tmgr_mac'],params['tagid']))
            for node in self.poly.nodes():
                if node.id.type == 'wTag':
                    LOGGER.debug(' tmgr_mac={0} tagid={1}'.format(node.primary_n.mac,node.tag_id))
            return False
        #LOGGER.debug('calling node={0} command={1} params={2}'.format(node.address,command,params))
        return tnode.get_handler(command,params)

    """
     Misc funcs
    """
    def authorized(self,name):
        if self.wtServer is False or self.wtServer.oauth2_code is False:
            self.set_auth(False)
            msg = f"Not able to {name}"
            if self.wtServer is False:
                msg += " Server is not running"
            else:
                msg += f" oauth2_code={self.wtServer.oauth2_code}"
            return False
        return True

    def is_signed_in(self):
        if not self.authorized('is_signed_in'):
            return False
        mgd = self.wtServer.IsSignedIn()
        if 'data' in mgd:
            st = mgd['data']
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

        if key != 'nsdata':
            return

        LOGGER.info('Got nsdata update type={} {}'.format(type(data),data))

        self.Notices.delete('nsdata')
        if type(data) == str:
            LOGGER.error(f"NSDATA is a string?  Are you running a local copy? data={data}")
            self.Notices['nsdata'] = "NSDATA is a string?  Are you running a local copy?"
            self.handler_nsdata_st = False
            return

        try:
            #jdata = json.loads(data)
            self.client_id     = data['client_id']
            self.client_secret = data['client_secret']
        except:
            LOGGER.error(f'failed to parse nsdata={data}',exc_info=True)
            self.handler_nsdata_st = False
            return
        self.handler_nsdata_st = True

    def handler_data(self,data):
        LOGGER.debug(f'enter: Loading data {data}')
        self.Data.load(data)
        self.handler_data_st = True

    def handler_params(self,params):
        LOGGER.debug(f'enter: Loading params {params}')
        self.Params.load(params)
        self.poly.Notices.clear()
        """
        Check all user params are available and valid
        """
        # Assume it's good unless it's not
        st = True
        #
        # Make sure params exist
        #
        defaults = {
            "change_node_names": "false",
            #"delete_nodes": "false",
        }
        for param in defaults:
            if params is None or not param in params:
                self.Params[param] = defaults[param]
                return
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
            st    = False
            self.set_auth(False)
            self.set_comm(False)
        else:
            self.set_auth(True)
            self.set_comm(True)
        self.oauth2_code = value
        LOGGER.debug(f'oauth2_code={self.oauth2_code}')

        # If it's a config change, then need to restart the REST server
        # because the auth2_code must have changed.
        if not self.first_run:
            self.rest_restart()
        self.first_run = True

        #
        # Change Node Names
        #
        #if self.Params['delete_nodes'] == "true":
        #    self.delete_nodes = True
        #else:
        #    self.delete_nodes = False

        #
        # Change Node Names
        #
        if self.Params['change_node_names'] == "true":
            self.change_node_names = True
        else:
            self.change_node_names = False

        self.handler_params_st = st
        LOGGER.debug(f'exit: st={st}')

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
        LOGGER.warning("updating...")
        self.poly.updateProfile()

    """
    Node Definitions
    """
    id = 'wtController'
    commands = {
        'SET_SHORTPOLL': cmd_set_short_poll,
        'SET_LONGPOLL':  cmd_set_long_poll,
        'QUERY': query,
        'QUERY_ALL': query_all,
        'DISCOVER': discover,
        'INSTALL_PROFILE': cmd_install_profile
    }
    drivers = [
        {'driver': 'ST',  'value': 1, 'uom': 56},
        {'driver': 'GV3', 'value': 0, 'uom': 2},  # auth: Authorized (we have valid oauth2 token)
        {'driver': 'GV4', 'value': 0, 'uom': 2},  # comm: Communicating
        {'driver': 'GV6', 'value': 5, 'uom': 56}, # shortpoll
        {'driver': 'GV7', 'value': 60, 'uom': 56},  # longpoll
        {'driver': 'GV8', 'value': 0, 'uom': 56} # port: REST Server Listen port
    ]
