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

#   GUI operation functions 
#       o initUI: Builds basic window, loads WiNRADIO DLL, configures thread handling
#       o loaddata: Loads ocean climatology, bathymetry data once on initialization for use during quality control checks
#       o buildmenu: Builds file menu for main GUI
#       o openpreferencesthread: Opens advanced settings window (or reopens if a window is already open)
#       o updatesettings: pyqtSlot to receive updated settings exported from advanced settings window
#       o settingsclosed: pyqtSlot to receive notice when the advanced settings window is closed

from platform import system as cursys

global slash
if cursys() == 'Windows':
    slash = '\\'
else:
    slash = '/'

from struct import calcsize
from os import remove, path, listdir
from traceback import print_exc as trace_error
from datetime import datetime

if cursys() == 'Windows':
    from ctypes import windll
    
from tempfile import gettempdir

from PyQt5.QtWidgets import (QAction, QWidget, QFileDialog, QTabWidget, QVBoxLayout, QDesktopWidget, 
    QStyle, QStyleOptionTitleBar, QMenu, QActionGroup)
from PyQt5.QtCore import pyqtSlot
from PyQt5.QtGui import QIcon, QFont, QColor
from PyQt5.Qt import QThreadPool

import numpy as np
import scipy.io as sio

import qclib.GPS_COM_interaction as gps
import ARESgui.settingswindow as swin


from ._globalfunctions import (addnewtab, whatTab, renametab, setnewtabcolor, closecurrenttab, savedataincurtab, postwarning, posterror, postwarning_option, closeEvent, parsestringinputs)


def initUI(self):

    #setting window size
    cursize = QDesktopWidget().availableGeometry(self).size()
    titleBarHeight = self.style().pixelMetric(QStyle.PM_TitleBarHeight, QStyleOptionTitleBar(), self)
    self.resize(cursize.width(), cursize.height()-titleBarHeight)

    # setting title/icon, background color
    self.setWindowTitle('AXBT Realtime Editing System')
    self.setWindowIcon(QIcon('qclib/dropicon.png'))
    p = self.palette()
    p.setColor(self.backgroundRole(), QColor(255,255,255))
    self.setPalette(p)

    #setting slash dependent on OS
    global slash
    if cursys() == 'Windows':
        slash = '\\'
    else:
        slash = '/'

    #getting temporary directory for files
    self.tempdir = gettempdir()

    #settings file source- places dotfile in user's home directory
    self.settingsfile = path.expanduser("~") + slash + ".ARESsettings"
    
    #setting up file dialog options
    self.fileoptions = QFileDialog.Options()
    self.fileoptions |= QFileDialog.DontUseNativeDialog
    self.defaultfilereaddir = path.expanduser("~")
    self.defaultfilewritedir = path.expanduser("~")

    #setting up dictionary to store data for each tab
    self.alltabdata = {}
    
    #loading default program settings
    self.settingsdict = swin.readsettings(self.settingsfile)
    self.settingsdict["comports"],self.settingsdict["comportdetails"] = gps.listcomports() #pulling available port info from OS
            
    #changes default com port to 'none' if previous default from settings isn't detected
    if not self.settingsdict["comport"] in self.settingsdict["comports"]:
        self.settingsdict["comport"] = 'n'
        
        
    
    if cursys() == 'Windows':
        myappid = 'ARES_v1.0'  # arbitrary string
        windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

        
    # prepping to include tabs
    mainWidget = QWidget()
    self.setCentralWidget(mainWidget)
    mainLayout = QVBoxLayout()
    mainWidget.setLayout(mainLayout)
    self.tabWidget = QTabWidget()
    mainLayout.addWidget(self.tabWidget)
    self.vBoxLayout = QVBoxLayout()
    self.tabWidget.setLayout(self.vBoxLayout)
    self.show()
    
    #changing default font appearance for program- REPLACE WITH SETFONT FUNCTION
    self.configureGuiFont()

    #track whether preferences tab is opened
    self.preferencesopened = False

    #tab tracking
    self.totaltabs = 0
    self.tabnumbers = []

    # creating threadpool
    self.threadpool = QThreadPool()
    self.threadpool.setMaxThreadCount(7)
    
    # variable to prevent recursion errors when updating VHF channel/frequency across multiple tabs
    self.changechannelunlocked = True

    # delete all temporary files
    allfilesanddirs = listdir(self.tempdir)
    for cfile in allfilesanddirs:
        if len(cfile) >= 5:
            cfilestart = cfile[:4]
            cfileext = cfile[-3:]
            if (cfilestart.lower() == 'temp' and cfileext.lower() == 'wav') or (cfilestart.lower() == 'sigd' and cfileext.lower() == 'txt'):
                remove(self.tempdir + slash + cfile)
                
    #initializing GPS thread
    self.goodPosition = False
    self.lat = 0.
    self.lon = 0.
    self.datetime = datetime(1,1,1) #default date- January 1st, 0001 so default GPS time is outside valid window for use
    self.bearing = 0.
    self.sendGPS2settings = False
    self.GPSthread = gps.GPSthread(self.settingsdict["comport"],self.settingsdict['gpsbaud'])
    self.GPSthread.signals.update.connect(self.updateGPSdata) #function located in this file after settingswindow update
    self.threadpool.start(self.GPSthread)

    # loading WiNRADIO DLL API
    if cursys() == 'Windows':
        try:
            if calcsize("P")*8 == 32: #32-bit
                self.wrdll = windll.LoadLibrary("qcdata/WRG39WSBAPI_32.dll") #32-bit
            elif calcsize("P")*8 == 64: #64-bit
                self.wrdll = windll.LoadLibrary("qcdata/WRG39WSBAPI_64.dll") #64-bit
            else:
                self.postwarning("WiNRADIO driver not loaded (unrecognized system architecture: "+str(calcsize("P")*8)+")!")
                self.wrdll = 0
        except:
            self.postwarning("Failed to load WiNRADIO driver!")
            self.wrdll = 0
            trace_error()
            
    else:
        self.postwarning("WiNRADIO communications only supported with Windows! Processing and editing from audio/ASCII files is still available.")
        self.wrdll = 0
        
        
        


        
        
        
