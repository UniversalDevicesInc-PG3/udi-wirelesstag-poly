#!/usr/bin/env python3

"""
  Simple GET handler with BaseHTTPServer
"""

from http.server import HTTPServer,BaseHTTPRequestHandler
from urllib import parse
from urllib.parse import parse_qsl
import socket, threading, sys, requests, json, time
import netifaces as ni

class wtHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        parsed_path = parse.urlparse(self.path)
        self.query = dict(parse_qsl(parsed_path.query))
        if 'debug' in self.query:
            message_parts = [
                'CLIENT VALUES:',
                'client_address={} ({})'.format(
                    self.client_address,
                    self.address_string()),
                'command={}'.format(self.command),
                'path={}'.format(self.path),
                'real path={}'.format(parsed_path.path),
                'query={}'.format(parsed_path.query),
                'query_dict={}'.format(self.query),
                'request_version={}'.format(self.request_version),
                '',
                'SERVER VALUES:',
                'server_version={}'.format(self.server_version),
                'sys_version={}'.format(self.sys_version),
                'protocol_version={}'.format(self.protocol_version),
                '',
                'HEADERS RECEIVED:',
            ]
            for name, value in sorted(self.headers.items()):
                message_parts.append(
                    '{}={}'.format(name, value.rstrip())
                )
        else:
            message_parts = ["Received: {0} {1}. ".format(parsed_path.path,self.query)]
        # We send back a response quickly cause the TAG Manager doesn't wait very long?
        hrt = self.parent.get_handler(parsed_path.path,self.query)
        message_parts.append("Code: {0}".format(int(hrt['code'])))
        message_parts.append(hrt['message'])
        self.send_response(int(hrt['code']))
        self.send_header('Content-Type',
                         'text/plain; charset=utf-8')
        self.end_headers()
        message_parts.append('')
        message = '\r\n'.join(message_parts)
        message += '\r\n'
        self.wfile.write(message.encode('utf-8'))

    def log_message(self, fmt, *args):
        # Stop log messages going to stdout
        self.parent.logger.info('wtHandler:log_message' + fmt % args)

class wtREST():

    def __init__(self,parent,logger):
        self.parent  = parent
        self.logger  = logger

    def start(self):
        port    = 0
        self.myip    = self.get_network_ip_rhost('8.8.8.8')
        if self.myip is False:
            self.logger.error("wtREST: Can not start on IP={0}".format(self.myip))
            return False
        self.logger.info("wtREST: Running on IP={0}".format(self.myip))
        self.address = (self.myip, port) # let the kernel give us a port
        self.logger.debug("wtREST: address={0}".format(self.address))
        # Get a handler and set parent to myself, so we can process the requests.
        eh = wtHandler
        eh.parent = self
        self.server = HTTPServer(self.address, wtHandler)
        self.url     = 'http://{0}:{1}'.format(self.server.server_address[0],self.server.server_address[1])
        self.listen_port = self.server.server_address[1]
        self.logger.info("wtREST: Running on: {0}".format(self.url))
        self.thread  = threading.Thread(target=self.server.serve_forever)
        # Need this so the thread will die when the main process dies
        self.thread.daemon = True
        self.thread.start()
        return True
        #try:
        #    self.server.serve_forever()
        #except KeyboardInterrupt:
        #    self.logger.info('wtREST: Exiting from interupt')
        #    self.server.shutdown()
        #    self.server.server_close()
        #    raise
        #except Exception as err:
        #    self.logger.error('wtREST: failed: {0}'.format(err), exc_info=True)
        #self.server.shutdown()
        #self.server.server_close()

    def get_handler(self,path,query):
        return self.parent.get_handler(path,query)

    def get_network_ip_rhost(self,rhost):
        self.logger.info("wtREST:get_network_ip: {0}".format(rhost))
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect((rhost, 80))
            rt = s.getsockname()[0]
        except Exception as err:
            self.logger.error('wtREST:get_network_id: failed: {0}'.format(err), exc_info=True)
            rt = False
        finally:
            s.close()
        self.logger.info("wtREST:get_network_ip: Returning {0}".format(rt))
        return rt

    # This didn't work on a mac, needs a try/except, which I didn't like...
    def get_network_ip(self):
        try:
            ifaddr = ni.ifaddresses(iface)[ni.AF_INET][0]
            if 'addr' in ifaddr and ifaddr['addr'] != '127.0.0.1':
                self.logger.info("wtREST:get_network_ip: Got {0}".format(rt))
                return ifaddr['addr']
        except:
            pass
        self.logger.info("wtREST:get_network_ip: Failed")
        return False

