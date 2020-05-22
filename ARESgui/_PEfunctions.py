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
#   Profile Editor functions
#       o processprofile: handles initial transition from signal processor to profile editor tab
#       o makenewproftab: populates tab to read data from AXBT ASCII raw data file (e.g. LOG, EDF)
#       o selectdatafile: enables user to browse/select a source data file
#       o checkdatainputs_editorinput: checks validity of user inputs
#       o continuetoqc: populates profile editor tab from either new file or signal processor tab
#       o applychanges: updates profile preferences for surface correction, cutoff, and depth delay features
#       o updateprofeditplots: updates profile plot and metadata text after user-specifed changes are applied
#       o generateprofiledescription: generates text block with profile metadata displayed on GUI
#       o runqc: Reruns the autoQC algorithm with current advanced preferences
#       o addpoint: lets user add a point to the profile
#       o removepoint: lets user remove a point from the profile
#       o removerange: lets user select vertical range of points to remove
#       o on_press_spike: gets point where user clicks to remove a range of points (executed when user first 
#           clicks plot after selecting "remove range")
#       o on_release: finds and adds or removes user-selected point or range of points from profile (executed
#           after user releases mouse click when selecting points to add or remove)
#       o toggleclimooverlay: toggles visibility of climatology profile on plot
#       o parsestringinputs (at end of file): checks validity of user inputs
#       o CustomToolbar (class, located outside of function): configures icons, functions, tooltips, etc. available 
#           in matplotlib toolbar embedded in profile editor tab that enables users to change profile views 
#           (pan, zoom, etc.)

from os import path
from traceback import print_exc as trace_error

from PyQt5.QtWidgets import (QApplication, QLineEdit, QLabel, QSpinBox, QCheckBox, QPushButton, QWidget, 
    QFileDialog, QComboBox, QTextEdit, QGridLayout)
from PyQt5.QtCore import QObjectCleanupHandler, Qt


from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
import matplotlib.pyplot as plt

import time as timemodule
import numpy as np

#autoQC-specific modules
import qclib.tropicfileinteraction as tfio
import qclib.makeAXBTplots as tplot
import qclib.autoqc as qc
import qclib.ocean_climatology_interaction as oci

from ._globalfunctions import (addnewtab, whatTab, renametab, setnewtabcolor, closecurrenttab, savedataincurtab, postwarning, posterror, postwarning_option, closeEvent, parsestringinputs)


      
# =============================================================================
#    TAB TO LOAD EXISTING DATA FILE INTO EDITOR
# =============================================================================
def makenewproftab(self):
    try:
        #tab indexing update
        newtabnum,curtabstr = self.addnewtab()

        self.alltabdata[curtabstr] = {"tab":QWidget(),"tablayout":QGridLayout(),"tabtype":"ProfileEditorInput", "isprocessing":False, "datasource":"None"} #isprocessing and datasource are only relevant for processor tabs
        self.alltabdata[curtabstr]["tablayout"].setSpacing(10)
        
        self.setnewtabcolor(self.alltabdata[curtabstr]["tab"])

        self.tabWidget.addTab(self.alltabdata[curtabstr]["tab"],'New Tab') #self.tabWidget.addTab(self.currenttab,'New Tab')
        self.tabWidget.setCurrentIndex(newtabnum)
        self.tabWidget.setTabText(newtabnum,"Tab #" + str(newtabnum+1))
        self.alltabdata[curtabstr]["tabnum"] = self.totaltabs #assigning unique, unchanging number to current tab
        
        #Create widgets for UI
        self.alltabdata[curtabstr]["tabwidgets"] = {}
        self.alltabdata[curtabstr]["tabwidgets"]["title"] = QLabel('Enter AXBT Drop Information:')
        self.alltabdata[curtabstr]["tabwidgets"]["lattitle"] = QLabel('Latitude (N>0): ')
        self.alltabdata[curtabstr]["tabwidgets"]["latedit"] = QLineEdit('XX.XXX')
        self.alltabdata[curtabstr]["tabwidgets"]["lontitle"] = QLabel('Longitude (E>0): ')
        self.alltabdata[curtabstr]["tabwidgets"]["lonedit"] = QLineEdit('XX.XXX')
        self.alltabdata[curtabstr]["tabwidgets"]["datetitle"] = QLabel('Date: ')
        self.alltabdata[curtabstr]["tabwidgets"]["dateedit"] = QLineEdit('YYYYMMDD')
        self.alltabdata[curtabstr]["tabwidgets"]["timetitle"] = QLabel('Time (UTC): ')
        self.alltabdata[curtabstr]["tabwidgets"]["timeedit"] = QLineEdit('HHMM')
        self.alltabdata[curtabstr]["tabwidgets"]["idtitle"] = QLabel('Platform ID/Tail#: ')
        self.alltabdata[curtabstr]["tabwidgets"]["idedit"] = QLineEdit('AFNNN')
        self.alltabdata[curtabstr]["tabwidgets"]["logtitle"] = QLabel('Select Source File: ')
        self.alltabdata[curtabstr]["tabwidgets"]["logbutton"] = QPushButton('Browse')
        self.alltabdata[curtabstr]["tabwidgets"]["logedit"] = QTextEdit('filepath/LOGXXXXX.DTA')
        self.alltabdata[curtabstr]["tabwidgets"]["logedit"].setMaximumHeight(100)
        self.alltabdata[curtabstr]["tabwidgets"]["logbutton"].clicked.connect(self.selectdatafile)
        self.alltabdata[curtabstr]["tabwidgets"]["submitbutton"] = QPushButton('PROCESS PROFILE')
        self.alltabdata[curtabstr]["tabwidgets"]["submitbutton"].clicked.connect(self.checkdatainputs_editorinput)
        
        #formatting widgets
        self.alltabdata[curtabstr]["tabwidgets"]["title"].setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.alltabdata[curtabstr]["tabwidgets"]["lattitle"].setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.alltabdata[curtabstr]["tabwidgets"]["lontitle"].setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.alltabdata[curtabstr]["tabwidgets"]["datetitle"].setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.alltabdata[curtabstr]["tabwidgets"]["timetitle"].setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.alltabdata[curtabstr]["tabwidgets"]["idtitle"].setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.alltabdata[curtabstr]["tabwidgets"]["logtitle"].setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        
        #should be 15 entries
        widgetorder = ["title","lattitle","latedit","lontitle","lonedit","datetitle","dateedit","timetitle",
                       "timeedit","idtitle","idedit","logtitle","logedit","logbutton","submitbutton"]
        wrows     = [1,2,2,3,3,4,4,5,5,6,6,7,7,8,9]
        wcols     = [1,1,2,1,2,1,2,1,2,1,2,1,2,1,1]
        wrext     = [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1]
        wcolext   = [2,1,1,1,1,1,1,1,1,1,1,1,1,2,2]    
        
        
        #adding user inputs
        for i,r,c,re,ce in zip(widgetorder,wrows,wcols,wrext,wcolext):
            self.alltabdata[curtabstr]["tabwidgets"][i].setFont(self.labelfont)
            self.alltabdata[curtabstr]["tablayout"].addWidget(self.alltabdata[curtabstr]["tabwidgets"][i],r,c,re,ce)
        
        #forces grid info to top/center of window
        self.alltabdata[curtabstr]["tablayout"].setRowStretch(10,1)
        self.alltabdata[curtabstr]["tablayout"].setColumnStretch(0,1)
        self.alltabdata[curtabstr]["tablayout"].setColumnStretch(3,1)

        #applying layout
        self.alltabdata[curtabstr]["tab"].setLayout(self.alltabdata[curtabstr]["tablayout"]) 

    except Exception:
        trace_error()
        self.posterror("Failed to build editor input tab!")

        
        
