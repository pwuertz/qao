from qao.devices.TicoMCS import IonScanSequence,IonSignal
from qao.basics.ScanBasics import Unit,ScanRegion,ScanDescriptor
from qao.io import CSVReader
import os,h5py
import numpy as np
import copy
import scipy.weave as weave

__compiler_args = ["-O3", "-march=native", "-ffast-math", "-fno-openmp"]
__linker_args   = ["-fno-openmp"]
opt_args = {"extra_compile_args": __compiler_args,
            "extra_link_args": __linker_args}

DEFAULT_TYPE_NPY = np.double
DEFAULT_TYPE_C = "double"
DEFAULT_TYPEDEFC = "typedef {0} float_type;\n".format(DEFAULT_TYPE_C)

class DataTooLongException(BaseException):
    pass

def createIonImage(scanDescriptor,ionSignal,bins):
    slowImage, slowxedges, slowyedges = createIonImageSlow(scanDescriptor,ionSignal,bins)
    #cImage, cxedges, cyedges = createIonImageC(scanDescriptor,ionSignal,bins)
    #print slowImage-cImage
    
    
    return slowImage, slowxedges, slowyedges

def createIonImageSlow(scanDescriptor,ionSignal,bins):
    path = scanDescriptor.getXYData()
    if len(ionSignal.rawData) > 0 and ionSignal.rawData.max() > (scanDescriptor.duration*10e7):
        raise DataTooLongException({"message":"Ion gate too long"})
    if len(ionSignal.rawData) < 1:
        return np.zeros(bins), np.linspace(scanDescriptor.scanRegion.width(),0,bins[0]), np.linspace(scanDescriptor.scanRegion.height(),0,bins[1]) 
    data = ionSignal.rawData*1./(scanDescriptor.duration*10e7)*len(path[0])
    X,Y = path[:,data.astype(int)]
    H, xedges, yedges = np.histogram2d(-Y,X, bins=(bins[0],bins[1]),range=((-1,0),(0,1)))
    xedges *= -scanDescriptor.scanRegion.width()
    yedges *= scanDescriptor.scanRegion.height()
    
    return H, xedges, yedges


def createIonImageC(scanDescriptor,ionSignal,bins):
    f_code = DEFAULT_TYPEDEFC + """
        const int n_counts = Ndata[0];
        const int n_path = NpathX[0];
        const int bins_x = Nhist[0];
        const int bins_y = Nhist[1];
        int pathIndex = 0;
        int histIndex = 0;
        for (int i = 0; i < n_counts; i++) {
            pathIndex = (int)floor(data[i]*n_path/dur);
            histIndex = (int)floor(pathY[pathIndex]*bins_y)*bins_x+(int)floor(pathX[pathIndex]*bins_x);
            //printf("histIndex: %i\\n",histIndex);
            hist[histIndex]++;
        }
        """
        
    data = ionSignal.rawData
    pathX, pathY = scanDescriptor.getXYData()
    dur = scanDescriptor.duration*10e7
    hist = np.zeros(bins)
    weave.inline(f_code, ["data", "pathX", "pathY", "dur", "hist"], **opt_args)
    
    return hist, np.linspace(0,scanDescriptor.scanRegion.width(),bins[0],endpoint=False), np.linspace(0,scanDescriptor.scanRegion.height(),bins[1],endpoint=False)


def addTimestamp(fname):
    if not os.path.isfile(fname):
        raise Exception("File Not Found: %s"%fname)
    fname = fname
    fh = h5py.File(fname, 'a')
    scanNames = []
    seqTimestamp = os.path.basename(fname).rsplit("-",1)[1].split(".",1)[0]
    print seqTimestamp
    
    for name in fh:
        if name[-5:] == "_data":
            scanNames.append(name[:-5])
            print name
            fh[name].attrs["seqTimestamp"] = seqTimestamp
    fh.close()