# =============================================================================
#    LOAD DATA, BUILD MENU, GENERAL SETTINGS 
# =============================================================================

#saves a tiny amount of time by loading climatology and bathymetry data indices once each on initialization
def loaddata(self):
    self.climodata = {}
    self.bathymetrydata = {}
    
    try:
        climodata = sio.loadmat('qcdata/climo/indices.mat')
        self.climodata["vals"] = climodata['vals'][:, 0]
        self.climodata["depth"] = climodata['Z'][:, 0]
        del climodata
    except:
        self.posterror("Unable to find/load climatology data")
    
    try:
        bathydata = sio.loadmat('qcdata/bathy/indices.mat')
        self.bathymetrydata["vals"] = bathydata['vals'][:, 0]
        del bathydata
    except:
        self.posterror("Unable to find/load bathymetry data")    
        
        
    
#builds file menu for GUI
def buildmenu(self):
    #setting up primary menu bar
    menubar = self.menuBar()
    FileMenu = menubar.addMenu('Options')
    
    #File>New Signal Processor (Mk21) Tab
    newsigtab = QAction('&New Data Acquisition System Tab',self)
    newsigtab.setShortcut('Ctrl+N')
    newsigtab.triggered.connect(self.makenewprocessortab)
    FileMenu.addAction(newsigtab)
    
    #File>New Profile Editor Tab
    newptab = QAction('&New Profile Editing Tab',self)
    newptab.setShortcut('Ctrl+P')
    newptab.triggered.connect(self.makenewproftab)
    FileMenu.addAction(newptab)
    
    #File>Rename Current Tab
    renametab = QAction('&Rename Current Tab',self)
    renametab.setShortcut('Ctrl+R')
    renametab.triggered.connect(self.renametab)
    FileMenu.addAction(renametab)
    
    #File>Close Current Tab
    closetab = QAction('&Close Current Tab',self)
    closetab.setShortcut('Ctrl+X')
    closetab.triggered.connect(self.closecurrenttab)
    FileMenu.addAction(closetab)
    
    #File>Save Files
    savedataintab = QAction('&Save Profile',self)
    savedataintab.setShortcut('Ctrl+S')
    savedataintab.triggered.connect(self.savedataincurtab)
    FileMenu.addAction(savedataintab)

    #File> Open Settings
    openpreferences = QAction('&Preferences', self)
    openpreferences.setShortcut('Ctrl+T')
    openpreferences.triggered.connect(self.openpreferencesthread)
    FileMenu.addAction(openpreferences)
    
    #GUI font size control- !!this requires that self.configureGuiFont() has already been run to set self.fontoptions, self.fonttitles, and self.fontindex
    self.fontMenu = QMenu("Font Size") #making menu, action group
    self.fontMenuActionGroup = QActionGroup(self,exclusive=True)
    
    try: #getting current option (defaults to size=14 if option fails)
        self.fontindex = self.fontoptions.index(self.settingsdict["fontsize"])
    except:
        self.fontindex = 2
        self.settingsdict["fontsize"] = 14
        self.labelfont = QFont()
        self.labelfont.setFamily("Arial")
        self.labelfont.setPointSize(self.settingsdict["fontsize"])
        self.setFont(self.labelfont)
    
    #adding options to menu bar, checking current option
    for i,option in enumerate(self.fonttitles):
        curaction = self.fontMenuActionGroup.addAction(QAction(option, self, checkable=True))
        self.fontMenu.addAction(curaction)
        if i == self.fontindex:
            curaction.setChecked(True)
        
    self.fontMenuActionGroup.triggered.connect(self.changeGuiFont)
    FileMenu.addMenu(self.fontMenu)
    
    
        
        
        