#browse for raw data file to QC
def selectdatafile(self):
    try:
        fname,ok = QFileDialog.getOpenFileName(self, 'Open file',self.defaultfilereaddir,
        "Source Data Files (*.DTA *.Dta *.dta *.EDF *.Edf *.edf *.edf *.NVO *.Nvo *.nvo *.FIN *.Fin *.fin *.JJVV *.Jjvv *.jjvv *.TXT *.Txt *.txt)","",self.fileoptions)
         
        if ok:
            curtabstr = "Tab " + str(self.whatTab())
            self.alltabdata[curtabstr]["tabwidgets"]["logedit"].setText(fname)
            
            #getting file directory
            if fname != "":
                splitpath = path.split(fname)
                self.defaultfilereaddir = splitpath[0]
                
    except Exception:
        trace_error()
        self.posterror("Failed to select file- please try again or manually enter full path to file in box below.")

        
        
#Pull data, check to make sure it is valid before proceeding
def checkdatainputs_editorinput(self):
    try:
        curtabstr = "Tab " + str(self.whatTab())
        
        #pulling data from inputs
        latstr = self.alltabdata[curtabstr]["tabwidgets"]["latedit"].text()
        lonstr = self.alltabdata[curtabstr]["tabwidgets"]["lonedit"].text()
        identifier = self.alltabdata[curtabstr]["tabwidgets"]["idedit"].text()
        profdatestr = self.alltabdata[curtabstr]["tabwidgets"]["dateedit"].text()
        timestr = self.alltabdata[curtabstr]["tabwidgets"]["timeedit"].text()
        logfile = self.alltabdata[curtabstr]["tabwidgets"]["logedit"].toPlainText()
        
        #check that logfile exists
        if not path.isfile(logfile):
            self.postwarning('Selected Data File Does Not Exist!')
            return

        if logfile[-4:].lower() == '.dta': #checks inputs if log file, otherwise doesnt need them
            
            #check and correct inputs
            try:
                lat,lon,year,month,day,time,_,_,identifier = self.parsestringinputs(latstr,lonstr,profdatestr,timestr,identifier,True,True,True)
            except:
                return
            
        else:
            lon = np.NaN
            lat = np.NaN
            month = np.NaN
            day = np.NaN
            time= np.NaN
            try: #year is important if jjvv file
                year = int(profdatestr[:4])
            except:
                year = np.NaN
                
        try:
            #identifying and reading file data
            if logfile[-4:].lower() == '.dta':
                rawtemperature,rawdepth = tfio.readlogfile(logfile)
            elif logfile[-4:].lower() == '.edf':
                rawtemperature,rawdepth,year,month,day,hour,minute,second,lat,lon = tfio.readedffile(logfile)
                time = hour*100 + second
            elif logfile[-4:].lower() in ['.fin','.nvo','.txt']: #assumes .txt are fin/nvo format
                rawtemperature,rawdepth,day,month,year,time,lat,lon,_ = tfio.readfinfile(logfile)
            elif logfile[-5:].lower() == '.jjvv':
                rawtemperature,rawdepth,day,month,year,time,lat,lon,identifier = tfio.readjjvvfile(logfile,round(year,-1))
            else:
                QApplication.restoreOverrideCursor()
                self.postwarning('Invalid Data File Format (must be .dta,.edf,.nvo,.fin, or .jjvv)!')
                return
                                    
            #removing NaNs
            notnanind = ~np.isnan(rawtemperature*rawdepth)
            rawtemperature = rawtemperature[notnanind]
            rawdepth = rawdepth[notnanind]
            
            if len(rawdepth) == 0:
                self.postwarning('This file does not contain any valid profile data. Please select a different file!')
                return
            
        except Exception:
            trace_error()
            QApplication.restoreOverrideCursor()
            self.posterror('Failed to read selected data file!')
            return
    except Exception:
        trace_error()
        self.posterror("Failed to read profile input data")
        QApplication.restoreOverrideCursor()
        return
    #only gets here if all inputs are good- this function switches the tab to profile editor view
    self.continuetoqc(curtabstr,rawtemperature,rawdepth,lat,lon,day,month,year,time,logfile,identifier)
    
    
    
    
    
