#
#    This file is part of the AXBT Realtime Editing System (ARES).
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
#   Mission Plotter functions 
#       o  


from platform import system as cursys

global slash
if cursys() == 'Windows':
    slash = '\\'
else:
    slash = '/'

from os import path
from traceback import print_exc as trace_error

from PyQt5.QtWidgets import (QLineEdit, QLabel, QSpinBox, QPushButton, QWidget, QFileDialog, QComboBox, QGridLayout, QDoubleSpinBox, QTableWidget, QTableWidgetItem, QHeaderView, QProgressBar, QApplication, QMessageBox, QTextEdit)
from PyQt5.QtCore import QObjectCleanupHandler, Qt, pyqtSlot
from PyQt5.QtGui import QColor

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap, LinearSegmentedColormap

import cartopy.crs as ccrs
from cartopy.mpl.gridliner import LONGITUDE_FORMATTER, LATITUDE_FORMATTER

import time as timemodule
import datetime as dt
import numpy as np

import qclib.ocean_climatology_interaction as oci

from ._globalfunctions import (addnewtab, whatTab, renametab, setnewtabcolor, closecurrenttab, savedataincurtab, postwarning, posterror, postwarning_option, closeEvent, parsestringinputs, CustomToolbar)

            
# =============================================================================
#     MISSION PLOTTER TAB AND INPUTS HERE
# =============================================================================
def makenewMissiontab(self):     
    try:

        newtabnum,curtabstr = self.addnewtab()
        
        #default values for tab
        if self.goodPosition:
            fillPlot = True
            clat = round(self.lat)
            clon = round(self.lon)
            extent = [clon-5,clon+5,clat-3,clat+3] #W,E,S,N
            
        else:
            extent = [-90,-60,10,35]
            fillPlot = False
            
        lwid = 2
        linecolor = "k"
        radius = 120 #km   
            
        #also creates proffig and locfig so they will both be ready to go when the tab transitions from signal Mission to profile editor
        self.alltabdata[curtabstr] = {"tab":QWidget(),"tablayout":QGridLayout(),"MissionFig":plt.figure(), "profileSaved":True,
                  "tabtype":"MissionPlotter","isprocessing":False, "datasource":None, "gpshandle":False, "lineactive":False, "linex":[], "liney":[], "interactivetype":0, "overlayhandles":[], "plotEvent":False}
        
        self.alltabdata[curtabstr]["colornames"] = ['Black', 'White', 'Blue', 'Green', 'Red', 'Cyan', 'Magenta', 'Yellow']
        self.alltabdata[curtabstr]["colors"] = ['k', 'w', 'b', 'g', 'r', 'c', 'm', 'y']
        self.alltabdata[curtabstr]["units"] = ["km","mi","nm"] 
        self.alltabdata[curtabstr]["unitconversion"] = [1, 1.60934, 1.852]
                  
        self.setnewtabcolor(self.alltabdata[curtabstr]["tab"])
        
        #initializing raw data storage
        self.alltabdata[curtabstr]["plotlines"] = []
        
        self.alltabdata[curtabstr]["tablayout"].setSpacing(10)

        #creating new tab, assigning basic info
        self.tabWidget.addTab(self.alltabdata[curtabstr]["tab"],'New Tab') 
        self.tabWidget.setCurrentIndex(newtabnum)
        self.tabWidget.setTabText(newtabnum, "Mission Planner")
        self.alltabdata[curtabstr]["tabnum"] = self.totaltabs #assigning unique, unchanging number to current tab
        self.alltabdata[curtabstr]["tablayout"].setSpacing(10)
        
        #ADDING FIGURE TO GRID LAYOUT
        self.alltabdata[curtabstr]["MissionCanvas"] = FigureCanvas(self.alltabdata[curtabstr]["MissionFig"]) 
        self.alltabdata[curtabstr]["tablayout"].addWidget(self.alltabdata[curtabstr]["MissionCanvas"],0,0,20,3)
        self.alltabdata[curtabstr]["MissionCanvas"].setStyleSheet("background-color:transparent;")
        self.alltabdata[curtabstr]["MissionFig"].patch.set_facecolor('None')  
        self.alltabdata[curtabstr]["MissionToolbar"] = CustomToolbar(self.alltabdata[curtabstr]["MissionCanvas"], self) 
        self.alltabdata[curtabstr]["tablayout"].addWidget(self.alltabdata[curtabstr]["MissionToolbar"],21,1,1,1)   
        
        #and add new buttons and other widgets
        self.alltabdata[curtabstr]["tabwidgets"] = {}
        
        #making widgets
        self.alltabdata[curtabstr]["tabwidgets"]["boundaries"] = QLabel('Boundaries:') 
        self.alltabdata[curtabstr]["tabwidgets"]["updateplot"] = QPushButton('Update Plot')  
        self.alltabdata[curtabstr]["tabwidgets"]["updateplot"].clicked.connect(self.updateMissionPlot)
        
        
        self.alltabdata[curtabstr]["tabwidgets"]["wboundtitle"] = QLabel('West:')
        self.alltabdata[curtabstr]["tabwidgets"]["eboundtitle"] = QLabel('East:')
        self.alltabdata[curtabstr]["tabwidgets"]["sboundtitle"] = QLabel('South:')
        self.alltabdata[curtabstr]["tabwidgets"]["nboundtitle"] = QLabel('North:') 
        
        self.alltabdata[curtabstr]["tabwidgets"]["wbound"] = QLineEdit(str(extent[0]))
        self.alltabdata[curtabstr]["tabwidgets"]["ebound"] = QLineEdit(str(extent[1]))
        self.alltabdata[curtabstr]["tabwidgets"]["sbound"] = QLineEdit(str(extent[2]))
        self.alltabdata[curtabstr]["tabwidgets"]["nbound"] = QLineEdit(str(extent[3]))
        
        
        self.alltabdata[curtabstr]["tabwidgets"]["updateposition"] = QPushButton('Update Position')  
        self.alltabdata[curtabstr]["tabwidgets"]["updateposition"].clicked.connect(self.updateMissionPosition)
        
        
        self.alltabdata[curtabstr]["tabwidgets"]["overlays"] = QLabel('Overlays:') 
        
        self.alltabdata[curtabstr]["tabwidgets"]["colortitle"] = QLabel('Line Color:') 
        self.alltabdata[curtabstr]["tabwidgets"]["colors"] = QComboBox() 
        for c in self.alltabdata[curtabstr]["colornames"]:
            self.alltabdata[curtabstr]["tabwidgets"]["colors"].addItem(c) 
        self.alltabdata[curtabstr]["tabwidgets"]["colors"].setCurrentIndex(self.alltabdata[curtabstr]["colors"].index(linecolor))
            
    
        self.alltabdata[curtabstr]["tabwidgets"]["linewidthtitle"] = QLabel('Line Width:') 
        self.alltabdata[curtabstr]["tabwidgets"]["linewidth"] = QSpinBox() 
        self.alltabdata[curtabstr]["tabwidgets"]["linewidth"].setRange(1,10)
        self.alltabdata[curtabstr]["tabwidgets"]["linewidth"].setSingleStep(1)
        self.alltabdata[curtabstr]["tabwidgets"]["linewidth"].setValue(lwid)
        
        self.alltabdata[curtabstr]["tabwidgets"]["radiustitle"] = QLabel('Radius:') 
        self.alltabdata[curtabstr]["tabwidgets"]["radius"] = QLineEdit(str(radius)) 
        self.alltabdata[curtabstr]["tabwidgets"]["radiusunits"] = QComboBox()
        for unit in self.alltabdata[curtabstr]["units"]:
            self.alltabdata[curtabstr]["tabwidgets"]["radiusunits"].addItem(unit)
        
        self.alltabdata[curtabstr]["tabwidgets"]["addline"] = QPushButton('Draw Line') 
        self.alltabdata[curtabstr]["tabwidgets"]["addline"].setCheckable(True)
        self.alltabdata[curtabstr]["tabwidgets"]["addline"].setChecked(False)
        self.alltabdata[curtabstr]["tabwidgets"]["addline"].clicked.connect(self.updateMissionPlot_line)
        self.alltabdata[curtabstr]["tabwidgets"]["addbox"] = QPushButton('Draw Box') 
        self.alltabdata[curtabstr]["tabwidgets"]["addbox"].clicked.connect(self.updateMissionPlot_box)
        self.alltabdata[curtabstr]["tabwidgets"]["addcircle"] = QPushButton('Draw Circle') 
        self.alltabdata[curtabstr]["tabwidgets"]["addcircle"].clicked.connect(self.updateMissionPlot_circle)
        
        
        #formatting widgets
        self.alltabdata[curtabstr]["tabwidgets"]["wboundtitle"].setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.alltabdata[curtabstr]["tabwidgets"]["eboundtitle"].setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.alltabdata[curtabstr]["tabwidgets"]["sboundtitle"].setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.alltabdata[curtabstr]["tabwidgets"]["nboundtitle"].setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.alltabdata[curtabstr]["tabwidgets"]["colortitle"].setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.alltabdata[curtabstr]["tabwidgets"]["linewidthtitle"].setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.alltabdata[curtabstr]["tabwidgets"]["radiustitle"].setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        
        #mouse lat and lon
        #connect the figure to the mouse move event so the x and y coordinate can be tracked
        self.alltabdata[curtabstr]["MissionCanvas"].mpl_connect('motion_notify_event', lambda event: self.mouse_move(event, curtabstr))
        self.alltabdata[curtabstr]['tabwidgets']['mouselatlabel'] = QLabel('Mouse Lat')
        self.alltabdata[curtabstr]['tabwidgets']['mouselonlabel'] = QLabel('Mouse Lon')
        self.alltabdata[curtabstr]['tabwidgets']['mouselat'] = QTextEdit()
        self.alltabdata[curtabstr]['tabwidgets']['mouselon'] = QTextEdit()
        self.alltabdata[curtabstr]['tabwidgets']['mouselat'].setReadOnly(True)
        self.alltabdata[curtabstr]['tabwidgets']['mouselat'].setReadOnly(True)
        
        
        #should be XX entries 
        widgetorder = ['mouselatlabel', 'mouselonlabel', 'mouselat', 'mouselon', "boundaries", "updateplot", "wboundtitle", "wbound", "eboundtitle", "ebound", "sboundtitle", "sbound", "nboundtitle", "nbound", "updateposition", "overlays", "colortitle", "colors", "linewidthtitle", "linewidth", "radiustitle", "radius", "radiusunits", "addline", "addbox", "addcircle"]
        
        wrows     = [0,0,1,1,2,3,4,4,4,4,5,5,5,5,6,8,9,9,10,10,11,11,11,13,14,15]
        wcols     = [5,7,5,7,5,5,5,6,8,9,5,6,8,9,5,5,5,8,5,8,5,8,9,5,5,5] 
        wrext     = [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1]
        wcolext   = [2,2,2,2,5,5,1,1,1,1,1,1,1,1,5,5,3,2,3,2,3,1,1,5,5,5]
        

        #adding user inputs
        for i,r,c,re,ce in zip(widgetorder,wrows,wcols,wrext,wcolext):
            self.alltabdata[curtabstr]["tabwidgets"][i].setFont(self.labelfont)
            self.alltabdata[curtabstr]["tablayout"].addWidget(self.alltabdata[curtabstr]["tabwidgets"][i],r,c,re,ce)
                

        #adjusting stretch factors for all rows/columns
        colstretch = [10,10,10,0,1,1,1,1,1,1,3]
        for col,cstr in enumerate(colstretch):
            self.alltabdata[curtabstr]["tablayout"].setColumnStretch(col,cstr)
        
        rowstretch = [5,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1]
        for row,rstr in enumerate(rowstretch):
            self.alltabdata[curtabstr]["tablayout"].setRowStretch(row,rstr)

        #making the current layout for the tab
        self.alltabdata[curtabstr]["tab"].setLayout(self.alltabdata[curtabstr]["tablayout"])
        
        #generating/formatting map axes
        self.alltabdata[curtabstr]["MissionAx"] = plt.axes(projection=ccrs.PlateCarree())
        if fillPlot:
            self.updateMissionPlot()

        #prep window to plot data
        self.alltabdata[curtabstr]["MissionCanvas"].draw() #refresh plots on window
        # self.alltabdata[curtabstr]["MissionToolbar"] = CustomToolbar(self.alltabdata[curtabstr]["MissionCanvas"], self) 
        # self.alltabdata[curtabstr]["tablayout"].addWidget(self.alltabdata[curtabstr]["MissionToolbar"],19,1,1,1)
        

        
        
    except Exception: #if something breaks
        trace_error()
        self.posterror("Failed to build new Mission Planner tab")
    
        
                
        
            
            
            
