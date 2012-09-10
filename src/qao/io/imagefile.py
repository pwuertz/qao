"""
Imagefile
---------

Provides utility functions for reading and writing scientific image data from and to files.

Being both flexible and efficient, HDF5 has been chosen as preferred file format for storing data.
The functions in this module are provided for conveniently accessing this data while fulfilling conventions
for structure and naming.
"""

import os
import numpy
import h5py

img_names = ["absImage", "signalImage", "flatImage", "darkImage"]

def saveAbsorptionImage(filename, absImage, signalImage = None, flatImage = None, darkImage = None,
                        metadata = {}, dtype = None):
    """Use this function to save absorption images taken by CCD cameras. The data is saved in a HDF5
    file. You may optionally provide the signal-, flat- and dark-image to be saved within the same file
    as well. It is encouraged to provide a dictionary of metadata, stored as attributes in HDF5.
    
    :param filename: (str) The filename to use for saving the data.
    :param absImage: (ndarray) Absorption image data, preferably a 2d numpy array.
    :param signalImage: (ndarray) Optional signal image data.
    :param flatImage: (ndarray) Optional flat image data.
    :param darkImage: (ndarray) Optional dark image data.
    :param metadata: (dict) Information to be stored as image attributes.
    :param dtype: (numpy.dtype) Convert data to different type when saving the data.

    .. seealso:: :func:`loadAbsorptionImage`
    
    Example::
    
        data = numpy.random.rand(512, 512)
        info = {"dwell_ms": 2.0}
        saveAbsorptionImage("random.hdf5", absImage=data, signalImage=data, metadata=info)
    
    """
    # check/append file extension
    basename, ext = os.path.splitext(filename)
    if ext.lower() not in [".h5", ".hdf", ".hdf5"]: ext += ".h5"

    # create new h5 file and save data
    fh = h5py.File(basename+ext, "w")
    for name, data in zip(img_names, [absImage, signalImage, flatImage, darkImage]):
        if data is None: continue
        ds = fh.create_dataset(name, data=data, dtype=dtype, compression="gzip")
        ds.attrs["CLASS"] = "IMAGE"
        ds.attrs["IMAGE_VERSION"] = "1.3"
        if name == "absImage":
            for key, val in metadata.items(): ds.attrs[key] = val
    fh.close()

def loadAbsorptionImage(filename):
    """Use this function to save absorption images taken by CCD cameras. The data is saved in a HDF5
    file. You may optionally provide the signal-, flat- and dark-image to be saved within the same file
    as well. It is encouraged to provide a dictionary of metadata, stored as attributes in HDF5. 

    :param filename: (str) The filename to use for loading the data.
    :returns:
        (abs_image, images, metadata)
    
        `abs_image` contains the absorption image, `images` is a dict with optional images
        and `metadata` contains the attributes found in the data file.
    
    .. seealso:: :func:`saveAbsorptionImage`
    
    Example::
    
        abs_image, other_images, metadata = loadAbsorptionImage("random.hdf5")
        
    """
    
    # open absorption image
    fh = h5py.File(filename, "r")
    if "absImage" not in fh: raise Exception("not an absorption image")
    
    # get metadata
    metadata = dict(fh["absImage"].attrs)
    try:
        del metadata["IMAGE_VERSION"]
        del metadata["CLASS"]
    except:
        pass
    
    # get images
    images = {}
    for name in img_names:
        if name not in fh: continue
        images[name] = numpy.asarray(fh[name])
    
    fh.close()
    return images.pop("absImage"), images, metadata

if __name__ == '__main__':
    import tempfile
    fname = os.path.join(tempfile.gettempdir(), "test.h5") 
    
    info = {"dwell": 3.0}
    data = numpy.random.rand(512, 512)
    saveAbsorptionImage(fname, absImage=data, signalImage=data, metadata=info)
    print "saved", os.stat(fname).st_size, "bytes"
    print "-"*30
    absImage, otherImages, meta = loadAbsorptionImage(fname)
    print "loaded from file"
    print "absImage:   ", absImage.shape, absImage.dtype
    print "otherImages:", otherImages.keys()
    print "metadata:   ", meta
    
    os.remove(fname)
