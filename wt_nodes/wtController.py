
import polyinterface
import sys
import time

from wt_nodes import wTagManager
from wtServer import wtServer
from wt_funcs import get_server_data,get_valid_node_name

LOGGER = polyinterface.LOGGER

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
        self.set_port(self.wtServer.listen_port)
        self.save_params()
        self.discover() # TODO: Temporary, discover on startup, or always?
        self.query()

    def shortPoll(self):
        """
        Optional.
        This runs every 10 seconds. You would probably update your nodes either here
        or longPoll. No need to Super this method the parent version does nothing.
        The timer can be overriden in the server.json.
        """
        pass

    def longPoll(self):
        """
        Optional.
        This runs every 30 seconds. You would probably update your nodes either here
        or shortPoll. No need to Super this method the parent version does nothing.
        The timer can be overriden in the server.json.
        """
        # MAke sure we don't do this while startin up or discover is running!
        return True # Do nothing for now.
        mgd = self.get_tag_managers()
        if mgd['st']:
            for mgr in mgd['result']:
                node = self.get_node(get_valid_node_name(mgr['mac']))
                if node is not None:
                    node.set_params(mgr)

    def query(self):
        """
        Optional.
        By default a query to the control node reports the FULL driver set for ALL
        nodes back to ISY. If you override this method you will need to Super or
        issue a reportDrivers() to each node manually.
        """
        if self.wtServer.oauth2_code == False:
            self.set_auth(False)
            self.l_error('discover',"Not able to query oauth2_code={}".format(self.wtServer.oauth2_code))
            return False
        self.set_auth(True)
        # Call longPoll since it check the comm status
        self.longPoll()
        # Don't do this on initial startup!
        #for node in self.nodes:
            #self.nodes[node].reportDrivers()

    def discover(self, *args, **kwargs):
        """
        Example
        Do discovery here. Does not have to be called discovery. Called from example
        controller start method and from DISCOVER command recieved from ISY as an exmaple.
        """
        if self.wtServer.oauth2_code == False:
            self.set_auth(False)
            self.l_error('discover',"Not able to discover oauth2_code={}".format(self.wtServer.oauth2_code))
            return False
        self.set_auth(True)
        self.save_params()
        mgd = self.get_tag_managers()
        if mgd['st']:
            for mgr in mgd['result']:
                self.l_debug("discover","TagManager={0}".format(mgr))
                address = get_valid_node_name(mgr['mac'])
                if address in self.nodes:
                    is_new = True
                else:
                    is_new = False
                self.l_info('discover','Adding Node {0} new={1}'.format(address,is_new))
                self.addNode(wTagManager(self, address, mgr['name'], mac=mgr['mac'], new=is_new))

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

    """
    This handle's all the 'get's from the tag URL calling.
    """
    def get_handler(self,command,params):
        self.l_debug('get_handler','processing command={0} params={1}'.format(command,params))
        if command == '/code':
            return self.set_oauth2(params['oauth2_code'])
        node = None
        if not 'tagname' in params:
            self.l_error('get_handler','Tag name not in params? command={0} params={1}'.format(command,params))
            return False
        for address in self.nodes:
            if self.nodes[address].name == params['tagname']:
                node = self.nodes[address]
        if node is None:
            self.l_error('get_handler',"Did not find node with name '{0}' id '{1}'".format(params['tagname'],params['tagid']))
            return False
        if command == '/motion_detected':
            # {'ts': '2018-02-15T12:44:04 00:00', 'tagid': '0', 'zaxis': '-81', 'xaxis': '51', 'tagname': 'GarageFreezer', 'orien': '100', 'yaxis': '129'}
            node.set_motion(1)
            node.set_orien(params['orien'])
            node.set_xaxis(params['xaxis'])
            node.set_yaxis(params['yaxis'])
            node.set_zaxis(params['zaxis'])
        elif command == '/update':
            #tagname=Garage Freezer&tagid=0&temp=-21.4213935329179&hum=0&lux=0&ts=2018-02-15T11:18:02+00:00 HTTP/1.1" 400 -
            if 'temp' in params:
                node.set_temp(params['temp'])
            if 'hum' in params:
                node.set_hum(params['hum'])
            if 'lux' in params:
                node.set_lux(params['lux'])
        else:
            self.l_error('get_handler',"Unknown command '{0}'".format(command))
            return False
        return True

    """
     Misc funcs
    """
    def get_tag_managers(self):
        if self.wtServer.oauth2_code == False:
            self.l_error('get_tag_managers',"oauth2_code={}".format(self.wst.oauth2_code))
            return { 'st': False }
        mgd = self.wtServer.GetTagManagers();
        if mgd['st']:
            self.set_comm(True)
        else:
            self.set_comm(False)
        return mgd

    def get_node(self,address):
        self.l_info('get_node',"adress={0}".format(address))
        for node in self.nodes:
            #self.l_debug('get_node',"node={0}".format(node))
            if self.nodes[node].address == address:
                return self.nodes[node]
        return None

    def load_params(self):
        if 'oauth2_code' in self.polyConfig['customParams']:
            self.oauth2_code = self.polyConfig['customParams']['oauth2_code']
        else:
            self.l_error('load_params',"oauth2_code not defined in customParams, please authorizze")
            self.oauth2_code = False
            st = False

    def save_params(self):
        # Make sure latest code is in the params
        self.addCustomParam({'oauth2_code': self.oauth2_code})
        self.removeNoticesAll()
        if self.oauth2_code == False:
            self.addNotice('Click <a target="_blank" href="{0}&redirect_uri={1}/code">Authorize</a> to link your CAO Wireless Sensor Tags account'.format(self.auth_url,self.wtServer.url))

    def set_url_config(self):
        # TODO: Loop over tags and set_url_config on each
        for address in self.nodes:
            if not (self.nodes[address].id == 'wtController' or self.nodes[address].id == 'wTagManger'):
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
    def set_oauth2(self,value):
        if self.oauth2_code != value:
            self.oauth2_code = value
            self.save_params()
            self.set_url_config()
        if value is False:
            self.set_auth(False)
            self.set_comm(False)
        else:
            self.set_auth(True)
            self.set_comm(True)
        return True

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
        self.setDriver('GV5', value)

    """
    Command Functions
    """
    def cmd_install_profile(self,command):
        self.l_info("cmd_install_profile","installing...")
        self.poly.installprofile()

    """
    Node Definitions
    """
    id = 'wtController'
    commands = {
        'QUERY': query,
        'DISCOVER': discover,
        'INSTALL_PROFILE': cmd_install_profile,
    }
    drivers = [
        {'driver': 'ST',  'value': 0, 'uom': 2},
        {'driver': 'GV1', 'value': 0, 'uom': 56}, # vmaj: Version Major
        {'driver': 'GV2', 'value': 0, 'uom': 56}, # vmin: Version Minor
        {'driver': 'GV3', 'value': 0, 'uom': 2},  # auth: Authorized (we have valid oauth2 token)
        {'driver': 'GV4', 'value': 0, 'uom': 2},  # comm: Communicating
        {'driver': 'GV5', 'value': 0, 'uom': 56}, # port: REST Server Listen port
    ]