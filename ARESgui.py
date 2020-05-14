# =============================================================================
#     Code: ARESgui.py
#     Author: ENS Casey R. Densmore, 25JUN2019
#     
#     Purpose: GUI script for AXBT Realtime Editing System (ARES). See README 
#       for program overview, external dependencies and additional information. 
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
#   File Description: This function contains the PyQt5 QMainWindow class which
#       which builds/controls the primary GUI for ARES. This file also
#       calls functions from the following necessary files:
#           o autoqc.py: autoQC algorithm for temperature-depth profiles
#           o tropicfileinteraction.py: file reading/writing functions
#           o makeAXBTplots.py: Profile/location plot generation
#           o geoplotfunctions.py: Location plot formatting
#           o ocean_climatology_interaction.py: Interaction with climatology
#               and bathymetry datasets
#           o GPS_COM_interaction.py: Interaction with COM ports and NMEA feeds
#               to autopopulate drop location after each launch
#           o VHFsignalprocessor.py: Signal processing and temperature/depth
#               conversion equation functions, interface for interaction with
#               C++ based DLL file for WiNRADIO receivers, QRunnable thread
#               class to process AXBT data from radio receivers or audio files
#           o settingswindow.py: Separate settings GUI and slots necessary to
#               export updated settings to the main GUI
#   Individual functions within the RunProgram class are listed below (grouped by general purpose, then
#       in order of occurence) with brief descriptions.
#
#   General functions within main.py "RunProgram" class of QMainWindow:
#           (start of file)
#       o __init__: Calls functions to initialize GUI
#       o initUI: Builds basic window, loads WiNRADIO DLL, configures thread handling
#       o loaddata: Loads ocean climatology, bathymetry data once on initialization for use during quality control checks
#       o buildmenu: Builds file menu for main GUI
#       o openpreferencesthread: Opens advanced settings window (or reopens if a window is already open)
#       o updatesettings: pyqtSlot to receive updated settings exported from advanced settings window
#       o settingsclosed: pyqtSlot to receive notice when the advanced settings window is closed
#
#           (end of file)
#       o addnewtab: updates ARES tab-tracking system with information for new tab
#       o whatTab: gets identifier for open tab
#       o renametab: renames open tab
#       o setnewtabcolor: sets the background color pattern for new tabs
#       o closecurrenttab: closes open tab
#       o savedataincurtab: saves data in open tab (saved file types depend on tab type and user preferences)
#       o postwarning: posts a warning box specified message
#       o posterror: posts an error box with a specified message
#       o postwarning_option: posts a warning box with Okay/Cancel options
#       o closeEvent: pre-existing function that closes the GUI- function modified to prompt user with an "are you sure" box
#
#   Signal Processor functions within main.py "RunProgram" class of QMainWindow:
#       o makenewprocessortab: builds signal processing tab
#       o datasourcerefresh: refreshes list of connected receivers
#       o datasourcechange: update function when a different receiver is selected
#       o changefrequencytomatchchannel: uses VHF channel/frequency lookup to ensure the two fields match (pyqtSignal)
#       o changechanneltomatchfrequency: uses VHF channel/frequency lookup to ensure the two fields match (pyqtSignal)
#       o changechannelandfrequency: called by previous two functions to actually update channel/frequency in ARES
#       o updatefftsettings: updates minimum thresholds, window size for FFT in thread for open tab (pyqtSignal)
#       o startprocessor: starts a signal processor thread (pyqtSignal)
#       o stopprocessor: stops/aborts a signal processor thread (pyqtSignal)
#       o gettabstrfromnum: gets the self.alltabdata key for the current tab to access that tab's information
#       o triggerUI: updates tab information when that tab is triggered with signal from an AXBT (pyqtSlot)
#       o updateUIinfo: updates user interface/tab data with information from connected thread (pyqtSlot)
#       o updateUIfinal: updates user interface for the final time after signal processing thread is terminated (pyqtSlot)
#       o failedWRmessage: posts a message in the GUI if the signal processor thread encounters an error (pyqtSlot)
#       o updateaudioprogressbar: updates progress bar with progress of signal processing thread using an audio file source (pyqtSlot)
#
#   Profile Editor functions within main.py "RunProgram" class of QMainWindow:
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
#
# =============================================================================



# =============================================================================
#   CALL NECESSARY MODULES HERE
# =============================================================================
from sys import argv, exit
from platform import system as cursys
from struct import calcsize
from os import remove, path, listdir
from traceback import print_exc as trace_error

if cursys() == 'Windows':
    from ctypes import windll

from shutil import copy as shcopy

from tempfile import gettempdir

from PyQt5.QtWidgets import (QMainWindow, QAction, QApplication, QLineEdit, QLabel, QSpinBox, QCheckBox,
    QPushButton, QMessageBox, QWidget, QFileDialog, QComboBox, QTextEdit, QTabWidget, QVBoxLayout, QInputDialog, 
    QGridLayout, QDoubleSpinBox, QTableWidget, QTableWidgetItem, QHeaderView, QProgressBar, QDesktopWidget, 
    QStyle, QStyleOptionTitleBar, QMenu, QActionGroup)
from PyQt5.QtCore import QObjectCleanupHandler, Qt, pyqtSlot
from PyQt5.QtGui import QIcon, QColor, QPalette, QBrush, QLinearGradient, QFont
from PyQt5.Qt import QThreadPool

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
import matplotlib.pyplot as plt

import time as timemodule
import datetime as dt
import numpy as np

import scipy.io as sio

#autoQC-specific modules
import qclib.tropicfileinteraction as tfio
import qclib.makeAXBTplots as tplot
import qclib.autoqc as qc
import qclib.ocean_climatology_interaction as oci
import qclib.VHFsignalprocessor as vsp
import qclib.GPS_COM_interaction as gps
import settingswindow as swin



