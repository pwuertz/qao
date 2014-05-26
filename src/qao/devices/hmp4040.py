'''
Created on Sep 9, 2013

@author: tlausch
'''
import serial
import numpy

class HMP4040(object):
    '''
    The HMP4040 is a programmable power supply by Rhode & Schwarz
    This class implements communcation via the HP0720 USB device
    Basically the linux kernel after 2.7 will use ftdi_sio by default.
    an earlier configuration has to be adobted as described in http://www.hameg.com/646.0.html?&L=1
    any value will be given in the corresponding units voltage -> 1V and current -> 1A
    
    mistakes:
    - make sure the current user belongs to group dialout
    - make sure that the device listens to USB / RS232 interface
    - baudrate determined by the RS232 settings of the device
    '''

    __TIMEOUT__ = 1.0 #timeout for the serial communication
    __BAUDRATE__ = 115200 #max baudrate for the serial interface. keep in mind the usb baudrate equals the serial com baudrate. for serial com is the only one customizable in UI  
    __CHANNEL__ = ["OUTP1","OUTP2","OUTP3","OUTP4"] #available channel names
    __OVPMODES__ = ["MEAS","PROT"] #over voltage proction modes. either measured or adjusted voltage
    __MINFUSEDELAY__ = 0.0 #minimum delay for triggering the fuse
    __MAXFUSEDELAY__ = 250.0 #maximum delay for triggering the fuse
    __MAXREPETITIONS__ = 255 #maximum amount of arbitrary waveform repeptitions
    __MAXTIMEPOINTS__ = 128 #maximum amount of points within an arbitrary waveform 
    
    def __init__(self, port, baud=__BAUDRATE__, timeout=__TIMEOUT__):
        '''
        Opens Serial Connection 8N1
        '''
        self.port = port
        self.baud = baud
        self.com = serial.Serial(port,baud)
        self.com.setByteSize(8)
        self.com.setParity('N')
        self.com.setStopbits(1)
        self.com.setTimeout(timeout)
        if(not self.com.isOpen()):
            raise serial.serialutil.SerialException("Could not open device %s"%port)
        try:
            self.__id = self.read("*IDN?")
            self.__ver = self.read("SYST:VERS?")
        except Exception as ex:
            raise ex
    
    @property
    def error(self):
        return self.read("SYST:ERR?")
    
    @property
    def measuredVoltage(self):
        volt = float(self.read("MEAS:VOLT?"))
        return volt
    @property
    def measuredCurrent(self):
        curr = float(self.read("MEAS:CURR?"))
        return curr
    
    @property
    def ver(self):
        '''
        the device's firmware version
        '''
        return self.__ver
    
    @property
    def id(self):
        '''
        the device's name
        '''
        return self.__id

    @property
    def selectedChannel(self):
        return self.read("INST:SEL?")
    
    def read(self,command):
        self.send(command)
        return self.com.readline().rstrip()
    def send(self,command):
        self.com.write(command+"\n")
    def reset(self):
        self.send("*RST")
        
    def select(self,channel):
        '''
        selects the specified channel
        :param channel: a channel contained in self.__CHANNEL__
        '''
        if(type(channel) is int):
            _channel = self.__CHANNEL__[channel]
        else:
            _channel = str(channel)
        if(_channel in self.__CHANNEL__):
            self.send("INST:SEL "+_channel)
        else:
            raise KeyError("No such channel %s in available channels %s "%(_channel,str(self.__CHANNEL__)))
    
    @property
    def defaultVoltage(self):
        voltage = float(self.read("SOUR:VOLT:LEV:AMPL? DEF"))
        return voltage
    @property
    def minVoltage(self):
        voltage = float(self.read("SOUR:VOLT:LEV:AMPL? MIN"))
        return voltage
    @property
    def maxVoltage(self):
        voltage = float(self.read("SOUR:VOLT:LEV:AMPL? MAX"))
        return voltage
        
    def getVoltage(self):
        voltage = float(self.read("SOUR:VOLT:LEV:AMPL?"))
        return voltage
    def setVoltage(self,voltage):
        self.send("SOUR:VOLT:LEV:IMM:AMPL "+str(voltage))
    
    def getVoltageIncrement(self):
        _voltageIncrement = float(self.read("SOUR:VOLT:LEV:AMPL:STEP:INCR?")) 
        return _voltageIncrement        
    def setVoltageIncrement(self,increment):
        _increment = abs(increment)
        self.send("SOUR:VOLT:LEV:AMPL:STEP:INCR %f"%_increment)
    
    
    def rampVoltage(self,voltage,increment):
        self.setVoltageIncrement(increment)
        self.setVoltage(voltage)
        
    @property
    def defaultCurrent(self):
        _current = float(self.read("SOUR:CURR:LEV:AMPL? DEF"))
        return _current
    @property
    def minCurrent(self):
        _current = float(self.read("SOUR:CURR:LEV:AMPL? MIN"))
        return _current
    @property
    def maxCurrent(self):
        _current = float(self.read("SOUR:CURR:LEV:AMPL? MAX"))
        return _current
    
    def getCurrent(self):
        _current = float(self.read("SOUR:CURR:LEV:AMPL?"))
        return _current
    def setCurrent(self,current):
        self.send("SOUR:CURR:LEV:IMM:AMPL "+str(current))
    
    def getCurrentIncrement(self):
        _currentIncrement = float(self.read("SOUR:CURR:LEV:AMPL:STEP:INCR?")) 
        return _currentIncrement        
    def setCurrentIncrement(self,increment):
        _increment = abs(increment)
        self.send("SOUR:CURR:LEV:AMPL:STEP:INCR %f"%_increment)
    
    def apply(self,voltage,current):
        self.current = current
        self.voltage = voltage
        '''
        !!be aware that handbooks apply doens't work properly!!
        self.send("APPL %f %f")%(voltage,current))
        '''
    def applied(self):
        appl = self.read("APPL?")
        return appl
    
    def rampCurrent(self,current,increment):
        self.setCurrentIncrement(increment)
        self.setCurrent(current)
        
    def turnOn(self,_channel=None):
        if(self.__ver > 2.0):
            if(_channel != None):
                self.send("OUTP:SEL 0")
                for _chan in _channel:
                    self.select(_chan)
                    self.send("OUTP:SEL 1")
            self.send("OUTP:GEN 1")
        else:
            raise Exception("ATTENTION: Turn ON Only available for FIRMWARE > 2.0")
        '''
        Turns all previously selected channel on
        
        ATTENTION: Only available for FIRMWARE > 2.0
        '''
        
    def turnOff(self,_channel=None):
        if(self.__ver > 2.0):
            if(_channel != None):
                self.send("OUTP:SEL 0")
                for _chan in _channel:
                    self.select(_chan)
                    self.send("OUTP:SEL 1")
            self.send("OUTP:GEN 0")
        else:
            raise Exception("ATTENTION: Turn ON Only available for FIRMWARE > 2.0")
        '''
        Turns all previously selected channel off
        
        ATTENTION: Only available for FIRMWARE > 2.0
        '''
        
    def getOVP(self):
        '''
        returns the current level for ovp
        '''
        ovp = float(self.read("VOLT:PROT:LEV?"))
        return ovp
    def setOVP(self,voltage):
        '''
        assigns the current level for ovp
        '''
        self.send("VOLT:PROT:LEV %f"%voltage)
    
    def getOVPMode(self):
        return self.read("VOLT:PROT:MODE?")
    def setOVPMode(self,mode):
        if mode in self.__OVPMODES__:
            self.send("VOLT:PROT:MODE %s"%mode)
        else:
            raise KeyError("no such mode %s in available protection modes %s"%(mode,str(self.__OVPMODES__)))
    
    def ovpTripped(self):
        '''
        returns True in case that the ovp has been exceeded
        '''
        return self.read("VOLT:PROT:TRIP?")
    def ovpClear(self):
        '''
        this will reset the ovp ovpTripped flag
        '''
        self.send("VOLT:PROT:CLE")
    
    
    def on(self):
        '''
        Turns the current selected Channel on
        '''
        self.state = True
    def off(self):
        '''
        Turns the current selected Channel off
        '''
        self.state = False
    def isOn(self):
        return self.getState()
    def getState(self):
        return self.read("OUTP:STAT?") == "1"
    def setState(self,on):
        if(on):
            self.send("OUTP:STAT 1")
        else:
            self.send("OUTP:STAT 0")
    
    def getFuse(self):
        _fuse = self.read("FUSE:STATE?")
        return _fuse == "1"
    def setFuse(self,value):
        if(value):
            self.send("FUSE:STATE 1")
        else:
            self.send("FUSE:STATE 0")
    
    def fuseTripped(self):
        '''
        returns true in case that the fuse for the current channel has been tripped
        '''
        _fuseTripped = self.read("FUSE:TRIP?")
        return _fuseTripped == "1"
    
    def getFuseDelay(self):
        '''
        returns the delay before triping the fuse in ms
        '''
        _fuseDelay = float(self.read("FUSE:DEL?"))
        return _fuseDelay
    def setFuseDelay(self,value):
        '''
        Sets a delay before triping the fuse
        :param value: time delay in ms
        '''
        if value >= self.__MINFUSEDELAY__ and value < self.__MAXFUSEDELAY__:
            self.send("FUSE:DEL %f"%value)

    def fuseLinked(self,_channel):
        '''
        Is the current fuse linked to channel _channel
        :param _channel: index of the channel
        '''
        if(type(_channel) is int):
            linked = self.read("FUSE:LINK? %i"%(_channel+1))
            return linked == "1"
        else:
            channelnumber = self.getChannelIndex(_channel)
            linked = self.read("FUSE:LINK? %i"%channelnumber)
            return linked == "1"
    def linkFuse(self,_channel):
        '''
        Link the current fuse to another channel
        :param _channel: index of the channel
        '''
        if(type(_channel) is int):
            self.send("FUSE:LINK %i"%(_channel+1))
        else:
            channelnumber = self.getChannelIndex(_channel)
            self.send("FUSE:LINK %i"%channelnumber)
    def unlinkFuse(self,_channel):
        '''
        Unlink the current fuse from channel
        :param _channel: index of the channel
        '''
        if(type(_channel) is int):
            self.send("FUSE:UNL %i"%(_channel+1))
        else:
            channelnumber = self.getChannelIndex(_channel)
            self.send("FUSE:UNL %i"%channelnumber)
        
    def save(self,slot):
        '''
        saves the current settings to slot number
        :param slot: the slot to save must be in range(1,11)
        '''
        self.send("*SAV %i"%slot)
    def load(self,slot):
        '''
        loads settings stored to slot number
        :param slot: the slot to load must be in range(1,11)
        '''
        self.send("*RCL %i"%slot)
    
    def getChannelIndex(self,_channel):
        '''
        returns the correct index for the channel name
        :param _channel: name of the channel
        '''
        if(_channel in self.__CHANNEL__):
            return self.__CHANNEL__.index(_channel)+1
        else:
            raise KeyError("no Such Channel %s in Channels %s"%(_channel,str(self.__CHANNEL__)))
        
    def arbStop(self,_channel=None):
        '''
        stops the arbitrary waveform on _channel
        :param _channel: per default, the selected channel is used
        '''
        if(_channel == None):
            _channel = self.getChannelIndex(self.selectedChannel())
        elif(type(_channel) is int):
            _channel += 1
        else:
            _channel = self.getChannelIndex(_channel)
        self.send("ARB:STOP %i"%_channel)
        
    def arbTransfer(self,_channel=None):
        '''
        transfers the arbitrary waveform on _channel
        :param _channel: per default, the selected channel is used
        '''
        if(_channel == None):
            _channel = self.getChannelIndex(self.selectedChannel())
        elif(type(_channel) is int):
            _channel += 1
        else:
            _channel = self.getChannelIndex(_channel)
        self.send("ARB:TRAN %i"%_channel)
        
    def arbStart(self,_channel=None):
        '''
        starts the arbitrary waveform on _channel
        :param _channel: per default, the selected channel is used
        '''
        if(_channel == None):
            _channel = self.getChannelIndex(self.selectedChannel())
        elif(type(_channel) is int):
            _channel += 1
        else:
            _channel = self.getChannelIndex(_channel)
        self.send("ARB:STAR %i"%_channel)
    
    def arbSave(self,_store):
        '''
        Saves the last transmitted arbitrary data to storage
        :param _store: Storage must be in range(1,4)
        '''
        self.send("ARB:SAVE %i"%_store)
    
    def arbRestore(self,_store):
        '''
        Loads stored data in order to transfer it to an channel
        :param _store: Storage must be in range(1,4)
        '''
        self.send("ARB:REST %i"%_store)
    
    def setArbRepetitions(self,_rep):
        '''
        Assigns the nummber of repetitions for an arbitrary sequence
        :param _rep: must be < 255 | self.__MAXREPETITIONS__; 0 equals infinite repetition
        '''
        self.send("ARB:REP %i"%_rep)
        if _rep > self.__MAXREPETITIONS__:
            print "WARNING: max of %i Repetitions breached. Consider using 0 and stopping the power supply at the end of the waveform" % self.__MAXREPETITIONS__
    
    def getArbRepetitions(self):
        '''
        returns the current repetition of a channel
        '''
        rep = int(self.read("ARB:REP?"))
        return rep
    
    def arbClear(self):    
        '''
        clears the arbitrary data storage
        '''
        self.send("ARB:CLE")
    
    def arbData(self,data):
        '''
        transfers the given data to the device
        it has to be an float[3] numpy array
        data[0,:] gives the voltage
        data[1,:] gives the current
        data[2,:] gives the holding time for the corresponding (voltage,current) set must be greater than 10ms
        :param data: numpy.array(data, dtype=numpy.float,ndmin=3) max self.__MAXTIMEPOINTS__ here 128 points 
        '''
        #reshape data to 1D array [voltage,current,time,voltage2,current2,time2...]
        data = numpy.array(data, dtype=numpy.float,ndmin=3)
        shape = data.shape
        if(shape[1] >= self.__MAXTIMEPOINTS__):
            raise AttributeError("Maximum of %i points breached"%self.__MAXTIMEPOINTS__)
        data = data.ravel()
        
        #and join them comma separated
        datastr = ','.join([`num` for num in data])
        print datastr
        self.send("ARB:DATA "+datastr)
        
      
    ovp = property(getOVP,setOVP)
    ovpMode = property(getOVPMode,setOVPMode)        
    voltage = property(getVoltage,setVoltage)
    voltageIncrement = property(getVoltageIncrement,setVoltageIncrement)
    current = property(getCurrent,setCurrent)
    currentIncrement = property(getCurrentIncrement,setCurrentIncrement)
    state = property(getState,setState)
    fuse = property(getFuse,setFuse)
    fuseDelay = property(getFuseDelay,setFuseDelay)
    repetitions = property(getArbRepetitions,setArbRepetitions)
    def open(self):
        '''
        Opens the communication with the serial port
        '''
        if not self.com.isOpen:
            self.com.open()
    def close(self):
        '''
        Closes the communication with the serial port
        '''
        if self.com.isOpen:
            self.com.close()
    
    
    
