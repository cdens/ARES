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

from os import path, mkdir, listdir
import shutil
from traceback import print_exc as trace_error

from PyQt5.QtWidgets import (QTextEdit, QLineEdit, QLabel, QPushButton, QWidget, QFileDialog, QGridLayout, QCheckBox)
from PyQt5.QtCore import Qt

import datetime as dt
import numpy as np
import re
import matplotlib.pyplot as plt
from matplotlib import cm

from ._globalfunctions import (addnewtab, whatTab, renametab, setnewtabcolor, closecurrenttab, savedataincurtab, postwarning, posterror, postwarning_option, closeEvent, parsestringinputs)

import ARESgui.settingswindow as swin
import qclib.tropicfileinteraction as tfio
import qclib.ocean_climatology_interaction as oci
import qclib.makeAXBTplots as tplot


#generates new mission tracker tab
def maketrackertab(self):
    try:
        newtabnum,curtabstr = self.addnewtab()
        
        self.missiondir_selected = False

        #also creates proffig and locfig so they will both be ready to go when the tab transitions from signal processor to profile editor
        self.alltabdata[curtabstr] = {"tab":QWidget(),"tablayout":QGridLayout(),"profileSaved":True,
                  "tabtype":"MissionTracker","isprocessing":False, "source":"none"}

        self.setnewtabcolor(self.alltabdata[curtabstr]["tab"])
                
        self.alltabdata[curtabstr]["tablayout"].setSpacing(10)

        #creating new tab, assigning basic info
        self.tabWidget.addTab(self.alltabdata[curtabstr]["tab"],'New Tab') 
        self.tabWidget.setCurrentIndex(newtabnum)
        self.tabWidget.setTabText(newtabnum, "Mission Tracker")
        self.alltabdata[curtabstr]["tabnum"] = self.totaltabs #assigning unique, unchanging number to current tab
        self.alltabdata[curtabstr]["tablayout"].setSpacing(10)
                
        #and add new buttons and other widgets
        self.alltabdata[curtabstr]["tabwidgets"] = {}
        
        #making widgets
        self.alltabdata[curtabstr]["tabwidgets"]["missionnametitle"] = QLabel('Mission Name:') #1
        self.alltabdata[curtabstr]["tabwidgets"]["missionname"] = QLineEdit('Current_Mission_Name') #2
        
        self.alltabdata[curtabstr]["tabwidgets"]["tailnumtitle"] = QLabel('Tail NNumber:') #3
        self.alltabdata[curtabstr]["tabwidgets"]["tailnum"] = QLineEdit('AFNNN') #4
        
        self.alltabdata[curtabstr]["tabwidgets"]["missionfoldertitle"] = QLabel('Mission Folder:') #5
        self.alltabdata[curtabstr]["tabwidgets"]["missionfolderbutton"] = QPushButton('Select')  #6
        self.alltabdata[curtabstr]["tabwidgets"]["missionfolderbutton"].clicked.connect(self.mission_folder_selection)
        self.alltabdata[curtabstr]["tabwidgets"]["missionfolder"] = QTextEdit('Select Mission Folder') #7
        self.alltabdata[curtabstr]["tabwidgets"]["missionfolder"].setReadOnly(True)
        self.alltabdata[curtabstr]["tabwidgets"]["maketempdir"] = QCheckBox('Create temp file directory in mission folder') #8
        self.alltabdata[curtabstr]["tabwidgets"]["maketempdir"].setChecked(True)
        
                
        self.alltabdata[curtabstr]["tabwidgets"]["export"] = QPushButton('Organize/Export Files')  #9
        self.alltabdata[curtabstr]["tabwidgets"]["export"].clicked.connect(self.mission_export)
        self.alltabdata[curtabstr]["tabwidgets"]["genKML"] = QCheckBox('Generate KML files') #10
        self.alltabdata[curtabstr]["tabwidgets"]["genKML"].setChecked(True)
        self.alltabdata[curtabstr]["tabwidgets"]["genprofplot"] = QCheckBox('Generate summary profile plot') #11
        self.alltabdata[curtabstr]["tabwidgets"]["genprofplot"].setChecked(True)
        self.alltabdata[curtabstr]["tabwidgets"]["genposplot"] = QCheckBox('Generate summary position plot') #12
        self.alltabdata[curtabstr]["tabwidgets"]["genposplot"].setChecked(True)
        self.alltabdata[curtabstr]["tabwidgets"]["orgfiles"] = QCheckBox('Organize files by type') #13
        self.alltabdata[curtabstr]["tabwidgets"]["orgfiles"].setChecked(True)
        self.alltabdata[curtabstr]["tabwidgets"]["catjjvv"] = QCheckBox('Create combined JJVV file') #14
        self.alltabdata[curtabstr]["tabwidgets"]["catjjvv"].setChecked(True)
        
        #formatting widgets
        self.alltabdata[curtabstr]["tabwidgets"]["missionnametitle"].setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.alltabdata[curtabstr]["tabwidgets"]["tailnumtitle"].setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.alltabdata[curtabstr]["tabwidgets"]["missionfoldertitle"].setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        
        
        #should be 19 entries 
        widgetorder = ["missionnametitle", "missionname", "tailnumtitle", "tailnum", "missionfoldertitle", "missionfolderbutton", "missionfolder", "maketempdir", "export", "genKML", "genprofplot", "genposplot", "orgfiles", "catjjvv"]
        wrows     = [1,1,2,2,3,3,4,6,8,9,10,11,12,13]
        wcols     = [1,2,1,2,1,2,1,1,1,1,1,1,1,1]
        wrext     = [1,1,1,1,1,1,2,1,1,1,1,1,1,1]
        wcolext   = [1,2,1,2,1,1,3,2,1,2,2,2,2,2]
        

        #adding user inputs
        for i,r,c,re,ce in zip(widgetorder,wrows,wcols,wrext,wcolext):
            self.alltabdata[curtabstr]["tabwidgets"][i].setFont(self.labelfont)
            self.alltabdata[curtabstr]["tablayout"].addWidget(self.alltabdata[curtabstr]["tabwidgets"][i],r,c,re,ce)
            
        #adjusting stretch factors for all rows/columns
        colstretch = [5,1,1,1,5]
        for col,cstr in enumerate(colstretch):
            self.alltabdata[curtabstr]["tablayout"].setColumnStretch(col,cstr)
        rowstretch = [3,1,1,1,1,1,1,2,1,1,1,1,1,1,8]
        for row,rstr in enumerate(rowstretch):
            self.alltabdata[curtabstr]["tablayout"].setRowStretch(row,rstr)

        #making the current layout for the tab
        self.alltabdata[curtabstr]["tab"].setLayout(self.alltabdata[curtabstr]["tablayout"])

    except Exception: #if something breaks
        trace_error()
        self.posterror("Failed to build new mission tracker tab")
        
        
    

