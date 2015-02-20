import numpy as np
import csv

def isfloat(value):
  try:
    float(value)
    return True
  except ValueError:
    return False

def safeComp(x1,x2):
    try:
        if float(x1) == float(x2):
            return True
        else:
            return False
    except:
        return False

def safeConvert(x):
    try:
        return float(x)
    except:
        return 0


unitDict = {'n':1e-9, 'u':1e-6, 'm':1e-3, 'k':1e3, 'M':1e6, 'G':1e9}
def convertUnitNumbers(unitNumberString):
    """
    Converts numbers with units in a string to a float in the corresponding SI-unit. In other words it
    removes prefactors like milli, micro, nano and so on and scales the number accordingly.
    The string has to have the format .*\..*\*{n,u,m,k,M,G}.*
    """
    unitNumberString = unitNumberString.replace("*"," ")
    splitIdx = unitNumberString.rfind(" ")
    if splitIdx < 0:
        return float(unitNumberString)
    number = float(unitNumberString[:splitIdx])
    modifier = (unitNumberString[splitIdx+1:].strip())[0]
    unit = (unitNumberString[splitIdx+1:].strip())[1:]
    if unit != "" and modifier in unitDict:
        number *= unitDict[modifier]
    return number

class CSVReader:
    def __init__(self,fname):
        # read csv to list
        reader = csv.reader(open(fname, "rb"))
        self.header = reader.next()
        dtype  = np.dtype({'names': self.header, 'formats': [object]*len(self.header)})
        self.rows   = [row for row in reader if row[self.header.index(self.__discardColumnName__())] != 'True']
        # convert to recarray
        self.data = np.empty(len(self.rows), dtype=dtype)
        for i in range(len(self.rows)): self.data[i] = tuple(self.rows[i])
        
        
    def setMask(self,mask):
        dtype  = np.dtype({'names': self.header, 'formats': [object]*len(self.header)})
        rows   = [row for row in self.rows if float(row[self.header.index(mask[0])]) == mask[1]]
        self.data = np.empty(len(rows), dtype=dtype)
        for i in range(len(rows)): self.data[i] = tuple(rows[i])

    def setMaskInterval(self,mask):
        dtype  = np.dtype({'names': self.header, 'formats': [object]*len(self.header)})
        rows   = [row for row in self.rows if (float(row[self.header.index(mask[0])]) > mask[1][0] and float(row[self.header.index(mask[0])]) < mask[1][1])]
        self.data = np.empty(len(rows), dtype=dtype)
        for i in range(len(rows)): self.data[i] = tuple(rows[i])
        
    def getData(self,col):
        return [[safeConvert(self.data[x][idx]) for idx in range(len(self.data[x]))] for x in col]
    
    def getUniqueData(self,cols):
        dataUnique = np.unique(np.array([safeConvert(number) for number in self.data[cols[0]] if isfloat(number)]))
        ordereddata = [[[safeConvert(y[curcol]) for y in self.data if safeComp(y[cols[0]],uniquevalue) and isfloat(y[curcol]) ] for uniquevalue in dataUnique]   for curcol in cols[1:]]
        dataMean = dataUnique
        dataStd = dataUnique
        for column in ordereddata:
            dataMean = np.column_stack([dataMean, [[np.asarray(x).mean()] for x in column ]])
            dataStd = np.column_stack([dataStd, [[np.asarray(x).std()] for x in column ]])
        return dataMean, dataStd

class CamCSVReader:
    def __discardColumnName__(self):
        return 'Omit'

class IACSVReader(CSVReader):
    def __discardColumnName__(self):
        return 'discard'
    
