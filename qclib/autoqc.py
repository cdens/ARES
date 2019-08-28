import numpy as np

def autoqc(rawtemp,rawdepth,sfc_correction,maxdepth,maxderiv,profres,checkforgaps):
    
# =============================================================================
#     Code: autoqc.py
#     Author: ENS Casey R. Densmore, 18JUN2019
#    
#     Purpose: This function quality controls a raw temperature-depth profile 
#     (rawtemp, rawdepth) determining inflection points with curvature >= reslev,
#     isothermal above sfc_correction (mitigate erroneous sfc spikes), and cut 
#     off at z = maxdepth. 
#     Additional considerations incorporated to remove the effects of VHF 
#     interference triggering false starts and other issues associated with
#     AXBT data transmission.
# =============================================================================
    
    #Step 1: cut off all values below maximum depth
    index = rawdepth <= maxdepth
    rawtemp = rawtemp[index]
    rawdepth = rawdepth[index]
    
    #Step 2: remove spikes using running standard deviation filter
    temp_despike = np.array([])
    depth_despike = np.array([])
    
    for n in range(len(rawdepth)):
        
        #assigning region for running standard deviation filter
        if n <= 24:
            tempspike = rawtemp[:49]
        elif n >= len(rawdepth)-51:
            tempspike = rawtemp[-50:]
        else:
            tempspike = rawtemp[n-25:n+25]
        
        #mean and standard deviation of current range
        curmean = np.mean(tempspike)
        curstd = np.std(tempspike)
        
        #only retain values within +/- 1 standard deviation of running mean
        if abs(rawtemp[n]-curmean) <= curstd:
            depth_despike = np.append(depth_despike,rawdepth[n])
            temp_despike = np.append(temp_despike,rawtemp[n])
    
    
    #Step 3: smooth the despiked profile
    temp_smooth = np.array([])
    depth_smooth = depth_despike.copy()
    smoothint = 5. #smoothing range in meters
    for n in range(len(depth_despike)):
        if depth_despike[n] <= smoothint/2:
            temp_smooth = np.append(temp_smooth,np.mean(temp_despike[np.less_equal(depth_despike,smoothint)]))
        elif depth_despike[n] >= depth_despike[-1] - smoothint/2:
            temp_smooth = np.append(temp_smooth,np.mean(temp_despike[np.greater_equal(depth_despike,depth_despike[-1]-smoothint)]))
        else:
            ge = np.greater_equal(depth_despike, depth_despike[n] - smoothint/2)
            le = np.less_equal(depth_despike,depth_despike[n] + smoothint/2)
            
            goodindex = np.all([ge,le],axis=0)
            temp_smooth = np.append(temp_smooth,np.mean(temp_despike[goodindex]))
        
        
    
    #Step 4: Find and remove gaps due to VHF interference kicking off early Mk21 start
    if checkforgaps:
        maxcheckdepth = np.min([len(depth_smooth),40])
        isgap = [0]*maxcheckdepth
        for i in range(1,maxcheckdepth):
            if depth_smooth[i] >= depth_smooth[i-1]+5: #NOTE: the logical 1 is placed at the first depth AFTER the gap
                isgap[i] = 1
        #if there is/are 1+ gap(s), find the deepest one and correct as surface
        if np.sum(isgap) > 0:
            lastgap = np.max(np.argwhere(isgap))
            realstartdepth = depth_smooth[lastgap]
            temp_smooth = temp_smooth[lastgap:]
            depth_smooth = depth_smooth[lastgap:]-realstartdepth


    
    #Step 5: Set all values above sfc_correction to equal t(z=sfc_correction)
    if sfc_correction > 0:
        t_corrected = np.interp(sfc_correction,depth_smooth,temp_smooth)
        temp_smooth[depth_smooth <= sfc_correction] = t_corrected
    
    
    
    #Step 6: pull critical points from profile to save
    dTdz = [] #first derivative calc
    dT2dz2 = [] #second derivative calc
    for i in range(1,len(temp_smooth)-1):
        dTdz.append(((temp_smooth[i+1] - temp_smooth[i-1])/
              (depth_smooth[i+1]-depth_smooth[i-1])))
        dT2dz2.append(((temp_smooth[i+1] - 2*temp_smooth[i] + temp_smooth[i-1])/
          (0.5*(depth_smooth[i+1]-depth_smooth[i])+0.5*(depth_smooth[i]-depth_smooth[i-1]))**2))
    
    depth = []
    temperature = []
    lastdepth = -15
    for i in range(len(dT2dz2)):
        if dTdz[i] <= 0.5: #constraint on first derivative of temp with depth
            iscriticalpoint = (depth_smooth[i+1]-lastdepth >= profres or
                               abs(dT2dz2[i]) >= maxderiv)
            
            #if the point is a critical value given the selected resolution level
            if iscriticalpoint:
                depth.append(depth_smooth[i+1])
                temperature.append(temp_smooth[i+1])
                lastdepth = depth_smooth[i+1]
                
    
    #add surface value
    if depth[0] != 0:
        sst = temperature[0]
        depth.insert(0,0)
        temperature.insert(0,sst)
    
    temperature = np.array(temperature)
    depth = np.array(depth)
    
    return [temperature,depth]