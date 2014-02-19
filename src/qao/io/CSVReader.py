import numpy as np
import csv

def safeComp(x1,x2):
    try:
        if float(x1) == float(x2):
            return True
        else:
            return False
    except:
        print "omitting %s"%x1
        return False

def saveConvert(x):
    try:
        return float(x)
    except:
        return 0

class CamCSVReader:
    def __init__(self,fname):
        # read csv to list
        reader = csv.reader(open(fname, "rb"))
        self.header = reader.next()
        dtype  = np.dtype({'names': self.header, 'formats': [object]*len(self.header)})
        self.rows   = [row for row in reader if row[self.header.index('Omit')] != 'True']
        # convert to recarray
        self.data = np.empty(len(self.rows), dtype=dtype)
        for i in range(len(self.rows)): self.data[i] = tuple(self.rows[i])
        
        
    def setMask(self,mask):
        dtype  = np.dtype({'names': self.header, 'formats': [object]*len(self.header)})
        rows   = [row for row in self.rows if float(row[self.header.index(mask[0])]) == mask[1]]
        self.data = np.empty(len(rows), dtype=dtype)
        for i in range(len(rows)): self.data[i] = tuple(rows[i])
        
    def getData(self,col):
        return [self.data[x] for x in col]
    
    def getUniqueData(self,cols):
        dataUnique = np.unique(self.data[cols[0]].astype(float))
        ordereddata = [[[saveConvert(y[curcol]) for y in self.data if safeComp(y[cols[0]],uniquevalue) ]  for uniquevalue in dataUnique] for curcol in cols[1:]]
        dataMean = dataUnique
        dataStd = dataUnique
        for column in ordereddata:
            dataMean = np.column_stack([dataMean, [[np.asarray(x).mean()] for x in column]])
            dataStd = np.column_stack([dataStd, [[np.asarray(x).std()] for x in column]])
        return dataMean, dataStd

class IACSVReader:
    def __init__(self,fname):
        # read csv to list
        reader = csv.reader(open(fname, "rb"))
        self.header = reader.next()
        dtype  = np.dtype({'names': self.header, 'formats': [object]*len(self.header)})
        self.rows   = [row for row in reader if row[self.header.index('discard')] != 'True']
        # convert to recarray
        self.data = np.empty(len(self.rows), dtype=dtype)
        for i in range(len(self.rows)): self.data[i] = tuple(self.rows[i])
        
        
    def setMask(self,mask):
        dtype  = np.dtype({'names': self.header, 'formats': [object]*len(self.header)})
        rows   = [row for row in self.rows if float(row[self.header.index(mask[0])]) == mask[1]]
        self.data = np.empty(len(rows), dtype=dtype)
        for i in range(len(rows)): self.data[i] = tuple(rows[i])
        
    def getData(self,col):
        return [self.data[x] for x in col]
    
    def getUniqueData(self,cols):
        dataUnique = np.unique(self.data[cols[0]].astype(float))
        #TODO: omit data like that can not be casted to float rather than replacing it by 0
        ordereddata = [[[saveConvert(y[curcol]) for y in self.data if safeComp(y[cols[0]],uniquevalue) ]  for uniquevalue in dataUnique] for curcol in cols[1:]]
        dataMean = dataUnique
        dataStd = dataUnique
        for column in ordereddata:
            dataMean = np.column_stack([dataMean, [[np.asarray(x).mean()] for x in column ]])
            dataStd = np.column_stack([dataStd, [[np.asarray(x).std()] for x in column ]])
        return dataMean, dataStd
