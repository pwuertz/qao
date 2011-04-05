#############################################
# QMI module for python
# read/write quantum microscope images (qmi)
#############################################

import os
import numpy
import struct, bz2
import xml.dom.minidom

class qmi:
   def __init__(self, width=100, height=100, filename=None):
      "create a blank 100x100 image of ints"
      self.filename = filename
      self.image_data = numpy.zeros([height, width], numpy.int)
      self.image_parameters = {}

   def copy(self):
      new = qmi()
      new.image_data = self.image_data.copy()
      new.image_parameters = self.image_parameters.copy()
      return new

   def __add__(self, other):
      if not isinstance(other, qmi):
            raise TypeError, "object must be a qmi instance"
      new = qmi()
      new.image_data = self.image_data + other.image_data
      new.image_parameters.update(other.image_parameters)
      new.image_parameters.update(self.image_parameters)
      
      # check for "NumberOfShots" parameters and add them
      if ("NumberOfShots" in self.image_parameters) and ("NumberOfShots" in other.image_parameters):
         new.image_parameters["NumberOfShots"] = str(int(self.image_parameters["NumberOfShots"]) + int(other.image_parameters["NumberOfShots"]))
            
      return new

   def __buildXML(self, compr):
      "build the xml information block"
      # create xml document
      doc = xml.dom.minidom.Document()
      qmi_root = doc.createElement("QMI")
      qmi_image = doc.createElement("image")
      qmi_parameters = doc.createElement("parameters")
      doc.appendChild(qmi_root)
      qmi_root.appendChild(qmi_image)
      qmi_root.appendChild(qmi_parameters)
      
      # save image properties
      qmi_size = doc.createElement("size")
      qmi_size.setAttribute("height", str(self.image_data.shape[0]))
      qmi_size.setAttribute("width", str(self.image_data.shape[1]))
      qmi_image.appendChild(qmi_size)
      # save data type
      qmi_dtype = doc.createElement("dtype")
      textnode = doc.createTextNode(str(self.image_data.dtype))
      qmi_dtype.appendChild(textnode)
      qmi_image.appendChild(qmi_dtype)
      # save compression
      qmi_compr = doc.createElement("compression")
      qmi_compr.appendChild(doc.createTextNode(compr))
      qmi_image.appendChild(qmi_compr)
      
      # save parameters
      for (key, value) in self.image_parameters.items():
         qmi_param = doc.createElement("parameter")
         qmi_param.setAttribute("name", key)
         textnode = doc.createTextNode(str(value))
         qmi_parameters.appendChild(qmi_param)
         qmi_param.appendChild(textnode)
      
      # return xml
      return doc.toxml()

   def shift(self, pixels_x, pixels_y):
       """
       move all pixels by pixels_x to the left (-x) and pixels_y upwards (-y)
       """       
       self.image_data = utils.shift(self.image_data, pixels_x, pixels_y)
       
   def save(self, filename = None, compr = "bz2"):
      "save image to file, if no filename is given, try to reuse old filename"
      if not filename:
          if not self.filename: raise RuntimeError("don't know where to save the file")
          filename = self.filename

      # open file
      # TODO: check for errors
      f = open(filename, "wb")
      
      # compress
      if compr == "bz2":
          data = bz2.compress(self.image_data.data)
      else:
          compr == "raw"
          data = self.image_data.data
      f.write(struct.pack("!4sQ", "QMI2", len(data)))
      f.write(data)
      f.write(self.__buildXML(compr = compr))
      
   def saveAscii(self, filename):
       """
       save the x,y coordinate of each ion as text file
       """
       if self.image_data.dtype != numpy.int:
           raise TypeError("only integer type images may be ascii-saved")
       
       # build coordinate system
       self.image_parameters
       X = numpy.arange(self.image_data.shape[1])
       Y = numpy.arange(self.image_data.shape[0])
       # check for scaling information
       if ("PixelDistanceX" in self.image_parameters) and ("PixelDistanceY" in self.image_parameters):
           # pixel distance given in nm, rescale to um
           X = X * float(self.image_parameters["PixelDistanceX"]) * 1e-3
           Y = Y * float(self.image_parameters["PixelDistanceY"]) * 1e-3
       else:
           print "warning: no pixel distance information found"
       
       out = open(filename, "w")
       for yi, y in enumerate(Y):
           for xi, x in enumerate(X):
               for i in range(self.image_data[yi, xi]):
                   out.write("%f\t%f\n" % (x, y))
       out.close()

#####################################################################
# global functions
#####################################################################

def sum(qmi_list):
   """
   summarize a list of qmi images and return a new qmi object
   """
   assert type(qmi_list) == list, "list of qmi objects required"
   qmi_sum = qmi_list[0].copy()
   for image in qmi_list[1:]:
      qmi_sum = qmi_sum + image
   return qmi_sum

def load(filename, **kwargs):
   """
   Load .ASC or .qmi files. If filename is a directory, all qmi files
   within the directory will be loaded and returned in a list.
   
   optional kwargs:
      callback_progress: call a function(filename, i, n)
                         when loading files from a directory
      callback: call a function(filename, qmi_image) after loading a file
   """
   if (os.path.isdir(filename)):
      return __loadAllFromDir(filename, **kwargs)
   if (filename[ - 4:].lower() == ".asc"):
      return __loadAsc(filename, **kwargs)
   if (filename[ - 4:].lower() == ".qmi"):
      return __loadQmi(filename, **kwargs)

