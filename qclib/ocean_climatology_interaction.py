import numpy as np
from shapely.geometry import Point
from shapely.geometry.polygon import Polygon
import scipy.interpolate as sint
import scipy.io as sio

def runningsmooth(data,halfwindow):
    
    #if the running filter is longer than the dataset, return an array with same length as dataset containing dataset mean
    if halfwindow*2+1 >= len(data): 
        smoothdata = np.ones(len(data))*np.mean(data)
        
    #otherwise apply smoothing filter
    else:
        smoothdata = np.array([])
        for i in range(len(data)):
            if i <= halfwindow:
                smoothdata = np.append(smoothdata,np.mean(data[:i+halfwindow]))
            elif i >= len(data) - halfwindow:
                smoothdata = np.append(smoothdata,np.mean(data[i-halfwindow:]))
            else:
                smoothdata = np.append(smoothdata,np.mean(data[i-halfwindow:i+halfwindow]))
            
    return smoothdata


#pulling climatology profile, creating polygon for shaded "climo match" region
def getclimatologyprofile(lat,lon,month):

    # climodata = Dataset('qcdata/climo/Levitus_monthlyoceanclimo.nc', mode='r')
    # clon = climodata.variables['X'][:]
    # clat = climodata.variables['Y'][:]
    # depth = climodata.variables['Z'][:]
    # temp_climo_gridded = climodata.variables['temp'][:]

    climodata = sio.loadmat('qcdata/climo/LevitusClimo.mat')
    clon = climodata['X'][:,0]
    clat = climodata['Y'][:,0]
    depth = climodata['Z'][:,0]
    temp_climo_gridded = climodata['temp']

    #get current month of climo
    # temp_climo_curmonth = temp_climo_gridded[month-1,:,:,:]
    temp_climo_curmonth = temp_climo_gridded[:,:,:,month-1]

    #convert profile longitude from degW<0 to degW>180 to match climo arrangement
    if lon < 0:
        lon = 360 + lon
        
    #making sure coordinates are within interpolation area
    if lon < 0.5:
        lon = 0.5
    elif lon > 359.5:
        lon = 359.5
    if lat < -89.5:
        lat = -89.5
    elif lat > 89.5:
        lat = 89.5

    #interpolate to current latitude/longitude
    # climotemps = sint.interpn((clon,clat,depth),temp_climo_curmonth,(lon,lat,depth))
    climotemps = sint.interpn((depth,clat, clon), temp_climo_curmonth, (depth,lat, lon))

    #introduce error range for fill- should be +/- 1 standard deviation when standard deviation data is available
    climotemperrors = np.array([3.,3.,3.,3.,3.,3.,3.,3.,3.,3.,2.,2.,2.,2.,1.,1.,1.,1.,1.])
    
    tempfill = np.append(climotemps-climotemperrors,np.flip(climotemps+climotemperrors))
    depthfill = np.append(depth,np.flip(depth))
    
    return [climotemps,depth,tempfill,depthfill]


#comparing current profile to climatology
def comparetoclimo(temperature,depth,climotemps,climodepths,climotempfill,climodepthfill):
    
    climotemps[np.less_equal(climotemps,-8)] = np.nan
    
    #interpolating climatology to match profile depths
    intclimotemp = np.interp(depth,climodepths,climotemps)
    
    #identifying and removing NaNs from dataset
    isnandata = np.isnan(intclimotemp*temperature)
    
    if sum(isnandata) != len(isnandata): #if there are non-NaN datapoints
        temperature = temperature[isnandata == 0]
        intclimotemp = intclimotemp[isnandata == 0]
        depth = depth[isnandata == 0]
        
        #determining profile slopes
        climoslope = np.diff(intclimotemp)/np.diff(depth)
        profslope = np.diff(temperature)/np.diff(depth)
        slopedepths = 0.5*depth[1:] + 0.5*depth[:-1]
        
        #comparing slopes:
        threshold = 0.1
        ismismatch = abs(runningsmooth(climoslope-profslope, 50)) >= threshold
        
        #determining if there is a max depth
        if sum(ismismatch) != 0:
            climobottomcutoff = np.max(slopedepths[ismismatch])
            isabovecutoff = np.less_equal(depth,climobottomcutoff)
            temperature = temperature[isabovecutoff == 1]
            depth = depth[isabovecutoff == 1]
        else:
            climobottomcutoff = np.nan
        
        #check to see if climatology generally matches profile (is 90% of profile within climatology fill window?)
        isinclimo = []
        climopolylist = []
        for i in range(len(climotempfill)):
            climopolylist.append([climotempfill[i],climodepthfill[i]])
        climopolygon = Polygon(climopolylist)    
        
        depth[0] = 0.1
        for i in range(len(temperature)):
            curpoint = Point(temperature[i], depth[i])
            isinclimo.append(int(climopolygon.contains(curpoint)))
        if sum(isinclimo)/len(isinclimo) >= 0.9:
            matchclimo = 1
        else:
            matchclimo = 0
    
    else: #if no valid datapoints- say that the climatology matches (because we can't tell otherwise)
        matchclimo = 1
        climobottomcutoff = np.nan
        
    return matchclimo,climobottomcutoff



#pull ocean depth from ETOPO1 Grid-Registered Ice Sheet based global relief dataset 
#Data source: NOAA-NGDC: https://www.ngdc.noaa.gov/mgg/global/global.html
def getoceandepth(lat,lon,dcoord):

    bathydata = sio.loadmat('qcdata/bathy/ETOPO1_bathymetry.mat')

    # clon = np.array(bathydata.variables['x'][:])
    # clat = np.array(bathydata.variables['y'][:])
    # z = np.array(bathydata.variables['z'][:])

    clon = bathydata['x'][:,0]
    clat = bathydata['y'][:,0]
    z = bathydata['z']
    
    #interpolate maximum ocean depth
    maxoceandepth = -sint.interpn((clon,clat),z,(lon,lat))
    maxoceandepth = maxoceandepth[0]
    
    isnearlatind = np.less_equal(clat,lat+dcoord+3)*np.greater_equal(clat,lat-dcoord-3)
    isnearlonind = np.less_equal(clon,lon+dcoord+3)*np.greater_equal(clon,lon-dcoord-3)
    
    exportlat = clat[isnearlatind]
    exportlon = clon[isnearlonind]
    exportrelief = z[:,isnearlatind]
    exportrelief = exportrelief[isnearlonind,:]
    
    num = 1 #adjust this to pull every n elements for topographic data
    exportlat = exportlat[::num]
    exportlon = exportlon[::num]
    exportrelief = exportrelief[::num,::num]
    exportrelief = exportrelief.transpose()
    
    return maxoceandepth,exportlat,exportlon,exportrelief
    