#   DEFINE CLASS FOR PROGRAM (TO BE CALLED IN MAIN)
class RunProgram(QMainWindow):
    
    
# =============================================================================
#   INITIALIZE WINDOW, INTERFACE
# =============================================================================
    def __init__(self):
        super().__init__()
        
        try:
            self.initUI() #creates GUI window
            self.buildmenu() #Creates interactive menu, options to create tabs and start autoQC
            self.loaddata() #loads climo and bathy data into program first if using the full datasets
            self.makenewprocessortab() #Opens first tab

        except Exception:
            trace_error()
            self.posterror("Failed to initialize the program.")
            
            
        
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
        self.threadpool.setMaxThreadCount(6)
        
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
        


            
# =============================================================================
#     SIGNAL PROCESSOR TAB AND INPUTS HERE
# =============================================================================
    def makenewprocessortab(self):     
        try:

            newtabnum,curtabstr = self.addnewtab()
    
            #also creates proffig and locfig so they will both be ready to go when the tab transitions from signal processor to profile editor
            self.alltabdata[curtabstr] = {"tab":QWidget(),"tablayout":QGridLayout(),"ProcessorFig":plt.figure(),
                      "tabtype":"SignalProcessor_incomplete","isprocessing":False, "source":"none"}

            self.setnewtabcolor(self.alltabdata[curtabstr]["tab"])
            
            #initializing raw data storage
            self.alltabdata[curtabstr]["rawdata"] = {"temperature":np.array([]),
                      "depth":np.array([]),"frequency":np.array([]),"time":np.array([]),
                      "istriggered":False,"firstpointtime":0,"starttime":0}
            
            self.alltabdata[curtabstr]["tablayout"].setSpacing(10)
    
            #creating new tab, assigning basic info
            self.tabWidget.addTab(self.alltabdata[curtabstr]["tab"],'New Tab') 
            self.tabWidget.setCurrentIndex(newtabnum)
            self.tabWidget.setTabText(newtabnum, "New Drop #" + str(self.totaltabs))
            self.alltabdata[curtabstr]["tabnum"] = self.totaltabs #assigning unique, unchanging number to current tab
            self.alltabdata[curtabstr]["tablayout"].setSpacing(10)
            
            #ADDING FIGURE TO GRID LAYOUT
            self.alltabdata[curtabstr]["ProcessorCanvas"] = FigureCanvas(self.alltabdata[curtabstr]["ProcessorFig"]) 
            self.alltabdata[curtabstr]["tablayout"].addWidget(self.alltabdata[curtabstr]["ProcessorCanvas"],0,0,10,1)
            self.alltabdata[curtabstr]["ProcessorCanvas"].setStyleSheet("background-color:transparent;")
            self.alltabdata[curtabstr]["ProcessorFig"].patch.set_facecolor('None')

            #making profile processing result plots
            self.alltabdata[curtabstr]["ProcessorAx"] = plt.axes()

    
            #prep window to plot data
            self.alltabdata[curtabstr]["ProcessorAx"].set_xlabel('Temperature ($^\circ$C)')
            self.alltabdata[curtabstr]["ProcessorAx"].set_ylabel('Depth (m)')
            self.alltabdata[curtabstr]["ProcessorAx"].set_title('Data Received',fontweight="bold")
            self.alltabdata[curtabstr]["ProcessorAx"].grid()
            self.alltabdata[curtabstr]["ProcessorAx"].set_xlim([-2,32])
            self.alltabdata[curtabstr]["ProcessorAx"].set_ylim([5,1000])
            self.alltabdata[curtabstr]["ProcessorAx"].invert_yaxis()
            self.alltabdata[curtabstr]["ProcessorCanvas"].draw() #refresh plots on window
            
            #and add new buttons and other widgets
            self.alltabdata[curtabstr]["tabwidgets"] = {}
                    
            #Getting necessary data
            if self.wrdll != 0:
                winradiooptions = vsp.listwinradios(self.wrdll)
            else:
                winradiooptions = []

            #making widgets
            self.alltabdata[curtabstr]["tabwidgets"]["datasourcetitle"] = QLabel('Data Source:') #1
            self.alltabdata[curtabstr]["tabwidgets"]["refreshdataoptions"] = QPushButton('Refresh')  # 2
            self.alltabdata[curtabstr]["tabwidgets"]["refreshdataoptions"].clicked.connect(self.datasourcerefresh)
            self.alltabdata[curtabstr]["tabwidgets"]["datasource"] = QComboBox() #3
            self.alltabdata[curtabstr]["tabwidgets"]["datasource"].addItem('Test')
            self.alltabdata[curtabstr]["tabwidgets"]["datasource"].addItem('Audio')
            for wr in winradiooptions:
                self.alltabdata[curtabstr]["tabwidgets"]["datasource"].addItem(wr) #ADD COLOR OPTION
            self.alltabdata[curtabstr]["tabwidgets"]["datasource"].currentIndexChanged.connect(self.datasourcechange)
            self.alltabdata[curtabstr]["datasource"] = self.alltabdata[curtabstr]["tabwidgets"]["datasource"].currentText()
            
            self.alltabdata[curtabstr]["tabwidgets"]["channeltitle"] = QLabel('VHF Channel:') #4
            self.alltabdata[curtabstr]["tabwidgets"]["freqtitle"] = QLabel('VHF Frequency (MHz):') #5
            
            self.alltabdata[curtabstr]["tabwidgets"]["vhfchannel"] = QSpinBox() #6
            self.alltabdata[curtabstr]["tabwidgets"]["vhfchannel"].setRange(1,99)
            self.alltabdata[curtabstr]["tabwidgets"]["vhfchannel"].setSingleStep(1)
            self.alltabdata[curtabstr]["tabwidgets"]["vhfchannel"].setValue(12)
            self.alltabdata[curtabstr]["tabwidgets"]["vhfchannel"].valueChanged.connect(self.changefrequencytomatchchannel)
            
            self.alltabdata[curtabstr]["tabwidgets"]["vhffreq"] = QDoubleSpinBox() #7
            self.alltabdata[curtabstr]["tabwidgets"]["vhffreq"].setRange(136, 173.5)
            self.alltabdata[curtabstr]["tabwidgets"]["vhffreq"].setSingleStep(0.375)
            self.alltabdata[curtabstr]["tabwidgets"]["vhffreq"].setDecimals(3)
            self.alltabdata[curtabstr]["tabwidgets"]["vhffreq"].setValue(170.5)
            self.alltabdata[curtabstr]["tabwidgets"]["vhffreq"].valueChanged.connect(self.changechanneltomatchfrequency)
            
            self.alltabdata[curtabstr]["tabwidgets"]["startprocessing"] = QPushButton('START') #8
            self.alltabdata[curtabstr]["tabwidgets"]["startprocessing"].clicked.connect(self.startprocessor)
            self.alltabdata[curtabstr]["tabwidgets"]["stopprocessing"] = QPushButton('STOP') #9
            self.alltabdata[curtabstr]["tabwidgets"]["stopprocessing"].clicked.connect(self.stopprocessor)
            self.alltabdata[curtabstr]["tabwidgets"]["processprofile"] = QPushButton('PROCESS PROFILE') #10
            self.alltabdata[curtabstr]["tabwidgets"]["processprofile"].clicked.connect(self.processprofile)
            
            self.alltabdata[curtabstr]["tabwidgets"]["datetitle"] = QLabel('Date: ') #11
            self.alltabdata[curtabstr]["tabwidgets"]["dateedit"] = QLineEdit('YYYYMMDD') #12
            self.alltabdata[curtabstr]["tabwidgets"]["timetitle"] = QLabel('Time (UTC): ') #13
            self.alltabdata[curtabstr]["tabwidgets"]["timeedit"] = QLineEdit('HHMM') #14
            self.alltabdata[curtabstr]["tabwidgets"]["lattitle"] = QLabel('Latitude (N>0): ') #15
            self.alltabdata[curtabstr]["tabwidgets"]["latedit"] = QLineEdit('XX.XXX') #16
            self.alltabdata[curtabstr]["tabwidgets"]["lontitle"] = QLabel('Longitude (E>0): ') #17
            self.alltabdata[curtabstr]["tabwidgets"]["lonedit"] = QLineEdit('XX.XXX') #18
            self.alltabdata[curtabstr]["tabwidgets"]["idtitle"] = QLabel('Platform ID/Tail#: ') #19
            self.alltabdata[curtabstr]["tabwidgets"]["idedit"] = QLineEdit(self.settingsdict["platformid"]) #20
            
            #formatting widgets
            self.alltabdata[curtabstr]["tabwidgets"]["channeltitle"].setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.alltabdata[curtabstr]["tabwidgets"]["freqtitle"].setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.alltabdata[curtabstr]["tabwidgets"]["lattitle"].setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.alltabdata[curtabstr]["tabwidgets"]["lontitle"].setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.alltabdata[curtabstr]["tabwidgets"]["datetitle"].setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.alltabdata[curtabstr]["tabwidgets"]["timetitle"].setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.alltabdata[curtabstr]["tabwidgets"]["idtitle"].setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            
            #should be 19 entries 
            widgetorder = ["datasourcetitle","refreshdataoptions","datasource","channeltitle","freqtitle","vhfchannel","vhffreq","startprocessing","stopprocessing","processprofile","datetitle","dateedit","timetitle","timeedit","lattitle","latedit","lontitle","lonedit","idtitle","idedit"]
            wrows     = [1,1,2,3,4,3,4,5,6,6,1,1,2,2,3,3,4,4,5,5]
            wcols     = [3,4,3,3,3,4,4,3,3,6,6,7,6,7,6,7,6,7,6,7]
            wrext     = [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1]
            wcolext   = [1,1,2,1,1,1,1,2,2,2,1,1,1,1,1,1,1,1,1,1]
            
    
            #adding user inputs
            for i,r,c,re,ce in zip(widgetorder,wrows,wcols,wrext,wcolext):
                self.alltabdata[curtabstr]["tabwidgets"][i].setFont(self.labelfont)
                self.alltabdata[curtabstr]["tablayout"].addWidget(self.alltabdata[curtabstr]["tabwidgets"][i],r,c,re,ce)
                    
            #adding table widget after all other buttons populated
            self.alltabdata[curtabstr]["tabwidgets"]["table"] = QTableWidget() #19
            self.alltabdata[curtabstr]["tabwidgets"]["table"].setColumnCount(7)
            self.alltabdata[curtabstr]["tabwidgets"]["table"].setRowCount(0) 
            self.alltabdata[curtabstr]["tabwidgets"]["table"].setHorizontalHeaderLabels(('Time (s)', 'Freq (Hz)', 'ChS (dBm)', 'Sp (dB)', 'Rp (%)' ,'Depth (m)','Temp (C)'))
            self.alltabdata[curtabstr]["tabwidgets"]["table"].setFont(self.labelfont)
            self.alltabdata[curtabstr]["tabwidgets"]["table"].verticalHeader().setVisible(False)
            self.alltabdata[curtabstr]["tabwidgets"]["table"].setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff) #removes scroll bars
            self.alltabdata[curtabstr]["tabwidgets"]["tableheader"] = self.alltabdata[curtabstr]["tabwidgets"]["table"].horizontalHeader() 
            self.alltabdata[curtabstr]["tabwidgets"]["tableheader"].setFont(self.labelfont)
            for ii in range(0,7):
                self.alltabdata[curtabstr]["tabwidgets"]["tableheader"].setSectionResizeMode(ii, QHeaderView.Stretch)  
            self.alltabdata[curtabstr]["tabwidgets"]["table"].setEditTriggers(QTableWidget.NoEditTriggers)
            self.alltabdata[curtabstr]["tablayout"].addWidget(self.alltabdata[curtabstr]["tabwidgets"]["table"],8,2,2,7)

            #adjusting stretch factors for all rows/columns
            colstretch = [8,0,1,1,1,1,1,1,1]
            for col,cstr in enumerate(colstretch):
                self.alltabdata[curtabstr]["tablayout"].setColumnStretch(col,cstr)
            rowstretch = [1,1,1,1,1,1,1,1,10]
            for row,rstr in enumerate(rowstretch):
                self.alltabdata[curtabstr]["tablayout"].setRowStretch(row,rstr)

            #making the current layout for the tab
            self.alltabdata[curtabstr]["tab"].setLayout(self.alltabdata[curtabstr]["tablayout"])

        except Exception: #if something breaks
            trace_error()
            self.posterror("Failed to build new processor tab")
        
        
        
