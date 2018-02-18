#!/usr/bin/env python3

"""
  Simple GET handler with BaseHTTPServer
"""

from http.server import HTTPServer,BaseHTTPRequestHandler
from urllib import parse
from urllib.parse import parse_qsl
import socket, threading, sys, requests, json

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
        self.myip    = self.get_network_ip('8.8.8.8')
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
        #t.setDaemon(True) # don't hang on exit
        self.thread.start()
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
        
    def get_network_ip(self,rhost):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect((rhost, 0))
        except:
            self.l_error("get_network_ip","Failed to open socket to " + rhost)
            return False
        rt = s.getsockname()[0]
        s.close()
        return rt

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
        self.rest.start()
        self.listen_url  = self.rest.url
        self.listen_port = self.rest.listen_port
        self.url = self.rest.url
        if self.oauth2_code != False:
            self.get_access_token()

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

    # These match the names used in the API:
    # http://wirelesstag.net/ethAccount.asmx?op=GetTagManagers
    def GetTagManagers(self):
        aret = self.http_post('ethAccount.asmx/GetTagManagers',{})
        self.l_debug('getTagManagers',aret)
        if aret is False or not 'd' in aret:
            ret = { 'st': False }
        else:
            ret = { 'st': True, 'result': aret['d'] }
        return ret

    # http://wirelesstag.net/ethAccount.asmx?op=SelectTagManager
    def SelectTagManager(self,mgr_mac):
        # This doesn't like how request converts dict to json, so do it here.
        aret = self.http_post('ethAccount.asmx/SelectTagManager',json.dumps({'mac':mgr_mac}))
        self.l_debug('SelectTagManager',aret)
        if 'd' in aret:
            ret = { 'st': True, 'result': aret['d'] }
        else:
            ret = { 'st': False }
        return ret
        
    # http://wirelesstag.net/ethClient.asmx?op=GetTagList
    def GetTagList(self):
        aret = self.http_post('ethClient.asmx/GetTagList',{})
        self.l_debug('GetTagList',aret)
        if 'd' in aret:
            ret = { 'st': True, 'result': aret['d'] }
        else:
            ret = { 'st': False }
        return ret

    # http://wirelesstag.net/ethClient.asmx?op=LoadEventURLConfig
    def LoadEventURLConfig(self,params):
        aret = self.http_post('ethClient.asmx/LoadEventURLConfig',json.dumps(params))
        self.l_debug('LoadEventURLConfig',aret)
        if 'd' in aret:
            ret = { 'st': True, 'result': aret['d'] }
        else:
            ret = { 'st': False }
        return ret

    # http://wirelesstag.net/ethClient.asmx?op=SaveEventURLConfig
    def SaveEventURLConfig(self,params):
        aret = self.http_post('ethClient.asmx/SaveEventURLConfig',json.dumps(params))
        self.l_debug('SaveEventURLConfig',aret)
        #if 'd' in aret:
        #    ret = { 'st': True, 'result': aret['d'] }
        #else:
        #    ret = { 'st': False }
        return aret

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