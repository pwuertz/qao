#############################################
# QCI module for python
# read/write qcamera image files (qci)
#
# class qci
#    +image_data
#    +image_parameters
#    +save()
#
#############################################

import numpy
import struct, bz2
import xml.dom.minidom

class qci:
   def __init__(self):
      "create a blank image"
      self.size = (512,768)
      self.image_data = numpy.ones(self.size,numpy.float32)
      self.image_parameters = {}
      
   def buildXML(self):
      "build the xml information block"
      # create xml document
      doc = xml.dom.minidom.Document()
      qci_root = doc.createElement("QCI")
      qci_image = doc.createElement("image")
      qci_parameters = doc.createElement("parameters")
      doc.appendChild(qci_root)
      qci_root.appendChild(qci_image)
      qci_root.appendChild(qci_parameters)
      
      # save image properties
      qci_size = doc.createElement("size")
      qci_size.setAttribute("height",str(self.image_data.shape[0]))
      qci_size.setAttribute("width",str(self.image_data.shape[1]))
      qci_image.appendChild(qci_size)
      # save data type
      qci_dtype = doc.createElement("dtype")
      qci_dtype.appendChild(doc.createTextNode(str(self.image_data.dtype)))
      qci_image.appendChild(qci_dtype)
      # save compression
      qci_compr = doc.createElement("compression")
      qci_compr.appendChild(doc.createTextNode("bz2"))
      qci_image.appendChild(qci_compr)
      
      # save parameters
      for (key,value) in self.image_parameters.items():
         qci_param = doc.createElement("parameter")
         qci_param.setAttribute("name",key)
         textnode = doc.createTextNode(self.image_parameters[key])
         qci_parameters.appendChild(qci_param)
         qci_param.appendChild(textnode)
      
      # return xml
      return doc.toxml()

   def save(self,filename):
      "save image to file"
      # open file
      # TODO: check for errors
      f = open(filename,"wb")
     
      # save header, compressed data, xml
      data = bz2.compress(self.image_data.data)
      f.write(struct.pack("!4sQ","QCI2",len(data))) # big-endian!
      f.write(data)
      f.write(self.buildXML())

   def getRect(self,name="roi"):
       if "rect_"+name in self.image_parameters:
          signal_x,signal_y,signal_w,signal_h = self.image_parameters["rect_"+name].split(",")
       else:
          signal_x,signal_y = (0,0)
          signal_w,signal_h = self.image_data.shape
       signal = self.image_data[int(signal_y):(int(signal_y)+int(signal_h)),int(signal_x):(int(signal_x)+int(signal_w))]
       return signal
   
   def getRoi(self):
       return self.getRect("roi")
#####################################################################
# global functions
#####################################################################

def load(filename):
   "load image from file"
   # open file
   # TODO: check for errors
   f = open(filename,"rb")

   # read / check header
   headersize = struct.calcsize("!4sQ")
   (magic,datasize) = struct.unpack("!4sQ",f.read(headersize))
   if magic == "QCI1":
      import qci_v1
      qci1_image = qci_v1.load(filename)
      qci2_image = qci()
      qci2_image.image_data = qci1_image.image_data
      qci2_image.image_parameters = qci1_image.image_parameters
      return qci2_image
   elif magic != "QCI2":
      raise Exception("Invalid QCI file")

   # read data block
   data = f.read(datasize)

   # read XML
   doc = xml.dom.minidom.parse(f)
   image_parameters = {}
   # read parameters
   for par in doc.getElementsByTagName("parameter"):
      if par.hasChildNodes():
         image_parameters[par.getAttribute("name")] = par.firstChild.data

   # read image properties
   qci_size = doc.getElementsByTagName("size")[0]
   width  = int(qci_size.getAttribute("width"))
   height = int(qci_size.getAttribute("height"))
   dtype  = str(doc.getElementsByTagName("dtype")[0].firstChild.data)
   compr  = str(doc.getElementsByTagName("compression")[0].firstChild.data)

   # interpret data
   if   compr == "bz2":  data = bz2.decompress(data)
   elif compr == "raw":  None
   else:                 raise Exception("Invalid compression '%s'", compr)
   image_data = numpy.fromstring(data,dtype)
   image_data = image_data.reshape(height,width)

   # return qci object
   qci_image = qci()
   qci_image.image_data = image_data
   qci_image.image_parameters = image_parameters
   return qci_image

