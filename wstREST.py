#!/usr/bin/env python3

import requests, threading, socketserver, re, socket, time
from http.client import BadStatusLine  # Python 3.x

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
        self.url     = 'http://{0}:{1}'.format(self.server.server_address[0],self.server.server_address[1]))
        self.logger.info("wstREST: Running on: {0}".format(self.url)
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
        self.logger.debug("wstRESTServer:handler: Got {0}".format(data.strip()))
        match = re.match( r'GET /motion/(.*) ', data, re.I)
        if match:
            address = match.group(1)
            self.parent.motion(address,1)
        else:
            self.logger.error("wstREST:handler: Unrecognized socket server command: " + data)


if __name__ == "__main__":
    import logging
    logger = logging.getLogger(__name__)
    logging.basicConfig(
        level=10,
        format='%(levelname)s:\t%(name)s\t%(message)s'
    )
    logger.setLevel(logging.DEBUG)
    rest_server = wstREST(False,logger)
    rest_server.start()
    while True:
        time.sleep(1)