# =============================================================================
#         BUTTONS FOR PROCESSOR TAB
# =============================================================================

    #refresh list of available receivers
    def datasourcerefresh(self): 
        try:
            curtabstr = "Tab " + str(self.whatTab())
            # only lets you change the WINRADIO if the current tab isn't already processing
            if not self.alltabdata[curtabstr]["isprocessing"]:
                self.alltabdata[curtabstr]["tabwidgets"]["datasource"].clear()
                self.alltabdata[curtabstr]["tabwidgets"]["datasource"].addItem('Test')
                self.alltabdata[curtabstr]["tabwidgets"]["datasource"].addItem('Audio')
                # Getting necessary data
                if self.wrdll != 0:
                    winradiooptions = vsp.listwinradios(self.wrdll)
                else:
                    winradiooptions = []
                for wr in winradiooptions:
                    self.alltabdata[curtabstr]["tabwidgets"]["datasource"].addItem(wr)  # ADD COLOR OPTION
                self.alltabdata[curtabstr]["tabwidgets"]["datasource"].currentIndexChanged.connect(self.datasourcechange)
                self.alltabdata[curtabstr]["datasource"] = self.alltabdata[curtabstr]["tabwidgets"]["datasource"].currentText()

            else:
                self.postwarning("You cannot refresh input devices while processing. Please click STOP to discontinue processing before refreshing device list")
        except Exception:
            trace_error()
            self.posterror("Failed to refresh available receivers")
            
            

    def datasourcechange(self):
        try:
            #only lets you change the data source if it isn't currently processing
            curtabstr = "Tab " + str(self.whatTab())
            index = self.alltabdata[curtabstr]["tabwidgets"]["datasource"].findText(self.alltabdata[curtabstr]["datasource"], Qt.MatchFixedString)
            
            isbusy = False

            #checks to see if selection is busy
            woption = self.alltabdata[curtabstr]["tabwidgets"]["datasource"].currentText()
            if woption != "Audio" and woption != "Test":
                for ctab in self.alltabdata:
                    if ctab != curtabstr and (self.alltabdata[ctab]["tabtype"] == "SignalProcessor_incomplete" or
                                              self.alltabdata[ctab]["tabtype"] == "SignalProcessor_completed"):
                        if self.alltabdata[ctab]["isprocessing"] and self.alltabdata[ctab]["datasource"] == woption:
                            isbusy = True

            if isbusy:
                self.posterror("This WINRADIO appears to currently be in use! Please stop any other active tabs using this device before proceeding.")
                if index >= 0:
                    self.alltabdata[curtabstr]["tabwidgets"]["datasource"].setCurrentIndex(index)
                return
     
            #only lets you change the WINRADIO if the current tab isn't already processing
            if not self.alltabdata[curtabstr]["isprocessing"]:
                self.alltabdata[curtabstr]["datasource"] = woption
            elif self.alltabdata[curtabstr]["datasource"] != woption:
                if index >= 0:
                     self.alltabdata[curtabstr]["tabwidgets"]["datasource"].setCurrentIndex(index)
                self.postwarning("You cannot change input devices while processing. Please click STOP to discontinue processing before switching devices")
        except Exception:
            trace_error()
            self.posterror("Failed to change selected WiNRADIO receiver for current tab.")
            
            
        
    #these options use a lookup table for VHF channel vs frequency
    def changefrequencytomatchchannel(self,newchannel):
        try:
            if self.changechannelunlocked: #to prevent recursion
                self.changechannelunlocked = False 
                
                curtabstr = "Tab " + str(self.whatTab())
                newfrequency,newchannel = vsp.channelandfrequencylookup(newchannel,'findfrequency')
                self.changechannelandfrequency(newchannel,newfrequency,curtabstr)
                self.changechannelunlocked = True 
            
        except Exception:
            trace_error()
            self.posterror("Frequency/channel mismatch (changing frequency to match channel)!")
            
            
            
    #these options use a lookup table for VHF channel vs frequency
    def changechanneltomatchfrequency(self,newfrequency):
        try:
            if self.changechannelunlocked: #to prevent recursion
                self.changechannelunlocked = False 
                
                curtabstr = "Tab " + str(self.whatTab())
                #special step to skip invalid frequencies!
                if newfrequency == 161.5 or newfrequency == 161.875:
                    oldchannel = self.alltabdata[curtabstr]["tabwidgets"]["vhfchannel"].value()
                    oldfrequency,_ = vsp.channelandfrequencylookup(oldchannel,'findfrequency')
                    if oldfrequency >= 161.6:
                        newfrequency = 161.125
                    else:
                        newfrequency = 162.25
                        
                newchannel,newfrequency = vsp.channelandfrequencylookup(newfrequency,'findchannel')
                self.changechannelandfrequency(newchannel,newfrequency,curtabstr)
                self.changechannelunlocked = True 
            
        except Exception:
            trace_error()
            self.posterror("Frequency/channel mismatch (changing channel to match frequency)!")
            
            
            
    def changechannelandfrequency(self,newchannel,newfrequency,curtabstr):
        try:

            curdatasource = self.alltabdata[curtabstr]["datasource"]
            
            # sets all tabs with the current receiver to the same channel/freq
            for ctab in self.alltabdata:
                #changes channel+frequency values for all tabs set to current data source
                if self.alltabdata[ctab]["datasource"] == curdatasource:
                    self.alltabdata[ctab]["tabwidgets"]["vhfchannel"].setValue(int(newchannel))
                    self.alltabdata[ctab]["tabwidgets"]["vhffreq"].setValue(newfrequency)
                    
                    #sends signal to processor thread to change demodulation VHF frequency for any actively processing non-test/non-audio tabs
                    if self.alltabdata[ctab]["isprocessing"] and curdatasource != 'Audio' and curdatasource != 'Test':
                        self.alltabdata[curtabstr]["processor"].changecurrentfrequency(newfrequency)
                
        except Exception:
            trace_error()
            self.posterror("Frequency/channel update error!")
            
            

    #update FFT thresholds/window setting
    def updatefftsettings(self):
        try:
            curtabstr = "Tab " + str(self.whatTab())
            #updates fft settings for any active tabs
            for ctab in self.alltabdata:
                if self.alltabdata[ctab]["isprocessing"]: 
                    self.alltabdata[curtabstr]["processor"].changethresholds(self.settingsdict["fftwindow"], self.settingsdict["minfftratio"], self.settingsdict["minsiglev"], self.settingsdict["triggerfftratio"], self.settingsdict["triggersiglev"])
        except Exception:
            trace_error()
            self.posterror("Error updating FFT settings!")
            
            
            
    #starting signal processing thread
    def startprocessor(self):
        try:
            curtabstr = "Tab " + str(self.whatTab())
            if not self.alltabdata[curtabstr]["isprocessing"]:

                datasource = self.alltabdata[curtabstr]["datasource"]
                #running processor here
                
                #if too many signal processor threads are already running
                if self.threadpool.activeThreadCount() + 1 > self.threadpool.maxThreadCount():
                    self.postwarning("The maximum number of simultaneous processing threads has been exceeded. This processor will automatically begin collecting data when STOP is selected on another tab.")
                    return
                    
                    
                #checks to make sure that this tab hasn't been used to process from a different source (e.g. user is attempting to switch from "Test" to "Audio" or a receiver), raise error if so
                if datasource == 'Audio':
                    newsource = "audio"
                elif datasource == "Test":
                    newsource = "test"
                else:
                    newsource = "rf"
                    
                oldsource = self.alltabdata[curtabstr]["source"]
                if oldsource == "none":
                    self.alltabdata[curtabstr]["source"] = newsource #assign current source as processor if previously unassigned
                    
                elif oldsource == "audio": #once you have stopped an audio processing tab, ARES won't let you restart it
                    self.postwarning(f"You cannot restart an audio processing instance after stopping. Please open a new tab to process additional audio files.")
                    return
                    
                elif oldsource != newsource: #if "Start" has been selected previously and a source type (test, audio, or rf) was assigned
                    self.postwarning(f"You cannot switch between Test, Audio, and RF data sources after starting processing. Please open a new tab to process a profile from a different source and reset this profile's source to {oldsource} to continue processing.")
                    return

                if datasource == 'Audio': #gets audio file to process
                    try:
                        # getting filename
                        fname, ok = QFileDialog.getOpenFileName(self, 'Open file',self.defaultfilereaddir,"Source Data Files (*.WAV *.Wav *.wav *PCM *Pcm *pcm *MP3 *Mp3 *mp3)","",self.fileoptions)
                        if not ok or fname == "":
                            self.alltabdata[curtabstr]["isprocessing"] = False
                            return
                        else:
                            splitpath = path.split(fname)
                            self.defaultfilereaddir = splitpath[0]

                        datasource = datasource + '_' + fname
                        
                        # building progress bar
                        self.alltabdata[curtabstr]["tabwidgets"]["audioprogressbar"] = QProgressBar()
                        self.alltabdata[curtabstr]["tablayout"].addWidget(
                            self.alltabdata[curtabstr]["tabwidgets"]["audioprogressbar"], 7, 2, 1, 4)
                        self.alltabdata[curtabstr]["tabwidgets"]["audioprogressbar"].setValue(0)
                        QApplication.processEvents()

                    except Exception:
                        self.posterror("Failed to execute audio processor!")
                        trace_error()

                elif datasource != "Test":
                    
                    #checks to make sure current receiver isn't busy
                    for ctab in self.alltabdata:
                        if ctab != curtabstr and self.alltabdata[ctab]["isprocessing"] and self.alltabdata[ctab]["datasource"] == datasource:
                            self.posterror("This WINRADIO appears to currently be in use! Please stop any other active tabs using this device before proceeding.")
                            return
                            
                            
                #gets current tab number
                curtabnum = self.alltabdata[curtabstr]["tabnum"]
                
                #gets rid of scroll bar on table
                self.alltabdata[curtabstr]["tabwidgets"]["table"].setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

                #saving start time for current drop
                if self.alltabdata[curtabstr]["rawdata"]["starttime"] == 0:
                    starttime = dt.datetime.utcnow()
                    self.alltabdata[curtabstr]["rawdata"]["starttime"] = starttime
                    
                    #autopopulating selected fields
                    if datasource[:5] != 'Audio': #but not if reprocessing from audio file
                        if self.settingsdict["autodtg"]:#populates date and time if requested
                            curdatestr = str(starttime.year) + str(starttime.month).zfill(2) + str(starttime.day).zfill(2)
                            self.alltabdata[curtabstr]["tabwidgets"]["dateedit"].setText(curdatestr)
                            curtimestr = str(starttime.hour).zfill(2) + str(starttime.minute).zfill(2)
                            self.alltabdata[curtabstr]["tabwidgets"]["timeedit"].setText(curtimestr)
                        if self.settingsdict["autolocation"] and self.settingsdict["comport"] != 'n':
                            lat, lon, gpsdate, flag = gps.getcurrentposition(self.settingsdict["comport"], 20)
                            if flag == 0 and abs((gpsdate - starttime).total_seconds()) <= 60:
                                self.alltabdata[curtabstr]["tabwidgets"]["latedit"].setText(str(lat))
                                self.alltabdata[curtabstr]["tabwidgets"]["lonedit"].setText(str(lon))
                        if self.settingsdict["autoid"]:
                            self.alltabdata[curtabstr]["tabwidgets"]["idedit"].setText(self.settingsdict["platformid"])
                            
                else:
                    starttime = self.alltabdata[curtabstr]["rawdata"]["starttime"]
                    
                #this should never happen (if there is no DLL loaded there shouldn't be any receivers detected), but just in case
                if self.wrdll == 0 and datasource != 'Test' and datasource[:5] != 'Audio':
                    self.postwarning("The WiNRADIO driver was not successfully loaded! Please restart the program in order to initiate a processing tab with a connected WiNRADIO")
                    return

                #initializing thread, connecting signals/slots
                vhffreq = self.alltabdata[curtabstr]["tabwidgets"]["vhffreq"].value()
                self.alltabdata[curtabstr]["processor"] = vsp.ThreadProcessor(self.wrdll, datasource, vhffreq, curtabnum,  starttime, self.alltabdata[curtabstr]["rawdata"]["istriggered"], self.alltabdata[curtabstr]["rawdata"]["firstpointtime"], self.settingsdict["fftwindow"], self.settingsdict["minfftratio"],self.settingsdict["minsiglev"], self.settingsdict["triggerfftratio"],self.settingsdict["triggersiglev"],slash,self.tempdir)
                
                self.alltabdata[curtabstr]["processor"].signals.failed.connect(self.failedWRmessage) #this signal only for actual processing tabs (not example tabs)
                self.alltabdata[curtabstr]["processor"].signals.iterated.connect(self.updateUIinfo)
                self.alltabdata[curtabstr]["processor"].signals.triggered.connect(self.triggerUI)
                self.alltabdata[curtabstr]["processor"].signals.terminated.connect(self.updateUIfinal)

                #connecting audio file-specific signal (to update progress bar on GUI)
                if datasource[:5] == 'Audio':
                    self.alltabdata[curtabstr]["processor"].signals.updateprogress.connect(self.updateaudioprogressbar)
                
                #starting thread
                self.threadpool.start(self.alltabdata[curtabstr]["processor"])
                self.alltabdata[curtabstr]["isprocessing"] = True
                
                #the code is still running but data collection has at least been initialized. This allows self.savecurrenttab() to save raw data files
                self.alltabdata[curtabstr]["tabtype"] = "SignalProcessor_completed"
                
        except Exception:
            trace_error()
            self.posterror("Failed to start processor!")
            
            
            
    #aborting processor
    def stopprocessor(self):
        try:
            curtabstr = "Tab " + str(self.whatTab())
            if self.alltabdata[curtabstr]["isprocessing"]:
                curtabstr = "Tab " + str(self.whatTab())
                datasource = self.alltabdata[curtabstr]["datasource"]

                self.alltabdata[curtabstr]["processor"].abort()
                self.alltabdata[curtabstr]["isprocessing"] = False #processing is done
                self.alltabdata[curtabstr]["tabwidgets"]["table"].setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)

                # checks to make sure all other tabs with same receiver are stopped (because the radio device is stopped)
                if datasource != 'Test' and datasource != 'Audio':
                    for ctab in self.alltabdata:
                        if self.alltabdata[ctab]["isprocessing"] and self.alltabdata[ctab]["datasource"] == datasource:
                            self.alltabdata[ctab]["processor"].abort()
                            self.alltabdata[ctab]["isprocessing"] = False  # processing is done
                            self.alltabdata[ctab]["tabwidgets"]["table"].setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
                    
        except Exception:
            trace_error()
            self.posterror("Failed to stop processor!")
                
                
                
