import qclib.geoplotfunctions as gplt
import numpy as np
import cmocean.cm as cmo
from matplotlib.colors import ListedColormap

def makeprofileplot(ax,rawtemperature,rawdepth,temperature,depth,climotempfill,climodepthfill,dtg,matchclimo):
    climohandle = ax.fill(climotempfill,climodepthfill,color='b',alpha=0.3,label='Climo')
    climohandle = climohandle[0]
    ax.plot(rawtemperature,rawdepth,'k',linewidth=2,label='Raw')
    ax.plot(temperature,depth,'r',linewidth=2,label='QC')
    if matchclimo == 0:
        ax.text(np.max(temperature)-10,900,'Climatology Mismatch!',color = 'r')
    ax.set_xlabel('Temperature ($^\circ$C)')
    ax.set_ylabel('Depth (m)')
    ax.set_title('Drop: ' + dtg,fontweight="bold")
    ax.legend()
    ax.grid()
    ax.set_xlim([-2,32])
    ax.set_ylim([5,1000])
    ax.invert_yaxis()
    
    return climohandle
    

def makelocationplot(fig,ax,lat,lon,dtg,exportlon,exportlat,exportrelief,dcoord):
    
    #get basin and region
    region = gplt.getoceanregion(lon,lat)
    
    #set inital axis limits
    lonrange = [round(lon)-dcoord,round(lon)+dcoord]
    latrange = [round(lat)-dcoord,round(lat)+dcoord]

    topo = np.genfromtxt('qclib/topocolors.txt',delimiter=',')
    alphavals = np.ones((np.shape(topo)[0], 1))
    topo = np.append(topo, alphavals, axis=1)
    topomap = ListedColormap(topo)

    c = ax.pcolormesh(exportlon,exportlat,exportrelief,vmin=-4000,vmax=4000,cmap = topomap)
    cbar = fig.colorbar(c,ax=ax)
    cbar.set_label('Elevation (m)')
#    gplt.addcoastdata(ax,latrange,lonrange,'k')
    
    #scatter AXBT location
    ax.scatter(lon,lat,color='r',marker='x',linewidth=2) 
    #overlay dtg in text
    halflim = dcoord*0.309
    ax.fill([lon-halflim,lon-halflim,lon+halflim,lon+halflim],[lat+0.6,lat+1.25,lat+1.25,lat+0.6],color='w',edgecolor='none',alpha=0.2)
    ax.text(lon-halflim,lat+0.75,dtg,fontweight='bold')
    
    #plot formatting
    gplt.setgeoaxes(fig,ax,lonrange,latrange,'x')
    
    gplt.setgeotick(ax)
    ax.grid()
    ax.set_title(' Region: ' + region,fontweight="bold")