# =============================================================================
#        MISSION PROCESSOR PLOT UPDATER
# =============================================================================

def mouse_move(self, event, curtabstr):
    mouse_x = event.xdata
    mouse_y = event.ydata
    if mouse_x == None or mouse_y == None:
        text_x = 'N/A'
        text_y = 'N/A'
    else :
        text_x = str(round(mouse_x, 3))
        text_y = str(round(mouse_y, 3))
    
    self.alltabdata[curtabstr]['tabwidgets']['mouselat'].setText(text_y)
    self.alltabdata[curtabstr]['tabwidgets']['mouselon'].setText(text_x)
    return

#populating map axes
def plotMapAxes(self, fig, ax, extent):
    
    try:
        ax.cla()
        
        gl = ax.gridlines(draw_labels=True)
        gl.xformatter = LONGITUDE_FORMATTER
        gl.yformatter = LATITUDE_FORMATTER
        
        
        #checking that positions are whole numbers, within -180 to 180, -90 to 90, setting plot extent
        roundextent = []
        for i in extent:
            roundextent.append(int(np.round(i)))
        extent = roundextent    
        if extent[0] >= extent[1]:
            extent[0] -= 1
            extent[1] += 1
        if extent[2] >= extent[3]:
            extent[2] -= 1
            extent[3] += 1        
        for i,maxval in enumerate([180,180,90,90]):
            if extent[i] > maxval:
                extent[i] = maxval
            elif extent[i] < -maxval:
                extent[i] = -maxval
        ax.set_extent(extent)
        
        #contouring bathymetry data
        lonstopull = [lon for lon in range(extent[0],extent[1]+1)]
        latstopull = [lat for lat in range(extent[2],extent[3]+1)]
        lon,lat,data = oci.getbathydata(latstopull,lonstopull, self.bathymetrydata)
        lon = lon[::4]
        lat = lat[::4]
        data = data[::4,::4]
        data[data >= 0] = np.NaN
        
        conts = [100,250,500,1000,2500,5000,7500]
        colors = [[0.886271729124078,0.954615491464059,0.740091293728959,1],
        [0.338576643584847,0.692018371754271,0.641578720328368,1],
        [0.292203723814070,0.584764950085021,0.624862740533897,1],
        [0.258394967455256,0.480159292762069,0.601175999802655,1],
        [0.241741177927927,0.373135022148264,0.578802643189424,1],
        [0.256832205065477,0.262155154029401,0.499638604613378,1],
        [0.221762510221711,0.180277856909926,0.327115685990924,1]]
    
        #cmap = ListedColormap(colors)
        cmap = LinearSegmentedColormap.from_list("", colors)
        
        c = ax.contour(lon, lat, -data.transpose(), conts, cmap=cmap, transform=ccrs.PlateCarree(), zorder=0)
        
        contstrings = [str(cc) + " m" for cc in conts]
        for (i,cnum) in enumerate(conts):
            c.collections[i].set_label(str(cnum) + " m")
        l = plt.legend()
        l.set_zorder(90)
        
        
        for record in self.landshp.records():
            
            #checking if plot is within region- cbounds = (minx,miny,maxx,maxy) and extent = (minx,maxx,miny,maxy)
            cbounds = record.bounds
            if (((extent[0] >= cbounds[0] and extent[0] <= cbounds[2]) or (extent[1] >= cbounds[0] and extent[1] <= cbounds[2])) and ((extent[2] >= cbounds[1] and extent[2] <= cbounds[3]) or (extent[3] >= cbounds[1] and extent[3] <= cbounds[3]))) or (((cbounds[0] >= extent[0] and cbounds[0] <= extent[1]) or (cbounds[2] >= extent[0] and cbounds[2] <= extent[1])) and ((cbounds[1] >= extent[2] and cbounds[1] <= extent[3]) or (cbounds[3] >= extent[2] and cbounds[3] <= extent[3]))):
                ax.add_geometries([record.geometry], ccrs.PlateCarree(), facecolor='lightgray', edgecolor='black', zorder=10)
                
        curtabstr = "Tab " + str(self.whatTab())
        self.alltabdata[curtabstr]["MissionCanvas"].draw()
    
    except Exception:
        trace_error()
        self.posterror("Failed to update map axes")
    
    


