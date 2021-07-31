 # =============================================================================
#     Code: makeAXBTplots.py
#     Author: ENS Casey R. Densmore, 20JUN2019
#     
#     Purpose: Create profile and location plots for AXBT drops
#
#    This file is part of the AXBT Realtime Editing System (ARES)
#
#    ARES is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    ARES is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with ARES.  If not, see <https://www.gnu.org/licenses/>.
#
#   Functions:
#       o climohandle = makeprofileplot(ax,rawtemperature,rawdepth,temperature,
#           depth,climotempfill,climodepthfill,dtg,matchclimo): Plots the overlaid
#           raw and QC'ed temperature-depth profiles, along with the shaded 
#           climatology at the given location/month
#           Inputs:
#               > ax: current plot axes
#               > rawtemperature, rawdepth: Unedited T-D profile
#               > temperature, depth: QC'ed T-D profile
#               > dtg: date/time (string) for title
#               > climotempfill, climodepthfill: Vectors corresponding to shape of
#                   filled climatology region to shade
#               > matchclimo: 1/0 or T/F corresponding to whether or not QC'ed 
#                   profile matches climo (plot is annotated if matchclimo = 0)
#           Returns: "climohandle": handle to climatology shading which can be
#               set to invisible, depending on user preference
#       o makelocationplot(fig,ax,lat,lon,dtg,exportlon,exportlat,exportrelief,dcoord):
#           Creates location plot for current drop with contoured bathymetry.
#           Uses code in geoplotfunctions.py to customize plot. 
#           Inputs:
#               > fig, ax: current plot figure and axes
#               > lat, lon: AXBT position for plot
#               > dtg: date/time (string) for title
#               > exportlon,exportlat,exportrelief: lon/lat vectors, 2D bathymetry
#                   field to be overlaid in plot
#               > dcoord: lon/lat range for plot (longitude and latitude limits
#                   on plot are set to position-dcoord:position+dcoord)
#           Returns: "climohandle": handle to climatology shading which can be       
#       
# =============================================================================

import qclib.geoplotfunctions as gplt
import numpy as np
from matplotlib.colors import ListedColormap



def makeprofileplot(ax,rawtemperature,rawdepth,temperature,depth,climotempfill,climodepthfill,dtg,matchclimo):
    
    #plotting climatology, raw/QC profiles
    climohandle = ax.fill(climotempfill,climodepthfill,color='b',alpha=0.3,label='Climo') #fill climo, save handle
    climohandle = climohandle[0]
    ax.plot(rawtemperature,rawdepth,'k',linewidth=2,label='Raw') #plot raw profile
    ax.plot(temperature,depth,'r',linewidth=2,label='QC') #plot QC profile
    
    #adding climo mismatch warning if necessary
    if matchclimo == 0:
        try: 
            maxT = np.max(temperature)
        except (NameError, ValueError, TypeError):
            maxT = np.max(rawtemperature)
            
        if maxT <= 10:
            xloc = maxT + 10
        else:
            xloc = maxT - 10
        ax.text(xloc,900,'Climatology Mismatch!',color = 'r') #noting climo mismatch if necessary

    #plot labels/ranges
    ax.set_xlabel('Temperature ($^\circ$C)')
    ax.set_ylabel('Depth (m)')
    ax.set_title('Drop: ' + dtg,fontweight="bold")
    ax.legend()
    ax.grid()
    ax.set_xlim([-3,32])
    ax.set_ylim([-5,1000])
    ax.set_yticks([0,100,200,400,600,800,1000])
    ax.set_yticklabels([0,100,200,400,600,800,1000])
    ax.invert_yaxis()
    
    return climohandle
    
    
    

def makelocationplot(fig,ax,lat,lon,dtg,exportlon,exportlat,exportrelief,dcoord):
    
    
    multipoints = False
    try:
        if len(lon) == len(lat) and len(lon) > 1:
            multipoints = True
        elif len(lon) != len(lat):
            raise Exception("Latitude and longitude lists must be equal in length!")
    except TypeError: #if lon/lat are floats (single point) this check raises a TypeError
        pass
        
    #set inital axis limits
    if multipoints:
        lonrange = [int(round(np.min(lon))-dcoord),int(round(np.max(lon))+dcoord)]
        latrange = [int(round(np.min(lat))-dcoord),int(round(np.max(lat))+dcoord)]
        region = gplt.getoceanregion(lon[0],lat[0]) #get basin and region for first point
        
    else:
        lonrange = [int(round(lon)-dcoord),int(round(lon)+dcoord)]
        latrange = [int(round(lat)-dcoord),int(round(lat)+dcoord)]
        region = gplt.getoceanregion(lon,lat) #get basin and region

    #read/generate topography colormap
    topo = np.genfromtxt('qclib/topocolors.txt',delimiter=',')
    alphavals = np.ones((np.shape(topo)[0], 1))
    topo = np.append(topo, alphavals, axis=1)
    topomap = ListedColormap(topo)

    #contour bathymetry
    c = ax.pcolormesh(exportlon,exportlat,exportrelief,vmin=-4000,vmax=10,cmap = topomap, shading='gouraud')
    ax.contour(exportlon, exportlat, exportrelief, np.arange(-8000,-4000,1000), colors='white',linestyles='dashed', linewidths=0.5,alpha=0.5)
    cbar = fig.colorbar(c,ax=ax)
    cbar.set_label('Elevation (m)')
    
    #scatter AXBT location
    if multipoints:
        for clat,clon in zip(lat,lon):
            ax.scatter(clon,clat,color='r',marker='x',linewidth=2) 
    else:
        ax.scatter(lon,lat,color='r',marker='x',linewidth=2) 
        #overlay dtg in text
        halflim = dcoord*0.309
        ax.text(lon-halflim,lat+0.75,dtg,fontweight='bold',bbox=dict(facecolor='white', alpha=0.3))
    
    #plot formatting
    gplt.setgeoaxes(fig,ax,lonrange,latrange,'x')
    dx = 3 #setting x tick spacing farther apart (every 3 degrees) so plot looks better
    ax.set_xticks([d for d in range(lonrange[0]-dx,lonrange[1]+dx,dx)]) 
    gplt.setgeotick(ax)
    ax.grid()
    ax.set_title(f"Region: {region}",fontweight="bold")
    
    
    