# =============================================================================
#    ARES FONT SIZE CONTROL
# =============================================================================
        
        
def configureGuiFont(self):
    
    #font options and corresponding menu entires (options saved to self for later access)
    self.fontoptions = [8,12,14,16,20] 
    self.fonttitles = ["Very Small (8)", "Small (12)", "Medium (14)", "Large (16)", "Very Large (20)"]
    
    #initializing font
    self.labelfont = QFont()
    self.labelfont.setFamily("Arial")
    
    #getting current option (defaults to size=14 if option fails)
    try: 
        self.fontindex = self.fontoptions.index(self.settingsdict["fontsize"])
        
    except: #if error- set default font size to 14 !!Must also change this in settingswindow.setdefaultsettings()
        self.fontindex = 2
        self.settingsdict["fontsize"] = self.fontoptions[self.fontindex] 
                
    #applying font size to general font
    self.labelfont.setPointSize(self.settingsdict["fontsize"])        
    
    #list of widgets to be updated for each type:
    daswidgets = ["datasourcetitle", "refreshdataoptions", "datasource","channeltitle", "freqtitle","vhfchannel", "vhffreq", "startprocessing", "stopprocessing","processprofile", "datetitle","dateedit", "timetitle","timeedit", "lattitle", "latedit", "lontitle","lonedit", "idtitle","idedit", "table", "tableheader"] #signal processor (data acquisition system)
    peinputwidgets = ["title", "lattitle", "latedit", "lontitle", "lonedit", "datetitle", "dateedit", "timetitle", "timeedit", "idtitle", "idedit", "logtitle", "logedit", "logbutton", "submitbutton"]
    pewidgets = ["toggleclimooverlay", "addpoint", "removepoint", "removerange", "sfccorrectiontitle", "sfccorrection", "maxdepthtitle", "maxdepth", "depthdelaytitle", "depthdelay", "runqc", "proftxt", "isbottomstrike", "rcodetitle", "rcode"]
    
    self.tabWidget.setFont(self.labelfont)
    
    #applying updates to all tabs- method dependent on which type each tab is
    for ctab in self.alltabdata:
        ctabtype = self.alltabdata[ctab]["tabtype"]
        
        if ctabtype[:15] == "SignalProcessor": #data acquisition
            curwidgets = daswidgets
        elif ctabtype == "ProfileEditorInput": #prompt to select ASCII file
            curwidgets = peinputwidgets
        elif ctabtype == "ProfileEditor": #profile editor
            curwidgets = pewidgets
        else:
            self.posterror(f"Unable to identify tab type when updating font: {ctabtype}")
            curwidgets = []
            
        #updating font sizes for tab and all widgets
        for widget in curwidgets:
            self.alltabdata[ctab]["tabwidgets"][widget].setFont(self.labelfont)
            
    #save new font to settings file
    swin.writesettings(self.settingsfile, self.settingsdict)
            
            
