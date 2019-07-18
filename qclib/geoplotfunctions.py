import numpy as np
from shapely.geometry import Point
from shapely.geometry.polygon import Polygon
import shapefile


def setgeoaxes(fig,ax,xrange,yrange,changeaxis):
    
    # set initial x and y ranges
    ax.set_xlim(xrange)
    ax.set_ylim(yrange)
    
    # plot aspect ratio
    wfig,hfig = fig.get_size_inches()
    _, _, wax, hax = ax.get_position().bounds
    yoverxratio = hax/wax*(hfig/wfig)
    
    # coordinate information
    dlonold = np.diff(xrange)/2
    dlatold = np.diff(yrange)/2
    meanlon = np.mean(xrange)
    meanlat = np.mean(yrange)
    
    # correct contraction ratio for latitude
    lonoverlatratio = np.cos(meanlat*np.pi/180)
    
    # find new dlat and dlon such that the other is conserved and the aspect ratio is accurate
    dlatnew = dlonold/lonoverlatratio*yoverxratio
    dlonnew = dlatold*lonoverlatratio/yoverxratio
    
    latrangenew = [meanlat-dlatnew,meanlat+dlatnew]
    lonrangenew = [meanlon-dlonnew,meanlon+dlonnew]
    
    # find new axes limits
    if changeaxis.lower() == 'x':
        ax.set_xlim(lonrangenew)
    elif changeaxis.lower() == 'y':
        ax.set_ylim(latrangenew)
    


def setgeotick(ax):
    
    # getting plot info
    xticks = ax.get_xticks()
    yticks = ax.get_yticks()

    xticklabels = ax.get_xticklabels()
    yticklabels = ax.get_yticklabels()
    
    # xticklabel correction
    for i in range(len(xticklabels)):
        
        # hemisphere of current tick
        if xticks[i] >= 0:
            hem = 'E'
        else:
            hem = 'W'
            
        # pull current tick label
        clab = str(abs(xticks[i])) + '$^\circ$' + hem
        xticklabels[i]._text = clab
        
    # yticklabel correction
    for i in range(len(yticklabels)):
        if yticks[i] >= 0:
            hem = 'N'
        else:
            hem = 'S'
        clab = str(abs(yticks[i])) + '$^\circ$' + hem
        yticklabels[i]._text = clab
        
    # applying corrections
    ax.set_xticklabels(xticklabels)
    ax.set_yticklabels(yticklabels)


    
# determine ocean basin, localized region from latitude/longitude
# region data from Natural Earth Physical Labels dataset
# https://www.naturalearthdata.com/downloads/10m-physical-vectors/10m-physical-labels/
def getoceanregion(lon,lat):
    
    droppoint = Point(lon, lat)
    region = 'Region Unassigned'
    
    regioninput = shapefile.Reader("qcdata/regions/World_Seas_IHO_v3.shp")
    shapes = regioninput.shapes()
    
    #reading in list of first NANs
    nanind = []
    f_in = open('qcdata/regions/IHO_seas.txt','r')
    for line in f_in:
        nanind.append(int(line.strip()))

    for i in range(len(shapes)):
        if Polygon(shapes[i].points[:nanind[i]]).contains(droppoint):
            region = regioninput.record(i).NAME
        
    return region