#function to select location for mission folder
def mission_folder_selection(self):
    
    try:
        curtabstr = "Tab " + str(self.whatTab())
        
        outdir = str(QFileDialog.getExistingDirectory(self, "Select directory in which the mission folder will be made",self.defaultfilewritedir,QFileDialog.DontUseNativeDialog))
        
        badcharlist = "[@!#$%^&*()<>?/\|}{~:]"
        strcheck = re.compile(badcharlist)
        #checking directory validity
        if strcheck.search("name") != None: #verify its a valid file name
            self.postwarning("Mission names cannot include the following: " + badcharlist)
            
        elif outdir != '':
            missionname = self.alltabdata[curtabstr]["tabwidgets"]["missionname"].text().strip()
            self.missiondir = outdir + self.slash + missionname
            self.defaultfilewritedir = self.missiondir
            self.defaultfilereaddir = self.missiondir
            
            #create/set mission folder and tempfile folder
            if not path.exists(self.missiondir):
                mkdir(self.missiondir)
            if self.alltabdata[curtabstr]["tabwidgets"]["maketempdir"].isChecked():
                self.tempdir = self.missiondir + self.slash + "tempfiles"
                if not path.exists(self.tempdir):
                    mkdir(self.tempdir)
            self.alltabdata[curtabstr]["tabwidgets"]["missionfolder"].setText(self.defaultfilewritedir)
            
            
            #also update tail number in settings
            tailnum = self.alltabdata[curtabstr]["tabwidgets"]["tailnum"].text().strip()
            self.settingsdict['platformid'] = tailnum
            swin.writesettings(self.settingsfile, self.settingsdict)
            
            self.missiondir_selected = True
    except:
        trace_error()
        self.posterror("Error raised in mission folder selection")
    
    
        
#exports mission files upon completion of data processing
def mission_export(self):
    try:
        
        if not self.missiondir_selected:
            self.postwarning("You must select a mission directory before exporting/organizing files in that directory")
            return
        
        curtabstr = "Tab " + str(self.whatTab())
        
        #getting preferences
        if self.alltabdata[curtabstr]["tabwidgets"]["genKML"].isChecked():
            genKML = True
        else:
            genKML = False
            
        if self.alltabdata[curtabstr]["tabwidgets"]["genprofplot"].isChecked():
            genprofplot = True
        else:
            genprofplot = False
            
        if self.alltabdata[curtabstr]["tabwidgets"]["genposplot"].isChecked():
            genposplot = True
        else:
            genposplot = False
            
        if self.alltabdata[curtabstr]["tabwidgets"]["orgfiles"].isChecked():
            orgfiles = True
        else:
            orgfiles = False
            
        if self.alltabdata[curtabstr]["tabwidgets"]["catjjvv"].isChecked():
            catjjvv = True
        else:
            catjjvv = False
            
        
        if genKML:
            if orgfiles:
                kmldir = self.missiondir + self.slash + "KML"
                if not path.exists(kmldir):
                    mkdir(kmldir)
            else:
                kmldir = self.missiondir
            self.gen_kml_files(self.missiondir,kmldir)
        
        if genprofplot or genposplot:
            self.profplotter(self.missiondir, genprofplot, genposplot)
            
        if catjjvv:
            self.gen_jjvv_combined(self.missiondir)
        
        if orgfiles: #this must be last because files must remain in the mission directory for the previous steps
            filetypes = ["DTA","EDF","WAV","SIGDATA","FIN","BUFR","JJVV","PNG"] #MUST be upper-case (files to move)
            all_files = [f for f in listdir(self.missiondir) if path.isfile(self.missiondir + self.slash + f)] #getting list of files only in mission dir (non-recursive)            
            for file in all_files:
                if file[:7].lower() != "mission" and file[0] not in ['.','_']: #if filename starts with mission, it isn't for a specific drop and shouldn't be moved
                    for ftype in filetypes:
                        cl = len(ftype)
                        if file[-cl:].upper() == ftype:
                            fdir = self.missiondir + self.slash + ftype
                            if not path.exists(fdir): #creating directory if necessary
                                mkdir(fdir)
                            shutil.move(self.missiondir + self.slash + file, fdir + self.slash + file) #moving file
    
    except:
        trace_error()
        self.posterror("Error raised in mission folder export/organization")
    
        
        
        
        
