import numpy as np

defaultSampleRate = 1e6

class Unit:
    def __init__(self,name,xScale,yScale):
        self.name = name
        self.xScale = xScale
        self.yScale = yScale
        
    def unitToVolt(self,val):
        return val/xScale, val/yScale
        
    def voltToUnit(self,val):
        return val*xScale, val*yScale

    def __eq__(self, other):
        return self.name == other.name and self.xScale == other.xScale and self.yScale == other.yScale

defaultUnit = Unit("mV",1e-3,1e-3)

class ScanRegion:
    def __init__(self,x,y,width,height,rotation=0.0,unit=defaultUnit):
        self.x = x
        self.y = y
        self.w = width
        self.h = height
        self.rot = rotation
        self._calcRegion()
        self.unit = unit
    
    def point(self,pointname = "middle"):
        if pointname is "middle":
            return np.array([self.x,self.y])
        if pointname is "upLeft":
            return np.array([self.reg[0],self.reg[3]])
        if pointname is "upRight":
            return np.array([self.reg[2],self.reg[3]])
        if pointname is "downLeft":
            return np.array([self.reg[0],self.reg[1]])
        if pointname is "downRight":
            return np.array([self.reg[2],self.reg[1]])
    
    def pointVolt(self,pointname = "middle"):
        return self.point(pointname)*np.array([self.unit.xScale,self.unit.yScale])
    
    def width(self):
        return self.w
        
    def widthVolt(self):
        return self.width()*self.unit.xScale
    
    def height(self):
        return self.h
        
    def heightVolt(self):
        return self.height()*self.unit.yScale
    
    def rotation(self):
        return self.rot
        
    def region(self):
        return np.asarray(self.reg)
        
    def regionVolt(self):
        return self.region()*np.array([self.unit.xScale,self.unit.yScale,self.unit.xScale,self.unit.yScale])
    
    def _calcRegion(self):
        X = .5*(abs(self.height()*np.sin(-self.rotation()))+abs(self.width()*np.cos(-self.rotation())))
        Y = .5*(abs(self.width()*np.sin(-self.rotation()))+abs(self.height()*np.cos(-self.rotation())))
        self.reg = [self.x-X,self.y-Y,self.x+X,self.y+Y]
        
        
    def setX(self,x):
        self.x = x
        self._calcRegion()

    def setY(self,y):
        self.y = y
        self._calcRegion()
        
    def setWidth(self,width):
        self.w = width
        self._calcRegion()
        
    def setHeight(self,height):
        self.h = height
        self._calcRegion()
        
    def setRotation(self,rotation):
        self.rot = rotation
        self._calcRegion()
        
    def setRotationDeg(self,rotation):
        self.setRotation(rotation/180.0*np.pi)
        
    def __eq__(self,other):
        return self.x == other.x\
                and self.y == other.y\
                and self.w == other.w\
                and self.h == other.h\
                and self.rot == other.rot\
                and self.unit == other.unit

