#!/usr/local/bin/python3.6

"""
Simple Wireless Sensor Tags Object
"""

import logging
import requests
import json

logging.basicConfig(
    level=10,
    format='%(levelname)s:\t%(name)s\t%(message)s'
)
LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.DEBUG)

class wst():

    def __init__(self):
        pass

    def start(self):
        # TODO: This will optionally start a rest server to be the re-direct to read the oauth code.
        pass

    def get_access_token(self,client_id,client_secret,oauth_code):
        aret = self.http_post('oauth2/access_token.aspx',
                              {
                                  'client_id': client_id,
                                  'client_secret': client_secret,
                                  'code': code
                              }, use_token=False)
        # This gives us:
        # {'token_type': 'Bearer', 'access_token': '...', 'expires_in': 9999999}
        self.access_token = aret['access_token']
        self.token_type    = aret['token_type']
        self.l_debug('start',"token_type={} access_token={}".format(self.token_type,self.access_token))

        
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
        
if __name__ == "__main__":
    client_id     = "3b08b242-f0f8-41c0-ba29-6b0478cd0b77"
    client_secret = "0b947853-1676-4a63-a384-72769c88f3b1"
    code          = "d967868a-144e-49ed-921f-c27b65dda06a"
    obj = wst()
    obj.start()
    # Manually get the access token
    obj.get_access_token(client_id,client_secret,code)
    obj.GetTagManagers()
    
    