# =============================================================================
#         PROFILE EDITOR TAB
# =============================================================================
def continuetoqc(self,curtabstr,rawtemperature,rawdepth,lat,lon,day,month,year,time,logfile,identifier):
    try:
        QApplication.setOverrideCursor(Qt.WaitCursor)
        
        dtg = str(year) + str(month).zfill(2) + str(day).zfill(2) + str(time).zfill(4)
        
        #concatenates profile if depths stop increasing
        negind = np.argwhere(np.diff(rawdepth) < 0)
        if len(negind) > 0: #if depths do decrease at some point, truncate the profile there
            cutoff = negind[0][0] + 1
            rawtemperature = rawtemperature[:cutoff]
            rawdepth = rawdepth[:cutoff]

        # pull ocean depth from ETOPO1 Grid-Registered Ice Sheet based global relief dataset
        # Data source: NOAA-NGDC: https://www.ngdc.noaa.gov/mgg/global/global.html
        try:
            oceandepth, exportlat, exportlon, exportrelief = oci.getoceandepth(lat, lon, 6, self.bathymetrydata)
        except:
            oceandepth = np.NaN
            exportlat = exportlon = np.array([0,1])
            exportrelief = np.NaN*np.ones((2,2))
            self.posterror("Unable to find/load bathymetry data for profile location!")
        
        #getting climatology
        try:
            climotemps,climodepths,climotempfill,climodepthfill = oci.getclimatologyprofile(lat,lon,month,self.climodata)
        except:
            climotemps = climodepths = np.array([np.NaN,np.NaN])
            climotempfill = climodepthfill = np.array([np.NaN,np.NaN,np.NaN,np.NaN])
            self.posterror("Unable to find/load climatology data for profile location!")
            
            
        self.alltabdata[curtabstr]["profdata"] = {"temp_raw": rawtemperature, "depth_raw": rawdepth,
                                             "lat": lat, "lon": lon, "year": year, "month": month, "day": day,
                                             "time": time, "DTG": dtg,
                                             "climotemp": climotemps, "climodepth": climodepths,
                                             "climotempfill": climotempfill,
                                             "climodepthfill": climodepthfill,
                                             "datasourcefile": logfile,
                                             "ID": identifier, "oceandepth": oceandepth}
        
        #deleting old buttons and inputs
        for i in self.alltabdata[curtabstr]["tabwidgets"]:
            try:
                self.alltabdata[curtabstr]["tabwidgets"][i].deleteLater()
            except:
                self.alltabdata[curtabstr]["tabwidgets"][i] = 1 #bs variable- overwrites spacer item
                            
        if self.settingsdict["renametabstodtg"]:
            curtab = self.tabWidget.currentIndex()
            self.tabWidget.setTabText(curtab,dtg)  
            
        #now delete widget entries
        del self.alltabdata[curtabstr]["tabwidgets"]
        QObjectCleanupHandler().add(self.alltabdata[curtabstr]["tablayout"])
        
        self.alltabdata[curtabstr]["tablayout"] = QGridLayout()
        self.alltabdata[curtabstr]["tab"].setLayout(self.alltabdata[curtabstr]["tablayout"]) 
        self.alltabdata[curtabstr]["tablayout"].setSpacing(10)
        
        #ADDING FIGURES AND AXES TO GRID LAYOUT (row column rowext colext)
        self.alltabdata[curtabstr]["ProfFig"] = plt.figure()
        self.alltabdata[curtabstr]["ProfCanvas"] = FigureCanvas(self.alltabdata[curtabstr]["ProfFig"]) 
        self.alltabdata[curtabstr]["tablayout"].addWidget(self.alltabdata[curtabstr]["ProfCanvas"],0,0,14,1)
        self.alltabdata[curtabstr]["ProfCanvas"].setStyleSheet("background-color:transparent;")
        self.alltabdata[curtabstr]["ProfFig"].patch.set_facecolor('None')
        self.alltabdata[curtabstr]["ProfAx"] = plt.axes()
        self.alltabdata[curtabstr]["LocFig"] = plt.figure()
        self.alltabdata[curtabstr]["LocCanvas"] = FigureCanvas(self.alltabdata[curtabstr]["LocFig"]) 
        self.alltabdata[curtabstr]["tablayout"].addWidget(self.alltabdata[curtabstr]["LocCanvas"],11,2,1,5)
        self.alltabdata[curtabstr]["LocCanvas"].setStyleSheet("background-color:transparent;")
        self.alltabdata[curtabstr]["LocFig"].patch.set_facecolor('None')
        self.alltabdata[curtabstr]["LocAx"] = plt.axes()

        #adding toolbar
        self.alltabdata[curtabstr]["ProfToolbar"] = CustomToolbar(self.alltabdata[curtabstr]["ProfCanvas"], self) #changed from NavigationToolbar to customize w/ class @ end of file
        self.alltabdata[curtabstr]["tablayout"].addWidget(self.alltabdata[curtabstr]["ProfToolbar"],2,2,1,2)

        #Create widgets for UI populated with test example
        self.alltabdata[curtabstr]["tabwidgets"] = {}
        
        #first column: profile editor functions:
        self.alltabdata[curtabstr]["tabwidgets"]["toggleclimooverlay"] = QPushButton('Overlay Climatology') #1
        self.alltabdata[curtabstr]["tabwidgets"]["toggleclimooverlay"].setCheckable(True)
        self.alltabdata[curtabstr]["tabwidgets"]["toggleclimooverlay"].setChecked(True)
        self.alltabdata[curtabstr]["tabwidgets"]["toggleclimooverlay"].clicked.connect(self.toggleclimooverlay) 
        
        self.alltabdata[curtabstr]["tabwidgets"]["addpoint"] = QPushButton('Add Point') #2
        self.alltabdata[curtabstr]["tabwidgets"]["addpoint"].clicked.connect(self.addpoint)
        self.alltabdata[curtabstr]["tabwidgets"]["addpoint"].setToolTip("After clicking, select a single point to add")
        
        self.alltabdata[curtabstr]["tabwidgets"]["removepoint"] = QPushButton('Remove Point') #3
        self.alltabdata[curtabstr]["tabwidgets"]["removepoint"].clicked.connect(self.removepoint)
        self.alltabdata[curtabstr]["tabwidgets"]["removepoint"].setToolTip("After clicking, select a single point to remove")

        self.alltabdata[curtabstr]["tabwidgets"]["removerange"] = QPushButton('Remove Range') #4
        self.alltabdata[curtabstr]["tabwidgets"]["removerange"].clicked.connect(self.removerange)
        self.alltabdata[curtabstr]["tabwidgets"]["removerange"].setToolTip("After clicking, click and drag over a (vertical) range of points to remove")
        
        self.alltabdata[curtabstr]["tabwidgets"]["sfccorrectiontitle"] = QLabel('Isothermal Layer (m):') #5
        self.alltabdata[curtabstr]["tabwidgets"]["sfccorrection"] = QSpinBox() #6
        self.alltabdata[curtabstr]["tabwidgets"]["sfccorrection"].setRange(0, int(np.max(rawdepth+200)))
        self.alltabdata[curtabstr]["tabwidgets"]["sfccorrection"].setSingleStep(1)
        self.alltabdata[curtabstr]["tabwidgets"]["sfccorrection"].setValue(0)
        
        self.alltabdata[curtabstr]["tabwidgets"]["maxdepthtitle"] = QLabel('Maximum Depth (m):') #7
        self.alltabdata[curtabstr]["tabwidgets"]["maxdepth"] = QSpinBox() #8
        self.alltabdata[curtabstr]["tabwidgets"]["maxdepth"].setRange(0, int(np.round(np.max(rawdepth+200),-2)))
        self.alltabdata[curtabstr]["tabwidgets"]["maxdepth"].setSingleStep(1)
        # self.alltabdata[curtabstr]["tabwidgets"]["maxdepth"].setValue(int(np.round(maxdepth)))
        self.alltabdata[curtabstr]["tabwidgets"]["maxdepth"].setValue(int(np.round(1000)))
        
        self.alltabdata[curtabstr]["tabwidgets"]["depthdelaytitle"] = QLabel('Depth Delay (m):') #9
        self.alltabdata[curtabstr]["tabwidgets"]["depthdelay"] = QSpinBox() #10
        self.alltabdata[curtabstr]["tabwidgets"]["depthdelay"].setRange(0, int(np.round(np.max(rawdepth+200),-2)))
        self.alltabdata[curtabstr]["tabwidgets"]["depthdelay"].setSingleStep(1)
        self.alltabdata[curtabstr]["tabwidgets"]["depthdelay"].setValue(0)

        self.alltabdata[curtabstr]["tabwidgets"]["runqc"] = QPushButton('Re-QC Profile (Reset)') #11
        self.alltabdata[curtabstr]["tabwidgets"]["runqc"].clicked.connect(self.runqc)    
        
        
        #Second column: profile information
        self.alltabdata[curtabstr]["tabwidgets"]["proftxt"] = QLabel(' ')#12
        self.alltabdata[curtabstr]["tabwidgets"]["isbottomstrike"] = QCheckBox('Bottom Strike?') #13
        self.alltabdata[curtabstr]["tabwidgets"]["rcodetitle"] = QLabel('Profile Quality:') #14
        self.alltabdata[curtabstr]["tabwidgets"]["rcode"] = QComboBox() #15
        self.alltabdata[curtabstr]["tabwidgets"]["rcode"].addItem("Good Profile")
        self.alltabdata[curtabstr]["tabwidgets"]["rcode"].addItem("No Signal")
        self.alltabdata[curtabstr]["tabwidgets"]["rcode"].addItem("Spotty/Intermittent")
        self.alltabdata[curtabstr]["tabwidgets"]["rcode"].addItem("Hung Probe/Early Start")
        self.alltabdata[curtabstr]["tabwidgets"]["rcode"].addItem("Isothermal")
        self.alltabdata[curtabstr]["tabwidgets"]["rcode"].addItem("Late Start")
        self.alltabdata[curtabstr]["tabwidgets"]["rcode"].addItem("Slow Falling")
        self.alltabdata[curtabstr]["tabwidgets"]["rcode"].addItem("Bottom Strike")
        self.alltabdata[curtabstr]["tabwidgets"]["rcode"].addItem("Climatology Mismatch")
        self.alltabdata[curtabstr]["tabwidgets"]["rcode"].addItem("Action Required/Reprocess")
            
        #formatting widgets
        self.alltabdata[curtabstr]["tabwidgets"]["proftxt"].setAlignment(Qt.AlignCenter | Qt.AlignVCenter)
        self.alltabdata[curtabstr]["tabwidgets"]["rcodetitle"].setAlignment(Qt.AlignCenter | Qt.AlignVCenter)
        self.alltabdata[curtabstr]["tabwidgets"]["depthdelaytitle"].setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.alltabdata[curtabstr]["tabwidgets"]["sfccorrectiontitle"].setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.alltabdata[curtabstr]["tabwidgets"]["maxdepthtitle"].setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        
        
        #should be 15 entries
        widgetorder = ["toggleclimooverlay", "addpoint", "removepoint", "removerange", "sfccorrectiontitle", "sfccorrection", "maxdepthtitle", "maxdepth", "depthdelaytitle", "depthdelay", "runqc", "proftxt", "isbottomstrike", "rcodetitle", "rcode"]
        
        wrows     = [3,4,4,5,6,6,7,7,8,8,9,5,3,3,4]
        wcols     = [2,2,3,2,2,3,2,3,2,3,2,5,6,5,5]
        wrext     = [1,1,1,1,1,1,1,1,1,1,1,4,1,1,1]
        wcolext   = [2,1,1,2,1,1,1,1,1,1,2,2,1,1,2]
        
        #adding user inputs
        for i,r,c,re,ce in zip(widgetorder,wrows,wcols,wrext,wcolext):
            self.alltabdata[curtabstr]["tabwidgets"][i].setFont(self.labelfont)
            self.alltabdata[curtabstr]["tablayout"].addWidget(self.alltabdata[curtabstr]["tabwidgets"][i],r,c,re,ce)
            

        #adjusting stretch factors for all rows/columns
        colstretch = [13,1,1,1,1,1,1,1,1]
        for col,cstr in zip(range(0,len(colstretch)),colstretch):
            self.alltabdata[curtabstr]["tablayout"].setColumnStretch(col,cstr)
        rowstretch = [0,1,1,1,1,1,1,1,0,1,1,5]
        for row,rstr in zip(range(0,len(rowstretch)),rowstretch):
            self.alltabdata[curtabstr]["tablayout"].setRowStretch(row,rstr)

        #run autoQC code, pull variables from self.alltabdata dict
        self.alltabdata[curtabstr]["hasbeenprocessed"] = False
        
        if self.runqc(): #only executes following code if autoQC runs sucessfully
            depth = self.alltabdata[curtabstr]["profdata"]["depth_plot"]
            temperature = self.alltabdata[curtabstr]["profdata"]["temp_plot"]
            matchclimo = self.alltabdata[curtabstr]["profdata"]["matchclimo"]

            # plot data, refresh plots on window
            self.alltabdata[curtabstr]["climohandle"] = tplot.makeprofileplot(self.alltabdata[curtabstr]["ProfAx"],
                                                                         rawtemperature,
                                                                         rawdepth, temperature, depth,
                                                                         climotempfill,
                                                                         climodepthfill, dtg, matchclimo)
            tplot.makelocationplot(self.alltabdata[curtabstr]["LocFig"],self.alltabdata[curtabstr]["LocAx"],lat,lon,dtg,exportlon,exportlat,exportrelief,6)
            self.alltabdata[curtabstr]["ProfCanvas"].draw() #update figure canvases
            self.alltabdata[curtabstr]["LocCanvas"].draw()
            self.alltabdata[curtabstr]["pt_type"] = 0  # sets that none of the point selector buttons have been pushed
            self.alltabdata[curtabstr]["hasbeenprocessed"] = True #note that the autoQC driver has run at least once

            #configure spinboxes to run "applychanges" function after being changed
            self.alltabdata[curtabstr]["tabwidgets"]["sfccorrection"].valueChanged.connect(self.applychanges)
            self.alltabdata[curtabstr]["tabwidgets"]["maxdepth"].valueChanged.connect(self.applychanges)
            self.alltabdata[curtabstr]["tabwidgets"]["depthdelay"].valueChanged.connect(self.applychanges)

            self.alltabdata[curtabstr]["tabtype"] = "ProfileEditor"
    except Exception:
        trace_error()
        self.posterror("Failed to build profile editor tab!")
    finally:
        QApplication.restoreOverrideCursor()
        
        
        
        