# =============================================================================
#        SIGNAL PROCESSOR SLOTS AND OTHER CODE
# =============================================================================
    #getting tab string (self.alltabdata key for specified tab) from tab number
    def gettabstrfromnum(self,tabnum):
        for tabname in self.alltabdata:
            if self.alltabdata[tabname]["tabnum"] == tabnum:
                return tabname
    
                
                
    #slot to notify main GUI that the thread has been triggered with AXBT data
    @pyqtSlot(int,float)
    def triggerUI(self,plottabnum,firstpointtime):
        try:
            plottabstr = self.gettabstrfromnum(plottabnum)
            self.alltabdata[plottabstr]["rawdata"]["firstpointtime"] = firstpointtime
            self.alltabdata[plottabstr]["rawdata"]["istriggered"] = True
        except Exception:
            self.posterror("Failed to trigger temperature/depth profile in GUI!")
            trace_error()

            
            
    #slot to pass AXBT data from thread to main GUI
    @pyqtSlot(int,float,float,float,float,float,float,float,int)
    def updateUIinfo(self,plottabnum,ctemp,cdepth,cfreq,csig,cact,cratio,ctime,i):
        try:
            plottabstr = self.gettabstrfromnum(plottabnum)
            
            #defaults so the last depth will be different unless otherwise explicitly stored (z > 0 here)
            lastdepth = -1
            if len(self.alltabdata[plottabstr]["rawdata"]["depth"]) > 0:
                lastdepth = self.alltabdata[plottabstr]["rawdata"]["depth"][-1]
                
            #only appending a datapoint if depths are different
            if cdepth != lastdepth:
                #writing data to tab dictionary
                self.alltabdata[plottabstr]["rawdata"]["time"] = np.append(self.alltabdata[plottabstr]["rawdata"]["time"],ctime)
                self.alltabdata[plottabstr]["rawdata"]["depth"] = np.append(self.alltabdata[plottabstr]["rawdata"]["depth"],cdepth)
                self.alltabdata[plottabstr]["rawdata"]["frequency"] = np.append(self.alltabdata[plottabstr]["rawdata"]["frequency"],cfreq)
                self.alltabdata[plottabstr]["rawdata"]["temperature"] = np.append(self.alltabdata[plottabstr]["rawdata"]["temperature"],ctemp)

                #plot the most recent point
                if i%50 == 0: #draw the canvas every fifty points (~5 sec for 10 Hz sampling)
                    try:
                        del self.alltabdata[plottabstr]["ProcessorAx"].lines[-1]
                    except:
                        pass
                    self.alltabdata[plottabstr]["ProcessorAx"].plot(self.alltabdata[plottabstr]["rawdata"]["temperature"],self.alltabdata[plottabstr]["rawdata"]["depth"],color='k')
                    self.alltabdata[plottabstr]["ProcessorCanvas"].draw()

                #coloring new cell based on whether or not it has good data
                if np.isnan(ctemp):
                    ctemp = '*****'
                    cdepth = '*****'
                    curcolor = QColor(179, 179, 255) #light blue
                else:
                    curcolor = QColor(204, 255, 220) #light green

                #updating table
                tabletime = QTableWidgetItem(str(ctime))
                tabletime.setBackground(curcolor)
                tabledepth = QTableWidgetItem(str(cdepth))
                tabledepth.setBackground(curcolor)
                tablefreq = QTableWidgetItem(str(cfreq))
                tablefreq.setBackground(curcolor)
                tabletemp = QTableWidgetItem(str(ctemp))
                tabletemp.setBackground(curcolor)
                if csig == 0:
                    tablesignal = QTableWidgetItem('N/A')
                elif csig >= -150:
                    tablesignal = QTableWidgetItem(str(csig))
                else:
                    tablesignal = QTableWidgetItem('*****')
                tablesignal.setBackground(curcolor)
                tableact = QTableWidgetItem(str(cact))
                tableact.setBackground(curcolor)
                tablerat = QTableWidgetItem(str(cratio))
                tablerat.setBackground(curcolor)

                table = self.alltabdata[plottabstr]["tabwidgets"]["table"]
                crow = table.rowCount()
                table.insertRow(crow)
                table.setItem(crow, 0, tabletime)
                table.setItem(crow, 1, tablefreq)
                table.setItem(crow, 2, tablesignal)
                table.setItem(crow, 3, tableact)
                table.setItem(crow, 4, tablerat)
                table.setItem(crow, 5, tabledepth)
                table.setItem(crow, 6, tabletemp)
                table.scrollToBottom()
                #        if crow > 20: #uncomment to remove old rows
                #            table.removeRow(0)
        except Exception:
            trace_error()
        
            
            
    #final update from thread after being aborted- restoring scroll bar, other info
    @pyqtSlot(int)
    def updateUIfinal(self,plottabnum):
        try:
            plottabstr = self.gettabstrfromnum(plottabnum)
            try:
                del self.alltabdata[plottabstr]["ProcessorAx"].lines[-1]
            except:
                pass
            self.alltabdata[plottabstr]["ProcessorAx"].plot(self.alltabdata[plottabstr]["rawdata"]["temperature"],self.alltabdata[plottabstr]["rawdata"]["depth"],color='k')
            self.alltabdata[plottabstr]["ProcessorCanvas"].draw()
            self.alltabdata[plottabstr]["isprocessing"] = False
            self.alltabdata[plottabstr]["tabwidgets"]["table"].setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)

            if "audioprogressbar" in self.alltabdata[plottabstr]["tabwidgets"]:
                self.alltabdata[plottabstr]["tabwidgets"]["audioprogressbar"].deleteLater()

        except Exception:
            self.posterror("Failed to complete final UI update!")
            trace_error()

            
            
    #posts message in main GUI if thread processor fails for some reason
    @pyqtSlot(int)
    def failedWRmessage(self,messagenum):
        if messagenum == 1:
            self.posterror("Failed to connect to specified WiNRADIO!")
        elif messagenum == 2:
            self.posterror("Failed to power on specified WiNRADIO!")
        elif messagenum == 3:
            self.posterror("Failed to initialize demodulator for specified WiNRADIO!")
        elif messagenum == 4:
            self.posterror("Failed to set VHF frequency for specified WiNRADIO!")
        elif messagenum == 5:
            self.postwarning("Failed to adjust volume on the specified WiNRADIO!")
        elif messagenum == 6:
            self.posterror("Error configuring the current WiNRADIO device!")
        elif messagenum == 7:
            self.posterror("Failed to configure the WiNRADIO audio stream!")
        elif messagenum == 8:
            self.posterror("Contact lost with WiNRADIO receiver! Please ensure device is connected and powered on!")
        elif messagenum == 9:
            self.posterror("Selected audio file is too large! Please trim the audio file before processing")
        elif messagenum == 10:
            self.posterror("Unspecified processing error raised during SignalProcessor.Run()")
        elif messagenum == 11:
            self.posterror("Unable to read audio file")
        elif messagenum == 12:
            self.posterror("Failed to initialize the signal processor thread")
        elif messagenum == 13:
            self.postwarning("ARES has stopped audio recording as the WAV file has exceeded maximum allowed length. Please start a new processing tab to continue recording AXBT signal to a WAV file.")

            
            
    #updates on screen progress bar if thread is processing audio data
    @pyqtSlot(int,int)
    def updateaudioprogressbar(self,plottabnum,newprogress):
        try:
            plottabstr = self.gettabstrfromnum(plottabnum)
            self.alltabdata[plottabstr]["tabwidgets"]["audioprogressbar"].setValue(newprogress)
        except Exception:
            trace_error()


        
