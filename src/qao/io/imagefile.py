import os
import h5py
import numpy

img_names = ["absImage", "signalImage", "flatImage", "darkImage"]

def saveAbsorptionImage(filename, absImage, signalImage = None, flatImage = None, darkImage = None, metadata = {}, dtype = None):
    # check/append file extension
    basename, ext = os.path.splitext(filename)
    if ext.lower() not in [".h5", ".hdf", ".hdf5"]: ext += ".h5"

    # create new h5 file and save data
    fh = h5py.File(basename+ext, "w")
    for name, data in zip(img_names, [absImage, signalImage, flatImage, darkImage]):
        if data == None: continue
        ds = fh.create_dataset(name, data=data, dtype=dtype, compression="gzip")
        ds.attrs["CLASS"] = "IMAGE"
        ds.attrs["IMAGE_VERSION"] = "1.3"
        if name == "absImage":
            for key, val in metadata.items(): ds.attrs[key] = val
    fh.close()

def loadAbsorptionImage(filename):
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
    
    return images.pop("absImage"), images, metadata

if __name__ == '__main__':
    import tempfile
    fname = os.path.join(tempfile.gettempdir(), "test.h5") 
    
    info = {"dwell": 3.0}
    data = numpy.random.rand(512, 512)
    saveAbsorptionImage(fname, absImage=data, metadata=info)
    absImage, otherImages, meta = loadAbsorptionImage(fname)
    print "loaded from file"
    print absImage.shape, absImage.dtype
    print otherImages
    print meta
    
    os.remove(fname)