# =============================================================================
#         AUTOQC DRIVER CODE
# =============================================================================

def runqc(self):
    try:
        curtabstr = "Tab " + str(self.whatTab())

        # getting necessary data for QC from dictionary
        rawtemperature = self.alltabdata[curtabstr]["profdata"]["temp_raw"]
        rawdepth = self.alltabdata[curtabstr]["profdata"]["depth_raw"]
        climotemps = self.alltabdata[curtabstr]["profdata"]["climotemp"]
        climodepths = self.alltabdata[curtabstr]["profdata"]["climodepth"]
        climotempfill = self.alltabdata[curtabstr]["profdata"]["climotempfill"]
        climodepthfill = self.alltabdata[curtabstr]["profdata"]["climodepthfill"]
        oceandepth = self.alltabdata[curtabstr]["profdata"]["oceandepth"]
        

        # TODO: Integrate this into the settings window
        self.settingsdict["maxstdev"] = 1

        try:
            # running QC, comparing to climo
            temperature, depth = qc.autoqc(rawtemperature, rawdepth, self.settingsdict["smoothlev"],self.settingsdict["profres"], self.settingsdict["maxstdev"], self.settingsdict["checkforgaps"])
            if self.settingsdict["comparetoclimo"]:
                matchclimo, climobottomcutoff = oci.comparetoclimo(temperature, depth, climotemps, climodepths,climotempfill,climodepthfill)
            else:
                matchclimo = True
                climobottomcutoff = np.NaN
                
        except Exception:
            temperature = np.array([np.NaN])
            depth = np.array([0])
            matchclimo = climobottomcutoff = 0
            trace_error()
            self.posterror("Error raised in automatic profile QC")
        
            
        #saving QC profile first (before truncating depth due to ID'd bottom strikes)
        self.alltabdata[curtabstr]["profdata"]["depth_qc"] = depth.copy() #using copy method so further edits made won't be reflected in these stored versions of the QC'ed profile
        self.alltabdata[curtabstr]["profdata"]["temp_qc"] = temperature.copy()
        

        # limit profile depth by climatology cutoff, ocean depth cutoff
        maxdepth = np.ceil(np.max(depth))
        isbottomstrike = 0
        if self.settingsdict["useoceanbottom"] and np.isnan(oceandepth) == 0 and oceandepth <= maxdepth:
            maxdepth = oceandepth
            isbottomstrike = 1
        if self.settingsdict["useclimobottom"] and np.isnan(climobottomcutoff) == 0 and climobottomcutoff <= maxdepth:
            isbottomstrike = 1
            maxdepth = climobottomcutoff
        isbelowmaxdepth = np.less_equal(depth, maxdepth)
        temperature = temperature[isbelowmaxdepth]
        depth = depth[isbelowmaxdepth]

        # writing values to alltabs structure: prof temps, and matchclimo
        self.alltabdata[curtabstr]["profdata"]["depth_plot"] = depth
        self.alltabdata[curtabstr]["profdata"]["temp_plot"] = temperature
        self.alltabdata[curtabstr]["profdata"]["matchclimo"] = matchclimo

        # resetting depth correction QSpinBoxes
        self.alltabdata[curtabstr]["tabwidgets"]["maxdepth"].setValue(int(np.round(maxdepth)))
        self.alltabdata[curtabstr]["tabwidgets"]["depthdelay"].setValue(0)
        self.alltabdata[curtabstr]["tabwidgets"]["sfccorrection"].setValue(0)

        # adjusting bottom strike checkbox as necessary
        if isbottomstrike == 1:
            self.alltabdata[curtabstr]["tabwidgets"]["isbottomstrike"].setChecked(True)
        else:
            self.alltabdata[curtabstr]["tabwidgets"]["isbottomstrike"].setChecked(False)

        self.updateprofeditplots() #update profile plot, data on window
        
        return True #return true if autoQC runs successfully

    except Exception:
        trace_error()
        self.posterror("Failed to run autoQC")
        
        return False #return false if autoQC fails



    