# =============================================================================
#         CHECKS/PREPS TAB TO TRANSITION TO PROFILE EDITOR MODE
# =============================================================================
    def processprofile(self): 
        try:
            #pulling and checking file input data
            curtabstr = "Tab " + str(self.whatTab())
            
            if self.alltabdata[curtabstr]["isprocessing"]:
                self.postwarning("You cannot proceed to the Profile Editor while the tab is actively processing. Please select 'Stop' before continuing!")
                return
            
            #pulling data from inputs
            latstr = self.alltabdata[curtabstr]["tabwidgets"]["latedit"].text()
            lonstr = self.alltabdata[curtabstr]["tabwidgets"]["lonedit"].text()
            identifier = self.alltabdata[curtabstr]["tabwidgets"]["idedit"].text()
            profdatestr = self.alltabdata[curtabstr]["tabwidgets"]["dateedit"].text()
            timestr = self.alltabdata[curtabstr]["tabwidgets"]["timeedit"].text()
                
            #check and correct inputs
            try:
                lat,lon,year,month,day,time,hour,minute,identifier = self.parsestringinputs(latstr,lonstr,profdatestr,timestr,identifier,True,True,True)
            except:
                return
            
            #pulling raw t-d profile
            rawtemperature = self.alltabdata[curtabstr]["rawdata"]["temperature"]
            rawdepth = self.alltabdata[curtabstr]["rawdata"]["depth"]
            
            #removing NaNs
            notnanind = ~np.isnan(rawtemperature*rawdepth)
            rawtemperature = rawtemperature[notnanind]
            rawdepth = rawdepth[notnanind]
            
            #writing other raw data inputs
            self.alltabdata[curtabstr]["rawdata"]["lat"] = lat
            self.alltabdata[curtabstr]["rawdata"]["lon"] = lon
            self.alltabdata[curtabstr]["rawdata"]["year"] = year
            self.alltabdata[curtabstr]["rawdata"]["month"] = month
            self.alltabdata[curtabstr]["rawdata"]["day"] = day
            self.alltabdata[curtabstr]["rawdata"]["droptime"] = time
            self.alltabdata[curtabstr]["rawdata"]["hour"] = hour
            self.alltabdata[curtabstr]["rawdata"]["minute"] = minute
            self.alltabdata[curtabstr]["rawdata"]["ID"] = identifier
            
            #saves profile if necessary
            if self.settingsdict["autosave"]:
                if not self.savedataincurtab(): #try to save profile, terminate function if failed
                    return
            else:
                reply = QMessageBox.question(self, 'Save Raw Data?',
                "Would you like to save the raw data file? \n Filetype options can be adjusted in File>Raw Data File Types \n All unsaved work will be lost!", 
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel, QMessageBox.Cancel)
                if reply == QMessageBox.Yes:
                    if not self.savedataincurtab(): #try to save profile, terminate function if failed
                        return
                elif reply == QMessageBox.Cancel:
                    return
                    
            #prevent processor from continuing if there is no data
            if len(rawdepth) == 0:
                self.postwarning("No valid signal was identified in this profile! Please reprocess from the .wav file with lower minimum signal thresholds to generate a valid profile.")
                return
            
            #delete Processor profile canvas (since it isn't in the tabwidgets sub-dict)
            self.alltabdata[curtabstr]["ProcessorCanvas"].deleteLater()
            
            
        except Exception:
            trace_error()
            self.posterror("Failed to read profile data")
            return
        
        #generating QC tab
        self.continuetoqc(curtabstr,rawtemperature,rawdepth,lat,lon,day,month,year,time,"NotFromFile",identifier)
        



      
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
        
        
        
