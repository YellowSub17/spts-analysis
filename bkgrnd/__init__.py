

import h5py
import matplotlib.pyplot as plt

xmin = 1000
xmax = 1700
ymin = 1100
ymax = 1800


class BackgroundRun:

    def __init__(self,fname):

        self.fname = fname
        
        
        with h5py.File(fname, 'r')  as f:
            self.bg = f['/bg'][xmin:xmax, ymin:ymax]
            self.bg_std = f['/bg_std'][xmin:xmax, ymin:ymax]
            self.good_pixels = f['/good_pixels'][xmin:xmax, ymin:ymax]

        



            
    def hist_i(self, range=None, bins=50):
        plt.figure()
        plt.hist(self.bg[self.good_pixels], range=range, bins=bins)
        
        