# =============================================================================
#         PROFILE EDITING FUNCTION CALLS
# =============================================================================
#apply changes from sfc correction/max depth/depth delay spin boxes
def applychanges(self):
    try:
        curtabstr = "Tab " + str(self.whatTab())
        #current t/d profile
        tempplot = self.alltabdata[curtabstr]["profdata"]["temp_qc"].copy()
        depthplot = self.alltabdata[curtabstr]["profdata"]["depth_qc"].copy()
        
        if len(tempplot) > 0 and len(depthplot) > 0:

            #new depth correction settings
            sfcdepth = self.alltabdata[curtabstr]["tabwidgets"]["sfccorrection"].value()
            maxdepth = self.alltabdata[curtabstr]["tabwidgets"]["maxdepth"].value()
            depthdelay = self.alltabdata[curtabstr]["tabwidgets"]["depthdelay"].value()

            if depthdelay > 0: #shifitng entire profile up if necessary
                depthplot = depthplot - depthdelay
                ind = depthplot >= 0
                depthplot = depthplot[ind]
                tempplot = tempplot[ind]

            if sfcdepth > 0: #replacing surface temperatures
                sfctemp = np.interp(sfcdepth,depthplot,tempplot)
                ind = depthplot <= sfcdepth
                tempplot[ind] = sfctemp

            if maxdepth < np.max(depthplot): #truncating base of profile
                ind = depthplot <= maxdepth
                tempplot = tempplot[ind]
                depthplot = depthplot[ind]

            #replacing t/d profile values
            self.alltabdata[curtabstr]["profdata"]["temp_plot"] = tempplot
            self.alltabdata[curtabstr]["profdata"]["depth_plot"] = depthplot

            #re-plotting, updating text
            self.updateprofeditplots()
            
    except Exception:
        trace_error()
        self.posterror("Failed to update profile!")
        

        
