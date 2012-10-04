import sys
import atexit
import ctypes

#######################################################################
# dynamic library loading

# TODO: determine OS and load the library accordingly
if sys.platform == 'linux2':
    _lib = ctypes.CDLL("libiowkit.so")
if sys.platform.startswith('win'):
    _lib = ctypes.WinDLL("iowkit")
else:
    NotImplementedError("loading the iowkit library not implemented yet")

#######################################################################
# iowkit definitions and declarations

# TODO: manually declare all function arguments and return types because
# ctypes does not seem to recognize 64bit pointers on its own
_lib.IowKitOpenDevice.restype = ctypes.c_voidp

_lib.IowKitVersion.restype = ctypes.c_char_p

_lib.IowKitGetProductId.argtypes = [ctypes.c_voidp]
_lib.IowKitGetProductId.restype = ctypes.c_ulong

_lib.IowKitRead.argtypes = [ctypes.c_voidp, ctypes.c_ulong, ctypes.c_voidp, ctypes.c_ulong]

_lib.IowKitCloseDevice.argtypes = [ctypes.c_voidp]

_lib.IowKitGetDeviceHandle.argtypes = [ctypes.c_ulong]
_lib.IowKitGetDeviceHandle.restype = ctypes.c_voidp

_lib.IowKitGetNumDevs.restype = ctypes.c_ulong

_lib.IowKitSetTimeout.argtypes = [ctypes.c_voidp, ctypes.c_ulong]

_lib.IowKitReadImmediate.argtypes = [ctypes.c_voidp, ctypes.POINTER(ctypes.c_ulong)]

# TODO: datatypes and definitions
IOW_PIPE_IO_PINS = 0

IOWKIT_PRODUCT_ID_IOW40 = 0x1500
IOWKIT_PRODUCT_ID_IOW24 = 0x1501

class IOWKIT40_IO_REPORT(ctypes.Structure):
    _pack_ = 1
    _fields_ = [("ReportID", ctypes.c_ubyte), ("Value", ctypes.c_uint32)]
IOWKIT40_IO_REPORT_SIZE = ctypes.sizeof(IOWKIT40_IO_REPORT)
assert IOWKIT40_IO_REPORT_SIZE == 5, "struct not aligned correctly"

# TODO: map product ids to correct report types
report_type_map = {
    IOWKIT_PRODUCT_ID_IOW40: (IOWKIT40_IO_REPORT, IOWKIT40_IO_REPORT_SIZE)
}

# always close devices at exit
# maybe ensure driver version _lib.IowKitVersion() >= 1.4 ?
atexit.register(_lib.IowKitCloseDevice, None)

#######################################################################
# pythonic interface

class IowDevice:
    
    # static methods
    is_open = False
    @staticmethod
    def _check_open():
        if not IowDevice.is_open:
            iowh = _lib.IowKitOpenDevice()
            if not iowh:
                raise IOError("No device found")
            IowDevice.is_open = True

    @staticmethod
    def getNumDevices():
        IowDevice._check_open()
        return _lib.IowKitGetNumDevs()
    
    def __init__(self, num_device=0):
        # check if the devices have been opened yet
        IowDevice._check_open()
            
        # check for valid device number
        if num_device not in range(_lib.IowKitGetNumDevs()):
            raise ValueError("Invalid device number")
        
        # check for supported device type
        self.handle = _lib.IowKitGetDeviceHandle(num_device+1)
        pid = _lib.IowKitGetProductId(self.handle)
        if pid not in report_type_map:
            print "pid", pid
            raise NotImplementedError("Unsupported device")
        
        # choose correct report type
        report_type, self.report_size = report_type_map[pid]
        self.report = report_type()    
    
    def setTimeout(self, millisec):
        _lib.IowKitSetTimeout(self.handle, millisec)
    
    def read(self):
        """
        Block until a new pin status is received.
        If a timeout is set, the function returns after the
        maximum waiting time and the value `success` is False.
        
        Returns tuple (pin_values, success).
        """
        n = _lib.IowKitRead(self.handle, IOW_PIPE_IO_PINS,
                            ctypes.byref(self.report), self.report_size)
        success = (n == self.report_size)
        return self.report.Value, success
    
    def readImmediate(self):
        """
        Force reading the pin status.
        
        Return (pin_values, is_new).
        """
        result = ctypes.c_ulong()
        is_new = _lib.IowKitReadImmediate(self.handle, ctypes.pointer(result))
        return result.value, is_new

#######################################################################
# example application

if __name__ == "__main__":
    n =  IowDevice.getNumDevices()
    print "Number of devices found:", n
    print "Waiting for pin changes at device 0 (CTRL+C to cancel)"
    
    # get first device
    iowdev = IowDevice(num_device=0)    
    # get current pin status
    pins, is_new = iowdev.readImmediate()
    # print status in binary
    bin_str = lambda val: "{0:0>{1}}".format(bin(val)[2:], 32)
    print bin_str(pins)
    
    # read pin status forever
    iowdev.setTimeout(500)
    while True:
        pins, read_ok = iowdev.read()
        if read_ok:
            print bin_str(pins)
