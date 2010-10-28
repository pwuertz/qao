#!/usr/bin/python
# -*- coding: utf-8 -*-

import socket, numpy, sys

class AgilentFuncGen:
    __BUFSIZE__ = 1024
    __TIMEOUT__ = 4.0
    __DEFPORT__ = 5025
    
    def __init__(self, host, debug=False):
        self.__sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.__sock.setblocking(True)
        self.__sock.settimeout(self.__TIMEOUT__)
        self._sock = self.__sock
        self.__host = host
        self.__debug = debug
    
    def setHostname(self, hostname):
        self.__host = hostname
        
    def connect(self):
        self.__sock.connect((self.__host, self.__DEFPORT__))
        
    def disconnect(self):
        self.__sock.close()
        
    def errorcheck(self):
        self.__sock.sendall("syst:err?\n")
        error = self.__sock.recv(self.__BUFSIZE__).rstrip()
        err_id, err_str = error.split(",")
        if int(err_id) != 0:
            raise Exception(err_str)
        
    def send(self, command):
        self.__sock.sendall(command + "\n")
        if self.__debug: self.errorcheck()
        
    def query(self, command):
        self.__sock.send(command + "\n")
        result = self.__sock.recv(self.__BUFSIZE__).rstrip()
        if self.__debug: self.errorcheck()
        return result
    
    def reset(self):
        self.send("*rst")
    
    def voltHigh(self, value=None, unit="V"):
        if value == None:
            return float(self.query("volt:high?"))
        else:
            self.send("volt:high %f %s" % (float(value), unit))
            
    def voltLow(self, value=None, unit="V"):
        if value == None:
            return float(self.query("volt:low?"))
        else:
            self.send("volt:low %f %s" % (float(value), unit))
            
    def voltAmplitude(self, value=None, unit="V"):
        if value == None:
            return float(self.query("volt:amplitude?"))
        else:
            self.send("volt:amplitude %f %s" % (float(value), unit))
            
    def voltOffset(self, value=None, unit="V"):
        if value == None:
            return float(self.query("volt:offs?"))
        else:
            self.send("volt:offs %f %s" % (float(value), unit))
            
    def frequency(self, value=None):
        if value == None:
            return float(self.query("freq?"))
        else:
            self.send("freq %.3f" % float(value))
            
    def period(self, value=None, unit="s"):
        if value == None:
            return float(self.query("puls:per?"))
        else:
            self.send("puls:per %.9f %s" % (float(value), unit))
            
    def setInverted(self, inverted):
        if inverted:
            self.send("output:polarity inv")
        else:
            self.send("output:polarity norm")
            
    def isInverted(self):
        return self.query("output:polarity?") == "INV"

    def setTriggeredBurst(self, ncycles = 1):
        """
        Wait for an external trigger and run the configured
        waveform for ncycles (burst mode).
        """
        self.send('burs:mode trig')
        self.send('burs:ncyc %d' % ncycles)
        self.send('trig:sour ext')
        self.send('burs:stat on')
        
    def setOutputLoad(self, load = 50):
        """
        Set the output termination to the specified load (ohms).
        The default is 50 ohms.
        """
        self.send('outp:load %d' % load)
        
    def setOutputHigh(self):
        """
        Set the output termination to high impedance.
        """
        self.send('outp:load inf')
        
    def setEnabled(self, enabled):
        """
        Enable or disable the output of the function generator.
        """
        if enabled:
            self.send('outp on')
        else:
            self.send('outp off')

    def applyRamp(self, freq, amp, off):
        """
        Apply a ramp with specified frequency, amplitude and offset.
        """
        self.send("appl:ramp %.3f, %.3f, %.3f" % (freq, amp, off))
        
    def applyPositiveRamp(self, freq, amp, off):
        """
        Apply a positive linear ramp with specified
        frequency, amplitude and offset.
        """
        self.applyRamp(freq, amp, off)
        self.setInverted(True)
        self.send("func:ramp:symm 0")
        
    def applyNegativeRamp(self, freq, amp, off):
        """
        Apply a negative linear ramp with specified
        frequency, amplitude and offset.
        """
        self.applyRamp(freq, amp, off)
        self.setInverted(False)
        self.send("func:ramp:symm 0")
        
    def applyPositiveRamp2(self, period, high, low):
        """
        Apply a positive linear ramp with specified
        period, low level and high level.
        """
        self.applyPositiveRamp(1./period, high-low, low + 0.5*(high-low))
        self.period(period) # 1/period might be inaccurate
        
    def applyNegativeRamp2(self, period, high, low):
        """
        Apply a negative linear ramp with specified
        period, low level and high level.
        """
        self.applyNegativeRamp(1./period, high-low, low + 0.5*(high-low))
        self.period(period) # 1/period might be inaccurate

    def applyDC(self, volt):
        """
        Apply a DC voltage.
        """
        self.send("appl:dc def, def, %.3f" % volt)

    def clearArb(self):
        """
        Delete all stored arbitrary waveforms.
        """
        self.send("data:del:all")
    
    def addArbNormalized(self, data):
        """
        Add an arbitrary waveform. The data must be an array or a list
        of floats normalized to -1.0,1.0.
        """
        # map [-1:1] to [-8191:8191]
        data = numpy.array(data, numpy.float)
        assert len(data) < 65536, "too many data points"
        data = numpy.clip(data, -1.0, 1.0)
        # convert data to 16bit signed int array
        data = numpy.round(data * 8191).astype(numpy.int16)
        datastr = data.tostring()
        
        # ieee-488.2 block header
        datalen = str(len(datastr))
        header = "#" + str(len(datalen)) + datalen
                         
        # set byte order
        if sys.byteorder == 'little':
            self.send("form:bord swap")
        else:
            self.send("form:bord norm")
        
        # upload data
        self.send("data:dac volatile, " + header + datastr)
        
        # ascii upload (slow)
        #self.send("data:dac volatile, " + ",".join([str(x) for x in data]))
        
    def addArbAbsolute(self, data, unit = "V"):
        data = numpy.array(data, numpy.float)
        
        # normalize data
        dmax = data.max()
        dmin = data.min()
        amp = dmax-dmin
        off = dmin + 0.5*amp
        data_norm = (data-off)/(0.5*amp)
        
        # add arb, set voltages
        self.voltAmplitude(amp, unit)
        self.voltOffset(off, unit)
        self.addArbNormalized(data_norm)
        
    def saveVolatile(self, name):
        self.send("data:copy " + name + ", volatile")
        self.send("data:del volatile")
        
    def applyArb(self, name = "volatile"):
        self.send("func:user " + name)
        self.send("func:shape user")