def loadDir(directory, **kwargs):
    """
    Load all .qmi files from a directory. 
   
    optional kwargs:
       callback_progress: call a function(filename, i, n)
                          when loading files from a directory
       callback: call a function(filename, qmi_image) after loading a file
    """
    # find qmi files in directory
    files = os.listdir(directory)
    files = filter(lambda name: name[-4:].lower() == ".qmi", files)
    files.sort()
    
    # shall we report the loading progress?
    callback_progress = kwargs["callback_progress"] if "callback_progress" in kwargs else None

    images = []
    n = len(files)
    for i, item in enumerate(files):
        image = load(os.path.join(directory, item), **kwargs)
        images.append(image)
        if callback_progress: callback_progress("Loaded "+item, i+1, n)

    return images

def assembleFromAsc(directory, **kwargs):
   """
   Read all ASC files from this directory.
   Summarize all images and return qmi object.
   """
   # find asc files in directory
   files = os.listdir(directory)
   files = filter(lambda name: name[ - 4:].lower() == ".asc", files)
   if len(files) == 0: raise Exception("no asc files found in: %s" % directory)
   files.sort()
   
   # for each asc, create qmi object, add it to image_sum   
   image_sum = load(os.path.join(directory, files[0]))
   for item in files[1:]:
      image_new = load(os.path.join(directory, item))
      image_sum = image_sum + image_new

   # return qmi object
   image_sum.image_parameters["NumberOfShots"] = str(len(files))
   return image_sum
   
def convertAscToQmi(directory):
   """
   Read all ASC files from this directory. Save each image as qmi.
   """
   # find asc files in directory
   files = os.listdir(directory)
   files = filter(lambda name: name[-4:].lower() == ".asc", files)
   if len(files) == 0: raise Exception("no asc files found in: %s" % directory)
   files.sort()
   
   # for each asc, create qmi object, save to file
   for item in files:
      image = load(os.path.join(directory, item))
      image.save(os.path.join(directory, item[: - 4] + ".qmi"))

def __loadAllFromDir(directory, **kwargs):
    # find qmi files in directory
    files = os.listdir(directory)
    files = filter(lambda name: name[-4:].lower() == ".qmi", files)
    files.sort()
    
    # shall we report the loading progress?
    callback_progress = None
    if "callback_progress" in kwargs:
        callback_progress = kwargs["callback_progress"]
    
    images = []
    n = len(files)
    for i, item in enumerate(files):
        image = load(os.path.join(directory, item), **kwargs)
        images.append([os.path.splitext(item)[0], image])
        if callback_progress: callback_progress("Loaded "+item, i+1, n)
        
    return images

def __loadAsc(filename, **kwargs):
   """
   Construct qmi object from Asc file. The 'info.xml' file is assumed to
   be in the same directory.
   
   If there is a qmi file with the same filename, just load the qmi file.
   """
   
   # check for qmi file
   if os.path.exists(filename[: - 4] + ".qmi"):
      return load(filename[: - 4] + ".qmi")
   
   # get parameters from xml file
   parameters = {}
   infofile = os.path.join(os.path.dirname(filename), "info.xml")
   info_doc = xml.dom.minidom.parse(infofile)
   for par in info_doc.getElementsByTagName("PARAMETER"):
      if par.hasChildNodes():
         parameters[par.getAttribute("name")] = par.firstChild.data

   # get image dimensions
   if "NumberOfPixelX" not in parameters or "NumberOfPixelY" not in parameters:
      raise Exception("Unable to determine image dimensions from info.xml")
   (width, height) = (int(parameters["NumberOfPixelX"]), int(parameters["NumberOfPixelY"]))
   
   # iterate through all lines in asc file
   image_single = []
   for line in open(filename, "r"):
      image_single.append(int(line.split(" ")[1]))
   image_single = numpy.array(image_single, dtype=numpy.int)
   
   # build and return qmi object
   parameters["NumberOfShots"] = str(1)
   qmi_image = qmi(filename = filename[:-4]+".qmi")
   qmi_image.image_data = image_single.reshape(height, width)
   qmi_image.image_parameters = parameters
   
   # check for callback method
   if ("callback" in kwargs):
      callback = kwargs["callback"]
      callback(filename, qmi_image) 
   
   return qmi_image

def __loadQmi(filename, **kwargs):
   """
   Load a qmi from a file.
   """
   # open file
   # TODO: check for errors
   f = open(filename, "rb")

   # read / check header
   headersize = struct.calcsize("!4sQ")
   (magic, datasize) = struct.unpack("!4sQ", f.read(headersize))
   if magic != "QMI2": raise Exception("Invalid QMI file")

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
   qmi_size = doc.getElementsByTagName("size")[0]
   width = int(qmi_size.getAttribute("width"))
   height = int(qmi_size.getAttribute("height"))
   qmi_dtype = doc.getElementsByTagName("dtype")[0]
   dtype = str(qmi_dtype.firstChild.data)
   compr = str(doc.getElementsByTagName("compression")[0].firstChild.data)

   # interpret data
   if   compr == "bz2":  data = bz2.decompress(data)
   elif compr == "raw":  None
   else:                 raise Exception("Invalid compression '%s'", compr)
   image_data = numpy.fromstring(data, dtype)
   image_data = image_data.reshape(height, width)

   # return qmi object
   qmi_image = qmi(filename = filename)
   qmi_image.image_data = image_data
   qmi_image.image_parameters = image_parameters
   
   # check for callback method
   if ("callback" in kwargs):
      callback = kwargs["callback"]
      callback(filename, qmi_image)

   return qmi_image
