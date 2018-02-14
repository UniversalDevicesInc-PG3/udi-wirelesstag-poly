
import polyinterface
import sys
import time

from wst_nodes import wstTagManager
from wst import wst
from wst_funcs import get_valid_node_name

LOGGER = polyinterface.LOGGER

class wstController(polyinterface.Controller):
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
        super(wstController, self).__init__(polyglot)

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
        self.wst = wst(LOGGER,self.client_id,self.client_secret,self.oauth2_code)
        self.wst.start()
        self.save_params()
        self.discover()

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
        for mgr in self.wst.GetTagManagers():
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
        self.longPoll()
        for node in self.nodes:
            self.nodes[node].reportDrivers()

    def discover(self):
        """
        Example
        Do discovery here. Does not have to be called discovery. Called from example
        controller start method and from DISCOVER command recieved from ISY as an exmaple.
        """
        if self.wst.oauth2_code == False:
            self.l_error('discover',"Not able to discover oauth2_code={}".format(self.wst.oauth2_code))
            return False
        self.save_params()
        mgrs = self.wst.GetTagManagers()
        for mgr in mgrs:
            self.l_debug("discover","TagManager={0}".format(mgrs))
            self.addNode(wstTagManager(self, get_valid_node_name(mgr['mac']), mgr['name']))
        #self.addNode(wstTagManager(self, 'testtagmanager', 'Test Tag Manager'))

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
     Misc funcs
    """
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
        # Always use the server oauth2_code if defined?s
        if self.wst.oauth2_code != False:
            self.oauth2_code = self.wst.oauth2_code
        self.addCustomParam({'oauth2_code': self.oauth2_code})
        self.removeNoticesAll()
        if self.oauth2_code == False:
            self.addNotice("Please authorize: {0}&redirect_uri={1}/code".format(self.auth_url,self.wst.url))

    def l_info(self, name, string):
        LOGGER.info("%s:%s: %s" %  (self.id,name,string))
        
    def l_error(self, name, string):
        LOGGER.error("%s:%s: %s" % (self.id,name,string))
        
    def l_warning(self, name, string):
        LOGGER.warning("%s:%s: %s" % (self.id,name,string))
        
    def l_debug(self, name, string):
        LOGGER.debug("%s:%s: %s" % (self.id,name,string))
        
    """
    Command Functions
    """
    def cmd_install_profile(self,command):
        self.l_info("cmd_install_profile","installing...")
        self.poly.installprofile()

    """
    Node Definitions
    """
    id = 'wstCntl'
    commands = {
        'QUERY': query,
        'DISCOVER': discover,
        'INSTALL_PROFILE': cmd_install_profile,
    }
    drivers = [
        {'driver': 'ST',  'value': 0, 'uom': 2},
        {'driver': 'GV1', 'value': 0, 'uom': 56}, # Version Major
        {'driver': 'GV2', 'value': 0, 'uom': 56}, # Version Minor
    ]
