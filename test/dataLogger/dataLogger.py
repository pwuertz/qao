'''
Created on 15.10.2013

@author: lausch
'''
import unittest, time
from qao.io.datalogger import DataLogClient, DataLogServer

# implement basic console server
class MockServer(DataLogServer):
    def __init__(self):
        DataLogServer.__init__(self,logTime=.5,database='mock')
        self.logged.connect(self.printEventLogged)
        self.time = 0
        self.testdata = None
        
    def start(self,testdata=None):
        self.testdata = testdata
        DataLogServer.start(self)
        
    def printEventLogged(self, data):
        self.testdata = data
        print "new event: %s took %s" % (str(data),time.time()-self.time)
        
class DataLogger(unittest.TestCase):
        

    def setUp(self): 
        
        self.app = QtCore.QCoreApplication([])
        self.serv = MockServer()
        self.serv.connectToMessageBus('localhost')

        self.cli = DataLogClient('key')
        self.cli.connectToMessageBus('localhost')
           
        self.serv.time = time.time()
    
    def tearDown(self):
        self.serv.disconnectFromServer()
        self.cli.disconnectFromServer()
        self.serv = None
        self.cli = None
        self.app.quit()
    
    def restartServer(self,testdata = None):
        self.serv.start(testdata)
        while(self.serv.testdata == None):
            time.sleep(.05)
            self.app.processEvents()
    
    def log01(self):
        mockDict = {'key':'value'}
        self.cli.log(mockDict['key'])
        
        self.restartServer()
        
        self.assertDictContainsSubset(mockDict, self.serv.testdata, 'Server doesn\'t receive data')        
       
    def logDict01(self):
        mockDict = {'key':'value'}
        self.cli.logDict(mockDict)
        
        self.restartServer()
        
        self.assertDictContainsSubset(mockDict, self.serv.testdata, 'Server doesn\'t receive data')
    
    def tellIgnore01(self):
        mockDict = {'key':'value'}
        self.cli.tellIgnore('key')
        self.cli.logDict(mockDict)
        
        self.restartServer()
        
        self.assertFalse('key' in self.serv.testdata, 'Server does not ignore the wished key')
    
    def tellUnignore01(self):
        mockDict = {'key':'value'}
        self.cli.tellIgnore('key')
        self.cli.tellUnignore('key')
        
        self.cli.logDict(mockDict)
        
        self.restartServer()
        
        self.assertDictContainsSubset(mockDict, self.serv.testdata, 'Server unignore failed.Data has gone missing')
    
    def tellRemove01(self):
        
        mockDict = {'key':'value'}
        self.cli.logDict(mockDict)
        self.cli.tellRemove('key')
        
        self.restartServer()
        
        self.assertFalse('key' in self.serv.testdata, 'Server does not ignore the wished key')
    
    def getLastData01(self):
        mockDict = {'key':'value'}
        self.cli.logDict(mockDict)
        self.returned = None
        def map2Current(args):
            self.returned = args
        self.cli.getLastData(map2Current)
        while(self.returned == None):
            time.sleep(.1)
            self.app.processEvents()
            
        self.assertDictContainsSubset(mockDict,self.returned,'Server did not deliver expected data')
    
    def tellSubscribe01(self):
        mockDict = {'topic':'value'}
        mockTopic = 'topic'
        self.cli.tellSubscribe(mockTopic)
        self.cli.mbus.publishEvent(mockTopic,mockDict)
        
        self.restartServer()
        
        self.assertDictContainsSubset(mockDict,self.serv.testdata,'Server did not subscribe the topic %s'%mockTopic)
    
    def tellSubscribe02(self):
        mockDict = {'key':'value'}
        mockTopic = 'topic'
        self.cli.tellSubscribe(mockTopic,'key')
        self.cli.mbus.publishEvent(mockTopic,mockDict['key'])
        
        self.restartServer()
        
        self.assertDictContainsSubset(mockDict,self.serv.testdata,'Server did not subsctibe the topic %s'%mockTopic)
    
    def tellUnsubscribe01(self):
        mockDict = {'key':'value'}
        mockTopic = 'topic'
        self.cli.tellSubscribe(mockTopic)
        self.cli.tellUnsubscribe(mockTopic)
        self.cli.mbus.publishEvent(mockTopic,mockDict['key'])
        
        self.restartServer()
        
        
        self.assertFalse('topic' in self.serv.testdata, 'Server does not ignore the wished key')
        self.assertFalse('key' in self.serv.testdata, 'Server does not ignore the wished key')
    
    def servSave01(self):
        mockDict = {'key':'value'}
        self.cli.log(mockDict['key'])
        
        self.restartServer()
        
        self.assertTrue('_rev' in self.serv.testdata, 'Missing Revision in saved data')
        self.assertTrue('_id' in self.serv.testdata, 'Missing Id in saved data')
        
        
        self.assertTrue(self.serv.testdata['_id'] in self.serv.db, 'Data not stored to database')
        
        self.assertEqual(self.serv.testdata,self.serv.db[self.serv.testdata['_id']],'Missmatch between stored and mock data')
        
if __name__ == "__main__":
    import sys;sys.argv = ['',
                           'DataLogger.log01',
                           'DataLogger.logDict01',
                           'DataLogger.tellIgnore01',
                           'DataLogger.tellUnignore01',
                           'DataLogger.tellRemove01',
                           'DataLogger.getLastData01',
                           'DataLogger.tellSubscribe01',
                           'DataLogger.tellSubscribe02',
                           'DataLogger.tellUnsubscribe01',
                           'DataLogger.servSave01']
    
    from PyQt4 import QtCore
    from qao.io import messageBus
        
    try:
            mbcli = messageBus.MessageBusClient()
            mbcli.connectToServer('localhost')
            if(not mbcli.isConnected()):
                raise Exception('no connection to messageBus')
    except Exception as ex:
        print 'no connection to messageBus: ',ex
        sys.exit()
        
    DataLogServer.setup(database='mock')
    unittest.main()