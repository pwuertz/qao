###############
# pyBandstructure
#
# uses approximation from Greiner's Phd Thesis
# to calculate Bandstructure et al. of bosons in an optical lattice
#
# 
################

import numpy
from numpy import linalg
import pylab as p

# parameters
qstep = 0.1
lmax = 5
d = 852e-9*1.0/2#numpy.sqrt(2)
xstep = 1e-9

# calculated 
# constants
hbar = 1.05457266e-34
pi = numpy.pi
k = pi/d
h = hbar*2*pi
m = 1.4431606e-25
Er = hbar**2*k**2/(2*m)
a = 101*0.529177208e-10

# change the lattice spacing and all dependend parameters
def setSpacing(newd):
  global d, k , Er
  d = newd
  k = pi/newd
  Er = hbar**2*k**2/(2*m)


# gives the approximate hamiltonian for quasi-momentum q and lattice depth s
def ham(q,s, scaleEnergy = 1):
  #scale energy is used to set the offset of the energy
  # scaleEnergy = 1  -> bound states negative
  # scaleEnergy = -1 -> all states shifted by potential depth
 
  if abs(scaleEnergy) != 1:
    raise Exception, "not a valid energy scale"	  
    
  hamiltonian = numpy.zeros((2*lmax+1,2*lmax+1))
  for i in range(-lmax, lmax+1):
    for j in range(-lmax, lmax+1):
      if i-j ==-1:
        hamiltonian[lmax+i,lmax+j] = -1.0/4*s
      elif i-j ==0:
        hamiltonian[lmax+i,lmax+j] = (2*i+q)**2-s*scaleEnergy*1.0/2
      elif i-j == 1:
        hamiltonian[lmax+i,lmax+j] = -1.0/4*s
  return hamiltonian

#gives the dispersion relations for lattice depth s
def energy(s,n = None, scaleEnergy = 1):
  values = []
  if n == None:
    for q in numpy.arange(0,1.+qstep,qstep):
      evalues, evectors = linalg.eigh(ham(q,s,scaleEnergy))
      values.append(evalues[:5])
  else:
    for q in numpy.arange(0,1.+qstep,qstep):
      evalues, evectors = linalg.eigh(ham(q,s,scaleEnergy))
      values.append(evalues[n])
  return values

#gives the bloch function of band n, quasi-momentum q at position x
def bloch(x,q,n,s):
  evalues, evectors = linalg.eigh(ham(q,s))
  temp = 0
  for l in range(-lmax,lmax+1):
    # evectors[:,i] = eigenvektor zum i-ten eigenwert
    temp += numpy.sign(evectors[l+lmax,n])*evectors[l+lmax,n]*numpy.exp(1j*(2*l+q)*k*x)
  return temp

#return wannier function with band index n, centered around xi
def wannier(x,xi, n,s):
  temp = 0
  for q in numpy.arange(-1,1,qstep):
    temp += numpy.exp(-1j*q*xi*k)*bloch(x,q,n,s)
  return temp

#return normalized wannier function
def wanniern(x,xi,n,s):
  norm = integrate(lambda x: wannier(x,xi,n,s)**2,-3*d,3*d,xstep)
  return wannier(x,xi,n,s)*1.0/numpy.sqrt(norm)

# poor man's numerical integration
def integrate(f, x1,x2,xstep):
  x = numpy.arange(x1,x2,xstep)
  data = f(x)
  return data.sum()*xstep

#onsite energy
def onsite_u(s, n=0):
  return 4*pi*hbar**2*a/(m*Er)*integrate(lambda x: wanniern(x,0,n,s).real**4,-3*d,3*d,xstep)**3

#tunneling matrix element
def tunneling_j(s, n=0):
  return abs(energy(s,n)[0]-energy(s,n)[-1])/4

#oscillation frequencies relevant for lattice calibration
def omega_lat(s):
    #abstand bei q=0 zwischen nullten und zweiten band
    return (numpy.abs(energy(s,2)[0]-energy(s,0)[0]))*Er/hbar

def nu_lat(s):
    return (numpy.abs(energy(s,2)[0]-energy(s,0)[0]))*Er/h
    
    
    
    
#examples

####print dispersion curves
#p.plot(energy(15,4))
#p.plot(energy(15))
#p.show()

#plot tunneling and onsite energy
#srange = range(50)
#u = []
#j = []
#for s in srange:
#print onsite_u(1.4)/tunneling_j(1.4)

#setSpacing(604e-9)

#print onsite_u(30)/tunneling_j(30)

#p.plot(u)
#p.plot(j)
#p.show()


####print bloch and wannier function
#x = numpy.arange(-5*d,5*d,xstep)
#p.plot(x, bloch(x,0,0).real**2)
#p.plot(x, bloch(x,1,0).real**2)
#p.plot(x,wanniern(x,0,0,0*1.0))
#p.plot(x,wannier(x,d,0)**2)
#p.show()

####animated wannier function
#x = numpy.arange(-5*d,5*d,xstep)
#line, = p.plot(x,wanniern(x,0,0,0*1.0))
#for s in range(1,25):
#  line.set_ydata(wanniern(x,0,0,s*1.0))  # update the data
#  p.draw()                         # redraw the canvas
    
####check norm and orthogonality
#print integrate(lambda x: wanniern(x,0,0).real**2,-3*d,3*d,xstep)
#print integrate(lambda x: wanniern(x,0,0).real*wanniern(x,d,0).real,-3*d,3*d,xstep)



