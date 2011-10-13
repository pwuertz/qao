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
    mu11 = (X * Y * data).sum()
    mu20 = (X**2 * data).sum()
    mu02 = (Y**2 * data).sum()
    mu22 = (X**2 * Y**2 * data).sum()
    mu31 = (X**3 * Y * data).sum()
    mu13 = (X * Y**3 * data).sum()
    mu40 = (X**4 * data).sum()
    mu04 = (Y**4 * data).sum()
    
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
    
    return dict(gv=gv, b22=b22, rv=rv, rk=rk)