#update background field
def updateMissionPlot(self):
    try:
        curtabstr = "Tab " + str(self.whatTab())
        
        try:
            extent = [int(np.floor(float(self.alltabdata[curtabstr]["tabwidgets"]["wbound"].text()))), int(np.ceil(float(self.alltabdata[curtabstr]["tabwidgets"]["ebound"].text()))), int(np.floor(float(self.alltabdata[curtabstr]["tabwidgets"]["sbound"].text()))), int(np.ceil(float(self.alltabdata[curtabstr]["tabwidgets"]["nbound"].text())))]
            self.plotMapAxes(self.alltabdata[curtabstr]["MissionFig"], self.alltabdata[curtabstr]["MissionAx"], extent)
            
            if self.goodPosition:
                self.updateMissionPosition()
            
        except (ValueError, TypeError):
            trace_error()
            self.posterror("Invalid value prescribed in position")
            
    except Exception:
        self.posterror("Failed to update plot")
        trace_error()
    
        
        
        
        
        
def updateMissionPosition(self):
    
    try:
        if self.goodPosition:
            curtabstr = "Tab " + str(self.whatTab())
            
            #pulling position
            clat = self.lat
            clon = self.lon
            cb = self.bearing*np.pi/180 #convert to trig-style
            
            #determining arrow size
            cxlim = self.alltabdata[curtabstr]["MissionAx"].get_xlim()
            cylim = self.alltabdata[curtabstr]["MissionAx"].get_ylim()
            C = 0.01*(cxlim[1] - cxlim[0] + cylim[1] - cylim[0])
                
            #overlaying plot (creating in polar then converting to cartesian and plotting)
            rad = np.array([C,C,C/3,C])
            phi = np.array([np.pi/2, -np.pi/4, -np.pi/2, -3*np.pi/4]) - cb
            x = clon + rad * np.cos(phi)
            y = clat + rad * np.sin(phi)
            
            #replotting
            if self.alltabdata[curtabstr]["gpshandle"]:
                self.alltabdata[curtabstr]["gpshandle"].set_visible(False)
                
            self.alltabdata[curtabstr]["gpshandle"] = self.alltabdata[curtabstr]["MissionAx"].fill(x,y,color="red", edgecolor="k", zorder=100)
            self.alltabdata[curtabstr]["gpshandle"] = self.alltabdata[curtabstr]["gpshandle"][0]
            
            if clat >= 0:
                ns = 'N'
            else:
                ns = 'S'
            if clon >= 0:
                ew = 'E'
            else:
                ew = 'W'
            
            self.alltabdata[curtabstr]["MissionAx"].set_title(f"Current Position: {abs(clat):6.3f}\xB0{ns}, {abs(clon):7.3f}\xB0{ew}",fontweight="bold")
            self.alltabdata[curtabstr]["MissionCanvas"].draw()
            
            
        else:
            self.postwarning("GPS stream is inactive")
        
    except Exception:
        trace_error()
        self.posterror("Failed to update current position")
    
        
