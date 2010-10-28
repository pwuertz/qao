#############################################
# QCI module for python
# read/write qcamera image files (qci)
#
# This class can load/save images saved in
# the QCI1 container. It is used for backward
# compatibility.
#
# class qci
#    +image_data
#    +image_parameters
#    +save()
#
#############################################

import numpy
import struct
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
     
      # save header, data, xml
      (height,width) = self.size
      f.write(struct.pack("4sQ","QCI1",height*width*4))
      f.write(self.image_data.astype("float32").data)
      f.write(self.buildXML())


#####################################################################
# global functions
#####################################################################

def load(filename):
   "load image from file"
   # open file
   # TODO: check for errors
   f = open(filename,"rb")

   # read / check header
   headersize = struct.calcsize("<4sQ")
   (magic,datasize) = struct.unpack("<4sQ",f.read(headersize))
   if magic != "QCI1": raise Exception("Invalid QCI file (not QCI1)")

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

   # interpret data
   image_data = numpy.fromstring(data,numpy.float32)
   image_data = image_data.reshape(height,width)

   # return qci object
   qci_image = qci()
   qci_image.image_data = image_data
   qci_image.image_parameters = image_parameters
   return qci_image