class wtServer():

    def __init__(self,logger,client_id,client_secret,ghandler=None,oauth2_code=False):
        self.logger = logger
        self.client_id = client_id
        self.client_secret = client_secret
        self.ghandler=ghandler
        self.oauth2_code = oauth2_code
        self.access_token = False
        self.token_type   = None

    def start(self):
        self.rest = wtREST(self,self.logger)
        self.st = self.rest.start()
        if self.st is False:
            self.l_error('wtServer:start','REST server not started {}'.format(self.st))
            return False
        self.listen_url  = self.rest.url
        self.listen_port = self.rest.listen_port
        self.url = self.rest.url
        if self.oauth2_code != False:
            self.get_access_token()
        self._slock = False
        return True

    def get_handler(self,command,params):
        """
        This is passed the incoming http get's to processes
        """
        self.l_debug('get_handler','command={}'.format(command))
        # This is from the oauth2 redirect with our code.
        if command == "/code":
            code = 200
            message = "\nGot code {}, asking for access token\n".format(params['code'])
            self.oauth2_code = params['code']
            self.l_info('get_handler','Got code: {}'.format(self.oauth2_code))
            tr = self.get_access_token()
            if tr == False:
                code = 500
                message += "ERROR: Unable to get access token from code, see log"
            else:
                message += "SUCCESS, received our token, will save in Polyglot database for the future"
            if self.ghandler is not None:
                self.ghandler(command,{'oauth2_code': self.oauth2_code})
        elif command == "/favicon.ico":
            # Ignore this, where does it come from?
            code = 200
            message = "Ignored {0}".format(command)
        else:
            if self.ghandler is None:
                code = 500
                message = "Unknown command, no ghandler specified '{}'".format(command)
            else:
                ret = self.ghandler(command,params)
                if ret:
                    code = 200
                    message = 'Command {0} success'.format(command)
                else:
                    code = 500
                    message = 'Command {0} failed'.format(command)
        if code == 200:
            self.l_debug('get_handler','code={0} message={1}'.format(code,message))
        else:
            self.l_error('get_handler','code={0} message={1}'.format(code,message))
        return  { 'code': code, 'message': message }

    def get_access_token(self,code=None):
        if code is not None:
            self.oauth2_code = code
        aret = self.http_post('oauth2/access_token.aspx',
                              {
                                  'client_id': self.client_id,
                                  'client_secret': self.client_secret,
                                  'code': self.oauth2_code
                              }, use_token=False)
        # This gives us:
        # {'token_type': 'Bearer', 'access_token': '...', 'expires_in': 9999999}
        if aret == False:
            self.l_error('get_access_token','Failed')
            self.access_token = aret
            return aret
        self.access_token = aret['access_token']
        self.token_type   = aret['token_type']
        self.l_debug('start',"token_type={} access_token={}".format(self.token_type,self.access_token))

    def http_post(self,path,payload,use_token=True):
        #url = "http://www.mytaglist.com/{}".format(path)
        url = "http://wirelesstag.net/{}".format(path)
        self.l_debug('http_post',"Sending: url={0} payload={1}".format(url,payload))
        if use_token:
            if self.access_token is False:
                self.l_error('http_post',"No authorization for url={0} payload={1}".format(url,payload))
                return False
            headers = {
                "Authorization": "{0} {1}".format(self.token_type,self.access_token),
                "Content-Type": "application/json"
            }
        else:
            headers = {}
        try:
            response = requests.post(
                url,
                headers=headers,
                data=payload,
                timeout=10
            )
        # This is supposed to catch all request excpetions.
        except requests.exceptions.RequestException as e:
            self.l_error('http_post',"Connection error for %s: %s" % (url, e))
            return False
        self.l_debug('http_post',' Got: code=%s' % (response.status_code))
        if response.status_code == 200:
            #self.l_debug('http_post',"Got: text=%s" % response.text)
            try:
                d = json.loads(response.text)
            except (Exception) as err:
                self.l_error('http_post','Failed to convert to json {0}: {1}'.format(response.text,err), exc_info=True)
                return False
            return d
        elif response.status_code == 400:
            self.l_error('http_post',"Bad request: %s" % (url) )
        elif response.status_code == 404:
            self.l_error('http_post',"Not Found: %s" % (url) )
        elif response.status_code == 401:
            # Authentication error
            self.l_error('http_post',
                "Failed to authenticate, please check your username and password")
        else:
            self.l_error('http_post',"Unknown response %s: %s %s" % (response.status_code, url, response.text) )
        return False

    def l_info(self, name, string):
        self.logger.info("%s: %s" %  (name,string))

    def l_error(self, name, string, exc_info=False):
        self.logger.error("%s: %s" % (name,string), exc_info=exc_info)

    def l_warning(self, name, string):
        self.logger.warning("%s: %s" % (name,string))

    def l_debug(self, name, string):
        self.logger.debug("%s: %s" % (name,string))

    """
    Wiress Tags API Functions
    """
    def api_post_d(self,path,payload,dump=True):
        """
        Call the api path with payload expecting data in d entry
        Return status and result
        """
        if dump:
            payload = json.dumps(payload)
        aret = self.http_post(path,payload)
        self.l_debug('api_post_d','path={0} got={1}'.format(path,aret))
        if aret == False or not 'd' in aret:
            mret = { 'st': False }
        else:
            mret = { 'st': True, 'result': aret['d'] }
        self.l_debug('api_post_d','ret={0}'.format(mret))
        return mret

    # These match the names used in the API

    # http://wirelesstag.net/ethAccount.asmx?op=IsSignedIn
    def IsSignedIn(self):
        return self.api_post_d('ethAccount.asmx/IsSignedIn',{})

    # These match the names used in the API:
    # http://wirelesstag.net/ethAccount.asmx?op=GetTagManagers
    def GetTagManagers(self):
        return self.api_post_d('ethAccount.asmx/GetTagManagers',{})

    # http://wirelesstag.net/ethAccount.asmx?op=SelectTagManager
    def SelectTagManager(self,mgr_mac):
        # This doesn't like how request converts dict to json, so do it here.
        if hasattr(self,'last_selected') and self.last_selected == mgr_mac: return True
        mgd = self.api_post_d('ethAccount.asmx/SelectTagManager',{'mac':mgr_mac})
        if mgd['st']:
            self.last_selected = mgr_mac
        return mgd['st']

    def api_select_and_post_d(self,tmgr_mac,path,params):
        # A very dumb lock...
        while self._slock is not False:
            self.l_debug('api_select_and_post_d',"Locked by {}".format(self._slock))
            time.sleep(1)
        self._slock = tmgr_mac
        if self.SelectTagManager(tmgr_mac):
            ret = self.api_post_d(path,params)
        else
            ret = { 'st': False }
        self._slock = False
        return ret

    # http://wirelesstag.net/ethClient.asmx?op=GetServerTime
    def GetServerTime(self,tmgr_mac):
        return self.api_select_and_post_d(tmgr_mac,'ethClient.asmx/GetServerTime',{})

    # http://wirelesstag.net/ethClient.asmx?op=GetTagList
    def GetTagList(self,tmgr_mac):
        return self.api_select_and_post_d(tmgr_mac,'ethClient.asmx/GetTagList',{})

    # http://wirelesstag.net/ethClient.asmx?op=LoadEventURLConfig
    def LoadEventURLConfig(self,tmgr_mac,params):
        return self.api_select_and_post_d(tmgr_mac,'ethClient.asmx/LoadEventURLConfig',params)

    # http://wirelesstag.net/ethClient.asmx?op=SaveEventURLConfig
    def SaveEventURLConfig(self,tmgr_mac,params):
        return self.api_select_and_post_d(tmgr_mac,'ethClient.asmx/SaveEventURLConfig',params)

    # http://wirelesstag.net/ethClient.asmx?op=LoadTempSensorConfig
    def LoadTempSensorConfig(self,tmgr_mac,params):
        return self.api_select_and_post_d(tmgr_mac,'ethClient.asmx/LoadTempSensorConfig',params)

    # http://wirelesstag.net/ethClient.asmx?op=GetTagListCached
    def DontUseThisGetTagListCached(self,tmgr_mac,params):
        return self.api_select_and_post_d(tmgr_mac,'ethClient.asmx/GetTagListCached',params)

    # http://wirelesstag.net/ethClient.asmx?op=RequestImmediatePostback
    def RequestImmediatePostback(self,tmgr_mac,params):
        return self.api_select_and_post_d(tmgr_mac,'ethClient.asmx/RequestImmediatePostback',params)

    def RebootTagManager(self,tmgr_mac):
        return self.api_select_and_post_d(tmgr_mac,'ethClient.asmx/RebootTagManager',{})

    def PingAllTags(self,tmgr_mac):
        return self.api_select_and_post_d(tmgr_mac,'ethClient.asmx/PingAllTags',{'autoRetry':True})

    def LightOn(self,tmgr_mac,id,flash):
        return self.api_select_and_post_d(tmgr_mac,'ethClient.asmx/LightOn',{'id': id, 'flash':flash})

    def LightOff(self,tmgr_mac,id):
        return self.api_select_and_post_d(tmgr_mac,'ethClient.asmx/LightOff',{'id': id})

def my_ghandler(command,params):
    return True

if __name__ == '__main__':
    import logging, time
    logging.basicConfig(
        level=10,
        format='%(levelname)s:\t%(name)s\t%(message)s'
    )
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    client_id     = "3b08b242-f0f8-41c0-ba29-6b0478cd0b77"
    client_secret = "0b947853-1676-4a63-a384-72769c88f3b1"
    code          = "d967868a-144e-49ed-921f-c27b65dda06a"
    obj = wtServer(logger,client_id,client_secret,ghandler=my_ghandler)
    try:
        obj.start()
    except KeyboardInterrupt:
        logger.info('Exiting from keyboard interupt')
        sys.exit()
    # Manually get the access token
    obj.get_access_token(code)
    #while obj.oauth2_code == False:
    #    logger.info("Waiting for code...");
    #    time.sleep(10)
    mgrs = obj.GetTagManagers()
    if mgrs['st']:
        obj.SelectTagManager(mgrs['result'][0]['mac'])
    obj.GetTagList()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    except Exception as err:
        logger.error('wtREST: failed: {0}'.format(err), exc_info=True)
    sys.exit()