#add line plot
def updateMissionPlot_line(self, pressed):
    try:
        curtabstr = "Tab " + str(self.whatTab())
        
        if pressed:
            self.alltabdata[curtabstr]["interactivetype"] = 1
            QApplication.setOverrideCursor(Qt.CrossCursor)
            self.alltabdata[curtabstr]["plotEvent"] = self.alltabdata[curtabstr]["MissionCanvas"].mpl_connect('button_release_event', self.getPoint)
            
        else:
            self.alltabdata[curtabstr]["lineactive"] = False
            self.alltabdata[curtabstr]["MissionCanvas"].mpl_disconnect(self.alltabdata[curtabstr]["plotEvent"])
            QApplication.restoreOverrideCursor()
            self.alltabdata[curtabstr]["interactivetype"] = 0

    except Exception:
        self.posterror("Failed to add point to line")
        trace_error()

        
def updateMissionPlot_circle(self):
    try:
        curtabstr = "Tab " + str(self.whatTab())
        
        if self.alltabdata[curtabstr]["interactivetype"] == 0:
            self.alltabdata[curtabstr]["interactivetype"] = 2
            QApplication.setOverrideCursor(Qt.CrossCursor)
            self.alltabdata[curtabstr]["plotEvent"] = self.alltabdata[curtabstr]["MissionCanvas"].mpl_connect('button_release_event', self.getPoint)
        
    except Exception:
        self.posterror("Failed to add circle")
        trace_error()    
        
        
        
