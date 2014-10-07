import numpy as np
import scipy.optimize
import scipy.interpolate
import math, h5py


class RNFitter():
    def __init__(self, time, zero_order, first_order, theoryFile ,p0=[1, 1], gridWidth=4):
        '''
        time:          array containing time in us
        zero_order:    array containing atom number in zero order after corresponding time
        first_order:   array containing atom number in first order after corresponding time
        p0:            [s_guess, A_guess]
        gridWidth:     interpolation grid starts @ s_guess-width and ends @ s_guess+width;
                       real s value should be within these boundaries
        '''
        
        self.guess = p0
        self.gridWidth = gridWidth
        self.grid = {}
        
        #loading simulated data - old for lattice with alpha = 90 degrees, retro for retro =)
        self._loadTheory_(theoryFile)
        self._createInterpolationGrid_()
        
        self.fitFunctions ={
            0: lambda t, s, A: A*scipy.interpolate.griddata((self.grid['pos_points'],self.grid['t_points']), self.grid['zero_order'], (self._s_to_pos_(s), t), method="cubic"),
            1: lambda t, s, A: A*scipy.interpolate.griddata((self.grid['pos_points'],self.grid['t_points']), self.grid['first_order'], (self._s_to_pos_(s), t), method="cubic")
        }
        
        #chopping data - simulation was only done up to 60us-pulses
        self.time = time[time <= self.tMax]
        self.zero_order = zero_order[time <= self.tMax]
        self.first_order = first_order[time <= self.tMax]
    
    
    def _loadTheory_(self, filename):
        f = h5py.File(filename)
        self.sMax = f.attrs['sMax']
        self.sStep = f.attrs['sStep']
        self.tMax = f.attrs['tMax']
        self.zero_order_theory  = np.array(f['zero'])
        self.first_order_theory = np.array(f['first'])
        f.close()
    
    def _s_to_pos_(self, s):
        """
            calculates position of given s_value in storage-array
        """
        return (s-1.0)/self.sStep
            
    def _createInterpolationGrid_(self):
        #checking boundaries, simulation were done between s = 1 E_rec and s = 50 E_rec
        if (self.guess[0]-self.gridWidth) < 1.0:
            start_pos = self._s_to_pos_(1)
        else:
            start_pos = int(math.floor(self._s_to_pos_(self.guess[0]-self.gridWidth)))
        if (self.guess[0]+self.gridWidth) > self.sMax:
            end_pos   = self._s_to_pos_(self.sMax)
        else:
            end_pos   = int(math.floor(self._s_to_pos_(self.guess[0]+self.gridWidth)))
        
        #creating interpolation grid
        steps            = (end_pos-start_pos+1)*1j
        grid_pos, grid_t = np.mgrid[start_pos:end_pos:steps, 0:self.tMax:(self.tMax+1)*1j]
        self.grid.update({
        'pos_points'  : np.ravel(grid_pos),
        't_points'    : np.ravel(grid_t),
        'zero_order'  : np.ravel(self.zero_order_theory[start_pos:end_pos+1]),
        'first_order' : np.ravel(self.first_order_theory[start_pos:end_pos+1])
        })

    def fitFunction(self, t, s, A, order=0):
        return self.fitFunctions[order](t,s,A)

    def fit(self):
        popt_zero, pcov_zero = scipy.optimize.curve_fit(f=self.fitFunctions[0], xdata=self.time, ydata=self.zero_order, p0=self.guess)
        err_zero = np.sqrt(np.diagonal(pcov_zero))
        popt_first, pcov_first = scipy.optimize.curve_fit(f=self.fitFunctions[1], xdata=self.time, ydata=self.first_order, p0=self.guess)
        err_first = np.sqrt(np.diagonal(pcov_first))
        return {0:(popt_zero, err_zero), 1:(popt_first, err_first)}
        
if __name__ == "__main__":
    from qao.io import CSVReader
    import pylab as pl
    
    #Data file to evaluate
    filename = "2014-10-06/RamanNath_EW_295mW.csv"   
    theoryFilename = "Theory/RN_742nm_retro.h5"
    
    #read data from csv-file
    reader    = CSVReader.IACSVReader(filename)
    mean, std = reader.getUniqueData(["pulsetime","Rb_N","first_N"])
    t_data, zero_order, first_order = mean[:,[0,1,2]].transpose()
    zero_std, first_std = std[:,[1,2]].transpose()
    
    fitter = RNFitter(t_data, zero_order, first_order, theoryFilename, p0=[27, 100])
    results = fitter.fit()
    
    #ploting everything
    t_theory = np.linspace(0,fitter.tMax,150)
    
    pl.errorbar(t_data, zero_order, zero_std, fmt=".", color="b", label = "0th Order: data")
    pl.plot(t_theory, fitter.fitFunction(t_theory,*results[0][0],order=0),label = "0th Order: theory")

    pl.errorbar(t_data, first_order, first_std, fmt=".", color="g", label = "1st Order: data")
    pl.plot(t_theory, fitter.fitFunction(t_theory,*results[1][0],order=1),label = "1st Order: theory")
    
    pl.xlabel("RN_pulse [us]")
    pl.ylabel("Population [10^3 atoms]")
   
    pl.show()
    