def changeGuiFont(self): 
    try:
        curind = self.fontoptions.index(self.settingsdict["fontsize"])
        for i,action in enumerate(self.fontMenuActionGroup.actions()):
            if action.isChecked():
                curind = i
                
        self.settingsdict["fontsize"] = self.fontoptions[curind]
        self.configureGuiFont()
    
    except Exception:
        trace_error()
        self.posterror("Failed to update GUI font!")
        
        
        
        

# =============================================================================
#     PREFERENCES THREAD CONNECTION AND SLOT
# =============================================================================

#opening advanced preferences window
def openpreferencesthread(self):
    if not self.preferencesopened: #if the window isn't opened in background- create a new window
        self.preferencesopened = True
        
        self.settingsthread = swin.RunSettings(self.settingsdict)
        self.settingsthread.signals.exported.connect(self.updatesettings)
        self.settingsthread.signals.closed.connect(self.settingsclosed)
        self.settingsthread.signals.updateGPS.connect(self.updateGPSsettings)
        
    else: #window is opened in background- bring to front
        self.settingsthread.show()
        self.settingsthread.raise_()
        self.settingsthread.activateWindow()

        
#slot to receive/update changed settings from advanced preferences window
@pyqtSlot(dict)
def updatesettings(self,settingsdict):

    #save settings to class
    self.settingsdict = settingsdict

    #save settings to file
    swin.writesettings(self.settingsfile, self.settingsdict)
    
    #update fft settings for actively processing tabs
    self.updatefftsettings()
    

#slot to update main GUI loop if the preferences window has been closed
@pyqtSlot(bool)
def settingsclosed(self,isclosed):
    if isclosed:
        self.preferencesopened = False
        self.sendGPS2settings = False #don't try to send GPS position to settings if window is closed
        
        
#function to receive request for GPS update from settings window
@pyqtSlot(str,int)
def updateGPSsettings(self,comport,baudrate):
    self.GPSthread.changeConfig(comport,baudrate)
    self.settingsdict['comport'] = comport
    self.settingsdict['gpsbaud'] = baudrate
    self.sendGPS2settings = True
        
        
#slot to receive (and immediately update) GPS port and baud rate
@pyqtSlot(int,float,float,datetime)
def updateGPSdata(self,isGood,lat,lon,gpsdatetime):
    if isGood == 0:
        dlat = lat - self.lat #for bearing
        dlon = lon - self.lon
        
        self.lat = lat
        self.lon = lon
        self.datetime = gpsdatetime
        self.goodPosition = True
        
        if dlat != 0. or dlon != 0. #only update bearing if position changed
            self.bearing = 90 - np.arctan2(dlat,dlon)*180/np.pi #oversimplified- doesn't account for cosine contraction
            if self.bearing < 0:
                self.bearing += 360
        
        if self.preferencesopened: #only send GPS data to settings window if it's open
            self.settingsthread.refreshgpsdata(lat, lon, gpsdatetime, True)
            
    elif self.preferencesopened:
        self.settingsthread.refreshgpsdata(0., 0., datetime(1,1,1), False)
        if self.sendGPS2settings:
            self.settingsthread.postGPSissue(isGood)
            self.sendGPS2settings = False
                
            


        