def updateMissionPlot_box(self):
    try:
        curtabstr = "Tab " + str(self.whatTab())
        if self.alltabdata[curtabstr]["interactivetype"] == 0:
            self.alltabdata[curtabstr]["interactivetype"] = 3
            QApplication.setOverrideCursor(Qt.CrossCursor)
            self.alltabdata[curtabstr]["plotEvent"] = self.alltabdata[curtabstr]["MissionCanvas"].mpl_connect('button_release_event', self.getPoint)

    except Exception:
        self.posterror("Failed to add box")
        trace_error()
        
        
        
#get clicked point
def getPoint(self, event):
    try:
        curtabstr = "Tab " + str(self.whatTab())
        
        
        if self.alltabdata[curtabstr]["interactivetype"] == 0:
            self.alltabdata[curtabstr]["MissionCanvas"].mpl_disconnect(self.alltabdata[curtabstr]["plotEvent"])
            return
        
        xx = event.xdata #selected x and y points
        yy = event.ydata
        
        goodPoint = True
        if xx == None or yy == None:
            goodPoint = False
            
        try:
            linecolor = self.alltabdata[curtabstr]["colors"][self.alltabdata[curtabstr]["tabwidgets"]["colors"].currentIndex()]
            lwid = self.alltabdata[curtabstr]["tabwidgets"]["linewidth"].value()
            radius = int(self.alltabdata[curtabstr]["tabwidgets"]["radius"].text())
            radunitconv = self.alltabdata[curtabstr]["unitconversion"][self.alltabdata[curtabstr]["tabwidgets"]["radiusunits"].currentIndex()]
            
            #converting to km
            radius *= radunitconv
            
        except:
            trace_error()
            self.posterror("Invalid plot specification (e.g. radius, line width)")
        
        if self.alltabdata[curtabstr]["interactivetype"] == 1: #draw line
            if goodPoint:
                
                if self.alltabdata[curtabstr]["lineactive"]: #if line is already active, append point
                    self.alltabdata[curtabstr]["linex"].append(xx)
                    self.alltabdata[curtabstr]["liney"].append(yy)
                    
                    try: #attempt to delete last line handle from tab, axes
                        if len(self.alltabdata[curtabstr]["linex"]) == 2: #previous point was scatter
                            self.alltabdata[curtabstr]["overlayhandles"][-1].remove()
                        else: #previous point was line
                            self.alltabdata[curtabstr]["MissionAx"].lines[-1]
                            
                        del self.alltabdata[curtabstr]["overlayhandles"][-1]
                        
                    except IndexError:
                        pass #if no handles added yet
                    
                else: #if line isn't active, activate it and initialize first point
                    self.alltabdata[curtabstr]["lineactive"] = True
                    self.alltabdata[curtabstr]["linex"] = [xx]
                    self.alltabdata[curtabstr]["liney"] = [yy]
                    
                xvals = self.alltabdata[curtabstr]["linex"]
                yvals = self.alltabdata[curtabstr]["liney"]
            
            else:
                self.alltabdata[curtabstr]["lineactive"] = False
                self.alltabdata[curtabstr]["tabwidgets"]["addline"].setChecked(False)
                        
        elif goodPoint:
            mi2dlat = 111
            mi2dlon = 111.3*np.cos(yy*np.pi/180)
            
            if self.alltabdata[curtabstr]["interactivetype"] == 2: #draw circle
                phi = np.arange(0,2*np.pi+np.pi/32,np.pi/32)
                rad = np.ones(len(phi))
                xcirc = rad * np.cos(phi)
                ycirc = rad * np.sin(phi)
                xvals = xcirc*radius/mi2dlon + xx 
                yvals = ycirc*radius/mi2dlat + yy
                
            elif self.alltabdata[curtabstr]["interactivetype"] == 3: #draw box
                xvals = np.array([-1,-1,1,1,-1])*radius/mi2dlon + xx
                yvals = np.array([-1,1,1,-1,-1])*radius/mi2dlat + yy
                
        if goodPoint: #if a valid point was given
            if len(xvals) > 1:
                chandle = self.alltabdata[curtabstr]["MissionAx"].plot(xvals,yvals,color=linecolor,linewidth=lwid, zorder=95)
            elif len(xvals) == 1:
                chandle = self.alltabdata[curtabstr]["MissionAx"].scatter(xvals[0],yvals[0],color=linecolor, zorder=95)
                
            self.alltabdata[curtabstr]["overlayhandles"].append(chandle)
            self.alltabdata[curtabstr]["MissionCanvas"].draw()
        
        if self.alltabdata[curtabstr]["interactivetype"] != 1 or not goodPoint: #if line terminated or circle/box were drawn
            self.alltabdata[curtabstr]["MissionCanvas"].mpl_disconnect(self.alltabdata[curtabstr]["plotEvent"])
            QApplication.restoreOverrideCursor()
            self.alltabdata[curtabstr]["interactivetype"] = 0
                        
            
        
    except Exception:
        trace_error()
        self.posterror("Failed to draw overlay")
        