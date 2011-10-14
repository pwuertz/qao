import numpy as np

def imageMoments(data, X = None, Y = None):
    data = np.asfarray(data)
    data = data * (1./data.sum())
    if X == None: X = np.arange(data.shape[1], dtype = float)
    if Y == None: Y = np.arange(data.shape[0], dtype = float)
    X = np.asfarray(X).reshape([1, data.shape[1]])
    Y = np.asfarray(Y).reshape([data.shape[0], 1])
    
    # calculate center
    mx = (X*data).sum()
    my = (Y*data).sum()
    Xc = X - mx 
    Yc = Y - my
    
    # calculate central moments
    mu11 = (Xc * Yc * data).sum()
    mu20 = (Xc**2 * data).sum()
    mu02 = (Yc**2 * data).sum()
    mu22 = (Xc**2 * Yc**2 * data).sum()
    mu31 = (Xc**3 * Yc * data).sum()
    mu13 = (Xc * Yc**3 * data).sum()
    mu40 = (Xc**4 * data).sum()
    mu04 = (Yc**4 * data).sum()
    
    # calculate derived quantities
    sigx = mu20**.5; sigy = mu02**.5
    ga40 = mu40/sigx**4; ga04 = mu04/sigy**4
    ga31 = mu31/sigx**3/sigy; ga13 = mu13/sigx/sigy**3
    ga22 = mu22/sigx**2/sigy**2
    rhoxy = mu11/sigx/sigy
    
    # bivariate varianve
    gv = mu20*mu02 - mu11**2
    # bivariate kurtosis
    b22 = (ga40 + ga04 + 2*ga22 + 4*rhoxy*(rhoxy*ga22-ga13-ga31)) / (1-rhoxy**2)**2
    # relative univariate variance difference
    rv = abs(mu20 - mu02) / min(mu20, mu02)
    # relative univariate kurtosis difference
    rk = abs(ga40 - ga04) / min(ga40, ga04)
    
    return dict(gv=gv, b22=b22, rv=rv, rk=rk, mu11=mu11, mu20=mu20, mu02=mu02)

if __name__ == '__main__':
    import pylab as p
    
    # produce gaussian test distribution
    n = 400
    alpha = 60 * np.pi / 180.
    sigy, sigx = 5., 50.
    x0, y0 = 200., 200.
    Y, X = np.ogrid[:400,:400]    
    Xr = np.sin(alpha) * (Y-y0) + np.cos(alpha) * (X-x0)
    Yr = -np.sin(alpha) * (X-x0) + np.cos(alpha) * (Y-y0) 
    d = np.exp(- Xr**2 / (2*sigx**2) - Yr**2 / (2*sigy**2))
    
    # measure statistic moments
    moments = imageMoments(d)
    mu11, mu20, mu02 = moments["mu11"], moments["mu20"], moments["mu02"]
    
    # calculate angle from statistic moments
    alpha_m = .5*np.arctan2(2.*mu11, (mu20-mu02))
    print "measured angle %.1fdeg, (orig %.1fdeg)" % (alpha_m*180./np.pi, alpha*180./np.pi)
    
    # show image
    p.imshow(d)
    p.show()
    