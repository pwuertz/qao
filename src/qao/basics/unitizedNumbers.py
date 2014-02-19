import numpy as np

multiplicators = {'f':-12,\
                    'n':-9,\
                    'u':-6,\
                    'm':-3,\
                    'k':3,\
                    'M':6,\
                    'G':9,\
                    'T':12,\
                    'P':15,\
                    'E':18}

class unitizedNumber:
    def __init__(self,numStr=None,number=None,mult=None,unit=None):
        if numStr:
            self.fromString(numStr)
        else:
            assert number and mult and unit
            self.number = number
            self.mult = mult
            self.unit = unit
        
    def fromString(self,numStr):
        number,unit = numStr.split('*')
        
        try:
            self.number = float(number)
            if len(unit)>1:
                if unit[0] in multiplicators.keys():
                    self.mult = 10**multiplicators[unit[0]]
                    self.unit = unit[1:]
                else:
                    self.mult = 1
                    self.unit = unit
        except:
            self.mult = 1
            self.number = 0.0
            self.unit = '' 
            raise Exception("could not convert %s to a unitized Number"%numStr)
    
    def __str__(self):
        multStr = ""
        for k,v in multiplicators.iteritems():
            if v ==  int(np.log10(self.mult)):
                multStr = k
        return "%f*%s%s"%(self.number,multStr,self.unit)
    
    def getWithoutMult(self):
        return self.number*self.mult
    
    def normalize(self):
        value = self.number*self.mult
        digits = int(np.floor(np.log10(value)))/3*3
        self.number = value/10**digits
        self.mult = 10**digits
        
    def __add__(self,other):
        assert isinstance(other,unitizedNumber)
        if self.unit != other.unit:
            raise Exception("Both numbers must have the same units")
        value = self.number*self.mult + other.number*other.mult
        num = unitizedNumber(number=value,mult=1,unit=self.unit)
        num.normalize()
        return num
        
    def __sub__(self,other):
        assert isinstance(other,unitizedNumber)
        if self.unit != other.unit:
            raise Exception("Both numbers must have the same units")
        value = self.number*self.mult - other.number*other.mult
        num = unitizedNumber(number=value,mult=1,unit=self.unit)
        num.normalize()
        return num
                    
if __name__ == "__main__":
    num1 = unitizedNumber("0.5*GHz")
    num2 = unitizedNumber("1*kHz")
    num3 = num1-num2
    print num3
            
