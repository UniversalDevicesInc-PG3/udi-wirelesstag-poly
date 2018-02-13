#!/usr/local/bin/python3.6

"""
Simple Wireless Sensor Tags Object
"""

import logging, json, requests, threading, socketserver, re, socket, time
from http.client import BadStatusLine  # Python 3.x
from urllib.parse import urlparse,parse_qsl

logging.basicConfig(
    level=10,
    format='%(levelname)s:\t%(name)s\t%(message)s'
)
LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.DEBUG)

class wst():

    def __init__(self,client_id,client_secret,):
        self.client_id = client_id
        self.client_secret = client_secret
        self.code = False
        pass

    def start(self):
        self.rest = wstREST(self,LOGGER)
        self.rest.start()
        pass

    def get_access_token(self):
        aret = self.http_post('oauth2/access_token.aspx',
                              {
                                  'client_id': self.client_id,
                                  'client_secret': self.client_secret,
                                  'code': self.oauth2_code
                              }, use_token=False)
        # This gives us:
        # {'token_type': 'Bearer', 'access_token': '...', 'expires_in': 9999999}
        self.access_token = aret['access_token']
        self.token_type    = aret['token_type']
        self.l_debug('start',"token_type={} access_token={}".format(self.token_type,self.access_token))

    def get_handler(self,command,params):
        """
        This is passed the incoming http get's to processes
        """
        self.l_debug('get_handler','command={}'.format(command))
        # This is from the oauth2 redirect with our code.
        if command == "code":
            self.oauth2_code = params['code']
            self.l_info('get_handler','Got code: {}'.format(self.code))
            obj.get_access_token()
        return True
    
    def http_post(self,path,payload,use_token=True):
        #url = "http://www.mytaglist.com/{}".format(path)
        url = "http://wirelesstag.net/{}".format(path)
        self.l_debug('http_post',"Sending: url={0} payload={1}".format(url,payload))
        if use_token:
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
                params=payload,
                timeout=10
            )
        # This is supposed to catch all request excpetions.
        except requests.exceptions.RequestException as e:
            self.l_error('http_get',"Connection error for %s: %s" % (url, e))
            return False
        self.l_debug('http_get',' Got: code=%s' % (response.status_code))
        if response.status_code == 200:
            #self.l_debug('http_get',"http_get: Got: text=%s" % response.text)
            try:
                d = json.loads(response.text)
            except (Exception) as err:
                LOGGER.error('http_post: Failed to convert to json {0}: {1}'.format(response.text,err), exc_info=True)
                return False
            return d
        elif response.status_code == 400:
            self.l_error('http_get',"Bad request: %s" % (url) )
        elif response.status_code == 404:
            self.l_error('http_get',"Not Found: %s" % (url) )
        elif response.status_code == 401:
            # Authentication error
            self.l_error('http_get',
                "Failed to authenticate, please check your username and password")
        else:
            self.l_error('http_get',"Unknown response %s: %s" % (response.status_code, url) )
        return False

    def l_info(self, name, string):
        LOGGER.info("%s: %s" %  (name,string))
        
    def l_error(self, name, string):
        LOGGER.error("%s: %s" % (name,string))
        
    def l_warning(self, name, string):
        LOGGER.warning("%s: %s" % (name,string))
        
    def l_debug(self, name, string):
        LOGGER.debug("%s: %s" % (name,string))

    # These match the names used in the API:
    # http://wirelesstag.net/ethAccount.asmx?op=GetTagManagers
    def GetTagManagers(self):
        aret = self.http_post('ethAccount.asmx/GetTagManagers',{})
        self.l_debug('getTagManagers',aret)
        mgrs = list()
        for mgr in aret['d']:
            mgrs.append(mgr)

class EchoRequestHandler(socketserver.BaseRequestHandler):
    
    def handle(self):
        try:
            # Echo the back to the client
            data = self.request.recv(1024)
            # Don't worry about a status for now, just echo back.
            self.request.sendall(data)
            # Then parse it.
            self.parent.handler(data.decode('utf-8','ignore'))
        except (Exception) as err:
            self.parent.logger.error("request_handler failed {0}".format(err), exc_info=True)
        return

class wstREST():

    def __init__(self,parent,logger):
        self.parent  = parent
        self.logger  = logger

    def start(self):
        self.myip    = self.get_network_ip('8.8.8.8')
        self.address = (self.myip, 0) # let the kernel give us a port
        self.logger.debug("wstREST: address={0}".format(self.address))
        eh = EchoRequestHandler
        eh.parent = self
        self.server  = socketserver.TCPServer(self.address, eh)
        self.url     = 'http://{0}:{1}'.format(self.server.server_address[0],self.server.server_address[1])
        self.logger.info("wstREST: Running on: {0}".format(self.url))
        self.thread  = threading.Thread(target=self.server.serve_forever)
        #t.setDaemon(True) # don't hang on exit
        self.thread.start()

    def get_network_ip(self,rhost):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect((rhost, 0))
        except:
            self.logger.error("wstREST:get_network_ip: Failed to open socket to " + rhost)
            return False
        rt = s.getsockname()[0]
        s.close()
        return rt

    def handler(self, data):
        up = urlparse(data.strip())
        self.logger.debug("wstRESTServer:handler: Got {0}".format(up))
        match = re.match( r'GET /(.*)', up.path, re.I)
        command = match.group(1)
        query = re.match( r'(.*) ', up.query, re.I)
        qs = dict(parse_qsl(query.group(1)))
        self.logger.debug("wstRESTServer:handler: {0}".format(qs))
        #self.logger.debug("code={}".format(qs['code']))
        return self.parent.get_handler(command=command,params=qs)
                                
        
if __name__ == "__main__":
    client_id     = "3b08b242-f0f8-41c0-ba29-6b0478cd0b77"
    client_secret = "0b947853-1676-4a63-a384-72769c88f3b1"
    code          = "d967868a-144e-49ed-921f-c27b65dda06a"
    obj = wst(client_id,client_secret)
    obj.start()
    # Manually get the access token
    #obj.get_access_token(client_id,client_secret,code)
    LOGGER.info("Waiting for code...");
    while obj.code == False:
        time.sleep(1)
    obj.GetTagManagers()
    while True:
        time.sleep(1)