class ScanDescriptor:
    def __init__(self,name,scanRegion,duration,samplerate=defaultSampleRate):
        #voltageRange of the scan [x_min,y_min,x_max,y_max]
        self.scanRegion = scanRegion
        self.name = name
        self.duration = duration
        self.samplerate = samplerate
        self.clearSegments()
        self.holdPosStart = [0,0]
        self.holdPosEnd = [1,1]
        self.patternPath = ""
        self.parameterName = None
        self.parameterValue = None
    
    def setHoldPosStart(self,pos):
        self.holdPosStart = pos
    
    def rotOuterRegion(self):
        return np.array([self.scanRegion.point("middle")-self._rotScale(),\
                        self.scanRegion.point("middle")+self._rotScale()]).ravel()
                
    def setHoldPosEnd(self,pos):
        self.holdPosEnd = pos
    
    def setScanRegion(self,region):
        self.scanRegion = region
        
    def setDuration(self,duration):
        self.duration = duration
        
    def setDurationMs(self,duration):
        self.setDuration(duration*1e-3)
    
    def addSegment(self,data,name,rep=1,channel=1):
        assert (data.min() >= 0 and data.max() <= 1)
        if channel == 1:
            self.segsCh1.append({"name":name, "data":data, "rep":rep})
        if channel == 2:
            self.segsCh2.append({"name":name, "data":data, "rep":rep})
    
    def loadSegmentsFromFile(self,filename,samplerate=None):
        if samplerate == None:
            samplerate = self.samplerate
        self.clearSegments()
        if self.patternPath != filename:
            self.parameterName = None
        scriptEnv = {"__builtins__": __builtins__, "np": np, "scan": self, "samples":round(self.duration*samplerate)}
        execfile(filename, scriptEnv)
        self.patternPath = filename
    
    def reloadSegmentsFromFile(self,samplerate=None):
        if self.patternPath != None:
            self.loadSegmentsFromFile(self.patternPath,samplerate)
            
    def registerParameter(self,name,initialValue):
        if self.parameterName != name or self.parameterValue == None:
            self.parameterName = name
            self.parameterValue = initialValue
        return self.parameterValue
    
    def hasParameter(self):
        if self.parameterName:
            return self.parameterName, self.parameterValue
        return None
    
    def setParameter(self,value):
        if self.parameterName:
            
            self.parameterValue = value
    
    def getSegments(self,channel=1):
        if channel == 1:
            return self.segsCh1
        else:
            return self.segsCh2
    
    def getXYData(self):
        return np.asarray([[elm  for seg in self.segsCh1 for rep in [seg['data']]*seg['rep'] for elm in rep],\
                [elm  for seg in self.segsCh2 for rep in [seg['data']]*seg['rep'] for elm in rep]])
        
    def getXYDataRotated(self):
        pattern = self.getXYData()-0.5
        scaleFactor = (float(self.scanRegion.height())/float(self.scanRegion.width()))
        a = -self.scanRegion.rotation()
        scaledPattern = np.array([pattern[0],pattern[1]*scaleFactor])
        rotatedPattern= np.dot(np.array([[np.cos(a), -np.sin(a)],\
                                         [np.sin(a), np.cos(a)]]),scaledPattern)
        
        xSize= abs(scaleFactor*np.sin(a))+abs(np.cos(a))
        ySize = abs(np.sin(a))+abs(scaleFactor*np.cos(a))
        
        return (np.array([(rotatedPattern[0])*1/xSize+.5,(rotatedPattern[1])*1/ySize+.5]))
        
        
    def add2DSegment(self,xData,yData,name,rep=1):
        self.addSegment(xData,"X%s"%name,rep,channel=1)
        self.addSegment(yData,"Y%s"%name,rep,channel=2)
        
    def clearSegments(self):
        self.segsCh1 = []
        self.segsCh2 = []
    
    def __eq__(self,other):
        return self.scanRegion == other.scanRegion\
            and self.name == other.name\
            and self.duration == other.duration\
            and self.samplerate == other.samplerate\
            and self.holdPosStart == other.holdPosStart \
            and self.holdPosEnd == other.holdPosEnd \
            and self.patternPath == other.patternPath \
            and self.parameterName == other.parameterName \
            and self.parameterValue == other.parameterValue 
    
class ScanSequence:
    def __init__(self,name="seq",unit=defaultUnit,samplerate=defaultSampleRate):
        self.scans = []
        self.samplerate = samplerate
        self.unit = unit
        self.name = name
        
    def addScan(self,scan):
        if scan.samplerate != self.samplerate:
            raise Exception("Samplerate of the scan %s does not match the samplerate of the sequence"%(scan.name))
        if not scan.scanRegion.unit == self.unit:
            print scan.scanRegion.unit.name
            print self.unit.name
            raise Exception("Unit of the scan %s does not match the unit of the sequence"%(scan.name))
        self.scans.append(scan)
        
    def getBoundaries(self):
        """
        Return the region to be updated in Volts
        """
        if len(self.scans) > 1:
            regions = np.asarray([scan.scanRegion.regionVolt() for scan in self.scans])
            return np.array([regions[:,0].min(),regions[:,1].min(),regions[:,2].max(),regions[:,3].max()])
        else:
            return self.scans[0].scanRegion.regionVolt()


if __name__ == "__main__":
    import pylab as pl
    
    scan1 = ScanDescriptor("scan",ScanRegion(0,0,100,100),0.182)
    scan1.loadSegmentsFromFile("pattern/scanEclex.pat")
    
    scan2 = ScanDescriptor("scan",ScanRegion(0,0,100,100),0.1)
    scan2.loadSegmentsFromFile("pattern/scan100.pat")
    
    pl.plot(*scan1.getXYDataRotated())
    pl.xlim(0,1)
    pl.ylim(0,1)
    pl.show()