# =============================================================================
#     TAB MANIPULATION OPTIONS, OTHER GENERAL FUNCTIONS
# =============================================================================

    #handles tab indexing
    def addnewtab(self):
        #creating numeric ID for newly opened tab
        self.totaltabs += 1
        self.tabnumbers.append(self.totaltabs)
        newtabnum = self.tabWidget.count()
        curtabstr = "Tab "+str(self.totaltabs) #pointable string for self.alltabdata dict
        return newtabnum,curtabstr
        
        

    #gets index of open tab in GUI
    def whatTab(self):
        return self.tabnumbers[self.tabWidget.currentIndex()]
        
        
    
    #renames tab (only user-visible name, not self.alltabdata dict key)
    def renametab(self):
        try:
            curtab = self.tabWidget.currentIndex()
            name, ok = QInputDialog.getText(self, 'Rename Current Tab', 'Enter new tab name:',QLineEdit.Normal,str(self.tabWidget.tabText(curtab)))
            if ok:
                self.tabWidget.setTabText(curtab,name)
        except Exception:
            trace_error()
            self.posterror("Failed to rename the current tab")
            
            
    
    #sets default color scheme for tabs
    @staticmethod
    def setnewtabcolor(tab):
        p = QPalette()
        gradient = QLinearGradient(0, 0, 0, 400)
        gradient.setColorAt(0.0, QColor(253,253,255))
        #gradient.setColorAt(1.0, QColor(248, 248, 255))
        gradient.setColorAt(1.0, QColor(225, 225, 255))
        p.setBrush(QPalette.Window, QBrush(gradient))
        tab.setAutoFillBackground(True)
        tab.setPalette(p)
        
        
            
    #closes a tab
    def closecurrenttab(self):
        try:
            reply = QMessageBox.question(self, 'Message',
                "Are you sure to close the current tab?", QMessageBox.Yes | 
                QMessageBox.No, QMessageBox.No)

            if reply == QMessageBox.Yes:

                #getting tab to close
                curtab = int(self.whatTab())
                curtabstr = "Tab " + str(curtab)
                indextoclose = self.tabWidget.currentIndex()
                
                #check to make sure there isn't a corresponding processor thread, close if there is
                if self.alltabdata[curtabstr]["tabtype"] == 'SignalProcessor_incomplete' or self.alltabdata[curtabstr]["tabtype"] == 'SignalProcessor_completed':
                    if self.alltabdata[curtabstr]["isprocessing"]:
                        reply = QMessageBox.question(self, 'Message',
                            "Closing this tab will terminate the current profile and discard the data. Continue?", QMessageBox.Yes | 
                            QMessageBox.No, QMessageBox.No)
                        if reply == QMessageBox.No:
                            return
                        else:
                            self.alltabdata[curtabstr]["processor"].abort()

                #closing open figures in tab to prevent memory leak
                if self.alltabdata[curtabstr]["tabtype"] == "ProfileEditor":
                    plt.close(self.alltabdata[curtabstr]["ProfFig"])
                    plt.close(self.alltabdata[curtabstr]["LocFig"])

                elif self.alltabdata[curtabstr]["tabtype"] == 'SignalProcessor_incomplete' or self.alltabdata[curtabstr]["tabtype"] == 'SignalProcessor_completed':
                    plt.close(self.alltabdata[curtabstr]["ProcessorFig"])

                #closing tab
                self.tabWidget.removeTab(indextoclose)

                #removing current tab data from the self.alltabdata dict, correcting tabnumbers variable
                self.alltabdata.pop("Tab "+str(curtab))
                self.tabnumbers.pop(indextoclose)

        except Exception:
            trace_error()
            self.posterror("Failed to close the current tab")
            
            
            
                
    #save data in open tab        
    def savedataincurtab(self):
        try:
            #getting directory to save files from QFileDialog
            try:
                outdir = str(QFileDialog.getExistingDirectory(self, "Select Directory to Save File(s)",self.defaultfilewritedir,QFileDialog.DontUseNativeDialog))
            except Exception:
                trace_error()
                return False
                                
            #checking directory validity
            if outdir == '':
                QApplication.restoreOverrideCursor()
                return False
            else:
                self.defaultfilewritedir = outdir
                                
        except:
            self.posterror("Error raised in directory selection")
            return

        try:
            QApplication.setOverrideCursor(Qt.WaitCursor)
            
            #pulling all relevant data
            curtabstr = "Tab " + str(self.whatTab())
            
            if self.alltabdata[curtabstr]["tabtype"] == "ProfileEditor":
                try:
                    rawtemperature = self.alltabdata[curtabstr]["profdata"]["temp_raw"]
                    rawdepth = self.alltabdata[curtabstr]["profdata"]["depth_raw"]
                    climotempfill = self.alltabdata[curtabstr]["profdata"]["climotempfill"]
                    climodepthfill = self.alltabdata[curtabstr]["profdata"]["climodepthfill"]
                    temperature = self.alltabdata[curtabstr]["profdata"]["temp_plot"]
                    depth = self.alltabdata[curtabstr]["profdata"]["depth_plot"]
                    day = self.alltabdata[curtabstr]["profdata"]["day"]
                    month = self.alltabdata[curtabstr]["profdata"]["month"]
                    year = self.alltabdata[curtabstr]["profdata"]["year"]
                    time = self.alltabdata[curtabstr]["profdata"]["time"]
                    lat = self.alltabdata[curtabstr]["profdata"]["lat"]
                    lon = self.alltabdata[curtabstr]["profdata"]["lon"]
                    identifier = self.alltabdata[curtabstr]["profdata"]["ID"]
                    num = 99 #placeholder- dont have drop number here currently!!
                    
                    dtg = str(year) + str(month).zfill(2) + str(day).zfill(2) + str(time).zfill(4)
                    curtab = self.tabWidget.currentIndex()
                    filename = self.tabWidget.tabText(curtab)
                    
                    if self.settingsdict["overlayclimo"]:
                        matchclimo = self.alltabdata[curtabstr]["profdata"]["matchclimo"]
                    else:
                        matchclimo = 1

                except:
                    self.posterror("Failed to retrieve profile information")
                    QApplication.restoreOverrideCursor()
                    return False

                if self.settingsdict["savefin"]:
                    try:
                        depth1m = np.arange(0,np.floor(depth[-1]))
                        temperature1m = np.interp(depth1m,depth,temperature)
                        tfio.writefinfile(outdir + slash + filename + '.fin',temperature1m,depth1m,day,month,year,time,lat,lon,num)
                    except Exception:
                        trace_error()
                        self.posterror("Failed to save FIN file")
                if self.settingsdict["savejjvv"]:
                    isbtmstrike = self.alltabdata[curtabstr]["tabwidgets"]["isbottomstrike"].isChecked()
                    try:
                        tfio.writejjvvfile(outdir + slash + filename + '.jjvv',temperature,depth,day,month,year,time,lat,lon,identifier,isbtmstrike)
                    except Exception:
                        trace_error()
                        self.posterror("Failed to save JJVV file")
                if self.settingsdict["savebufr"]:
                    try:
                        tfio.writebufrfile(outdir + slash + filename + '.bufr',temperature,depth,year,month,day,time,lon,lat,identifier,self.settingsdict["originatingcenter"],False,b'\0')
                    except Exception:
                        trace_error()
                        self.posterror("Failed to save BUFR file")
                if self.settingsdict["saveprof"]:
                    try:
                        fig1 = plt.figure()
                        fig1.clear()
                        ax1 = fig1.add_axes([0.1,0.1,0.85,0.85])
                        climohandle = tplot.makeprofileplot(ax1,rawtemperature,rawdepth,temperature,depth,climotempfill,climodepthfill,dtg,matchclimo)
                        if self.settingsdict["overlayclimo"] == 0:
                            climohandle.set_visible(False)
                        fig1.savefig(outdir + slash + filename + '_prof.png',format='png')
                    except Exception:
                        trace_error()
                        self.posterror("Failed to save profile image")
                    finally:
                        plt.close('fig1')

                if self.settingsdict["saveloc"]:
                    try:
                        fig2 = plt.figure()
                        fig2.clear()
                        ax2 = fig2.add_axes([0.1,0.1,0.85,0.85])
                        _,exportlat,exportlon,exportrelief = oci.getoceandepth(lat,lon,6,self.bathymetrydata)
                        tplot.makelocationplot(fig2,ax2,lat,lon,dtg,exportlon,exportlat,exportrelief,6)
                        fig2.savefig(outdir + slash + filename + '_loc.png',format='png')
                    except Exception:
                        trace_error()
                        self.posterror("Failed to save location image")
                    finally:
                        plt.close('fig2')

                    
            elif self.alltabdata[curtabstr]["tabtype"] == "SignalProcessor_completed":
                
                if self.alltabdata[curtabstr]["isprocessing"]:
                    self.postwarning('You must stop processing the current tab before saving data!')

                else:

                    try:
                        #pulling prof data
                        rawtemperature = self.alltabdata[curtabstr]["rawdata"]["temperature"]
                        rawdepth = self.alltabdata[curtabstr]["rawdata"]["depth"]
                        frequency = self.alltabdata[curtabstr]["rawdata"]["frequency"]
                        timefromstart = self.alltabdata[curtabstr]["rawdata"]["time"]

                        #pulling profile metadata if necessary
                        try:
                            lat = self.alltabdata[curtabstr]["rawdata"]["lat"]
                            lon = self.alltabdata[curtabstr]["rawdata"]["lon"]
                            year = self.alltabdata[curtabstr]["rawdata"]["year"]
                            month = self.alltabdata[curtabstr]["rawdata"]["month"]
                            day = self.alltabdata[curtabstr]["rawdata"]["day"]
                            time = self.alltabdata[curtabstr]["rawdata"]["droptime"]
                            hour = self.alltabdata[curtabstr]["rawdata"]["hour"]
                            minute = self.alltabdata[curtabstr]["rawdata"]["minute"]
                        except:
                            # pulling data from inputs
                            latstr = self.alltabdata[curtabstr]["tabwidgets"]["latedit"].text()
                            lonstr = self.alltabdata[curtabstr]["tabwidgets"]["lonedit"].text()
                            profdatestr = self.alltabdata[curtabstr]["tabwidgets"]["dateedit"].text()
                            timestr = self.alltabdata[curtabstr]["tabwidgets"]["timeedit"].text()

                            #only checks validity of necessary data
                            try:
                                if self.settingsdict["saveedf"]:
                                    lat, lon, year, month, day, time, hour, minute, _ = self.parsestringinputs(latstr, lonstr,profdatestr,timestr, 'omit', True, True, False)
                                else:
                                    _, _, year, month, day, time, hour, minute, _ = self.parsestringinputs(latstr, lonstr,profdatestr,timestr, 'omit', False, True, False)
                            except:
                                self.postwarning("Failed to save raw data files!")
                                QApplication.restoreOverrideCursor()
                                return False

                        #date and time strings for LOG file
                        initdatestr = str(year) + '/' + str(month).zfill(2) + '/' + str(day).zfill(2)
                        inittimestr = str(hour).zfill(2) + ':' + str(minute).zfill(2) + ':00'
                        
                        filename = str(year) + str(month).zfill(2) + str(day).zfill(2) + str(time).zfill(4)

                    except Exception:
                        trace_error()
                        self.posterror("Failed to pull raw profile data")
                        QApplication.restoreOverrideCursor()
                        return False
                    
                    if self.settingsdict["savelog"]:
                        try:
                            tfio.writelogfile(outdir + slash + filename + '.DTA',initdatestr,inittimestr,timefromstart,rawdepth,frequency,rawtemperature)
                        except Exception:
                            trace_error()
                            self.posterror("Failed to save LOG file")
                    if self.settingsdict["saveedf"]:
                        try:
                            # noinspection PyUnboundLocalVariable
                            tfio.writeedffile(outdir + slash + filename + '.edf',rawtemperature,rawdepth,year,month,day,hour,minute,0,lat,lon) #lat/lon only parsed if self.settingsdict["saveedf"] is True
                        except Exception:
                            trace_error()
                            self.posterror("Failed to save EDF file")

                    if self.settingsdict["savewav"]:
                        try:
                            oldfile = self.tempdir + slash + 'tempwav_' + str(self.alltabdata[curtabstr]["tabnum"]) + '.WAV'
                            newfile = outdir + slash + filename + '.WAV'

                            if path.exists(newfile):
                                remove(newfile)

                            shcopy(oldfile,newfile)
                        except Exception:
                            trace_error()
                            self.posterror("Failed to save WAV file")

                    if self.settingsdict["savesig"]:
                        try:
                            oldfile = self.tempdir + slash + 'sigdata_' + str(self.alltabdata[curtabstr]["tabnum"]) + '.txt'
                            newfile = outdir + slash + filename + '.sigdata'

                            if path.exists(newfile):
                                remove(newfile)

                            shcopy(oldfile, newfile)
                        except Exception:
                            trace_error()

            else:
                self.postwarning('You must process a profile before attempting to save data!')
                
        except Exception:
            trace_error() #if something else in the file save code broke
            self.posterror("Filed to save files")
            QApplication.restoreOverrideCursor()
            return False
        finally:
            QApplication.restoreOverrideCursor()
            return True
        
            
            
    #warning message
    @staticmethod
    def postwarning(warningtext):
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Warning)
        msg.setText(warningtext)
        msg.setWindowTitle("Warning")
        msg.setStandardButtons(QMessageBox.Ok)
        msg.exec_()
        
        
        
    #error message
    @staticmethod
    def posterror(errortext):
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Critical)
        msg.setText(errortext)
        msg.setWindowTitle("Error")
        msg.setStandardButtons(QMessageBox.Ok)
        msg.exec_()
        
        
    
    #warning message with options (Okay or Cancel)
    @staticmethod
    def postwarning_option(warningtext):
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Warning)
        msg.setText(warningtext)
        msg.setWindowTitle("Warning")
        msg.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
        outval = msg.exec_()
        option = 'unknown'
        if outval == 1024:
            option = 'okay'
        elif outval == 4194304:
            option = 'cancel'
        return option
    
        
        
    #add warning message before closing GUI
    def closeEvent(self, event):
        reply = QMessageBox.question(self, 'Message',
            "Are you sure to close the application? \n All unsaved work will be lost!", QMessageBox.Yes | 
            QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:

            if self.preferencesopened:
                self.settingsthread.close()

            #explicitly closing figures to clean up memory (should be redundant here but just in case)
            for curtabstr in self.alltabdata:
                if self.alltabdata[curtabstr]["tabtype"] == "ProfileEditor":
                    plt.close(self.alltabdata[curtabstr]["ProfFig"])
                    plt.close(self.alltabdata[curtabstr]["LocFig"])

                elif self.alltabdata[curtabstr]["tabtype"] == 'SignalProcessor_incomplete' or self.alltabdata[curtabstr]["tabtype"] == 'SignalProcessor_completed':
                    plt.close(self.alltabdata[curtabstr]["ProcessorFig"])

                    #aborting all threads
                    if self.alltabdata[curtabstr]["isprocessing"]:
                        self.alltabdata[curtabstr]["processor"].abort()

            event.accept()
            # delete all temporary files
            allfilesanddirs = listdir(self.tempdir)
            for cfile in allfilesanddirs:
                if len(cfile) >= 5:
                    cfilestart = cfile[:4]
                    cfileext = cfile[-3:]
                    if (cfilestart.lower() == 'temp' and cfileext.lower() == 'wav') or (cfilestart.lower() == 'sigd' and cfileext.lower() == 'txt'):
                        remove(self.tempdir + slash + cfile)
        else:
            event.ignore() 
    
            
            
    
# =============================================================================
#    PARSE STRING INPUTS/CHECK VALIDITY WHEN TRANSITIONING TO PROFILE EDITOR
# =============================================================================
    def parsestringinputs(self,latstr,lonstr,profdatestr,timestr,identifier,checkcoords,checktime, checkid):
        try:
            #parsing and checking data
            if checkcoords:
                try:
                    #checking latitude validity
                    latstr = latstr.split(',')
                    latsign = np.sign(float(latstr[0]))
                    if len(latstr) == 3:
                        lat = float(latstr[0]) + latsign*float(latstr[1])/60 + latsign*float(latstr[2])/3600
                    elif len(latstr) == 2:
                        lat = float(latstr[0]) + latsign*float(latstr[1])/60
                    else:
                        lat = float(latstr[0])
                except:
                    self.postwarning('Invalid Latitude Entered!')
                    return

                try:
                    #checking longitude validity
                    lonstr = lonstr.split(',')
                    lonsign = np.sign(float(lonstr[0]))
                    if len(lonstr) == 3:
                        lon = float(lonstr[0]) + lonsign*float(lonstr[1])/60 + lonsign*float(lonstr[2])/3600
                    elif len(lonstr) == 2:
                        lon = float(lonstr[0]) + lonsign*float(lonstr[1])/60
                    else:
                        lon = float(lonstr[0])
                except:
                    self.postwarning('Invalid Longitude Entered!')
                    return

                if lon < -180 or lon > 180:
                    self.postwarning('Longitude must be between -180 and 180')
                elif lat < -90 or lat > 90:
                    self.postwarning('Latitude must be between -90 and 90')

                lon = round(lon,3)
                lat = round(lat,3)

            else:
                lon = np.NaN
                lat = np.NaN


            if checktime: #checking time
                if len(timestr) != 4:
                    self.postwarning('Invalid Time Format!')
                    return
                elif len(profdatestr) != 8:
                    self.postwarning('Invalid Date Format!')
                    return

                try: #checking date
                    year = int(profdatestr[:4])
                    month = int(profdatestr[4:6])
                    day = int(profdatestr[6:])
                except:
                    self.postwarning('Invalid Date Entered!')
                    return
                try:
                    time = int(timestr)
                    hour = int(timestr[:2])
                    minute = int(timestr[2:4])
                except:
                    self.postwarning('Invalid Time Entered!')
                    return

                if year < 1938: #year the bathythermograph was invented
                    self.postwarning('Invalid Year Entered (< 1938 AD)!')
                    return
                elif month == 0 or month > 12:
                    self.postwarning("Invalid Month Entered (must be between 1 and 12)")
                    return
                elif day == 0 or day > 31:
                    self.postwarning("Invalid Day Entered (must be between 1 and 31")
                    return
                elif hour > 23 or hour < 0:
                    self.postwarning('Invalid Time Entered (hour must be between 0 and 23')
                    return
                elif minute >= 60:
                    self.postwarning('Invalid Time Entered (minutes must be < 60')
                    return

                #making sure the profile is within 12 hours and not in the future, warning if otherwise
                curtime = timemodule.gmtime()
                deltat = dt.datetime(curtime[0],curtime[1],curtime[2],curtime[3],curtime[4],curtime[5]) - dt.datetime(year,month,day,hour,minute,0)
                option = ''
                if self.settingsdict["dtgwarn"]:
                    if deltat.days < 0:
                        option = self.postwarning_option("Drop time appears to be after the current time. Continue anyways?")
                    elif deltat.days > 1 or (deltat.days == 0 and deltat.seconds > 12*3600):
                        option = self.postwarning_option("Drop time appears to be more than 12 hours ago. Continue anyways?")
                    if option == 'cancel':
                        return
            else:
                year = np.NaN
                month = np.NaN
                day = np.NaN
                time = np.NaN
                hour = np.NaN
                minute = np.NaN

            #check length of identifier
            if checkid and len(identifier) != 5:
                option = self.postwarning_option("Identifier is not 5 characters! Continue anyways?")
                if option == 'cancel':
                    return

            return lat,lon,year,month,day,time,hour,minute,identifier
        except Exception:
            trace_error()
            self.posterror("Unspecified error in reading profile information!")
            return


            
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
        
        