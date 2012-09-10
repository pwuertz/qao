"""
MCS
--------------

This module implements a python wrapper for the Ortec MCS-pci device.

The wrapper makes use of the "McbCIO32.dll" which is part of the Ortec
driver installed along with the MCS-32 Software.

.. note::

    This piece of hardware might not be used in the future anymore,
    as a solution using the ADwin realtime system as multichannel buffer
    is being developed.
"""
import time
import ctypes
import numpy
from ctypes import byref

__mcbDriver = None

def getDriver():
    global __mcbDriver
    if not __mcbDriver: __mcbDriver = McbDriver()
    return __mcbDriver

def getDevices():
    drv = getDriver()
    n = drv.getConfigMax()
    devices = [McbDevice(i, drv) for i in range(1,n+1)]
    return devices

class McbDriver:
    def __init__(self):
        self._driver = ctypes.windll.LoadLibrary("McbCIO32.dll")
        assert self._driver.MIOStartup() == 1, "driver not initialized"
    
    def __del__(self):
        self._driver.MIOCleanup()

    def getConfigMax(self):
        # read the number of devices present
        n = ctypes.c_int()
        assert self._driver.MIOGetConfigMax("", byref(n)) == 1
        return n.value
    
    def getConfigName(self, index):
        # read the name of a device
        n_name = 100
        name   = ctypes.create_string_buffer(n_name)
        id = ctypes.c_int()
        outOfDate = ctypes.c_bool()
        assert self._driver.MIOGetConfigName(index, "", n_name, name, byref(id), byref(outOfDate)) == 1
        return name.value, id.value
    
    def openDetector(self, index):
        return self._driver.MIOOpenDetector(index, "", "")
    
    def closeDetector(self, hDet):
        return self._driver.MIOCloseDetector(hDet)
    
    def getDetLength(self, hDet):
        # return the number of channels for a device
        return self._driver.MIOGetDetLength(hDet)

    def getData(self, hDet, startChan, numChans):
        data  = numpy.zeros(numChans, dtype = numpy.int32)
        pdata = data.ctypes.data_as(ctypes.POINTER(ctypes.c_int32)) 
        nRet = ctypes.c_int16()
        dataMask = ctypes.c_int32()
        roiMask  = ctypes.c_int32()
        assert self._driver.MIOGetData(hDet, startChan, numChans, pdata, byref(nRet),
                                       byref(dataMask), byref(roiMask), "") > 0, "getData failed"
        return data
    
    """ # old ctypes buffer method
    def getData(self, hDet, startChan, numChans):
        data = (ctypes.c_int32*numChans)()
        nRet = ctypes.c_int16()
        dataMask = ctypes.c_int32()
        roiMask  = ctypes.c_int32()
        assert self._driver.MIOGetData(hDet, startChan, numChans,
                                       byref(data), byref(nRet),
                                       byref(dataMask), byref(roiMask), "") > 0, "getData failed"
        return data
    """

    def isActive(self, hDet):
        """
        Return TRUE if the detector is collecting data.
        """
        return self._driver.MIOIsActive(hDet)
    
    def isDetector(self, hDet):
        """
        Return TRUE if the detector handle hDet is valid (associated with an open detector).
        """
        return self._driver.MIOIsDetector(hDet)
        
    def comm(self, hDet, cmd):
        """
        Send an instrument command and receive the instrument response.
        """
        n_resp = 128
        resp   = ctypes.create_string_buffer(n_resp)
        cmd = str(cmd)
        assert self._driver.MIOComm(hDet, cmd, "", "", n_resp, resp, 0) == 1, "command failed"
        return resp.value

class McbDevice:    
    def __init__(self, index, mcbDriver):
        self._mcbDriver = mcbDriver
        self._handle = mcbDriver.openDetector(index)
        self._maxChannels = mcbDriver.getDetLength(self._handle)
        self._name = self._mcbDriver.getConfigName(index)[0]
        assert self._handle > 0, "could not open device"
    
    def __del__(self):
        self._mcbDriver.closeDetector(self._handle)
    
    def getName(self):
        return self._name
    
    def getData(self, startChan = 0, numChans = 0):
        if not numChans: numChans = self._maxChannels
        return self._mcbDriver.getData(self._handle, startChan, numChans)
    
    def comm(self, cmd):
        return self._mcbDriver.comm(self._handle, cmd)
    
    def start(self):
        self.comm("START")
        
    def stop(self):
        self.comm("STOP")
        
    def clear(self):
        self.comm("CLEAR")

    def clear_all(self):
        self.comm("CLEAR_ALL")
    
    def setTriggerExternal(self, enabled):
        if enabled: self.comm("ENABLE_TRIGGER")
        else: self.comm("DISABLE_TRIGGER")
        
    def setDwellExternal(self, enabled):
        if enabled: self.comm("ENABLE_DWELL_EXTERNAL")
        else: self.comm("DISABLE_DWELL_EXTERNAL")
    
    def setDwellTime(self, time):
        self.comm("SET_DWELL %e" % time)
    
    def getDwellTime(self):
        return self.comm("SHOW_DWELL")
    
    def setPassLength(self, n):
        assert n > 3 and n < 65536, "invalid number of channels"
        self.comm("SET_PASS_LENGTH %d" % n)
    
    def setPassPreset(self, n):
        assert n > 0, "invalid number of passes"
        self.comm("SET_PASS_PRESET %d" % n)
    def setNumberOfScans(self, n):
        self.setPassPreset(n)
    
    def reset(self):
        self.comm("RESET")
        
    def initialize(self):
        self.comm("INITIALIZE")
        
    def isActive(self):
        if self.comm("SHOW_ACTIVE") == "$C00001088\n": return True
        else: return False
    
    def setPass(self, n):
        self.comm("SET_PASS %d" % n)
    
    def getPass(self):
        return int(self.comm("SHOW_PASS")[2:12])
    
    def getStatus(self):
        sstr = self.comm("SHOW_STATUS")
        status = {"pass": int(sstr[2:12]),
                  "channel": int(sstr[12:22]),
                  "active": int(sstr[22:27]),
                  "stopping": int(sstr[27:32]) }
        return status


# simple test of the driver module
if __name__ == "__main__":
    drv = getDriver()
    print "number of devices found: %d" % drv.getConfigMax()
    devices = getDevices()
    for device in devices:
        print " "*3 + device.getName()
    print "status of the devices:"
    for device in devices:
        print " "*3 + str(device.getStatus())
