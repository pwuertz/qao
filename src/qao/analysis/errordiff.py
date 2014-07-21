"""
Error Diffusion
---------------

This module implements error diffusion algorithms for converting floating point
images to binary images.
"""

import numpy as np
from scipy import weave

code_floyd_steinberg = """
const int nx = Ndata_src[1];
const int ny = Ndata_src[0];

for (int iy=0; iy < ny-1; ++iy) {
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

code_stucki = """
const int nx = Ndata_src[1];
const int ny = Ndata_src[0];

for (int iy=0; iy < ny-2; ++iy) {
    for (int ix=2; ix < nx-2; ++ix) {
        int i = iy * nx + ix;                 // index
        data_dst[i] = data_src[i] > .5;       // binary
        double e = data_dst[i] - data_src[i]; // error
        // diffuse error to pixel neighbours
        data_src[i+1]    += (-7./48.) * e;
        data_src[i+2]    += (-5./48.) * e;
        data_src[i+nx-2] += (-3./48.) * e;
        data_src[i+nx-1] += (-5./48.) * e;
        data_src[i+nx  ] += (-7./48.) * e;
        data_src[i+nx+1] += (-5./48.) * e;
        data_src[i+nx+2] += (-3./48.) * e;
        data_src[i+nx+nx-2] += (-1./48.) * e;
        data_src[i+nx+nx-1] += (-3./48.) * e;
        data_src[i+nx+nx  ] += (-5./48.) * e;
        data_src[i+nx+nx+1] += (-3./48.) * e;
        data_src[i+nx+nx+2] += (-1./48.) * e;
    }
}
"""

def floyd_steinberg(data):
    """
    Calculate the binary image of a 2d array using error diffusion
    (Floyd-Steinberg dithering).
    """
    data_src = np.asfarray(data).copy()
    data_dst = np.zeros(data_src.shape, dtype="uint8")
    weave.inline(code_floyd_steinberg, ["data_src", "data_dst"])
    return data_dst

def stucki(data):
    """
    Calculate the binary image of a 2d array using error diffusion
    (Stucki dithering).
    """
    data_src = np.asfarray(data).copy()
    data_dst = np.zeros(data_src.shape, dtype="uint8")
    weave.inline(code_stucki, ["data_src", "data_dst"])
    return data_dst

# Floyd Steinberg is the default algorithm
errordiff = floyd_steinberg

if __name__ == "__main__":
    import matplotlib.pyplot as plt
    Y, X = np.ogrid[-1:1:151j, -1:1:151j]
    data = np.exp(-(X**2 + Y**2)/(2*.4**2))
    data_fs = floyd_steinberg(data)
    data_st = stucki(data)

    plt.figure(figsize=[16,6])
    plt.gray()

    plt.subplot(1, 3, 1)
    plt.imshow(data)
    plt.gca().set_xticks([])
    plt.gca().set_yticks([])
    plt.xlabel("Original")

    plt.subplot(1, 3, 2)
    plt.imshow(data_fs, interpolation="nearest")
    plt.gca().set_xticks([])
    plt.gca().set_yticks([])
    plt.xlabel("Floyd-Steinberg")

    plt.subplot(1, 3, 3)
    plt.imshow(data_st, interpolation="nearest")
    plt.gca().set_xticks([])
    plt.gca().set_yticks([])
    plt.xlabel("Stucki")

    plt.tight_layout()
    plt.show()
