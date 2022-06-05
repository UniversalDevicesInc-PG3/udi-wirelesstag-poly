"""
This is a NodeServer for CAO Gadgets Wireless Sensor Tags for Polyglot v2 written in Python3
by JimBoCA jimboca3@gmail.com
"""
from udi_interface import Node,LOGGER
import sys
import time
from copy import deepcopy
import requests, json
from threading import Thread
from wtServer import wtSession
from wt_funcs import get_valid_node_name
from nodes import Tag

# For even more debug... should make a setting?
DEBUG_LEVEL=1

class TagManager(Node):
    def __init__(self, controller, address, name, mac, online=False, node_data=False, do_discover=False):
        # Fpr our logger lines
        self.l_name = "{}:{}:{}".format(self.id,address,name)
        LOGGER.debug('start')
        self.controller = controller
        self.type = self.id
        self.online = online # Only used on initialization
        # Save the real mac before we legalize it.
        self.ready       = False
        self.do_discover = do_discover
        self.node_data   = node_data
        self.mac         = mac
        super(TagManager, self).__init__(controller.poly, address, address, name)
        controller.poly.subscribe(controller.poly.START,             self.handler_start, address) 
        # These start in threads cause they take a while
        self.discover_thread = None
        self.set_url_thread = None
        self.set_url_config_st = None
        self.session = False
        LOGGER.debug('done')

    def handler_start(self):
        LOGGER.info('...')
        self.set_st(self.online)
        self.set_use_tags(self.get_use_tags())
        self.start_session()
        #LOGGER.info('{0} {1}'.format(self._drivers,self.use_tags))
        self.degFC = 1 # I like F.
        # When we are added by the controller discover, then run our discover.
        self.ready = True
        if self.do_discover:
            self.discover(thread=False)
        else:
            self.query() # To get latest tag info.
            if self.use_tags == 1:
                LOGGER.info('Call add_existing_tags because use_tags={0}'.format(self.use_tags))
                self.add_existing_tags()
                #self.discover() # Needed to fix tag_id's
        self.reportDrivers()
        LOGGER.info('done')

    def query(self):
        self.reportDrivers()

    def query_all(self):
        if self.use_tags == 0:
            LOGGER.debug('use_tags={}'.format(self.use_tags))
            return
        mgd = self.GetTagList()
        if mgd['st']:
            self.set_st(True)
            for tag in mgd['result']:
                tag_o = self.get_tag_by_id(tag['slaveId'])
                if tag_o is None:
                    LOGGER.error('No tag with id={0}'.format(tag['slaveId']))
                else:
                    tag_o.set_from_tag_data(tag)
                    tag_o.reportDrivers()
        else:
            self.set_st(False)
        self.reportDrivers()

    def shortPoll(self):
        if not self.ready: return False
        if self.discover_thread is not None:
            if self.discover_thread.isAlive():
                LOGGER.debug('discover thread still running...')
            else:
                LOGGER.debug('discover thread is done...')
                self.discover_thread = None
        if self.set_url_thread is not None:
            if self.set_url_thread.isAlive():
                LOGGER.debug('set_url thread still running...')
            else:
                LOGGER.debug('set_url thread is done...')
                self.set_url_thread = None
        if self.discover_thread is None and self.set_url_thread is None:
            if self.set_url_config_st == False:
                # Try again...
                LOGGER.error("Calling set_url_config since previous st={}".format(self.set_url_config_st))
                self.set_url_config()
        for tag in self.get_tags():
            tag.shortPoll()

    def longPoll(self):
        if not self.ready: return False
        LOGGER.debug('...')
        if self.st is False:
            if self.controller.wtServer is False:
                LOGGER.error("Unable to start TagManager session because main server was not started")
                self.set_st(False)
                return

    def discover(self, thread=True):
        """
        Start the discover in a thread so we don't cause timeouts :(
        """
        LOGGER.debug("enter")
        if getattr(self,'discover_running',None) is None:
            self.discover_running = False
        if self.discover_running:
            LOGGER.debug('Already running...')
            return False
        self.discover_running = True
        cnt = 30
        while ((not self.ready) and cnt > 0):
            LOGGER.debug('waiting for node to be ready ({})..'.format(cnt))
            cnt -= 1
            time.sleep(1)
        if not self.ready:
            LOGGER.error('timed out waiting for node to be ready, did it crash?')
            return
        if thread:
            self.discover_thread = Thread(target=self._discover)
            self.discover_thread.start()
        else:
            self._discover()
            self.discover_running = False
        LOGGER.debug("exit")

    def _discover(self):
        LOGGER.debug('use_tags={}'.format(self.use_tags))
        if self.use_tags == 0:
            return False
        ret = self.GetTagList()
        if ret['st'] is False:
            return
        index = 0
        tags = deepcopy(ret['result'])
        for tag in tags:
            LOGGER.debug(f"Will add Tag: {tag['name']}")
        for tag in tags:
            LOGGER.debug('Got Tag: {}'.format(tag))
            self.add_tag(tdata=tag, uom=self.get_tag_temp_unit(tag))
        self.reportDrivers() # Report now so they show up while set_url runs.
        self.set_url_config(thread=False)
        self.discover_running = False

    def add_existing_tags(self):
        """
        Called on startup to add the tags from the config.
        This has to loop thru the _nodes list to figure out if it's one of the
        tags for this tag manager.
        """
        LOGGER.debug("Looking for my tags")
        for node in self.poly.db_getNodeDrivers(''):
            address = node['address']
            if address != self.address:
                # One of my tags?
                LOGGER.debug("check node primary={}".format(node['primaryNode']))
                if node['primaryNode'] == self.address:
                    LOGGER.info("node={0} = {1}".format(address,node))
                    self.add_tag(address=node['address'], name=node['name'], is_new=False)
        self.set_url_config()

    def add_tag(self, address=None, name=None, tag_type=None, uom=None, tdata=None, is_new=True):
        LOGGER.info(f"Adding tag: address={address} name={name} tag_type={tag_type} uom={uom} tdata={tdata} is_new={is_new}")
        return self.controller.add_node(Tag(self.controller, self.address, address,
        name=name, tag_type=tag_type, uom=uom, tdata=tdata, is_new=is_new))

    def delete_all_tags(self):
        LOGGER.warning("Deleting all tags for this tag manager...")
        # Make sure use_tags is off, then delete them all.
        self.set_use_tags(0)
        for node in self.controller.poly.nodes():
            LOGGER.debug(f"my.address={self.address} node.address={node.address} node.primary={node.primary}")
            if node.address != self.address and node.primary == self.address:
                self.controller.del_node(node)

    """
    Misc functions
    """
    def get_tags(self):
        """
        Get all the active tags for this tag manager.
        """
        nodes = list()
        for node in self.controller.poly.nodes():
            #LOGGER.debug('node={}'.format(node))
            if hasattr(node,'tag_id') and node.primary_n.mac == self.mac:
                nodes.append(node)
        #LOGGER.debug('nodes={0}'.format(nodes))
        return nodes

    def get_tag_by_id(self,tid):
        tid = int(tid)
        for tag in self.get_tags():
            LOGGER.debug('{0} address={1} id={2}'.format(tid,tag.address,tag.tag_id))
            if int(tag.tag_id) == tid:
                return tag
        return None

    """
    Wireless Tags API Communication functions
    """
    def start_session(self):
        if self.controller.wtServer is False:
            LOGGER.error("Unable to start TagManager session because main server was not started")
            return False
        self.session = wtSession(self,LOGGER,self.controller.wtServer,self.mac)

    def session_post(self,path,params):
        if self.session is False:
            LOGGER.error("TagManager session is not running")
            self.controller.Notices['session_post'] = "TagManager session is not running"
            return {'st': False}
        self.controller.Notices.delete('session_post')
        return self.session.api_post_d(path,params)
    
    # http://wirelesstag.net/ethClient.asmx?op=GetTagList
    def GetTagList(self):
        ret = self.session_post('ethClient.asmx/GetTagList',{})
        if ret: return ret
        LOGGER.error("Failed: st={}".format(ret))
        return ret

    # http://wirelesstag.net/ethClient.asmx?op=LoadEventURLConfig
    def LoadEventURLConfig(self,params):
        return self.session_post('ethClient.asmx/LoadEventURLConfig',params)

    # http://wirelesstag.net/ethClient.asmx?op=SaveEventURLConfig
    def SaveEventURLConfig(self,params):
        return self.session_post('ethClient.asmx/SaveEventURLConfig',params)

    # http://wirelesstag.net/ethClient.asmx?op=LoadTempSensorConfig
    def LoadTempSensorConfig(self,params):
        return self.session_post('ethClient.asmx/LoadTempSensorConfig',params)

    # http://wirelesstag.net/ethClient.asmx?op=RequestImmediatePostback
    def RequestImmediatePostback(self,params):
        return self.session_post('ethClient.asmx/RequestImmediatePostback',params)

    def RebootTagManager(self,tmgr_mac):
        return self.session_post('ethClient.asmx/RebootTagManager',{})

    def PingAllTags(self):
        return self.session_post('ethClient.asmx/PingAllTags2',{'mac': self.mac, 'autoRetry':True})

    def LightOn(self,tmgr_mac,id,flash):
        return self.session_post('ethClient.asmx/LightOn',{'id': id, 'flash':flash})

    def LightOff(self,tmgr_mac,id):
        return self.session_post('ethClient.asmx/LightOff',{'id': id})

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
            LOGGER.error("No tags in Polyglot DB, you need to discover?")
            return False
        self.set_url_config_st = False
        for tag in tags:
            tag.set_url_config(force=force)
        self.set_url_config_st = True

    """
    Set Functions
    """
    def set_params(self,params):
        """
        Set params from the getTagManager data
        """
        self.set_st(params['online'])

    def set_st(self,value,force=False):
        LOGGER.debug(f"{self.l_name} value={value} force={force}")
        if not force and hasattr(self,"st") and self.st == value:
            return True
        self.st = value
        if value is True:
            self.setDriver('ST', 1)
        elif value is False:
            self.setDriver('ST', 0)
        else:
            LOGGER.error(f'{self.l_name} Unknown Value "{value}"', )
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

    def cmd_delete_all_tags(self,command):
        LOGGER.debug('enter:')
        self.delete_all_tags()
        LOGGER.debug('exit:')

    def cmd_reboot(self,command):
        self.RebootTagManager(self.mac)

    id = 'wTagManager'
    drivers = [
        {'driver': 'ST',  'value': 0, 'uom': 2},
        {'driver': 'GV1', 'value': 0, 'uom': 2}, # Use Tags
    ]
    commands = {
        'SET_USE_TAGS': cmd_set_use_tags,
        'QUERY': query,
        'QUERY_ALL': query_all,
        'SET_URL_CONFIG': cmd_set_url_config,
        'PING_ALL_TAGS': cmd_ping_all_tags,
        'DELETE_ALL_TAGS': cmd_delete_all_tags,
        'DISCOVER': discover,
        'REBOOT': cmd_reboot,
    }
