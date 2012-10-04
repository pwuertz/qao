from qao.devices.TicoMCS import IonScanSequence,IonSignal
import os,h5py
import numpy as np
import copy


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
        self.openFile()
        self.scanNames = []
        self.metadata = dict(self.fh.attrs)
        self.seqTimestamp = self.metadata["seqTimestamp"]
        
        for name in self.fh:
            if name[-5:] == "_data":
                self.scanNames.append(name[:-5])
                
        self.closeFile()
    
    def getIonSignal(self,name,scanNum = 0,keepOpen = False):
        if not self.fh:
            self.openFile()
        if name in self.scanNames:
            return IonSignal(dict(self.fh["%s_data"%name].attrs)["seqTimestamp"],scanNum,self.fh["%s_data"%name])            
        if not keepOpen:
            self.closeFile()
    
    def getIonScanSequence(self):
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

class IonMeasurement():
    def __init__(self,dirname):
        self.ionSignalFiles = {} 
        listing = os.listdir(dirname)
        for infile in listing:
            if infile.split('.')[-1] not in ["h5", "hdf", "hdf5"]: continue
            isf = IonSignalFile("%s%s"%(dirname,infile))
            self.ionSignalFiles.update({isf.seqTimestamp:isf})
            
    def getEvents(self,seqTimestamps,name):
        iontimes = np.empty(0)
        #TODO: list conprehension
        for seqTimestamp,isf in self.ionSignalFiles.items():
            if not isf.seqTimestamp in seqTimestamps: continue
            ionSignal = isf.getIonSignal(name)
            if not ionSignal: continue
            iontimes = np.append(iontimes,ionSignal.rawData)
        return iontimes
    
    def getNumRuns(self):
        return len(self.ionSignalFiles)
    
    def getAllEvents(self,name):
        return self.getEvents(self.ionSignalFiles.keys(),name)
        
    def getHistogram(self,seqTimestamp,name,bins):
        return np.histogram(self.getEvents(seqTimestamp,name)/100,bins = bins)
    
    def getHistogramSum(self,seqTimestamps,name,bins):
        return np.histogram(self.getEvents(seqTimestamps,name)/100,bins = bins)
        
    def getHistogramSumAll(self,name,bins):
        return np.histogram(self.getAllEvents(name)/100,bins = bins)