def updateprofeditplots(self):
    curtabstr = "Tab " + str(self.whatTab())

    try:
        tempplot = self.alltabdata[curtabstr]["profdata"]["temp_plot"]
        depthplot = self.alltabdata[curtabstr]["profdata"]["depth_plot"]
        
        # Replace drop info
        proftxt = self.generateprofiledescription(curtabstr,len(tempplot))
        self.alltabdata[curtabstr]["tabwidgets"]["proftxt"].setText(proftxt)

        # re-plotting (if not first pass through editor)
        if self.alltabdata[curtabstr]["hasbeenprocessed"]:
            del self.alltabdata[curtabstr]["ProfAx"].lines[-1]
            self.alltabdata[curtabstr]["ProfAx"].plot(tempplot, depthplot, 'r', linewidth=2, label='QC')
            self.alltabdata[curtabstr]["ProfCanvas"].draw()

    except Exception:
        trace_error()
        self.posterror("Failed to update profile editor plots!")

        
        
def generateprofiledescription(self,curtabstr,numpoints):
    try:
        sfcdepth = self.alltabdata[curtabstr]["tabwidgets"]["sfccorrection"].value()
        maxdepth = self.alltabdata[curtabstr]["tabwidgets"]["maxdepth"].value()
        depthdelay = self.alltabdata[curtabstr]["tabwidgets"]["depthdelay"].value()
        
        lon = self.alltabdata[curtabstr]["profdata"]["lon"]
        lat = self.alltabdata[curtabstr]["profdata"]["lat"]
        oceandepth = self.alltabdata[curtabstr]["profdata"]["oceandepth"]
        
        if lon >= 0: #prepping coordinate string
            ewhem = ' \xB0E'
        else:
            ewhem = ' \xB0W'
        if lat >= 0:
            nshem = ' \xB0N'
        else:
            nshem = ' \xB0S'
        
        #generating text string
        proftxt = ("Profile Data: \n" #header
           + f"{abs(round(lon, 3))}{ewhem}, {abs(round(lat, 3))}{nshem} \n" #lat/lon
           + f"Ocean Depth: {np.round(oceandepth,1)} m\n" #ocean depth
           + f"QC Profile Depth: {np.round(maxdepth,1)} m\n" #profile depth
           + f"QC SFC Correction: {sfcdepth} m\n" #user-specified surface correction
           + f"QC Depth Delay: {depthdelay} m\n" #user-added depth delay
           + f"# Datapoints: {numpoints}")
        
        return proftxt
    
    except Exception:
        trace_error()
        self.posterror("Failed to update profile!")
        return "Unable to\ngenerate text!"


        
