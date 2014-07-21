import numpy as np
from scipy import weave

errordiff_code = """
const int nx = Ndata_src[1];
const int ny = Ndata_src[0];

for (int iy=1; iy < ny-1; ++iy) {
    for (int ix=1; ix < nx-1; ++ix) {
        int i = iy * nx + ix;                 // index
        data_dst[i] = data_src[i] > .5;       // binary
        double e = data_dst[i] - data_src[i]; // error
        // diffuse error to pixel neighbours
        data_src[i+1]    += (-7./16.) * e;
        data_src[i+nx+1] += (-1./16.) * e;
        data_src[i+nx]   += (-5./16.) * e;
        data_src[i+nx-1] += (-3./16.) * e;
    }
}
"""
     
def errordiff(data):
    """
    Calculate the binary representation of a 2d array using error diffusion
    (Floyd–Steinberg dithering).)
    """
    data_src = np.asfarray(data).copy()
    data_dst = np.zeros(data_src.shape, dtype="uint8")
    weave.inline(errordiff_code, ["data_src", "data_dst"])
    return data_dst
