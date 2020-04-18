# =============================================================================
#     Code: autoqc.py
#     Author: ENS Casey R. Densmore, 18JUN2019
#    
#     Purpose: This function quality controls a raw temperature-depth profile 
#     (rawtemp, rawdepth)
#     Additional considerations incorporated to remove the effects of VHF 
#     interference triggering false starts, spike removal and other issues associated with
#     AXBT data transmission.
#
#   Inputs:
#       o rawtemp, rawdepth: unedited temperature-depth profile
#       o smoothlev: smoothing window length
#       o profres: minimum vertical resolution of profile (m)
#       o maxdev: maximum point deviation threshold for despiker
#       o checkforgaps: logical flag to check for and correct VHF false starts
# =============================================================================


import numpy as np

def autoqc(rawtemp,rawdepth,smoothlev,profres,maxdev,checkforgaps):
    

    #Step 1: Find and remove gaps due to VHF interference kicking off early Mk21 start
    if checkforgaps:
        rawdepth,rawtemp = removegaps(rawdepth,rawtemp)
    
    #Step 2: remove spikes using running standard deviation filter
    depth_despike,temp_despike = rundespiker(rawdepth,rawtemp,maxdev)
    
    #Step 3: smooth the despiked profile
    depth_smooth,temp_smooth = runsmoother(depth_despike,temp_despike,smoothlev)
    
    #Step 4: pull critical points from profile to save (note- returned variables are lists)
    depth,temperature = subsample_profile(depth_smooth,temp_smooth,profres)

    #add surface value if one doesn't exist
    if depth[0] != 0:
        sst = temperature[0]
        depth.insert(0,0)
        temperature.insert(0,sst)
    
    #convert back to numpy arrays
    temperature = np.array(temperature)
    depth = np.array(depth)
    
    return [temperature,depth]
    
    
    
    
    
#function to identify and remove gaps due to false starts from interference
def removegaps(rawdepth,rawtemp):
    donegapcheck = False
    while not donegapcheck:
        maxcheckdepth = 50 #only checks the upper 50m of the profile
        maxgapdiff = 10 #if gap is larger than this range (m), correct profile
        isgap = [0]
        for i in range(1,len(rawdepth)):
            if (rawdepth[i] >= rawdepth[i-1]+ maxgapdiff) and (rawdepth[i-1] <= maxcheckdepth): #if there is a gap of sufficient size to correct
                isgap.append(1) #NOTE: the logical 1 is placed at the first depth AFTER the gap
            else:
                isgap.append(0)

        #if there are gaps, find the deepest one and correct t/d profile with that depth as the surface (only works with linear fall rate equation)
        if np.sum(isgap) > 0:
            lastgap = np.max(np.argwhere(isgap))
            realstartdepth = rawdepth[lastgap]
            rawtemp = rawtemp[lastgap:]
            rawdepth = rawdepth[lastgap:]-realstartdepth
        else: #otherwise, exit loop
            donegapcheck = True
        
    return rawdepth,rawtemp
    
    
    
    
#removes spikes from profile with depth-based standard deviation filter
def rundespiker(rawdepth,rawtemp,maxdev):
    temp_despike = np.array([])
    depth_despike = np.array([])
    
    depthwin = 5 #range of spiker is +/- 5 meters
    maxdepth = np.max(rawdepth)
    
    for n,cdepth in enumerate(rawdepth):
        
        #assigning region for running standard deviation filter
        if cdepth <= depthwin:
            goodindex = np.less_equal(rawdepth,depthwin)
        elif cdepth >= maxdepth - depthwin:
            goodindex = np.greater_equal(rawdepth, maxdepth-depthwin)
        else:
            ge = np.greater_equal(rawdepth, cdepth - depthwin) #all depths above bottom threshold
            le = np.less_equal(rawdepth, cdepth + depthwin) #all depths below top threshold
            goodindex = np.all([ge,le],axis=0) #all depths with both requirements satisfied
            
        #pulling subset
        tempspike = rawtemp[goodindex]
        
        #mean and standard deviation of current range
        curmean = np.mean(tempspike)
        curstd = np.std(tempspike)
        
        #only retain values within +/- 1 standard deviation of running mean or top 10 m
        if abs(rawtemp[n]-curmean) <= maxdev*curstd or rawdepth[n] < 10:
            depth_despike = np.append(depth_despike,rawdepth[n])
            temp_despike = np.append(temp_despike,rawtemp[n])

    return depth_despike,temp_despike    
            
            
    
            
#run depth-based smoother- ensures that first and last datapoints match original profile
def runsmoother(depth_despike,temp_despike,smoothlev):
    
    temp_smooth = np.array([])
    depth_smooth = depth_despike.copy()
    mindepth = np.min(depth_despike)
    maxdepth = np.max(depth_despike)

    for n,cdepth in enumerate(depth_despike):
        if cdepth == mindepth or cdepth == maxdepth: #if first or last point in profile, append current temperature
            temp_smooth = np.append(temp_smooth,temp_despike[n])
            
        else: #otherwise- average a range of points
            if cdepth <= smoothlev/2: #in top of profile
                cursmoothlev = 2*cdepth
            elif cdepth >= maxdepth - smoothlev/2: #in bottom of profile
                cursmoothlev = 2*(maxdepth - cdepth)
            else: #in middle of profile
                cursmoothlev = smoothlev
                
            ge = np.greater_equal(depth_despike, cdepth - cursmoothlev/2)
            le = np.less_equal(depth_despike,cdepth + cursmoothlev/2)            
            goodindex = np.all([ge,le],axis=0)
                
            #append mean of all points in range as next datapoint
            temp_smooth = np.append(temp_smooth,np.mean(temp_despike[goodindex]))
            
    return depth_smooth,temp_smooth
    

    
    
#subsample profile
def subsample_profile(depth_smooth,temp_smooth,profres):
    
    dtdz = [] #calculating profile slope (append 0 at start and end so length matches that of depth_smooth)
    dtdz.append(0)
    for i in range(1,len(temp_smooth)-1): #need to use range here because we are only interested in a subset of indices
        #dtdz = (t3 - t1)/(z3 - z1): centered on z2
        dtdz.append(((temp_smooth[i+1] - temp_smooth[i-1])/ 
              (depth_smooth[i+1]-depth_smooth[i-1])))
    dtdz.append(0)

    depth = []
    temperature = []
    lastdepth = -100000 #large enough value so subsampler will always grab first datapoint
    for i,cdepth in enumerate(depth_smooth):
        #constraint on first derivative of temp with depth (no unrealistic spikes), if the point is a critical value given the selected resolution level, append to output profile
        if dtdz[i] <= 0.5 and cdepth-lastdepth >= profres:
            depth.append(cdepth)
            temperature.append(temp_smooth[i])
            lastdepth = cdepth
    
    return depth,temperature