import socket, numpy, sys

class Eclex:
    __BUFSIZE__ = 1024
    __TIMEOUT__ = 6.0
    __DEFPORT__ = 25000
    
    def __init__(self, host, sock=None, debug=False):
        socket.setdefaulttimeout(self.__TIMEOUT__)
        self.__sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.__host = host
        self.__debug = debug
        
    def connect(self):
        self.__sock.connect((self.__host, self.__DEFPORT__))
        
    def disconnect(self):
        self.__sock.close()
        
    def send(self, command):
        self.__sock.send(command + "\r")
        
    def query(self, command):
        self.__sock.send(command + "\r")
        result = self.__sock.recv(self.__BUFSIZE__).rstrip()
        return result
    
    def getFcupCurrent(self):
        return float(self.query("fcupcorIM"))
    
    def getEmissionCurrent(self):
        emissionIM = self.query("emissionIM")
        return (0.24425*(4095-int(emissionIM)))
    
    def getBeamCurrent(self):
        beamIM = self.query("beamIM")
        return (100./2047 * int(beamIM))
    