try:
    import OpenOPC
except:
    print "You don't have OpenOPC installed. You can only use the dummy class"
import time
import numpy as np

srvNameDefault = 'iseg.OPCServer.DA.6'
hostDefault = 'localhost'
waittimeDefault = 1

class VoltageSupply:

    def _readChannelsProperty_(self,chanList,attribute):
        raise NotImplementedError("Implement function _readChannelsProperty for child classes")

    def _writeChannelsProperty_(self,chanList,attribute):
        raise NotImplementedError("Implement function _writeChannelsProperty for child classes")

    #Voltage functions
    
    def readVSet(self, chanList):
        return self._readChannelsProperty_(chanList,'VSet')

    def writeVSet(self,voltDict):
        self._writeChannelsProperty_(voltDict,'VSet')

    def readVMeas(self, chanList):
        return self._readChannelsProperty_(chanList,'VMeas')

    def readNominalV(self, chanList):
        return self._readChannelsProperty_(chanList,'NominalV')

    #Current functions

    def readISet(self, chanList):
        return self._readChannelsProperty_(chanList,'ISet')

    def writeISet(self,voltDict):
        self._writeChannelsProperty_(voltDict,'ITrip')

    def readITrip(self, chanList):
        return self._readChannelsProperty_(chanList,'ITrip')

    def writeITrip(self,voltDict):
        self._writeChannelsProperty_(voltDict,'ISet')

    def readIMeas(self, chanList):
        return self._readChannelsProperty_(chanList,'IMeas')

    def readNominalI(self, chanList):
        return self._readChannelsProperty_(chanList,'NominalI')

    #Status functions

    def readStatus(self, chanList):
        return self._readChannelsProperty_(chanList,'Status')

    def readStat(self, chanList):
        return self._readChannelsProperty_(chanList,'Stat')

    def readOn(self, chanList):
        return self._readChannelsProperty_(chanList,'On')

    def writeOn(self,onDict):
        self._writeChannelsProperty_(onDict,'On')

    def close(self):
        return

class ISegDummy(VoltageSupply):
    def __init__(self,canNum,modNum,host=hostDefault,srvName=srvNameDefault):
        self.canNum = canNum
        self.modNum = modNum
        numChannels = 8
        self.properties = {}
        propNames = ['VSet', 'VMeas', 'NominalV', 'ISet', 'ITrip', 'IMeas', 'NominalI', 'On', 'Status', 'Stat']
        for prop in propNames:
            self.properties.update({prop:np.zeros(numChannels)})

    def _readChannelsProperty_(self,chanList,attribute):
        values = {}
        for chan in chanList:
            values.update({chan:self.properties[attribute][chan]})
        return values

    def _writeChannelsProperty_(self,valueDict,attribute):
        for key,val in valueDict.items():
            self.properties[attribute][key] = val


class ISeg(VoltageSupply):
    def __init__(self,canNum,modNum,host=hostDefault,srvName=srvNameDefault):
        self.canNum = canNum
        self.modNum = modNum

        #connect to OPC Server
        self.opc = OpenOPC.open_client(host)
        self.opc.connect(srvName,host)
        time.sleep(waittimeDefault)
        assert self.opc.ping()


    def readCANStatus(self):
        val,qual,time = self.opc.read('Status.CAN')
        if qual == "Good":
            return val
        else:
            return None

    def _readChannelsProperty_(self,chanList,attribute):
        reqList = ["can%01i.ma%02i.ch%02i.%s"%(self.canNum,self.modNum,chan,attribute) for chan in chanList]
        values = {}
        for i,(name,val,qual,time) in enumerate(self.opc.read(reqList)):
            if qual=="Good": values.update({i:val})
        return values

    def _writeChannelsProperty_(self,valueDict,attribute):
        reqList = []
        for key,val in valueDict.items():
            reqList.append(("can%01i.ma%02i.ch%02i.%s"%(self.canNum,self.modNum,key,attribute),val))
        self.opc.write(reqList)
    
    def close(self):
        self.opc.close()


if __name__ == "__main__":
    iseg = ISeg(0,1)
    iseg.writeVSet({0:0., 1:0.})
    
    for i in range(3):
        #print iseg.readCANStatus()
        print 'VSet', iseg.readVSet(range(7))
        print 'VMeas', iseg.readVMeas(range(7))
        print 'IMeas', iseg.readIMeas(range(7))
        print
        time.sleep(.5)
    iseg.close()
        
        
