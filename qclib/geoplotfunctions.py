# =============================================================================
#     Code: geoplotfunctions.py
#     Author: ENS Casey R. Densmore, 20JUN2019
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
#     Purpose: Functions necessary to customize the AXBT location plots (or 
#       geographic plots in general).
#
#   Functions:
#       o setgeoaxes(fig,ax,xrange,yrange,changeaxis): Adjusts the lat/lon limits
#           of a plot to account for plot aspect ratio and latitude
#           Inputs:
#               > fig, ax: handle to current figure and axes
#               > xrange,yrange: preferred (approximate) lat/lon limits for plot
#               > changeaxis: axis whose limits may not match x/yrange to account
#                   for aspect ratio and latitude
#       o setgeotick(ax): Changes x/y label to append degrees N,S,E,W
#           Inputs: ax: handle to current figure and axes
#       o region = getoceanregion(lon,lat): Gets ocean basin, sea, or other feature
#           corresponding to provided lat/lon using the World Seas IHO v3 shape file
#           Requires IHO shapefile and all associated files in same directory
#           
# =============================================================================


import numpy as np
from shapely.geometry import Point
from shapely.geometry.polygon import Polygon
from shapefile import Reader as shread




def setgeoaxes(fig,ax,xrange,yrange,changeaxis):
    
    # set initial x and y axis limits
    ax.set_xlim(xrange)
    ax.set_ylim(yrange)
    
    # determine plot aspect ratio
    wfig,hfig = fig.get_size_inches()
    _, _, wax, hax = ax.get_position().bounds
    yoverxratio = hax/wax*(hfig/wfig)
    
    # solve coordinate information
    dlonold = np.diff(xrange)/2
    dlatold = np.diff(yrange)/2
    meanlon = np.mean(xrange)
    meanlat = np.mean(yrange)
    
    # find correct contraction ratio as a function of latitude
    lonoverlatratio = np.cos(meanlat*np.pi/180)
    
    # find new dlat and dlon such that the other is conserved and the aspect ratio is accurate
    dlatnew = dlonold/lonoverlatratio*yoverxratio
    dlonnew = dlatold*lonoverlatratio/yoverxratio
    
    # corrected axes limits, depending on which axis is changed
    latrangenew = [meanlat-dlatnew,meanlat+dlatnew]
    lonrangenew = [meanlon-dlonnew,meanlon+dlonnew]
    
    # set new axis limits for the axis specified by "changeaxis"
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
    for i,ctick in enumerate(xticks):
        if ctick >= 0 and ctick <= 180: #eastern hemisphere
            hem = 'E'
        elif ctick < 0 and ctick > -180: #western hemisphere
            hem = 'W'
            ctick = abs(ctick)
        elif ctick <= -180: #WH plot overlap into EH
            ctick = ctick + 360
            hem = 'E'
        elif ctick > 180: #EH plot overlap into WH
            ctick = abs(ctick - 360)
            hem = 'W'
        clab = f"{ctick}$^\circ${hem}" # set current tick label
        xticklabels[i]._text = clab
        
    # yticklabel correction
    for i,ctick in enumerate(yticks):
        if ctick >= 0: # hemisphere of current tick
            hem = 'N'
        else:
            hem = 'S'
        clab = f"{ctick}$^\circ${hem}" # set current tick label
        if abs(ctick) <= 90:
            yticklabels[i]._text = clab
        else:
            yticklabels[i]._text = ''
        
    # applying corrections
    ax.set_xticklabels(xticklabels)
    ax.set_yticklabels(yticklabels)


    
    
# determine ocean basin, localized region from latitude/longitude
# region data from Natural Earth Physical Labels dataset
# https://www.naturalearthdata.com/downloads/10m-physical-vectors/10m-physical-labels/
def getoceanregion(lon,lat):
    
    #set point, initialize region output
    droppoint = Point(lon, lat)
    region = False
    
    #load shape file data
    regioninput = shread("qcdata/regions/World_Seas_IHO_v3.shp")
    shapes = regioninput.shapes()
    
    #reading in list of first NANs
    nanind = []
    f_in = open('qcdata/regions/IHO_seas.txt','r')
    for line in f_in:
        nanind.append(int(line.strip()))

    #searching for region containing lat/lon point, overwriting "region" variable if found
    for i in range(len(shapes)):
        if Polygon(shapes[i].points[:nanind[i]]).contains(droppoint):
            region = regioninput.record(i).NAME
            
    #if point wasn't in any seas distinguished by the shape file, logic to determine ocean basin
    if not region: 
        if lat >= 66.5:
            region = "Arctic Ocean"
        elif lat <= -60:
            region = "Southern Ocean"
        else:
            indianocn = Polygon([(20, -60), (20, 31), (100, 31), (100, 0), (146.817, 0), (146.817, -60)])
            pacificeh = Polygon([(146.817, -60), (146.817, 0), (100, 0), (100, 66.5), (180, 66.5), (180, -60)])
            pacificwh = Polygon([(-180, -60), (-180, 66.5), (-100, 66.5), (-100, 18), (-90, 18), (-90, 14), (-84, 14), (-84, 9), (-70, 9), (-70, -60)])
            
            if indianocn.contains(droppoint):
                region = "Indian Ocean"
                
            elif pacificeh.contains(droppoint) or pacificwh.contains(droppoint):
                if lat >= 0:
                    region = "Northern Pacific Ocean"
                else:
                    region = "Southern Pacific Ocean"
                    
            else: #only remaining option is atlantic
                if lat >= 0:
                    region = "Northern Atlantic Ocean"
                else:
                    region = "Southern Atlantic Ocean"
        
    return region