class IonSignalFile():
    def __init__(self,fname):
        if not os.path.isfile(fname):
            raise Exception("File Not Found: %s"%fname)
        self.fname = fname
        self.fh = None
        try:
            self.openFile()
        except:
            raise Exception("Could not open file %s"%(fname))
        self.scanNames = []
        self.metadata = dict(self.fh.attrs)
        
        if not "seqTimestamp" in self.metadata:
            #We are desperate at that point: Try to extract seqTimestamp from filename
            self.metadata["seqTimestamp"] = float(((fname.split("/")[-1]).split(".")[0]).split("-")[-1])
        
        self.seqTimestamp = self.metadata["seqTimestamp"]
        
        for name in self.fh:
            if name[-5:] == "_data":
                self.scanNames.append(name[:-5])
                
        self.closeFile()
    
    def getIonSignal(self,name,scanNum = 0,keepOpen = False):
        if not self.fh:
            self.openFile()
        if name in self.scanNames:
            timestamp = self.getScanMetadata(name,keepOpen=True)["seqTimestamp"]
            if not len(self.fh["%s_data"%name]) > 0: return IonSignal(timestamp,scanNum,[])            
            iSig = IonSignal(timestamp,scanNum,np.array(self.fh["%s_data"%name])) 
        else:
            print "scan name not found in File %s"%(self.fname)
            return None
        
        if not keepOpen: self.closeFile()
        return iSig
            
            
    def getScanNames(self):
        return self.scanNames           

    def getIonScanSequence(self):
        if not self.fh:
            self.openFile()
        iss = IonScanSequence(self.seqTimestamp)
        for i,name in enumerate(self.scanNames):
            iss.add(self.getIonSignal(name,i,True))
        self.closeFile()
        return iss
    
    def openFile(self):
        if not self.fh:
            plist = h5py.h5p.create(h5py.h5p.FILE_ACCESS)
            plist.set_fclose_degree(h5py.h5f.CLOSE_STRONG)
            f = h5py.h5f.open(self.fname,  h5py.h5f.ACC_RDONLY , fapl=plist)
            self.fh = h5py.File(f)
    
    def closeFile(self):
        self.fh.close()
        del(self.fh)
        self.fh = None
        return
    
    def getScanMetadata(self,name,keepOpen=False):
        if not self.fh:
            self.openFile()
        metadata = copy.copy(self.metadata)
        metadata.update(dict(self.fh["%s_data"%name].attrs)) 
        return metadata
        if not keepOpen:
            self.closeFile()
    
    def getScanDescriptor(self,name,keepOpen=False,patternPath=None):
        metadata = self.getScanMetadata(name,keepOpen=keepOpen)
        x = float(metadata['x'].split(" ")[0])
        y = float(metadata['y'].split(" ")[0])
        w = float(metadata['Width'].split(" ")[0])
        h = float(metadata['Height'].split(" ")[0])
        dur = float(metadata['Duration'].split(" ")[0])*1e-3
        rot = float(metadata['Rotation'].split(" ")[0])
        pat = metadata['Pattern']
        sr = float(metadata['Samples'].split(" ")[0])*1e3/dur
        sd = ScanDescriptor(name,ScanRegion(x,y,w,h,rotation=rot/180*np.pi),dur,samplerate=sr)
        if patternPath:
            sd.loadSegmentsFromFile("%s/%s"%(patternPath,pat),sr)
            if sd.parameterName:
                sd.parameterValue =  int(metadata[sd.parameterName])
                sd.reloadSegmentsFromFile(sr)
        return sd  

class IonMeasurement():
    def __init__(self,dirname,patternPath = None, ionDelay = 0, csvFile = None):
        self.ionSignalFiles = {} 
        self.patternPath = patternPath
        self.ionDelay = ionDelay
        seqTimestamps = []
        if csvFile != None:
            try:
                reader = CSVReader.IACSVReader(csvFile)
                seqTimestamps = reader.getData(["seqTimestamp"])[0]
            except:
                print "could not open specified csv file: %s"%csvFile
                    
        listing = os.listdir(dirname)
        for infile in listing:
            if infile.split('.')[-1] not in ["h5", "hdf", "hdf5"]: continue
            try:
                isf = IonSignalFile("%s%s"%(dirname,infile))
            except Exception as e:
                print "error: %s"%(e.message)
                continue            
            if len(seqTimestamps) > 0 and float(isf.seqTimestamp) not in seqTimestamps: 
                continue
            self.ionSignalFiles.update({int(isf.seqTimestamp):isf})
        
        #extract names of scans an their scan descriptors
        self.scansMetadata = {}
        self.scanDescriptors = {}
        
        if len(self.ionSignalFiles.values())>0:
            for name in self.ionSignalFiles.values()[0].scanNames:
                self.scansMetadata.update({name:isf.getScanMetadata(name)})
                try:
                    self.scanDescriptors.update({name:isf.getScanDescriptor(name,patternPath=patternPath)})
                except:
                    print "could not reconstruct scan descriptor from measurement"
        else:
            print "no files loaded! Strange.."
    
    def getTimestamps(self):
        return self.ionSignalFiles.keys()
    
    def getScanDescriptor(self,name):
        return self.scanDescriptors[name]        
     
    def getNumRuns(self):
        return len(self.ionSignalFiles)
    
    def getEvents(self,name,seqTimestamps=None):
        iontimes = np.empty(0)
        if seqTimestamps == None: seqTimestamps = self.getTimestamps()
        #TODO: list comprehension
        for seqTimestamp in seqTimestamps:
            seqTimestamp = int(seqTimestamp)
            if not self.ionSignalFiles.has_key(seqTimestamp): continue
            ionSignal = self.ionSignalFiles[seqTimestamp].getIonSignal(name)
            if not ionSignal: continue
            iontimes = np.append(iontimes,ionSignal.rawData+np.ones(len(ionSignal.rawData))*self.ionDelay)
        return iontimes
    
    def getHistogram(self,name,bins,seqTimestamps=None):
        if seqTimestamps == None: seqTimestamps = self.getTimestamps()
        return np.histogram(self.getEvents(name,seqTimestamps)/100,bins = bins)
   
    def getImage(self,name,bins,seqTimestamps=None):
        if not self.patternPath: raise Exception("No pattern Path supplied, can not create image")
        if seqTimestamps == None: seqTimestamps = self.getTimestamps()
        ionSignal = IonSignal(self.scansMetadata[name]["seqTimestamp"],0,self.getEvents(name,seqTimestamps))
        return createIonImage(self.scanDescriptors[name],ionSignal,bins)
