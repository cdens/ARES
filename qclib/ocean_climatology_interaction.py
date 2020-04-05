# =============================================================================
#     Code: ocean_climatology_interaction.py
#     Author: ENS Casey R. Densmore, 20JUN2019
#     
#     Purpose: Interaction with ocean climatology data
#
#   Functions:
#       o smoothdata = runningsmooth(data,halfwindow): Computes running mean
#           of length 2*"halfwindow" + 1 on "data", returns "smoothdata"
#       o climotemps,depth,tempfill,depthfill = getclimatologyprofile(lat,
#           lon,month,climodata): Returns climatology temperature/depth profile
#           from climodata dict for lat,lon,month combination.
#           Returns:
#               > climotemps, depth: Climatology temperature-depth profile
#               > tempfill, depthfill: Vectors corresponding to filled shape for
#                   climatological profile +/- a given buffer. Currently that 
#                   buffer is set within the function, however this could easily
#                   be modified to depend on external data if a climatology 
#                   dataset with standard deviations becomes available
#       o matchclimo,climobottomcutoff = comparetoclimo(temperature,depth,
#           climotemps,climodepths,climotempfill,climodepthfill)
#           Takes data from getclimatologyprofile() and compares to the actual
#           QC'ed profile to determine if the two roughly match. 
#           Returns:
#               > matchclimo: 1 if match, 0 if not a match
#               > climobottomcutoff: climo-indicated profile cutoff depth due
#                   to a profile bottom strike
#       o maxoceandepth,exportlat,exportlon,exportrelief = getoceandepth(lat,
#           lon,dcoord,bathydata): Determines ocean depth and pulls bathymetry
#           data within certain region (of size 2*dcoord deg lon x 2*dcoord deg
#           lat) of the point lat/lon. 
#           Returns:
#               > maxoceandepth: depth of ocean at point
#               > exportlat, exportlon, exportrelief: lat/lon vectors, 2D bathy
#                   data used in makeAXBTplots.makelocationplot()
#
# =============================================================================

import numpy as np
from shapely.geometry import Point
from shapely.geometry.polygon import Polygon
import scipy.interpolate as sint

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
def getclimatologyprofile(lat,lon,month,climodata):

    #accessing climatology grid data
    clon = climodata["lon"]
    clat = climodata["lat"]
    depth = climodata["depth"]
    
    #pulling current month's temperatures + stdevs, converting to int64, correcting scale
    #TODO: add lat/lon indexing so it only pulls a small spatial subset to reduce size
    cmonthtemps = climodata["temp"][:,:,:,month-1].astype('int64')/100
    cmonthdevs = climodata["stdev"][:,:,:,month-1].astype('int64')/100
    
    #correting fill values to NaN
    cmonthtemps[cmonthtemps == -320] = np.NaN
    cmonthdevs[cmonthdevs == 2.55] = np.NaN

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
    climotemps = sint.interpn((depth,clat, clon), cmonthtemps, (depth,lat, lon))
    
    #error margin for shading is +/- 1 standard deviation
    climotemperrors = sint.interpn((depth,clat, clon), cmonthdevs, (depth,lat, lon))
    
    #generating fill vectors
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

        #max depth for climo comparison (if a bottom strike is detected, consider that when comparing profile to climatology)
        if np.isnan(climobottomcutoff):
            maxd = 1E10
        else:
            maxd = climobottomcutoff
        
        #check to see if climatology generally matches profile (is 90% of profile within climatology fill window?)
        isinclimo = []
        climopolylist = []
        for i in range(len(climotempfill)):
            climopolylist.append([climotempfill[i],climodepthfill[i]])
        climopolygon = Polygon(climopolylist)    
        
        depth[0] = 0.1
        for i in range(len(temperature)):
            if depth[i] <= maxd:
                curpoint = Point(temperature[i], depth[i])
                isinclimo.append(int(climopolygon.contains(curpoint)))
        if sum(isinclimo)/len(isinclimo) >= 0.9: #this is where the 90% statistic is set
            matchclimo = 1
        else:
            matchclimo = 0
    
    else: #if no valid datapoints- say that the climatology matches (because we can't tell otherwise)
        matchclimo = 1
        climobottomcutoff = np.nan
        
    return matchclimo,climobottomcutoff



#pull ocean depth from ETOPO1 Grid-Registered Ice Sheet based global relief dataset 
#Data source: NOAA-NGDC: https://www.ngdc.noaa.gov/mgg/global/global.html
def getoceandepth(lat,lon,dcoord,bathydata):

    #pulling bathymetry data
    clon = bathydata['x']
    clat = bathydata['y']
    
    #setting indices/pulling data within the wanted region
    isnearlatind = np.less_equal(clat,lat+dcoord+3)*np.greater_equal(clat,lat-dcoord-3)
    isnearlonind = np.less_equal(clon,lon+dcoord+3)*np.greater_equal(clon,lon-dcoord-3)
    exportlat = clat[isnearlatind]
    exportlon = clon[isnearlonind]
    exportrelief = bathydata['z'][:,isnearlatind] #have to pull one index at a time (why Python?...)
    exportrelief = exportrelief[isnearlonind,:].astype('int64')
    
    #interpolate maximum ocean depth
    maxoceandepth = -sint.interpn((exportlon,exportlat),exportrelief,(lon,lat))
    maxoceandepth = maxoceandepth[0]
    
    num = 2 #adjust this to pull every n elements for topographic data
    exportlat = exportlat[::num]
    exportlon = exportlon[::num]
    exportrelief = exportrelief[::num,::num]
    exportrelief = exportrelief.transpose() #transpose matrix
    
    return maxoceandepth,exportlat,exportlon,exportrelief
    