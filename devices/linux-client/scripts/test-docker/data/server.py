from RangeHTTPServer import RangeRequestHandler
import http.server as SimpleHTTPServer
import argparse
import os

req_num = 0

class ConnectionTimeoutRequestHandler(RangeRequestHandler):
    def copyfile(self, source, outputfile):
        global req_num
        source_size = os.path.getsize(source.name)
        # The first request is dropped after 80% of the bytes sent
        # This is supposed to simulate a connection drop for the update caching test
        if req_num == 0:
            self.range = (self.range[0], int(self.range[0] + ((source_size - self.range[0]) * 0.8)) )
        super().copyfile(source, outputfile)
        req_num += 1


parser = argparse.ArgumentParser()
parser.add_argument('port', action='store',
                    default=8000, type=int,
                    nargs='?', help='Specify alternate port [default: 8000]')

args = parser.parse_args()
SimpleHTTPServer.test(HandlerClass=ConnectionTimeoutRequestHandler, port=args.port)
