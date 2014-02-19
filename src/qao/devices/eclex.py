"""
Eclex
---------

This module includes tools for interfacing with the Eclex electron microscope
software. Eclex monitors and controls the emission and adjustment of the
electron column using a network connection to the hardware. Also, Eclex exposes
a network service for reading and writing hardware parameters in a controlled
way.

"""

import socket

class Eclex:
    """
    This class simplifies the information exchange from and to the Eclex Software
    controlling the electron microscope. Once connected to Eclex, you can retrieve
    status parameters like the faraday cup current, or modify settings like the
    objective lens current.
    """
    
    __BUFSIZE__ = 1024
    __TIMEOUT__ = 6.0
    __DEFPORT__ = 25000
    
    def __init__(self, host, sock=None, debug=False):
        """
        Creates an Eclex control instance, without connecting
        to the Eclex service yet.
        
        :param host: (str) Hostname of the system running Eclex.
        :param sock: (socket) Optionally reuse a given socket.
        :param debug: (bool) Check for errors after each command.
        
        .. seealso:: :func:`connect`
        """
        socket.setdefaulttimeout(self.__TIMEOUT__)
        self.__sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.__host = host
        self.__debug = debug
        
    def connect(self):
        """
        Connect to the Eclex service.
        
        .. note::
        
            Eclex does not seem to parallelize network connections properly.
            An open network connection will slow down the user interface.
        
        .. seealso:: :func:`disconnect` 
        """
        self.__sock.connect((self.__host, self.__DEFPORT__))
        
    def disconnect(self):
        """
        Disconnect from the Eclex service.
        
        .. seealso:: :func:`connect`
        """
        self.__sock.close()
        
    def send(self, command):
        """
        Low level function. Sends a command to the Eclex service.
        
        You normally don't need to call this method directly.    
        """
        self.__sock.send(command + "\r")
        
    def query(self, command):
        """
        Low level function. Sends a command to the Eclex service
        and waits for an answer.
        
        You normally don't need to call this method directly.    
        """
        self.__sock.send(command + "\r")
        result = self.__sock.recv(self.__BUFSIZE__).rstrip()
        return result
    
    def getFcupCurrent(self):
        """
        :returns: (float) Faraday cup current.
        """
        return float(self.query("fcupcorIM"))
    
    def getEmissionCurrent(self):
        """
        :returns: (float) Emission current.
        """
        emissionIM = self.query("emissionIM")
        return (0.24425*(4095-int(emissionIM)))
    
    def getBeamCurrent(self):
        """
        :returns: (float) Beam current.
        """
        beamIM = self.query("beamIM")
        return (100./2047 * int(beamIM))
    
    def getZoomValue(self):
        """
        :returns: (float) Zoom slider value.
        """
        return float(self.query("zoom_sliderUM"))
    