def gen_kml_files(self,missiondir,kmldir):
    try:
        finfiles = [f for f in listdir(missiondir) if path.isfile(missiondir + self.slash + f) and f[-3:].lower() == "fin"]
        for file in finfiles:
            [_,_,day,month,year,time,lat,lon,_] = tfio.readfinfile(missiondir + self.slash + file)
            tfio.writekmlfile(kmldir + self.slash + file[:-3] + '.kml', lon, lat, year, month, day, time)    
    except:
        trace_error()
        self.posterror("Error raised in KML file generation")
     
     
     
        
        
def profplotter(self,missiondir,genprofplot,genposplot):
    
    try:
        header = self.missiondir + self.slash + "mission_"
        finfiles = [f for f in listdir(missiondir) if path.isfile(missiondir + self.slash + f) and f[-3:].lower() == "fin"]
        
        alltemps = []
        alldepths = []
        alllats = []
        alllons = []
        alldtgs = []
        
        for file in finfiles:
            [temp,depth,day,month,year,time,lat,lon,_] = tfio.readfinfile(missiondir + self.slash + file)
            alltemps.append(temp)
            alldepths.append(depth)
            alllats.append(lat)
            alllons.append(lon)
            alldtgs.append(f"{year:04d}{month:02d}{day:02d}{time:04d}")
        
        
        #multi-profile plot
        if genprofplot and len(alltemps) > 0:
            figprof, axprof = plt.subplots()
            
            if len(alltemps) >= 17: #only show ddhhmm in legend, make 2 columns
                manydrops = True
            else:
                manydrops = False
                
            colors = cm.get_cmap("brg",len(alltemps))
            
            i = 0
            for temp,depth,dtg in zip(alltemps,alldepths,alldtgs):
                if manydrops:
                    dtg = dtg[-6:]
                i += 1
                axprof.plot(temp,depth, label=dtg, color=colors(i)[:3]) 
                
            axprof.set_xlabel('Temperature ($^\circ$C)')
            axprof.set_ylabel('Depth (m)')
            if manydrops:
                axprof.legend(ncol=2)
            else:
                axprof.legend()
            axprof.grid()
            axprof.set_xlim([-3,32])
            axprof.set_ylim([-5,1000])
            axprof.set_yticks([0,100,200,400,600,800,1000])
            axprof.set_yticklabels([0,100,200,400,600,800,1000])
            axprof.invert_yaxis()
            
            figprof.savefig(header + "_profileplot.png")
        
        
        #location plot
        if genposplot and len(alltemps) > 0:
            figpos = plt.figure()
            figpos.clear()
            axpos = figpos.add_axes([0.1,0.1,0.85,0.85])
            
            _,exportlat,exportlon,exportrelief = oci.getoceandepth(alllats[0],alllons[0],10,self.bathymetrydata)
            tplot.makelocationplot(figpos,axpos,alllats,alllons,_,exportlon,exportlat,exportrelief,6)
            
            figpos.savefig(header + "_locationplot.png")
    
    except:
        trace_error()
        self.posterror("Error raised in mission profile/location plot generation")
    
 
     
        
def gen_jjvv_combined(self,missiondir):
    try:
        outfilename = "mission_axbt_drops.jjvv"
        jjvvfiles = [f for f in listdir(missiondir) if path.isfile(missiondir + self.slash + f) and f[-4:].lower() == "jjvv"]
        
        with open(missiondir + self.slash + outfilename,"w") as f_out:
            f_out.write("UNCLASSIFIED\n\nDATA distribution STATEMENT A: PUBLIC DOMAIN\\\n\n")
            for file in jjvvfiles:
                with open(missiondir + self.slash + file) as f_in:
                    f_out.write(f_in.read().strip() + "\n\n")
                    
    except:
        trace_error()
        self.posterror("Error raised in combined mission JJVV file generation")
    
    
    
    
    
    