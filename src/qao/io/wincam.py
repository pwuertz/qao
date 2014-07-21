import numpy as np

def load_wcb(fname):
    """
    WinCam image loader.
    Load data from WinCam Binary images (.wcb) as numpy array.
    """
    fh = open(fname, "rb")
    
    # read / check signature
    signature = np.fromfile(fh, dtype = "uint8", count=4)
    assert(chr(signature[3]) == "D")
    assert(chr(signature[2]) == "R")
    assert(chr(signature[1]) == "I")
    
    # read header
    header = np.fromfile(fh, dtype = "uint32", count=5)
    width, height, bits, xpels, ypels = header 
    
    # read data
    data = np.fromfile(fh, dtype = "uint%s" % bits, count=height*width)
    assert(data.size == height*width)
    
    return data.reshape([height, width])