if __name__ == '__main__':
    
    poco = HMP4040("/dev/ttyUSB0")
    poco.reset()
    print("Device: %s \n Firmware %s"+str((poco.id,poco.ver)))
    print(poco.selectedChannel)
    try:
        poco.select("OUT1")
    except Exception as ex:
        print(ex)
    
    for i in range(len(poco.__CHANNEL__)):
        poco.select(i)
        print("SELECT %i: %s"%(i,poco.selectedChannel))
        
    for chan in poco.__CHANNEL__:
        poco.select(chan)
        if(poco.selectedChannel != str(chan)):
            print("FAIL %s != %s" %(poco.selectedChannel,str(chan)))
        else:
            print("OK %s == %s" %(poco.selectedChannel,str(chan)))
            
    print("VOLTAGE %f"%poco.voltage)
    poco.voltage = 1.1
    print("VOLTAGE set to %f "%poco.getVoltage())    
    print("INCREMENT: %f"%poco.voltageIncrement)
    
    print("Voltage(default,min,max): "+str((poco.defaultVoltage,poco.minVoltage,poco.maxVoltage)))
    print("Current(default,min,max): "+str((poco.defaultCurrent,poco.minCurrent,poco.maxCurrent)))
    
    poco.rampVoltage(3.0, 0.1)
    print("VOLTAGE,INCREMENT: (%f,%f)"%(poco.voltage,poco.voltageIncrement))

    print("CURRENT %f"%poco.current)
    poco.current = 0.1
    print("CURRENT set to %f "%poco.getCurrent())    
    print("INCREMENT: %f"%poco.currentIncrement)
    
    poco.rampCurrent(0.5, 0.1)
    print("current,increment: (%f,%f)"%(poco.current,poco.currentIncrement))
    poco.select(3)
    poco.apply(5,0.15)
    print("voltage,current: (%f,%f)"%(poco.voltage,poco.current))
    print("applied: "+str(poco.applied()))
    
    poco.select(3)
    print("STATE: %s"%poco.state)
    poco.turnOn([1,2,3])
    print("turned On state: %s"%poco.state)
    poco.turnOff([0,3])
    print("turned OFF state: %s"%poco.state)
    poco.state = True
    print("turned On state: %s"%poco.state)
    poco.state = False
    print("turned OFF state: %s"%poco.state)
    print("has the OVP been ovpTripped? %s"%poco.ovpTripped())
    print("OVP Mode: %s"%poco.ovpMode)
    poco.ovpMode = poco.__OVPMODES__[1]
    print("OVP Mode[1]: %s"%poco.ovpMode)
    print("OVP level: %f"%poco.ovp)
    poco.ovp = 4.0
    print("OVP level set To 4.0: %f"%poco.ovp)
    poco.on()
    print("OVP level: %f where voltage is %f"%(poco.ovp,poco.voltage))
    print("has the OVP been ovpTripped? %s"%poco.ovpTripped())
    poco.voltage = 3.5
    poco.on()
    print("OVP level: %f where voltage is %f"%(poco.ovp,poco.voltage))
    print("has the OVP been ovpTripped? %s"%poco.ovpTripped())
    poco.off()
    
    print "fuse: %i"%poco.fuse
    poco.fuse = not poco.fuse
    print "toggled fuse: %i"%poco.fuse
    print "fuseDelay: %d"%poco.fuseDelay
    poco.fuseDelay = 50
    print "fuseDelay: %d==50"%poco.fuseDelay
    _linkedFuse = 1
    poco.linkFuse(_linkedFuse)
    print "linked Fuse %s"%poco.__CHANNEL__[_linkedFuse]
    
    for _chan in poco.__CHANNEL__:
        print "fuse %s is Linked: %s"%(_chan,str(poco.fuseLinked(_chan)))
    for i in range(len(poco.__CHANNEL__)):
        print "fuse %i is Linked: %s"%(i,str(poco.fuseLinked(i)))
        
    try:
        poco.fuseLinked("test")
    except KeyError as ex:
        print ("caugth KeyError properly")
        
    print "unlinked Fuse %s"%poco.__CHANNEL__[_linkedFuse]
    poco.unlinkFuse(poco.__CHANNEL__[_linkedFuse])
    
    for i in range(len(poco.__CHANNEL__)):
        print "fuse %i is Linked: %s"%(i,str(poco.fuseLinked(i)))
    
    #example for generating custom data
    
    data = [[0,0,.2]]
    I = 0.1
    dI = .1*I
    U = 1.0
    dU = .1*U
    t = 1.0
    dt = .001
    sign = 1.0
    for i in range(125):
        sign *= -1.0
        I -= dI*sign
        U -= dU*sign
        t -= dt
        print("%i :time,sign = %f,%f"%(i,t,sign))
        data.append([U,I,t])
    poco.arbData(data)
    print("arbData errors: %s"%poco.error)
    poco.arbRepetitions(50)
    print("arbRepetitions errors: %s"%poco.error)
    poco.arbTransfer(0)
    print("arbTransfer errors: %s"%poco.error)
    poco.arbStart(0)
    print("arbStart errors: %s"%poco.error)
    poco.select(0)
    print("select errors: %s"%poco.error)
    poco.on()
    print("on errors: %s"%poco.error)
    try:
        for i in range(100):
            #time.sleep(.5)
            print("repetition: %i"%poco.repetition)
    finally:
        poco.close()