#add point on profile
def addpoint(self):
    curtabstr = "Tab " + str(self.whatTab())
    if self.alltabdata[curtabstr]["pt_type"] == 0:
        try:
            QApplication.setOverrideCursor(Qt.CrossCursor)
            curtabstr = "Tab " + str(self.whatTab())
            self.alltabdata[curtabstr]["pt_type"] = 1
            self.alltabdata[curtabstr]["pt"] = self.alltabdata[curtabstr]["ProfCanvas"].mpl_connect('button_release_event', self.on_release)
        except Exception:
            trace_error()
            self.posterror("Failed to add point")
            
            
        
#remove point on profile
def removepoint(self):
    curtabstr = "Tab " + str(self.whatTab())
    if self.alltabdata[curtabstr]["pt_type"] == 0:
        try:
            QApplication.setOverrideCursor(Qt.CrossCursor)
            curtabstr = "Tab " + str(self.whatTab())
            self.alltabdata[curtabstr]["pt_type"] = 2
            self.alltabdata[curtabstr]["pt"] = self.alltabdata[curtabstr]["ProfCanvas"].mpl_connect('button_release_event', self.on_release)
        except Exception:
            trace_error()
            self.posterror("Failed to remove point")
            
            

#remove range of points (e.g. profile spike)
def removerange(self):
    curtabstr = "Tab " + str(self.whatTab())
    if self.alltabdata[curtabstr]["pt_type"] == 0:
        try:
            QApplication.setOverrideCursor(Qt.CrossCursor)
            curtabstr = "Tab " + str(self.whatTab())
            self.alltabdata[curtabstr]["pt_type"] = 3
            self.alltabdata[curtabstr]["ptspike"] = self.alltabdata[curtabstr]["ProfCanvas"].mpl_connect('button_press_event', self.on_press_spike)
            self.alltabdata[curtabstr]["pt"] = self.alltabdata[curtabstr]["ProfCanvas"].mpl_connect('button_release_event', self.on_release)
        except Exception:
            trace_error()
            self.posterror("Failed to remove range")
            
            

def on_press_spike(self,event):
    self.y1_spike = event.ydata #gets first depth argument
    
    
        
#update profile with selected point to add or remove
def on_release(self,event):

    curtabstr = "Tab " + str(self.whatTab())
    try:
        xx = event.xdata #selected x and y points
        yy = event.ydata
        
        #retrieve and update values
        tempplot = self.alltabdata[curtabstr]["profdata"]["temp_qc"]
        depthplot = self.alltabdata[curtabstr]["profdata"]["depth_qc"]
        
        #ADD A POINT
        if self.alltabdata[curtabstr]["pt_type"] == 1:
            rawt = self.alltabdata[curtabstr]["profdata"]["temp_raw"]
            rawd = self.alltabdata[curtabstr]["profdata"]["depth_raw"]
            pt = np.argmin(abs(rawt-xx)**2 + abs(rawd-yy)**2)
            addtemp = rawt[pt]
            adddepth = rawd[pt]
            if not adddepth in depthplot:
                try: #if np array
                    ind = np.where(adddepth > depthplot)
                    ind = ind[0][-1]+1 #index to add
                    depthplot = np.insert(depthplot,ind,adddepth)
                    tempplot = np.insert(tempplot,ind,addtemp)
                except: #if list
                    i = 0
                    for i,cdepth in enumerate(depthplot):
                        if cdepth > adddepth:
                            break
                    depthplot.insert(i,adddepth)
                    tempplot.insert(i,addtemp)
                    
        #REMOVE A POINT
        elif self.alltabdata[curtabstr]["pt_type"] == 2:
            pt = np.argmin(abs(tempplot-xx)**2 + abs(depthplot-yy)**2)
            try: #if its an array
                tempplot = np.delete(tempplot,pt)
                depthplot = np.delete(depthplot,pt)
            except: #if its a list
                tempplot.pop(pt)
                depthplot.pop(pt)

        #REMOVE A SPIKE
        elif self.alltabdata[curtabstr]["pt_type"] == 3:
            y1 = np.min([self.y1_spike,yy])
            y2 = np.max([self.y1_spike,yy])
            goodvals = (depthplot < y1) | (depthplot > y2)
            tempplot = tempplot[goodvals]
            depthplot = depthplot[goodvals]
                
        #replace values in profile
        self.alltabdata[curtabstr]["profdata"]["depth_qc"] = depthplot
        self.alltabdata[curtabstr]["profdata"]["temp_qc"] = tempplot
        
        #applying user corrections
        self.applychanges()


    except Exception:
        trace_error()
        self.posterror("Failed to select profile point!")

    finally:
        #restore cursor type, delete current indices, reset for next correction
        QApplication.restoreOverrideCursor()
        self.alltabdata[curtabstr]["ProfCanvas"].mpl_disconnect(self.alltabdata[curtabstr]["pt"])
        del self.alltabdata[curtabstr]["pt"]
        if self.alltabdata[curtabstr]["pt_type"] == 3: #if spike selection, remove additional mpl connection
            self.alltabdata[curtabstr]["ProfCanvas"].mpl_disconnect(self.alltabdata[curtabstr]["ptspike"])
            del self.alltabdata[curtabstr]["ptspike"]
        self.alltabdata[curtabstr]["pt_type"] = 0 #reset

        
        
        
#toggle visibility of climatology profile
def toggleclimooverlay(self,pressed):
    try:
        curtabstr = "Tab " + str(self.whatTab())
        if pressed:
            self.alltabdata[curtabstr]["climohandle"].set_visible(True)     
        else:
            self.alltabdata[curtabstr]["climohandle"].set_visible(False)
        self.alltabdata[curtabstr]["ProfCanvas"].draw()
    except Exception:
        trace_error()
        self.posterror("Failed to toggle climatology overlay")
        
        
        
        
        
        
#class to customize nagivation toolbar in profile editor tab
class CustomToolbar(NavigationToolbar):
    def __init__(self,canvas_,parent_):
        self.toolitems = (
            ('Home', 'Reset Original View', 'home', 'home'),
            ('Back', 'Go To Previous View', 'back', 'back'),
            ('Forward', 'Return to Next View', 'forward', 'forward'),
            (None, None, None, None),
            ('Pan', 'Click and Drag to Pan', 'move', 'pan'),
            ('Zoom', 'Select Region to Zoon', 'zoom_to_rect', 'zoom'),)
        NavigationToolbar.__init__(self,canvas_,parent_)
            