# =============================================================================
#     Code: main.py
#     Author: ENS Casey R. Densmore, 25JUN2019
#     
#     Purpose: Main script for AXBT Realtime Editing System (ARES). See README 
#       for program overview, external dependencies and additional information. 
#
#   File Description: This function contains the PyQt5 QMainWindow class which
#       which houses the primary GUI and event loop for ARES. This file also
#       calls functions from the following necessary files:
#           o autoqc.py: autoQC algorithm for temperature-depth profiles
#           o tropicfileinteraction.py: file reading/writing functions
#           o makeAXBTplots.py: Profile/location plot generation
#           o geoplotfunctions.py: Location plot special functions
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
#       o setdefaults: Sets default settings for program (could be reconfigured to read from/write to file)
#       o loaddata: Loads ocean climatology, bathymetry data once on initialization for use during quality control checks
#       o buildmenu: Builds file menu for main GUI
#       o openpreferencesthread: Opens advanced settings window (or reopens if a window is already open)
#       o updatesettings: pyqtSlot to receive updated settings exported from advanced settings window
#       o settingsclosed: pyqtSlot to receive notice when the advanced settings window is closed
#
#           (end of file)
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
#       o checkwinradiooptions: interacts with WiNRADIO DLL to get a list of serial numbers for connected receivers
#       o changefrequencytomatchchannel: uses VHF channel/frequency lookup to ensure the two fields match (pyqtSignal)
#       o changechanneltomatchfrequency: uses VHF channel/frequency lookup to ensure the two fields match (pyqtSignal)
#       o updatefftsettings: updates minimum thresholds, window size for FFT in thread for open tab (pyqtSignal)
#       o startprocessor: starts a signal processor thread (pyqtSignal)
#       o stopprocessor: stops/aborts a signal processor thread (pyqtSignal)
#       o gettabstrfromnum: gets the alltabdata key for the current tab to access that tab's information
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
#       o addpoint: lets user add a point to the profile
#       o removepoint: lets user remove a point from the profile
#       o on_release: adds or removes user-selected point from profile
#       o applychanges: updates profile preferences for surface correction, cutoff, and depth delay features
#       o rerunqc: Reruns the autoQC algorithm with current advanced preferences
#       o toggleclimooverlay: toggles visibility of climatology profile on plot
#       o parsestringinputs: checks validity of user inputs
#
# =============================================================================


# =============================================================================
#   CALL NECESSARY MODULES HERE
# =============================================================================
import sys
import platform
import os
import traceback
from ctypes import windll

import shutil

from PyQt5.QtWidgets import (QMainWindow, QAction, QApplication, QMenu, QLineEdit, QLabel, QSpinBox, QCheckBox,
                             QPushButton, QMessageBox, QActionGroup, QWidget, QFileDialog, QComboBox, QTextEdit,
                             QTabWidget, QVBoxLayout, QInputDialog, QGridLayout, QSlider, QDoubleSpinBox, 
                             QTableWidget, QTableWidgetItem, QHeaderView, QProgressBar, QDesktopWidget, QStyle, QStyleOptionTitleBar)
from PyQt5.QtCore import QObjectCleanupHandler, Qt, pyqtSlot
from PyQt5.QtGui import QIcon, QColor, QPalette, QBrush, QLinearGradient, QFont
from PyQt5.Qt import QThreadPool

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
import matplotlib.pyplot as plt

import time as timemodule
import datetime as dt
import numpy as np

from scipy.io import wavfile #for wav
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
            self.setdefaults() #Default autoQC preferences
            self.buildmenu() #Creates interactive menu, options to create tabs and start autoQC
            self.loaddata() #loads climo and bathy data into program
            self.makenewprocessortab() #Opens first tab

        except Exception:
            traceback.print_exc()
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

        myappid = 'ARES_v1.0'  # arbitrary string
        windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

        #changing font size
        font = QFont()
        font.setPointSize(11)
        font.setFamily("Arial")
        self.setFont(font)

        # prepping to include tabs
        mainWidget = QWidget()
        self.setCentralWidget(mainWidget)
        mainLayout = QVBoxLayout()
        mainWidget.setLayout(mainLayout)
        self.tabWidget = QTabWidget()
        mainLayout.addWidget(self.tabWidget)
        self.myBoxLayout = QVBoxLayout()
        self.tabWidget.setLayout(self.myBoxLayout)
        self.show()
        self.totaltabs = 0

        # creating threadpool
        self.threadpool = QThreadPool()
        self.threadpool.setMaxThreadCount(6)

        # delete all temporary files
        allfilesanddirs = os.listdir()
        for cfile in allfilesanddirs:
            if len(cfile) >= 5:
                cfilestart = cfile[:4]
                cfileext = cfile[-3:]
                if cfilestart.lower() == 'temp' and cfileext.lower() == 'wav':
                    os.remove(cfile)
                elif cfilestart.lower() == 'sigd' and cfileext.lower() == 'txt':
                    os.remove(cfile)

        # loading WiNRADIO DLL API
        if platform.system() == 'Windows':
            try:
                # self.wrdll = windll.LoadLibrary("qcdata/WRG39WSBAPI.dll") #32-bit
                self.wrdll = windll.LoadLibrary("qcdata/WRG39WSBAPI_64.dll") #64-bit
            except:
                self.postwarning("WiNRADIO driver NOT FOUND! Please ensure a WiNRADIO Receiver is connected and powered on and then restart the program!")
                self.wrdll = 0
                traceback.print_exc()
        else:
            self.postwarning("WiNRADIO communications only supported with Windows! Processing from audio/ASCII files is still available.")
            self.wrdll = 0


        
# =============================================================================
#     DECLARE DEFAULT VARIABLES, GLOBAL PARAMETERS
# =============================================================================
    def setdefaults(self):
        # processor preferences
        self.autodtg = True  # auto determine profile date/time as system date/time on clicking "START"
        self.autolocation = True  # auto determine location with GPS
        self.autoid = True  # autopopulate platform ID
        self.platformID = 'AFNNN'
        self.savelog = True
        self.saveedf = False
        self.savewav = True
        self.savesig = True
        self.dtgwarn = True  # warn user if entered dtg is more than 12 hours old or after current system time (in future)
        self.renametabstodtg = True  # auto rename tab to dtg when loading profile editor
        self.autosave = False  # automatically save raw data before opening profile editor (otherwise brings up prompt asking if want to save)
        self.fftwindow = 0.3  # window to run FFT (in seconds)
        self.minfftratio = 0.5  # minimum signal to noise ratio to ID data
        self.minsiglev = 5E6  # minimum total signal level to receive data
        self.triggerfftratio = 0.75  # minimum signal to noise ratio to ID data
        self.triggersiglev = 1E7  # minimum total signal level to receive data

        # profeditorpreferences
        self.useclimobottom = True  # use climatology to ID bottom strikes
        self.overlayclimo = True  # overlay the climatology on the plot
        self.comparetoclimo = True  # check for climatology mismatch and display result on plot
        self.savefin = True  # file types to save
        self.savejjvv = True
        self.savebufr = True
        self.saveprof = True
        self.saveloc = True
        self.useoceanbottom = True  # use NTOPO1 bathymetry data to ID bottom strikes
        self.checkforgaps = True  # look for/correct gaps in profile due to false starts from VHF interference
        self.maxderiv = 1.5  # d2Tdz2 threshold to call a point an inflection point
        self.profres = 8.0  # profile minimum vertical resolution (m)
        self.originatingcenter = 62 #default center for BUFR message: NAVO

        self.comport = 'n'
        
        #setting slash dependent on OS
        global slash
        if platform.system() == 'Windows':
            slash = '\\'
        else:
            slash = '/'

        global alltabdata
        alltabdata = {}

        #track whether preferences tab is opened
        self.preferencesopened = False
        
        
# =============================================================================
#    LOAD DATA, BUILD MENU, GENERAL SETTINGS
# =============================================================================

    #loads climatology and bathymetry data 
    def loaddata(self):
        climodata = sio.loadmat('qcdata/climo/LevitusClimo.mat')
        self.climodata = {}
        self.climodata["lon"] =  climodata['X'][:, 0]
        self.climodata["lat"] = climodata['Y'][:, 0]
        self.climodata["depth"] = climodata['Z'][:, 0]
        self.climodata["temp_climo_gridded"] = climodata['temp']

        bathydata = sio.loadmat('qcdata/bathy/ETOPO1_bathymetry.mat')
        self.bathymetrydata = {}
        self.bathymetrydata['x']= bathydata['x'][:,0]
        self.bathymetrydata['y'] = bathydata['y'][:,0]
        self.bathymetrydata['z'] = bathydata['z']

    #builds file menu for GUI
    def buildmenu(self):
        #setting up primary menu bar
        menubar = self.menuBar()
        FileMenu = menubar.addMenu('Options')
        
        #File>New Signal Processor (Mk21) Tab
        newsigtab = QAction('&New Signal Processor Tab',self)
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



# =============================================================================
#     PREFERENCES THREAD CONNECTION AND SLOT
# =============================================================================

    #opening advanced preferences window
    def openpreferencesthread(self):
        if not self.preferencesopened: #if the window isn't opened in background- create a new window
            self.preferencesopened = True
            self.settingsthread = swin.RunSettings(self.autodtg, self.autolocation, self.autoid, self.platformID, self.savelog, self.saveedf, self.savewav, 
                self.savesig, self.dtgwarn, self.renametabstodtg,self.autosave, self.fftwindow, self.minfftratio, self.minsiglev, self.triggerfftratio, 
                self.triggersiglev,self.useclimobottom, self.overlayclimo, self.comparetoclimo, self.savefin, self.savejjvv, self.savebufr, self.saveprof, 
                self.saveloc,self.useoceanbottom, self.checkforgaps, self.maxderiv, self.profres, self.originatingcenter, self.comport)
            self.settingsthread.signals.exported.connect(self.updatesettings)
            self.settingsthread.signals.closed.connect(self.settingsclosed)
        else: #window is opened in background- bring to front
            self.settingsthread.show()
            self.settingsthread.raise_()
            self.settingsthread.activateWindow()

    #slot to receive/update changed settings from advanced preferences window
    @pyqtSlot(bool,bool,bool,str,bool,bool,bool,bool,bool,bool,bool,float,float,float,float,float,bool,bool,bool,bool,bool,bool,bool,bool,bool,bool,float,float,int,str)
    def updatesettings(self,autodtg, autolocation, autoid, platformID, savelog, saveedf,savewav, savesig, dtgwarn,
                       renametabstodtg, autosave, fftwindow, minfftratio, minsiglev, triggerfftratio, triggersiglev, useclimobottom, overlayclimo,
                       comparetoclimo,savefin, savejjvv, savebufr, saveprof, saveloc, useoceanbottom, checkforgaps,maxderiv, profres, originatingcenter, comport):

        # processor preferences
        self.autodtg = autodtg  # auto determine profile date/time as system date/time on clicking "START"
        self.autolocation = autolocation  # auto determine location with GPS
        self.autoid = autoid  # autopopulate platform ID
        self.platformID = platformID
        self.savelog = savelog
        self.saveedf = saveedf
        self.savewav = savewav
        self.savesig = savesig
        self.dtgwarn = dtgwarn  # warn user if entered dtg is more than 12 hours old or after current system time (in future)
        self.renametabstodtg = renametabstodtg  # auto rename tab to dtg when loading profile editor
        self.autosave = autosave  # automatically save raw data before opening profile editor (otherwise brings up prompt asking if want to save)
        self.fftwindow = fftwindow  # window to run FFT (in seconds)
        self.minfftratio = minfftratio  # minimum signal to noise ratio to ID data
        self.minsiglev = minsiglev  # minimum total signal level to receive data
        self.triggerfftratio = triggerfftratio  # minimum signal to noise ratio to ID data
        self.triggersiglev = triggersiglev  # minimum total signal level to receive data

        #update FFT threshold settings in all active threads
        self.updatefftsettings()

        # profeditorpreferences
        self.useclimobottom = useclimobottom  # use climatology to ID bottom strikes
        self.overlayclimo = overlayclimo  # overlay the climatology on the plot
        self.comparetoclimo = comparetoclimo  # check for climatology mismatch and display result on plot
        self.savefin = savefin  # file types to save
        self.savejjvv = savejjvv
        self.savebufr = savebufr
        self.saveprof = saveprof
        self.saveloc = saveloc
        self.useoceanbottom = useoceanbottom  # use NTOPO1 bathymetry data to ID bottom strikes
        self.checkforgaps = checkforgaps  # look for/correct gaps in profile due to false starts from VHF interference
        self.maxderiv = maxderiv  # d2Tdz2 threshold to call a point an inflection point
        self.profres = profres  # profile minimum vertical resolution (m)
        self.originatingcenter = originatingcenter #originating center for BUFR message

        self.comport = comport

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
            #number of the new tab will be equal to the number of previous tabs (offset by 1 removed b/c of Python indexing)
            newtabnum = self.tabWidget.count()
            curtabstr = "Tab "+str(newtabnum) #pointable string for alltabdata dict
    
            #also creates proffig and locfig so they will both be ready to go when the tab transitions from signal processor to profile editor
            alltabdata[curtabstr] = {"tab":QWidget(),"tablayout":QGridLayout(),
                      "ProcessorFig":plt.figure(),"ProfFig":plt.figure(),"LocFig":plt.figure(),
                      "tabtype":"SignalProcessor_incomplete","isprocessing":False}

            self.setnewtabcolor(alltabdata[curtabstr]["tab"])
            
            #initializing raw data storage
            alltabdata[curtabstr]["rawdata"] = {"temperature":np.array([]),
                      "depth":np.array([]),"frequency":np.array([]),"time":np.array([]),
                      "istriggered":False,"firstpointtime":0,"starttime":0}
            
            alltabdata[curtabstr]["tablayout"].setSpacing(10)
    
            #creating new tab, assigning basic info
            self.tabWidget.addTab(alltabdata[curtabstr]["tab"],'New Tab') 
            self.tabWidget.setCurrentIndex(newtabnum)
            self.totaltabs += 1
            self.tabWidget.setTabText(newtabnum, "New Drop #" + str(self.totaltabs))
            alltabdata[curtabstr]["tabnum"] = self.totaltabs #assigning unique, unchanging number to current tab
            alltabdata[curtabstr]["tablayout"].setSpacing(10)
            
            #ADDING FIGURE TO GRID LAYOUT
            alltabdata[curtabstr]["ProcessorCanvas"] = FigureCanvas(alltabdata[curtabstr]["ProcessorFig"]) 
            alltabdata[curtabstr]["tablayout"].addWidget(alltabdata[curtabstr]["ProcessorCanvas"],0,0,10,1)
    
            #making profile processing result plots
            alltabdata[curtabstr]["ProcessorAx"] = alltabdata[curtabstr]["ProcessorFig"].add_axes([0.1, 0.05, 0.85, 0.9])
    
            #prep window to plot data
            alltabdata[curtabstr]["ProcessorAx"].set_xlabel('Temperature ($^\circ$C)')
            alltabdata[curtabstr]["ProcessorAx"].set_ylabel('Depth (m)')
            alltabdata[curtabstr]["ProcessorAx"].set_title('Data Received',fontweight="bold")
            alltabdata[curtabstr]["ProcessorAx"].grid()
            alltabdata[curtabstr]["ProcessorAx"].set_xlim([-2,32])
            alltabdata[curtabstr]["ProcessorAx"].set_ylim([5,1000])
            alltabdata[curtabstr]["ProcessorAx"].invert_yaxis()
            alltabdata[curtabstr]["ProcessorCanvas"].draw() #refresh plots on window
            
            #and add new buttons and other widgets
            alltabdata[curtabstr]["tabwidgets"] = {}
                    
            #Getting necessary data
            if self.wrdll != 0:
                winradiooptions = vsp.listwinradios(self.wrdll)
            else:
                winradiooptions = []

            #making widgets
            alltabdata[curtabstr]["tabwidgets"]["datasourcetitle"] = QLabel('Data Source:') #1
            alltabdata[curtabstr]["tabwidgets"]["refreshdataoptions"] = QPushButton('Refresh')  # 2
            alltabdata[curtabstr]["tabwidgets"]["refreshdataoptions"].clicked.connect(self.datasourcerefresh)
            alltabdata[curtabstr]["tabwidgets"]["datasource"] = QComboBox() #3
            alltabdata[curtabstr]["tabwidgets"]["datasource"].addItem('Test')
            alltabdata[curtabstr]["tabwidgets"]["datasource"].addItem('Audio')
            for wr in winradiooptions:
                alltabdata[curtabstr]["tabwidgets"]["datasource"].addItem(wr) #ADD COLOR OPTION
            alltabdata[curtabstr]["tabwidgets"]["datasource"].currentIndexChanged.connect(self.datasourcechange)
            alltabdata[curtabstr]["datasource"] = alltabdata[curtabstr]["tabwidgets"]["datasource"].currentText()
            
            alltabdata[curtabstr]["tabwidgets"]["channeltitle"] = QLabel('VHF Channel:') #4
            alltabdata[curtabstr]["tabwidgets"]["freqtitle"] = QLabel('VHF Frequency (MHz):') #5
            
            alltabdata[curtabstr]["tabwidgets"]["vhfchannel"] = QSpinBox() #6
            alltabdata[curtabstr]["tabwidgets"]["vhfchannel"].setRange(1,99)
            alltabdata[curtabstr]["tabwidgets"]["vhfchannel"].setSingleStep(1)
            alltabdata[curtabstr]["tabwidgets"]["vhfchannel"].setValue(12)
            alltabdata[curtabstr]["tabwidgets"]["vhfchannel"].valueChanged.connect(self.changefrequencytomatchchannel)
            
            alltabdata[curtabstr]["tabwidgets"]["vhffreq"] = QDoubleSpinBox() #7
            alltabdata[curtabstr]["tabwidgets"]["vhffreq"].setRange(136, 173.5)
            alltabdata[curtabstr]["tabwidgets"]["vhffreq"].setSingleStep(0.375)
            alltabdata[curtabstr]["tabwidgets"]["vhffreq"].setDecimals(3)
            alltabdata[curtabstr]["tabwidgets"]["vhffreq"].setValue(170.5)
            alltabdata[curtabstr]["tabwidgets"]["vhffreq"].valueChanged.connect(self.changechanneltomatchfrequency)
            
            alltabdata[curtabstr]["tabwidgets"]["startprocessing"] = QPushButton('START') #8
            alltabdata[curtabstr]["tabwidgets"]["startprocessing"].clicked.connect(self.startprocessor)
            alltabdata[curtabstr]["tabwidgets"]["stopprocessing"] = QPushButton('STOP') #9
            alltabdata[curtabstr]["tabwidgets"]["stopprocessing"].clicked.connect(self.stopprocessor)
            alltabdata[curtabstr]["tabwidgets"]["processprofile"] = QPushButton('PROCESS PROFILE') #10
            alltabdata[curtabstr]["tabwidgets"]["processprofile"].clicked.connect(self.processprofile)
            
            alltabdata[curtabstr]["tabwidgets"]["datetitle"] = QLabel('Date: ') #11
            alltabdata[curtabstr]["tabwidgets"]["dateedit"] = QLineEdit('YYYYMMDD') #12
            alltabdata[curtabstr]["tabwidgets"]["timetitle"] = QLabel('Time (UTC): ') #13
            alltabdata[curtabstr]["tabwidgets"]["timeedit"] = QLineEdit('HHMM') #14
            alltabdata[curtabstr]["tabwidgets"]["lattitle"] = QLabel('Latitude (N>0): ') #15
            alltabdata[curtabstr]["tabwidgets"]["latedit"] = QLineEdit('XX.XXX') #16
            alltabdata[curtabstr]["tabwidgets"]["lontitle"] = QLabel('Longitude (E>0): ') #17
            alltabdata[curtabstr]["tabwidgets"]["lonedit"] = QLineEdit('XX.XXX') #18
            alltabdata[curtabstr]["tabwidgets"]["idtitle"] = QLabel('Platform ID/Tail#: ') #19
            alltabdata[curtabstr]["tabwidgets"]["idedit"] = QLineEdit(self.platformID) #20
            
            #formatting widgets
            alltabdata[curtabstr]["tabwidgets"]["channeltitle"].setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            alltabdata[curtabstr]["tabwidgets"]["freqtitle"].setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            alltabdata[curtabstr]["tabwidgets"]["lattitle"].setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            alltabdata[curtabstr]["tabwidgets"]["lontitle"].setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            alltabdata[curtabstr]["tabwidgets"]["datetitle"].setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            alltabdata[curtabstr]["tabwidgets"]["timetitle"].setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            alltabdata[curtabstr]["tabwidgets"]["idtitle"].setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            
            #should be 19 entries 
            widgetorder = ["datasourcetitle","refreshdataoptions","datasource","channeltitle","freqtitle","vhfchannel","vhffreq",
            "startprocessing","stopprocessing","processprofile","datetitle","dateedit","timetitle","timeedit","lattitle","latedit",
            "lontitle","lonedit","idtitle","idedit"]
            wrows     = [1,1,2,3,4,3,4,5,5,6,1,1,2,2,3,3,4,4,5,5]
            wcols     = [2,3,2,2,2,3,3,2,3,3,4,5,4,5,4,5,4,5,4,5]
            wrext     = [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1]
            wcolext   = [1,1,2,1,1,1,1,1,1,2,1,1,1,1,1,1,1,1,1,1]
    
            #adding user inputs
            for i,r,c,re,ce in zip(widgetorder,wrows,wcols,wrext,wcolext):
                alltabdata[curtabstr]["tablayout"].addWidget(alltabdata[curtabstr]["tabwidgets"][i],r,c,re,ce)
                    
            #adding table widget after all other buttons populated
            alltabdata[curtabstr]["tabwidgets"]["table"] = QTableWidget() #19
            alltabdata[curtabstr]["tabwidgets"]["table"].setColumnCount(5)
            alltabdata[curtabstr]["tabwidgets"]["table"].setRowCount(0) 
            alltabdata[curtabstr]["tabwidgets"]["table"].setHorizontalHeaderLabels(('Time (s)', 'Frequency (Hz)', 'Signal Strength (dBm)', 'Depth (m)','Temperature (C)'))
            alltabdata[curtabstr]["tabwidgets"]["table"].verticalHeader().setVisible(False)
            alltabdata[curtabstr]["tabwidgets"]["table"].setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff) #removes scroll bars
            header = alltabdata[curtabstr]["tabwidgets"]["table"].horizontalHeader()       
            header.setSectionResizeMode(0, QHeaderView.Stretch)
            header.setSectionResizeMode(1, QHeaderView.Stretch)
            header.setSectionResizeMode(2, QHeaderView.Stretch)
            header.setSectionResizeMode(3, QHeaderView.Stretch)
            header.setSectionResizeMode(4, QHeaderView.Stretch)
            alltabdata[curtabstr]["tabwidgets"]["table"].setEditTriggers(QTableWidget.NoEditTriggers)
            alltabdata[curtabstr]["tablayout"].addWidget(alltabdata[curtabstr]["tabwidgets"]["table"],8,2,2,4)

            #adjusting stretch factors for all rows/columns
            colstretch = [5,1,1,1,1,1,1]
            for col,cstr in zip(range(0,len(colstretch)),colstretch):
                alltabdata[curtabstr]["tablayout"].setColumnStretch(col,cstr)
            rowstretch = [1,1,1,1,1,1,1,1,10]
            for row,rstr in zip(range(0,len(rowstretch)),rowstretch):
                alltabdata[curtabstr]["tablayout"].setRowStretch(row,rstr)

            #making the current layout for the tab
            alltabdata[curtabstr]["tab"].setLayout(alltabdata[curtabstr]["tablayout"])

        except Exception: #if something breaks
            traceback.print_exc()
            self.posterror("Failed to build new processor tab")
        
        
        
# =============================================================================
#         BUTTONS FOR PROCESSOR TAB
# =============================================================================
    #refresh list of available receivers
    def datasourcerefresh(self): 
        try:
            curtabstr = "Tab " + str(self.whatTab())
            # only lets you change the WINRADIO if the current tab isn't already processing
            if not alltabdata[curtabstr]["isprocessing"]:
                alltabdata[curtabstr]["tabwidgets"]["datasource"].clear()
                alltabdata[curtabstr]["tabwidgets"]["datasource"].addItem('Test')
                alltabdata[curtabstr]["tabwidgets"]["datasource"].addItem('Audio')
                # Getting necessary data
                if self.wrdll != 0:
                    winradiooptions = vsp.listwinradios(self.wrdll)
                else:
                    winradiooptions = []
                for wr in winradiooptions:
                    alltabdata[curtabstr]["tabwidgets"]["datasource"].addItem(wr)  # ADD COLOR OPTION
                alltabdata[curtabstr]["tabwidgets"]["datasource"].currentIndexChanged.connect(self.datasourcechange)
                alltabdata[curtabstr]["datasource"] = alltabdata[curtabstr]["tabwidgets"]["datasource"].currentText()
            else:
                self.postwarning("You cannot refresh input devices while processing. Please click STOP to discontinue processing before refreshing device list")
        except Exception:
            traceback.print_exc()
            self.posterror("Failed to refresh available receivers")

    def datasourcechange(self):
        try:
            #only lets you change the data source if it isn't currently processing
            curtabstr = "Tab " + str(self.whatTab())
            index = alltabdata[curtabstr]["tabwidgets"]["datasource"].findText(alltabdata[curtabstr]["datasource"], Qt.MatchFixedString)
            
            #checks to see if selection is busy
            woption = alltabdata[curtabstr]["tabwidgets"]["datasource"].currentText()
            if woption != "Audio" and woption != "Test":
                for ctab in alltabdata:
                    if ctab != curtabstr and (alltabdata[ctab]["tabtype"] == "SignalProcessor_incomplete" or
                                              alltabdata[ctab]["tabtype"] == "SignalProcessor_completed"):
                        if alltabdata[ctab]["isprocessing"] and alltabdata[ctab]["datasource"] == woption:
                            self.posterror("This WINRADIO appears to currently be in use! Please stop any other active tabs using this device before proceeding.")
                            if index >= 0:
                                alltabdata[curtabstr]["tabwidgets"]["datasource"].setCurrentIndex(index)
                            return
     
            #only lets you change the WINRADIO if the current tab isn't already processing
            if not alltabdata[curtabstr]["isprocessing"]:
                alltabdata[curtabstr]["datasource"] = woption
            else:
                if index >= 0:
                     alltabdata[curtabstr]["tabwidgets"]["datasource"].setCurrentIndex(index)
                self.postwarning("You cannot change input devices while processing. Please click STOP to discontinue processing before switching devices")
        except Exception:
            traceback.print_exc()
            self.posterror("Failed to change selected WiNRADIO receiver for current tab.")
        
    def checkwinradiooptions(self,winradiooptions):
        isbusy = [0] * len(winradiooptions)
        for wri in range(len(winradiooptions)):
            wr = winradiooptions[wri]
            for ctab in alltabdata:
                if alltabdata[ctab]["tabtype"] == "SignalProcessor_incomplete" or alltabdata[ctab]["tabtype"] == "SignalProcessor_completed":
                    if alltabdata[ctab]["isprocessing"] and alltabdata[ctab]["datasource"] == wr:
                        isbusy[wri] = 1
        return isbusy
    
    #these options use a lookup table for VHF channel vs frequency
    def changefrequencytomatchchannel(self,newchannel):
        try:
            curtabstr = "Tab " + str(self.whatTab())
            newfrequency,newchannel = vsp.channelandfrequencylookup(newchannel,'findfrequency')
            alltabdata[curtabstr]["tabwidgets"]["vhfchannel"].setValue(newchannel)
            alltabdata[curtabstr]["tabwidgets"]["vhffreq"].setValue(newfrequency)

            curdatasource = alltabdata[curtabstr]["datasource"]
            #checks to make sure all other tabs with same receiver are set to the same channel/freq
            for ctab in alltabdata:
                if alltabdata[ctab]["tabtype"] == "SignalProcessor_incomplete" or alltabdata[ctab]["tabtype"] == "SignalProcessor_completed":
                    if alltabdata[ctab]["isprocessing"] and alltabdata[ctab]["datasource"] == curdatasource:
                        alltabdata[ctab]["tabwidgets"]["vhfchannel"].setValue(newchannel)
                        alltabdata[ctab]["tabwidgets"]["vhffreq"].setValue(newfrequency)

            if alltabdata[curtabstr]["isprocessing"] and alltabdata[curtabstr]["datasource"] != 'Audio' and alltabdata[curtabstr]["datasource"] != 'Test':
                alltabdata[curtabstr]["processor"].changecurrentfrequency(newfrequency)
        except Exception:
            traceback.print_exc()
            self.posterror("Frequency/channel mismatch!")
            
    #these options use a lookup table for VHF channel vs frequency
    def changechanneltomatchfrequency(self,newfrequency):
        try:
            curtabstr = "Tab " + str(self.whatTab())
            #special step to skip invalid frequencies!
            if newfrequency == 161.5 or newfrequency == 161.875:
                oldchannel = alltabdata[curtabstr]["tabwidgets"]["vhfchannel"].value()
                oldfrequency,_ = vsp.channelandfrequencylookup(oldchannel,'findfrequency')
                if oldfrequency >= 161.6:
                    newfrequency = 161.125
                else:
                    newfrequency = 162.25
            newchannel,newfrequency = vsp.channelandfrequencylookup(newfrequency,'findchannel')
            alltabdata[curtabstr]["tabwidgets"]["vhfchannel"].setValue(newchannel)
            alltabdata[curtabstr]["tabwidgets"]["vhffreq"].setValue(newfrequency)

            curdatasource = alltabdata[curtabstr]["datasource"]
            # checks to make sure all other tabs with same receiver are set to the same channel/freq
            for ctab in alltabdata:
                if alltabdata[ctab]["tabtype"] == "SignalProcessor_incomplete" or alltabdata[ctab]["tabtype"] == "SignalProcessor_completed":
                    if alltabdata[ctab]["isprocessing"] and alltabdata[ctab]["datasource"] == curdatasource:
                        alltabdata[ctab]["tabwidgets"]["vhfchannel"].setValue(newchannel)
                        alltabdata[ctab]["tabwidgets"]["vhffreq"].setValue(newfrequency)

            if alltabdata[curtabstr]["isprocessing"] and alltabdata[curtabstr]["datasource"] != 'Audio' and alltabdata[curtabstr]["datasource"] != 'Test':
                alltabdata[curtabstr]["processor"].changecurrentfrequency(newfrequency)
        except Exception:
            traceback.print_exc()
            self.posterror("Frequency/channel mismatch!")

    #update FFT thresholds/window setting
    def updatefftsettings(self):
        try:
            curtabstr = "Tab " + str(self.whatTab())
            #updates fft settings for any active tabs
            for ctab in alltabdata:
                if alltabdata[ctab]["tabtype"] == "SignalProcessor_incomplete" or alltabdata[ctab]["tabtype"] == "SignalProcessor_completed":
                    if alltabdata[ctab]["isprocessing"]: # and alltabdata[ctab]["datasource"] != 'Test' and alltabdata[ctab]["datasource"] != 'Audio':
                        alltabdata[curtabstr]["processor"].changethresholds(self.fftwindow,self.minfftratio,self.minsiglev,self.triggerfftratio,self.triggersiglev)
        except Exception:
            traceback.print_exc()
            self.posterror("Error updating FFT settings!")
            
    #starting signal processing thread
    def startprocessor(self):
        try:
            curtabstr = "Tab " + str(self.whatTab())
            if not alltabdata[curtabstr]["isprocessing"]:

                datasource = alltabdata[curtabstr]["datasource"]
                #running processor here

                #if too many signal processor threads are already running
                if self.threadpool.activeThreadCount() + 1 > self.threadpool.maxThreadCount():
                    self.postwarning("The maximum number of simultaneous processing threads has been exceeded. This processor will automatically begin collecting data when STOP is selected on another tab.")

                if datasource == 'Audio': #gets audio file to process
                    try:
                        # getting filename
                        fname, ok = QFileDialog.getOpenFileName(self, 'Open file','',"Source Data Files (*.WAV *.Wav *.wav *PCM *Pcm *pcm *MP3 *Mp3 *mp3)")
                        if not ok:
                            alltabdata[curtabstr]["isprocessing"] = False
                            return

                        datasource = datasource + '_' + fname

                        # building progress bar
                        alltabdata[curtabstr]["tabwidgets"]["audioprogressbar"] = QProgressBar()
                        alltabdata[curtabstr]["tablayout"].addWidget(
                            alltabdata[curtabstr]["tabwidgets"]["audioprogressbar"], 7, 2, 1, 4)
                        alltabdata[curtabstr]["tabwidgets"]["audioprogressbar"].setValue(0)
                        QApplication.processEvents()

                    except Exception:
                        self.posterror("Failed to execute audio processor!")
                        traceback.print_exc()

                elif datasource != "Test":

                    #checks to make sure current receiver isn't busy
                    for ctab in alltabdata:
                        if ctab != curtabstr and (alltabdata[ctab]["tabtype"] == "SignalProcessor_incomplete" or
                                                  alltabdata[ctab]["tabtype"] == "SignalProcessor_completed"):
                            if alltabdata[ctab]["isprocessing"] and alltabdata[ctab]["datasource"] == datasource:
                                self.posterror("This WINRADIO appears to currently be in use! Please stop any other active tabs using this device before proceeding.")
                                return

                #finds current tab, gets rid of scroll bar on table
                curtabnum = alltabdata[curtabstr]["tabnum"]
                alltabdata[curtabstr]["tabwidgets"]["table"].setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

                #saving start time for current drop
                if alltabdata[curtabstr]["rawdata"]["starttime"] == 0:
                    starttime = dt.datetime.utcnow()
                    alltabdata[curtabstr]["rawdata"]["starttime"] = starttime

                    #autopopulating selected fields if possible
                    if datasource[:5] != 'Audio':
                        if self.autodtg:#populates date and time if requested
                            curdatestr = str(starttime.year) + str(starttime.month).zfill(2) + str(starttime.day).zfill(2)
                            alltabdata[curtabstr]["tabwidgets"]["dateedit"].setText(curdatestr)
                            curtimestr = str(starttime.hour).zfill(2) + str(starttime.minute).zfill(2)
                            alltabdata[curtabstr]["tabwidgets"]["timeedit"].setText(curtimestr)
                        if self.autolocation and self.comport != 'n':
                            lat, lon, gpsdate, flag = gps.getcurrentposition(self.comport, 20)
                            if flag == 0 and abs((gpsdate - starttime).total_seconds()) <= 60:
                                alltabdata[curtabstr]["tabwidgets"]["latedit"].setText(str(lat))
                                alltabdata[curtabstr]["tabwidgets"]["lonedit"].setText(str(lon))
                        if self.autoid:
                            alltabdata[curtabstr]["tabwidgets"]["idedit"].setText(self.platformID)
                else:
                    starttime = alltabdata[curtabstr]["rawdata"]["starttime"]

                #this should never happen (if there is no DLL loaded there shouldn't be any receivers detected), but just in case
                if self.wrdll == 0 and datasource != 'Test' and datasource[:5] != 'Audio':
                    self.postwarning("The WiNRADIO driver was not successfully loaded! Please restart the program in order to initiate a processing tab with a connected WiNRADIO")
                    return

                #initializing thread, connecting signals/slots
                vhffreq = alltabdata[curtabstr]["tabwidgets"]["vhffreq"].value()
                alltabdata[curtabstr]["processor"] = vsp.ThreadProcessor(self.wrdll, datasource, vhffreq, curtabnum, starttime,
                         alltabdata[curtabstr]["rawdata"]["istriggered"], alltabdata[curtabstr]["rawdata"]["firstpointtime"],self.fftwindow,
                         self.minfftratio,self.minsiglev,self.triggerfftratio,self.triggersiglev)
                alltabdata[curtabstr]["processor"].signals.failed.connect(self.failedWRmessage) #this signal only for actual processing tabs (not example tabs)

                alltabdata[curtabstr]["processor"].signals.iterated.connect(self.updateUIinfo)
                alltabdata[curtabstr]["processor"].signals.triggered.connect(self.triggerUI)
                alltabdata[curtabstr]["processor"].signals.terminated.connect(self.updateUIfinal)

                #connecting audio file-specific signal (to update progress bar on GUI)
                if datasource[:5] == 'Audio':
                    alltabdata[curtabstr]["processor"].signals.updateprogress.connect(self.updateaudioprogressbar)

                #starting thread
                self.threadpool.start(alltabdata[curtabstr]["processor"])
                alltabdata[curtabstr]["isprocessing"] = True

                #the code is still running but data collection has at least been initialized. This allows self.savecurrenttab() to save raw data files
                alltabdata[curtabstr]["tabtype"] = "SignalProcessor_completed"

        except Exception:
            traceback.print_exc()
            self.posterror("Failed to start processor!")
            
    #aborting processor
    def stopprocessor(self):
        try:
            curtabstr = "Tab " + str(self.whatTab())
            if alltabdata[curtabstr]["isprocessing"]:
                curtabstr = "Tab " + str(self.whatTab())
                datasource = alltabdata[curtabstr]["datasource"]

                alltabdata[curtabstr]["processor"].abort()
                alltabdata[curtabstr]["isprocessing"] = False #processing is done
                alltabdata[curtabstr]["tabwidgets"]["table"].setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)

                # checks to make sure all other tabs with same receiver are stopped (because the radio device is stopped)
                if datasource != 'Test' and datasource != 'Audio':
                    for ctab in alltabdata:
                        if alltabdata[ctab]["tabtype"] == "SignalProcessor_incomplete" or alltabdata[ctab]["tabtype"] == "SignalProcessor_completed":
                            if alltabdata[ctab]["isprocessing"] and alltabdata[ctab]["datasource"] == datasource:
                                alltabdata[ctab]["processor"].abort()
                                alltabdata[ctab]["isprocessing"] = False  # processing is done
                                alltabdata[ctab]["tabwidgets"]["table"].setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
                    
        except Exception:
            traceback.print_exc()
            self.posterror("Failed to stop processor!")
                
                
                
# =============================================================================
#        SIGNAL PROCESSOR SLOTS AND OTHER CODE
# =============================================================================
    #getting tab string (alltabdata key for specified tab) from tab number
    def gettabstrfromnum(self,tabnum):
        for tabname in alltabdata:
            if alltabdata[tabname]["tabnum"] == tabnum:
                return tabname
    
    #slot to notify main GUI that the thread has been triggered with AXBT data
    @pyqtSlot(int,float)
    def triggerUI(self,plottabnum,firstpointtime):
        try:
            plottabstr = self.gettabstrfromnum(plottabnum)
            alltabdata[plottabstr]["rawdata"]["firstpointtime"] = firstpointtime
            alltabdata[plottabstr]["rawdata"]["istriggered"] = True
        except Exception:
            self.posterror("Failed to trigger temperature/depth profile in GUI!")
            traceback.print_exc()

    #slot to pass AXBT data from thread to main GUI
    @pyqtSlot(int,float,float,float,float,float,int)
    def updateUIinfo(self,plottabnum,ctemp,cdepth,cfreq,csig,ctime,i):
        try:
            plottabstr = self.gettabstrfromnum(plottabnum)

            #writing data to tab dictionary
            alltabdata[plottabstr]["rawdata"]["time"] = np.append(alltabdata[plottabstr]["rawdata"]["time"],ctime)
            alltabdata[plottabstr]["rawdata"]["depth"] = np.append(alltabdata[plottabstr]["rawdata"]["depth"],cdepth)
            alltabdata[plottabstr]["rawdata"]["frequency"] = np.append(alltabdata[plottabstr]["rawdata"]["frequency"],cfreq)
            alltabdata[plottabstr]["rawdata"]["temperature"] = np.append(alltabdata[plottabstr]["rawdata"]["temperature"],ctemp)

            #plot the most recent point
            if i%50 == 0: #draw the canvas every fifty points (~5 sec for 10 Hz sampling)
                try:
                    del alltabdata[plottabstr]["ProcessorAx"].lines[-1]
                except:
                    pass
                alltabdata[plottabstr]["ProcessorAx"].plot(alltabdata[plottabstr]["rawdata"]["temperature"],alltabdata[plottabstr]["rawdata"]["depth"],color='k')
                alltabdata[plottabstr]["ProcessorCanvas"].draw()

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
            if csig >= -150:
                tablesignal = QTableWidgetItem(str(csig))
            else:
                tablesignal = QTableWidgetItem('*****')
            tablesignal.setBackground(curcolor)

            table = alltabdata[plottabstr]["tabwidgets"]["table"]
            crow = table.rowCount()
            table.insertRow(crow)
            table.setItem(crow, 0, tabletime)
            table.setItem(crow, 1, tablefreq)
            table.setItem(crow, 2, tablesignal)
            table.setItem(crow, 3, tabledepth)
            table.setItem(crow, 4, tabletemp)
            table.scrollToBottom()
    #        if crow > 20: #uncomment to remove old rows
    #            table.removeRow(0)
        except Exception:
            traceback.print_exc()
        
    #final update from thread after being aborted- restoring scroll bar, other info
    @pyqtSlot(int)
    def updateUIfinal(self,plottabnum):
        try:
            plottabstr = self.gettabstrfromnum(plottabnum)
            try:
                del alltabdata[plottabstr]["ProcessorAx"].lines[-1]
            except:
                pass
            alltabdata[plottabstr]["ProcessorAx"].plot(alltabdata[plottabstr]["rawdata"]["temperature"],alltabdata[plottabstr]["rawdata"]["depth"],color='k')
            alltabdata[plottabstr]["ProcessorCanvas"].draw()
            alltabdata[plottabstr]["isprocessing"] = False
            alltabdata[plottabstr]["tabwidgets"]["table"].setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)

            if alltabdata[plottabstr]["tabwidgets"].__contains__("audioprogressbar"):
                alltabdata[plottabstr]["tabwidgets"]["audioprogressbar"].deleteLater()

        except Exception:
            self.posterror("Failed to complete final UI update!")
            traceback.print_exc()

    #posts message in main GUI if thread processor fails for some reason
    @pyqtSlot(int)
    def failedWRmessage(self,messagenum):
        if messagenum == 0:
            self.posterror("Failed to connect to specified WiNRADIO!")
        elif messagenum == 1:
            self.posterror("Failed to power on specified WiNRADIO!")
        elif messagenum == 2:
            self.posterror("Failed to initialize demodulator for specified WiNRADIO!")
        elif messagenum == 3:
            self.posterror("Failed to set VHF frequency for specified WiNRADIO!")
        elif messagenum == 4:
            self.posterror("Unspecified error communicating with the current WiNRADIO device!")
        elif messagenum == 5:
            self.postwarning("Failed to adjust volume on the specified WiNRADIO!")
        elif messagenum == 6:
            self.posterror("Failed to configure the WiNRADIO audio stream!")
        elif messagenum == 7:
            self.posterror("Contact lost with WiNRADIO receiver! Please ensure device is connected and powered on!")

    #updates on screen progress bar if thread is processing audio data
    @pyqtSlot(int,int)
    def updateaudioprogressbar(self,plottabnum,newprogress):
        try:
            plottabstr = self.gettabstrfromnum(plottabnum)
            alltabdata[plottabstr]["tabwidgets"]["audioprogressbar"].setValue(newprogress)
        except Exception:
            traceback.print_exc()


        
# =============================================================================
#         CHECKS/PREPS TAB TO TRANSITION TO PROFILE EDITOR MODE
# =============================================================================
    def processprofile(self): 
        try:
            #pulling and checking file input data
            curtabstr = "Tab " + str(self.whatTab())
            
            #pulling data from inputs
            latstr = alltabdata[curtabstr]["tabwidgets"]["latedit"].text()
            lonstr = alltabdata[curtabstr]["tabwidgets"]["lonedit"].text()
            identifier = alltabdata[curtabstr]["tabwidgets"]["idedit"].text()
            profdatestr = alltabdata[curtabstr]["tabwidgets"]["dateedit"].text()
            timestr = alltabdata[curtabstr]["tabwidgets"]["timeedit"].text()
                
            #check and correct inputs
            try:
                lat,lon,year,month,day,time,hour,minute = self.parsestringinputs(latstr,lonstr,profdatestr,timestr,True,True)
            except:
                return
            
            #pulling raw t-d profile
            rawtemperature = alltabdata[curtabstr]["rawdata"]["temperature"]
            rawdepth = alltabdata[curtabstr]["rawdata"]["depth"]
            
            #writing other raw data inputs
            alltabdata[curtabstr]["rawdata"]["lat"] = lat
            alltabdata[curtabstr]["rawdata"]["lon"] = lon
            alltabdata[curtabstr]["rawdata"]["year"] = year
            alltabdata[curtabstr]["rawdata"]["month"] = month
            alltabdata[curtabstr]["rawdata"]["day"] = day
            alltabdata[curtabstr]["rawdata"]["droptime"] = time
            alltabdata[curtabstr]["rawdata"]["hour"] = hour
            alltabdata[curtabstr]["rawdata"]["minute"] = minute
            alltabdata[curtabstr]["rawdata"]["ID"] = identifier
            
            #saves profile if necessary
            if self.autosave:
                self.savedataincurtab()
            else:
                reply = QMessageBox.question(self, 'Save Raw Data?',
                "Would you like to save the raw data file? \n Filetype options can be adjusted in File>Raw Data File Types \n All unsaved work will be lost!", 
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel, QMessageBox.Cancel)
                if reply == QMessageBox.Yes:
                    if not self.savedataincurtab(): #try to save profile, terminate function if failed
                        return
                elif reply == QMessageBox.Cancel:
                    return
                
            
            #delete Processor profile canvas (since it isn't in the tabwidgets sub-dict)
            alltabdata[curtabstr]["ProcessorCanvas"].deleteLater()
            
            #removing NaNs from T-D profile
            ind = []
            for i in range(len(rawtemperature)):
                ind.append(not np.isnan(rawtemperature[i]) and not np.isnan(rawdepth[i]))
            rawdepth = rawdepth[ind]
            rawtemperature = rawtemperature[ind]
        except Exception:
            traceback.print_exc()
            self.posterror("Failed to read profile data")
            return
        
        #generating QC tab
        self.continuetoqc(curtabstr,rawtemperature,rawdepth,lat,lon,day,month,year,time,"NotFromFile",identifier)
        



      
# =============================================================================
#    TAB TO LOAD EXISTING DATA FILE INTO EDITOR
# =============================================================================
    def makenewproftab(self):
        try:
            #number of the new tab will be equal to the number of previous tabs (offset by 1 removed b/c of Python indexing)
            newtabnum = self.tabWidget.count()
            curtabstr = "Tab "+str(newtabnum) #pointable string for alltabdata dict
    
            alltabdata[curtabstr] = {"tab":QWidget(),"tablayout":QGridLayout(),
                      "ProfFig":plt.figure(),"LocFig":plt.figure(),
                      "tabtype":"ProfileEditorInput"}
            alltabdata[curtabstr]["tablayout"].setSpacing(10)
            
            self.setnewtabcolor(alltabdata[curtabstr]["tab"])
    
            self.tabWidget.addTab(alltabdata[curtabstr]["tab"],'New Tab') #self.tabWidget.addTab(self.currenttab,'New Tab')
            self.tabWidget.setCurrentIndex(newtabnum)
            self.tabWidget.setTabText(newtabnum,"Tab #" + str(newtabnum+1))
            self.totaltabs += 1
            alltabdata[curtabstr]["tabnum"] = self.totaltabs #assigning unique, unchanging number to current tab
            
            #Create widgets for UI
            alltabdata[curtabstr]["tabwidgets"] = {}
            alltabdata[curtabstr]["tabwidgets"]["title"] = QLabel('Enter AXBT Drop Information:')
            alltabdata[curtabstr]["tabwidgets"]["lattitle"] = QLabel('Latitude (N>0): ')
            alltabdata[curtabstr]["tabwidgets"]["latedit"] = QLineEdit('XX.XXX')
            alltabdata[curtabstr]["tabwidgets"]["lontitle"] = QLabel('Longitude (E>0): ')
            alltabdata[curtabstr]["tabwidgets"]["lonedit"] = QLineEdit('XX.XXX')
            alltabdata[curtabstr]["tabwidgets"]["datetitle"] = QLabel('Date: ')
            alltabdata[curtabstr]["tabwidgets"]["dateedit"] = QLineEdit('YYYYMMDD')
            alltabdata[curtabstr]["tabwidgets"]["timetitle"] = QLabel('Time (UTC): ')
            alltabdata[curtabstr]["tabwidgets"]["timeedit"] = QLineEdit('HHMM')
            alltabdata[curtabstr]["tabwidgets"]["idtitle"] = QLabel('Platform ID/Tail#: ')
            alltabdata[curtabstr]["tabwidgets"]["idedit"] = QLineEdit('AFNNN')
            alltabdata[curtabstr]["tabwidgets"]["logtitle"] = QLabel('Select Source File: ')
            alltabdata[curtabstr]["tabwidgets"]["logbutton"] = QPushButton('Browse')
            alltabdata[curtabstr]["tabwidgets"]["logedit"] = QTextEdit('filepath/LOGXXXXX.DTA')
            alltabdata[curtabstr]["tabwidgets"]["logedit"].setMaximumHeight(100)
            alltabdata[curtabstr]["tabwidgets"]["logbutton"].clicked.connect(self.selectdatafile)
            alltabdata[curtabstr]["tabwidgets"]["submitbutton"] = QPushButton('PROCESS PROFILE')
            alltabdata[curtabstr]["tabwidgets"]["submitbutton"].clicked.connect(self.checkdatainputs_editorinput)
            
            #formatting widgets
            alltabdata[curtabstr]["tabwidgets"]["title"].setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            alltabdata[curtabstr]["tabwidgets"]["lattitle"].setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            alltabdata[curtabstr]["tabwidgets"]["lontitle"].setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            alltabdata[curtabstr]["tabwidgets"]["datetitle"].setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            alltabdata[curtabstr]["tabwidgets"]["timetitle"].setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            alltabdata[curtabstr]["tabwidgets"]["idtitle"].setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            alltabdata[curtabstr]["tabwidgets"]["logtitle"].setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            
            #should be 15 entries
            widgetorder = ["title","lattitle","latedit","lontitle","lonedit","datetitle","dateedit","timetitle",
                           "timeedit","idtitle","idedit","logtitle","logedit","logbutton","submitbutton"]
            wrows     = [1,2,2,3,3,4,4,5,5,6,6,7,7,8,9]
            wcols     = [1,1,2,1,2,1,2,1,2,1,2,1,2,1,1]
            wrext     = [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1]
            wcolext   = [2,1,1,1,1,1,1,1,1,1,1,1,1,2,2]    
            
            #adding user inputs
            for i,r,c,re,ce in zip(widgetorder,wrows,wcols,wrext,wcolext):
                alltabdata[curtabstr]["tablayout"].addWidget(alltabdata[curtabstr]["tabwidgets"][i],r,c,re,ce)
            
            #forces grid info to top/center of window
            alltabdata[curtabstr]["tablayout"].setRowStretch(10,1)
            alltabdata[curtabstr]["tablayout"].setColumnStretch(0,1)
            alltabdata[curtabstr]["tablayout"].setColumnStretch(3,1)

            #applying layout
            alltabdata[curtabstr]["tab"].setLayout(alltabdata[curtabstr]["tablayout"]) 

        except Exception:
            traceback.print_exc()
            self.posterror("Failed to build editor input tab!")

    #browse for raw data file to QC
    def selectdatafile(self):
        try:
            fname,ok = QFileDialog.getOpenFileName(self, 'Open file', 
             '',"Source Data Files (*.DTA *.Dta *.dta *.EDF *.Edf *.edf *.edf)")
            if ok:
                curtabstr = "Tab " + str(self.whatTab())
                alltabdata[curtabstr]["tabwidgets"]["logedit"].setText(fname)
        except Exception:
            traceback.print_exc()
            self.posterror("Failed to select file- please try again or manually enter full path to file in box below.")

    #Pull data, check to make sure it is valid before proceeding
    def checkdatainputs_editorinput(self):
        try:
            curtabstr = "Tab " + str(self.whatTab())
            
            #pulling data from inputs
            latstr = alltabdata[curtabstr]["tabwidgets"]["latedit"].text()
            lonstr = alltabdata[curtabstr]["tabwidgets"]["lonedit"].text()
            identifier = alltabdata[curtabstr]["tabwidgets"]["idedit"].text()
            profdatestr = alltabdata[curtabstr]["tabwidgets"]["dateedit"].text()
            timestr = alltabdata[curtabstr]["tabwidgets"]["timeedit"].text()
            logfile = alltabdata[curtabstr]["tabwidgets"]["logedit"].toPlainText()
            
            #check that logfile exists
            if not os.path.isfile(logfile):
                self.postwarning('Selected Data File Does Not Exist!')
                return
    
            if logfile[-4:].lower() == '.dta': #checks inputs if log file, otherwise doesnt need them
                
                #check and correct inputs
                try:
                    lat,lon,year,month,day,time,_,_ = self.parsestringinputs(latstr,lonstr,profdatestr,timestr,True,True)
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
                elif logfile[-4:].lower() == '.fin':
                    rawtemperature,rawdepth,day,month,year,time,lat,lon,_ = tfio.readfinfile(logfile)
                elif logfile[-5:].lower() == '.jjvv':
                    rawtemperature,rawdepth,day,month,year,time,lat,lon,identifier = tfio.readjjvvfile(logfile,round(year,-1))
                else:
                    QApplication.restoreOverrideCursor()
                    self.postwarning('Invalid Data File Format (must be .dta,.edf,.fin, or .jjvv)!')
                    return
            except Exception:
                traceback.print_exc()
                QApplication.restoreOverrideCursor()
                self.posterror('Failed to read selected data file!')
                return
        except Exception:
            traceback.print_exc()
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
            
            #getting climatology
            climotemps,climodepths,climotempfill,climodepthfill = oci.getclimatologyprofile(lat,lon,month,self.climodata)
            
            #running autoqc code
            sfc_correction = 0
            maxdepth = 100000
            temperature,depth = qc.autoqc(rawtemperature,rawdepth,sfc_correction,maxdepth,self.maxderiv,self.profres,self.checkforgaps)
            
            #comparing to climatology
            matchclimo,climobottomcutoff = oci.comparetoclimo(temperature,depth,climotemps,climodepths,climotempfill,climodepthfill)
            
            #pull ocean depth from ETOPO1 Grid-Registered Ice Sheet based global relief dataset 
            #Data source: NOAA-NGDC: https://www.ngdc.noaa.gov/mgg/global/global.html
            oceandepth,exportlat,exportlon,exportrelief = oci.getoceandepth(lat,lon,6,self.bathymetrydata)
            
            #limit profile depth by climatology cutoff, ocean depth cutoff
            maxdepth = np.ceil(np.max(depth))
            isbottomstrike = 0
            if self.useoceanbottom and np.isnan(oceandepth) == 0 and oceandepth <= maxdepth:
                maxdepth = oceandepth
                isbottomstrike = 1
            if self.useclimobottom and np.isnan(climobottomcutoff) == 0 and climobottomcutoff <= maxdepth:
                isbottomstrike = 1
                maxdepth = climobottomcutoff
            isbelowmaxdepth = np.less_equal(depth,maxdepth)
            temperature = temperature[isbelowmaxdepth]
            depth = depth[isbelowmaxdepth]
            
            #writing values to alltabs structure
            alltabdata[curtabstr]["profdata"] = {"temp_raw":rawtemperature,"depth_raw":rawdepth,
                      "temp_qc":temperature,"depth_qc":depth,"temp_plot":temperature,"depth_plot":depth,
                      "lat":lat,"lon":lon,"year":year,"month":month,"day":day,"time":time,"DTG":dtg,
                      "climotemp":climotemps,"climodepth":climodepths,"climotempfill":climotempfill,
                      "climodepthfill":climodepthfill,"matchclimo":matchclimo,"datasourcefile":logfile,
                      "ID":identifier,"oceandepth":oceandepth}
            
            alltabdata[curtabstr]["maxderiv"] = self.maxderiv
            
            #deleting old buttons and inputs
            for i in alltabdata[curtabstr]["tabwidgets"]:
                try:
                    alltabdata[curtabstr]["tabwidgets"][i].deleteLater()
                except:
                    alltabdata[curtabstr]["tabwidgets"][i] = 1 #bs variable- overwrites spacer item
                                
            if self.renametabstodtg:
                curtab = int(self.whatTab())
                self.tabWidget.setTabText(curtab,dtg)  
                
            #now delete widget entries
            del alltabdata[curtabstr]["tabwidgets"]
            QObjectCleanupHandler().add(alltabdata[curtabstr]["tablayout"])
            
            alltabdata[curtabstr]["tablayout2"] = QGridLayout()
            alltabdata[curtabstr]["tab"].setLayout(alltabdata[curtabstr]["tablayout2"]) 
            alltabdata[curtabstr]["tablayout2"].setSpacing(10)
            
            #ADDING FIGURES TO GRID LAYOUT (row column rowext colext)
            alltabdata[curtabstr]["ProfCanvas"] = FigureCanvas(alltabdata[curtabstr]["ProfFig"]) #self.canvas = FigureCanvas(self.figure)
            alltabdata[curtabstr]["tablayout2"].addWidget(alltabdata[curtabstr]["ProfCanvas"],0,0,12,1) #tablayout.addWidget(self.canvas)
            alltabdata[curtabstr]["LocCanvas"] = FigureCanvas(alltabdata[curtabstr]["LocFig"]) #self.canvas = FigureCanvas(self.figure)
            alltabdata[curtabstr]["tablayout2"].addWidget(alltabdata[curtabstr]["LocCanvas"],11,2,1,5) #tablayout.addWidget(self.canvas)
            
            #making profile processing result plots
            alltabdata[curtabstr]["ProfAx"] = alltabdata[curtabstr]["ProfFig"].add_axes([0.1, 0.05, 0.85, 0.9])
            alltabdata[curtabstr]["LocAx"] = alltabdata[curtabstr]["LocFig"].add_axes([0.1, 0.08, 0.85, 0.85])
            
            #adding toolbar
            alltabdata[curtabstr]["ProfToolbar"] = NavigationToolbar(alltabdata[curtabstr]["ProfCanvas"], self)
            alltabdata[curtabstr]["tablayout2"].addWidget(alltabdata[curtabstr]["ProfToolbar"],1,2,1,2)
            # alltabdata[curtabstr]["ProfToolbar"].setFixedWidth(300)
            
            #plot data
            alltabdata[curtabstr]["climohandle"] = tplot.makeprofileplot(alltabdata[curtabstr]["ProfAx"],rawtemperature,
                                                                         rawdepth,temperature,depth,climotempfill,
                                                                         climodepthfill,dtg,matchclimo)
            tplot.makelocationplot(alltabdata[curtabstr]["LocFig"],alltabdata[curtabstr]["LocAx"],lat,lon,dtg,exportlon,exportlat,exportrelief,6)
            
            #refresh plots on window
            alltabdata[curtabstr]["ProfCanvas"].draw()
            alltabdata[curtabstr]["LocCanvas"].draw()
            
            #Create widgets for UI populated with test example
            alltabdata[curtabstr]["tabwidgets"] = {}
            
            #first column: profile editor functions:
            alltabdata[curtabstr]["tabwidgets"]["toggleclimooverlay"] = QPushButton('Overlay Climatology') #1
            alltabdata[curtabstr]["tabwidgets"]["toggleclimooverlay"].setCheckable(True)
            alltabdata[curtabstr]["tabwidgets"]["toggleclimooverlay"].setChecked(True)
            alltabdata[curtabstr]["tabwidgets"]["toggleclimooverlay"].clicked.connect(self.toggleclimooverlay) 
            
            alltabdata[curtabstr]["tabwidgets"]["addpoint"] = QPushButton('Add Point') #2
            alltabdata[curtabstr]["tabwidgets"]["addpoint"].clicked.connect(self.addpoint)
            
            alltabdata[curtabstr]["tabwidgets"]["removepoint"] = QPushButton('Remove Point') #3
            alltabdata[curtabstr]["tabwidgets"]["removepoint"].clicked.connect(self.removepoint)        
            
            alltabdata[curtabstr]["tabwidgets"]["sfccorrectiontitle"] = QLabel('Isothermal Layer (m):') #4
            alltabdata[curtabstr]["tabwidgets"]["sfccorrection"] = QSpinBox() #5
            alltabdata[curtabstr]["tabwidgets"]["sfccorrection"].setRange(0, int(np.max(rawdepth+200)))
            alltabdata[curtabstr]["tabwidgets"]["sfccorrection"].setSingleStep(1)
            alltabdata[curtabstr]["tabwidgets"]["sfccorrection"].setValue(0)
            alltabdata[curtabstr]["tabwidgets"]["sfccorrection"].valueChanged.connect(self.applychanges)
            
            alltabdata[curtabstr]["tabwidgets"]["maxdepthtitle"] = QLabel('Maximum Depth (m):') #6
            alltabdata[curtabstr]["tabwidgets"]["maxdepth"] = QSpinBox() #7
            alltabdata[curtabstr]["tabwidgets"]["maxdepth"].setRange(0, int(np.round(np.max(rawdepth+200),-2)))
            alltabdata[curtabstr]["tabwidgets"]["maxdepth"].setSingleStep(1)
            alltabdata[curtabstr]["tabwidgets"]["maxdepth"].setValue(maxdepth)
            alltabdata[curtabstr]["tabwidgets"]["maxdepth"].valueChanged.connect(self.applychanges)
            
            alltabdata[curtabstr]["tabwidgets"]["depthdelaytitle"] = QLabel('Depth Delay (m):') #8
            alltabdata[curtabstr]["tabwidgets"]["depthdelay"] = QSpinBox() #9
            alltabdata[curtabstr]["tabwidgets"]["depthdelay"].setRange(0, int(np.round(np.max(rawdepth+200),-2)))
            alltabdata[curtabstr]["tabwidgets"]["depthdelay"].setSingleStep(1)
            alltabdata[curtabstr]["tabwidgets"]["depthdelay"].setValue(0)
            alltabdata[curtabstr]["tabwidgets"]["depthdelay"].valueChanged.connect(self.applychanges)

            alltabdata[curtabstr]["tabwidgets"]["rerunqc"] = QPushButton('Re-QC Profile (Reset)') #12
            alltabdata[curtabstr]["tabwidgets"]["rerunqc"].clicked.connect(self.rerunqc)    
            
            
            #Second column: profile information
            if lon >= 0: #prepping coordinate string
                ewhem = ' \xB0E'
            else:
                ewhem = ' \xB0W'
            if lat >= 0:
                nshem = ' \xB0N'
            else:
                nshem = ' \xB0S'
            proftxt = ('Profile Data: ' + '\n'  # profile data 
                       + str(abs(round(lon,3))) + ewhem + ', ' + str(abs(round(lat,3))) + nshem + '\n'
                       + 'Ocean Depth: ' + str(np.round(oceandepth,1)) + ' m' + '\n'
                       + 'QC Profile Depth: ' + str(int(maxdepth)) + ' m' + '\n'
                       + 'QC SFC Correction: ' + str(sfc_correction) + ' m' + '\n'
                       + 'QC Depth Delay: ' + str(0) + ' m' + '\n'
                       + '# Datapoints: ' + str(len(temperature)) )
            alltabdata[curtabstr]["tabwidgets"]["proftxt"] = QLabel(proftxt)#13
            

            alltabdata[curtabstr]["tabwidgets"]["isbottomstrike"] = QCheckBox('Bottom Strike?') #14
            if isbottomstrike == 1:
                alltabdata[curtabstr]["tabwidgets"]["isbottomstrike"].setChecked(True)
            else:
                alltabdata[curtabstr]["tabwidgets"]["isbottomstrike"].setChecked(False)
            
            alltabdata[curtabstr]["tabwidgets"]["rcodetitle"] = QLabel('Profile Quality:') #15
            alltabdata[curtabstr]["tabwidgets"]["rcode"] = QComboBox() #16
            alltabdata[curtabstr]["tabwidgets"]["rcode"].addItem("Good Profile")
            alltabdata[curtabstr]["tabwidgets"]["rcode"].addItem("No Signal")
            alltabdata[curtabstr]["tabwidgets"]["rcode"].addItem("Spotty/Intermittent")
            alltabdata[curtabstr]["tabwidgets"]["rcode"].addItem("Hung Probe/Early Start")
            alltabdata[curtabstr]["tabwidgets"]["rcode"].addItem("Isothermal")
            alltabdata[curtabstr]["tabwidgets"]["rcode"].addItem("Late Start")
            alltabdata[curtabstr]["tabwidgets"]["rcode"].addItem("Slow Falling")
            alltabdata[curtabstr]["tabwidgets"]["rcode"].addItem("Bottom Strike")
            alltabdata[curtabstr]["tabwidgets"]["rcode"].addItem("Climatology Mismatch")
            alltabdata[curtabstr]["tabwidgets"]["rcode"].addItem("Action Required/Reprocess")
            if matchclimo == 0: #setting value of combobox
                alltabdata[curtabstr]["tabwidgets"]["rcode"].setCurrentIndex(8)
            elif isbottomstrike == 1:
                alltabdata[curtabstr]["tabwidgets"]["rcode"].setCurrentIndex(7)
            else:
                alltabdata[curtabstr]["tabwidgets"]["rcode"].setCurrentIndex(0)
                
            #formatting widgets
            alltabdata[curtabstr]["tabwidgets"]["proftxt"].setAlignment(Qt.AlignCenter | Qt.AlignVCenter)
            alltabdata[curtabstr]["tabwidgets"]["rcodetitle"].setAlignment(Qt.AlignCenter | Qt.AlignVCenter)
            titlefont = QFont()
            titlefont.setBold(True)
            alltabdata[curtabstr]["tabwidgets"]["rcodetitle"].setFont(titlefont)
            alltabdata[curtabstr]["tabwidgets"]["depthdelaytitle"].setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            alltabdata[curtabstr]["tabwidgets"]["sfccorrectiontitle"].setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            alltabdata[curtabstr]["tabwidgets"]["maxdepthtitle"].setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            
            #should be 16 entries 
            Wsize = app.desktop().screenGeometry()
            widgetorder = ["toggleclimooverlay","addpoint","removepoint","sfccorrectiontitle","sfccorrection",
                           "maxdepthtitle","maxdepth","depthdelaytitle","depthdelay",
                           "rerunqc","proftxt","isbottomstrike","rcodetitle","rcode"]
            
            wrows     = [2,3,3,4,4,5,5,6,6,9,1,6,6,7]
            wcols     = [2,2,3,2,3,2,3,2,3,2,5,6,5,6]
            wrext     = [1,1,1,1,1,1,1,1,1,1,4,1,1,1]
            wcolext   = [2,1,1,1,1,1,1,1,1,2,2,1,1,1]
            
            #adding user inputs
            for i,r,c,re,ce in zip(widgetorder,wrows,wcols,wrext,wcolext):
                alltabdata[curtabstr]["tablayout2"].addWidget(alltabdata[curtabstr]["tabwidgets"][i],r,c,re,ce)

            #adjusting stretch factors for all rows/columns
            colstretch = [7,1,1,1,1,1,1,1,1]
            for col,cstr in zip(range(0,len(colstretch)),colstretch):
                alltabdata[curtabstr]["tablayout2"].setColumnStretch(col,cstr)
            rowstretch = [1,1,1,1,1,1,1,1,0,1,1,8]
            for row,rstr in zip(range(0,len(rowstretch)),rowstretch):
                alltabdata[curtabstr]["tablayout2"].setRowStretch(row,rstr)
            
            alltabdata[curtabstr]["tabtype"] = "ProfileEditor"
        except Exception:
            traceback.print_exc()
            self.posterror("Failed to build profile editor tab!")
        finally:
            QApplication.restoreOverrideCursor()
        
        
        
# =============================================================================
#         PROFILE EDITING FUNCTION CALLS
# =============================================================================

    #add point on profile
    def addpoint(self):
        try:
            QApplication.setOverrideCursor(Qt.CrossCursor)
            curtabstr = "Tab " + str(self.whatTab())
            alltabdata[curtabstr]["pt_type"] = 1
            alltabdata[curtabstr]["pt"] = alltabdata[curtabstr]["ProfCanvas"].mpl_connect('button_release_event', self.on_release)
        except Exception:
            traceback.print_exc()
            self.posterror("Failed to add point")
            
    #remove point on profile
    def removepoint(self):
        try:
            QApplication.setOverrideCursor(Qt.CrossCursor)
            curtabstr = "Tab " + str(self.whatTab())
            alltabdata[curtabstr]["pt_type"] = 2
            alltabdata[curtabstr]["pt"] = alltabdata[curtabstr]["ProfCanvas"].mpl_connect('button_release_event', self.on_release)
        except Exception:
            traceback.print_exc()
            self.posterror("Failed to remove point")
            
    #update profile with selected point to add or remove
    def on_release(self,event):
        try:
            curtabstr = "Tab " + str(self.whatTab())
            
            xx = event.xdata #selected x and y points
            yy = event.ydata
            
            #retrieve and update values
            tempplot = alltabdata[curtabstr]["profdata"]["temp_qc"]
            depthplot = alltabdata[curtabstr]["profdata"]["depth_qc"]
            
            #depends on adding (from raw) or removing a point
            if alltabdata[curtabstr]["pt_type"] == 1:
                rawt = alltabdata[curtabstr]["profdata"]["temp_raw"]
                rawd = alltabdata[curtabstr]["profdata"]["depth_raw"]
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
                        for i in range(len(depthplot)):
                            if depthplot[i] > adddepth:
                                break
                        depthplot.insert(i,adddepth)
                        tempplot.insert(i,addtemp)
                        
                    
            elif alltabdata[curtabstr]["pt_type"] == 2:
                pt = np.argmin(abs(tempplot-xx)**2 + abs(depthplot-yy)**2)
                try: #if its an array
                    tempplot = np.delete(tempplot,pt)
                    depthplot = np.delete(depthplot,pt)
                except: #if its a list
                    tempplot.pop(pt)
                    depthplot.pop(pt)
                    
            #replace values in profile
            alltabdata[curtabstr]["profdata"]["depth_qc"] = depthplot
            alltabdata[curtabstr]["profdata"]["temp_qc"] = tempplot
            
            #new depth correction settings
            sfcdepth = alltabdata[curtabstr]["tabwidgets"]["sfccorrection"].value()
            maxdepth = alltabdata[curtabstr]["tabwidgets"]["maxdepth"].value()
            depthdelay = alltabdata[curtabstr]["tabwidgets"]["depthdelay"].value()

            if depthdelay > 0:  # shifitng entire profile up if necessary
                depthplot = depthplot - depthdelay
                ind = depthplot >= 0
                depthplot = depthplot[ind]
                tempplot = tempplot[ind]

            if sfcdepth > 0: #replacing surface temperatures
                sfctemp = np.interp(sfcdepth,depthplot,tempplot)
                ind = depthplot <= sfcdepth
                tempplot[ind] = sfctemp

            if maxdepth < np.max(depthplot):
                ind = depthplot <= maxdepth
                tempplot = tempplot[ind]
                depthplot = depthplot[ind]
                
            #replacing t/d profile values
            alltabdata[curtabstr]["profdata"]["temp_plot"] = tempplot
            alltabdata[curtabstr]["profdata"]["depth_plot"] = depthplot

            # Replace drop info
            lon = alltabdata[curtabstr]["profdata"]["lon"]
            lat = alltabdata[curtabstr]["profdata"]["lat"]
            oceandepth = alltabdata[curtabstr]["profdata"]["oceandepth"]
            if lon >= 0:  # prepping coordinate string
                ewhem = ' \xB0E'
            else:
                ewhem = ' \xB0W'
            if lat >= 0:
                nshem = ' \xB0N'
            else:
                nshem = ' \xB0S'
            proftxt = ('Profile Data: ' + '\n'  # profile data
                       + str(abs(round(lon, 3))) + ewhem + ', ' + str(abs(round(lat, 3))) + nshem + '\n'
                       + 'Ocean Depth: ' + str(np.round(oceandepth, 1)) + ' m' + '\n'
                       + 'QC Profile Depth: ' + str(int(maxdepth)) + ' m' + '\n'
                       + 'QC SFC Correction: ' + str(sfcdepth) + ' m' + '\n'
                       + 'QC Depth Delay: ' + str(depthdelay) + ' m' + '\n'
                       + '# Datapoints: ' + str(len(tempplot)))
            alltabdata[curtabstr]["tabwidgets"]["proftxt"].setText(proftxt)
            
            #redo plot, disconnect add event
            del alltabdata[curtabstr]["ProfAx"].lines[-1]
            alltabdata[curtabstr]["ProfAx"].plot(tempplot,depthplot,'r',linewidth=2,label='QC')
            alltabdata[curtabstr]["ProfCanvas"].mpl_disconnect(alltabdata[curtabstr]["pt"])
            alltabdata[curtabstr]["ProfCanvas"].draw()
            
            #delete current indices
            del alltabdata[curtabstr]["pt"], alltabdata[curtabstr]["pt_type"]
        except Exception:
            traceback.print_exc()
            self.posterror("Failed to select profile point!")
        finally:
            #restore cursor type
            QApplication.restoreOverrideCursor()
        
    #apply changes from sfc correction/max depth/depth delay spin boxes
    def applychanges(self):
        try:
            curtabstr = "Tab " + str(self.whatTab())
            #current t/d profile
            tempplot = alltabdata[curtabstr]["profdata"]["temp_qc"].copy()
            depthplot = alltabdata[curtabstr]["profdata"]["depth_qc"].copy()

            #new depth correction settings
            sfcdepth = alltabdata[curtabstr]["tabwidgets"]["sfccorrection"].value()
            maxdepth = alltabdata[curtabstr]["tabwidgets"]["maxdepth"].value()
            depthdelay = alltabdata[curtabstr]["tabwidgets"]["depthdelay"].value()

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
            alltabdata[curtabstr]["profdata"]["temp_plot"] = tempplot
            alltabdata[curtabstr]["profdata"]["depth_plot"] = depthplot

            #re-plotting
            del alltabdata[curtabstr]["ProfAx"].lines[-1]
            alltabdata[curtabstr]["ProfAx"].plot(tempplot,depthplot,'r',linewidth=2,label='QC')
            alltabdata[curtabstr]["ProfCanvas"].draw()

            #Replace drop info
            lon = alltabdata[curtabstr]["profdata"]["lon"]
            lat = alltabdata[curtabstr]["profdata"]["lat"]
            oceandepth = alltabdata[curtabstr]["profdata"]["oceandepth"]
            if lon >= 0: #prepping coordinate string
                ewhem = ' \xB0E'
            else:
                ewhem = ' \xB0W'
            if lat >= 0:
                nshem = ' \xB0N'
            else:
                nshem = ' \xB0S'
            proftxt = ('Profile Data: ' + '\n'  # profile data
                       + str(abs(round(lon, 3))) + ewhem + ', ' + str(abs(round(lat, 3))) + nshem + '\n'
                       + 'Ocean Depth: ' + str(np.round(oceandepth,1)) + ' m' + '\n'
                       + 'QC Profile Depth: ' + str(int(maxdepth)) + ' m' + '\n'
                       + 'QC SFC Correction: ' + str(sfcdepth) + ' m' + '\n'
                       + 'QC Depth Delay: ' + str(depthdelay) + ' m' + '\n'
                       + '# Datapoints: ' + str(len(tempplot)) )
            alltabdata[curtabstr]["tabwidgets"]["proftxt"].setText(proftxt)
        except Exception:
            traceback.print_exc()
            self.posterror("Failed to update profile!")
        
    def rerunqc(self):
        try:
            curtabstr = "Tab " + str(self.whatTab())
            
            #getting necessary data for QC from dictionary
            rawtemperature = alltabdata[curtabstr]["profdata"]["temp_raw"]
            rawdepth = alltabdata[curtabstr]["profdata"]["depth_raw"]
            climotemps = alltabdata[curtabstr]["profdata"]["climotemp"]
            climodepths = alltabdata[curtabstr]["profdata"]["climodepth"]
            climotempfill = alltabdata[curtabstr]["profdata"]["climotempfill"]
            climodepthfill = alltabdata[curtabstr]["profdata"]["climodepthfill"]
            oceandepth = alltabdata[curtabstr]["profdata"]["oceandepth"]
            
            #resetting depth correction data
            sfc_correction = 0
            maxdepth = 10000
            depthdelay = 0
            
            try:
                #running QC, comparing to climo
                temperature,depth = qc.autoqc(rawtemperature,rawdepth,sfc_correction,maxdepth,self.maxderiv,self.profres,self.checkforgaps)
                matchclimo,climobottomcutoff = oci.comparetoclimo(temperature,depth,climotemps,climodepths,climotempfill,climodepthfill)
            except Exception:
                temperature = depth = matchclimo = climobottomcutoff = 0
                traceback.print_exc()
                self.posterror("Error raised in automatic profile QC")
                
            #limit profile depth by climatology cutoff, ocean depth cutoff
            maxdepth = np.ceil(np.max(depth))
            isbottomstrike = 0
            if self.useoceanbottom and np.isnan(oceandepth) == 0 and oceandepth <= maxdepth:
                maxdepth = oceandepth
                isbottomstrike = 1
            if self.useclimobottom and np.isnan(climobottomcutoff) == 0 and climobottomcutoff <= maxdepth:
                isbottomstrike = 1
                maxdepth = climobottomcutoff
            isbelowmaxdepth = np.less_equal(depth,maxdepth)
            temperature = temperature[isbelowmaxdepth]
            depth = depth[isbelowmaxdepth]
            
            #writing values to alltabs structure: QC and prof temps, and matchclimo
            alltabdata[curtabstr]["profdata"]["depth_qc"] = depth
            alltabdata[curtabstr]["profdata"]["depth_plot"] = depth
            alltabdata[curtabstr]["profdata"]["temp_qc"] = temperature
            alltabdata[curtabstr]["profdata"]["temp_plot"] = temperature
            alltabdata[curtabstr]["profdata"]["matchclimo"] = matchclimo
            
            #resetting depth correction QSpinBoxes
            alltabdata[curtabstr]["tabwidgets"]["maxdepth"].setValue(maxdepth)
            alltabdata[curtabstr]["tabwidgets"]["depthdelay"].setValue(0)
            alltabdata[curtabstr]["tabwidgets"]["sfccorrection"].setValue(0)
            
            #adjusting bottom strike checkbox as necessary
            if isbottomstrike == 1:
                alltabdata[curtabstr]["tabwidgets"]["isbottomstrike"].setChecked(True)
            else:
                alltabdata[curtabstr]["tabwidgets"]["isbottomstrike"].setChecked(False)
            
            #re-plotting
            del alltabdata[curtabstr]["ProfAx"].lines[-1]
            alltabdata[curtabstr]["ProfAx"].plot(temperature,depth,'r',linewidth=2,label='QC')
            alltabdata[curtabstr]["ProfCanvas"].draw()
    
            #relabeling profile info
            lon = alltabdata[curtabstr]["profdata"]["lon"]
            lat = alltabdata[curtabstr]["profdata"]["lat"]
            #prepping coordinate string
            if lon >= 0:
                ewhem = ' \xB0E'
            else:
                ewhem = ' \xB0W'
            if lat >= 0:
                nshem = ' \xB0N'
            else:
                nshem = ' \xB0S'
            proftxt = ('Profile Data: ' + '\n' 
                       + str(abs(lon)) + ewhem + ', ' + str(abs(lat)) + nshem + '\n' 
                       + 'Ocean Depth: ' + str(np.round(oceandepth,1)) + ' m' + '\n'
                       + 'QC Profile Depth: ' + str(int(maxdepth)) + ' m' + '\n'
                       + 'QC SFC Correction: ' + str(sfc_correction) + ' m' + '\n'
                       + 'QC Depth Delay: ' + str(depthdelay) + ' m' + '\n'
                       + '# Datapoints: ' + str(len(temperature)) )
            alltabdata[curtabstr]["tabwidgets"]["proftxt"].setText(proftxt)
        except Exception:
            traceback.print_exc()
            self.posterror("Failed to Re-QC the profile")

    #toggle visibility of climatology profile
    def toggleclimooverlay(self,pressed):
        try:
            curtabstr = "Tab " + str(self.whatTab())
            if pressed:
                alltabdata[curtabstr]["climohandle"].set_visible(True)     
            else:
                alltabdata[curtabstr]["climohandle"].set_visible(False)
            alltabdata[curtabstr]["ProfCanvas"].draw()
        except Exception:
            traceback.print_exc()
            self.posterror("Failed to toggle climatology overlay")
        
        
        
        
# =============================================================================
#     TAB MANIPULATION OPTIONS, OTHER GENERAL FUNCTIONS
# =============================================================================

    #gets index of open tab in GUI
    def whatTab(self):
        currentIndex = self.tabWidget.currentIndex()
        return currentIndex
    
    #renames tab (only user-visible name, not alltabdata dict key)
    def renametab(self):
        try:
            curtab = int(self.whatTab())
            name, ok = QInputDialog.getText(self, 'Rename Current Tab', 'Enter new tab name:',QLineEdit.Normal,str(self.tabWidget.tabText(curtab)))
            if ok:
                self.tabWidget.setTabText(curtab,name)
        except Exception:
            traceback.print_exc()
            self.posterror("Failed to rename the current tab")
    
    #sets default color scheme for tabs
    def setnewtabcolor(self,tab):
        p = QPalette()
        gradient = QLinearGradient(0, 0, 0, 400)
        gradient.setColorAt(0.0, QColor(255,255,255))
        gradient.setColorAt(1.0, QColor(248, 248, 255))
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
                curtab = int(self.whatTab())
                curtabstr = "Tab " + str(curtab)
                
                #check to make sure there isn't a corresponding processor thread, close if there is
                if alltabdata[curtabstr]["tabtype"] == 'SignalProcessor_incomplete' or alltabdata[curtabstr]["tabtype"] == 'SignalProcessor_completed':
                    if alltabdata[curtabstr]["isprocessing"]:
                        reply = QMessageBox.question(self, 'Message',
                            "Closing this tab will terminate the current profile and discard the data. Continue?", QMessageBox.Yes | 
                            QMessageBox.No, QMessageBox.No)
                        if reply == QMessageBox.No:
                            return
                        else:
                            alltabdata[curtabstr]["processor"].abort()
                
                self.tabWidget.removeTab(curtab)
                
                #removing current tab data from the alltabdata dict, renaming all higher# tabs
                alltabdata.pop("Tab "+str(curtab))
                for i in alltabdata:
                    if int(i[-1]) > curtab:
                        ctab = int(i[-1])
                        alltabdata["Tab "+str(ctab-1)] = alltabdata.pop("Tab "+str(ctab))
        except Exception:
            traceback.print_exc()
            self.posterror("Failed to close the current tab")
                
    #save data in open tab        
    def savedataincurtab(self):
        try:
            #getting directory to save files from QFileDialog
            outdir = str(QFileDialog.getExistingDirectory(self, "Select Directory to Save File(s)"))
            if outdir == '':
                QApplication.restoreOverrideCursor()
                return False
        except:
            self.posterror("Error raised in directory selection")
            return

        try:
            QApplication.setOverrideCursor(Qt.WaitCursor)
            
            #pulling all relevant data
            curtabstr = "Tab " + str(self.whatTab())
            
            if alltabdata[curtabstr]["tabtype"] == "ProfileEditor":
                try:
                    rawtemperature = alltabdata[curtabstr]["profdata"]["temp_raw"]
                    rawdepth = alltabdata[curtabstr]["profdata"]["depth_raw"]
                    climotempfill = alltabdata[curtabstr]["profdata"]["climotempfill"]
                    climodepthfill = alltabdata[curtabstr]["profdata"]["climodepthfill"]
                    temperature = alltabdata[curtabstr]["profdata"]["temp_plot"]
                    depth = alltabdata[curtabstr]["profdata"]["depth_plot"]
                    day = alltabdata[curtabstr]["profdata"]["day"]
                    month = alltabdata[curtabstr]["profdata"]["month"]
                    year = alltabdata[curtabstr]["profdata"]["year"]
                    time = alltabdata[curtabstr]["profdata"]["time"]
                    lat = alltabdata[curtabstr]["profdata"]["lat"]
                    lon = alltabdata[curtabstr]["profdata"]["lon"]
                    identifier = alltabdata[curtabstr]["profdata"]["ID"]
                    num = 99 #placeholder- dont have drop number here currently!!
                    
                    dtg = str(year) + str(month).zfill(2) + str(day).zfill(2) + str(time).zfill(4)
                    curtab = int(self.whatTab())
                    filename = self.tabWidget.tabText(curtab)
                    
                    if self.comparetoclimo:
                        matchclimo = alltabdata[curtabstr]["profdata"]["matchclimo"]
                    else:
                        matchclimo = 1

                except:
                    self.posterror("Failed to retrieve profile information")
                    QApplication.restoreOverrideCursor()
                    return False

                if self.savefin:
                    try:
                        depth1m = np.arange(0,np.floor(depth[-1]))
                        temperature1m = np.interp(depth1m,depth,temperature)
                        tfio.writefinfile(outdir + slash + filename + '.fin',temperature1m,depth1m,day,month,year,time,lat,lon,num)
                    except Exception:
                        traceback.print_exc()
                        self.posterror("Failed to save FIN file")
                if self.savejjvv:
                    isbtmstrike = alltabdata[curtabstr]["tabwidgets"]["isbottomstrike"].isChecked()
                    try:
                        tfio.writejjvvfile(outdir + slash + filename + '.jjvv',temperature,depth,day,month,year,time,lat,lon,identifier,isbtmstrike)
                    except Exception:
                        traceback.print_exc()
                        self.posterror("Failed to save JJVV file")
                if self.savebufr:
                    try:
                        tfio.writebufrfile(outdir + slash + filename + '.bufr',temperature,depth,year,month,day,time,lon,lat,identifier,self.originatingcenter,False,b'\0')
                    except Exception:
                        traceback.print_exc()
                        self.posterror("Failed to save BUFR file")
                if self.saveprof:
                    try:
                        fig1 = plt.figure()
                        fig1.clear()
                        ax1 = fig1.add_axes([0.1,0.1,0.85,0.85])
                        climohandle = tplot.makeprofileplot(ax1,rawtemperature,rawdepth,temperature,depth,climotempfill,climodepthfill,dtg,matchclimo)
                        if self.overlayclimo == 0:
                            climohandle.set_visible(False)
                        fig1.savefig(outdir + slash + filename + '_prof.png',format='png')
                    except Exception:
                        traceback.print_exc()
                        self.posterror("Failed to save profile image")
                    finally:
                        plt.close('fig1')

                if self.saveloc:
                    try:
                        fig2 = plt.figure()
                        fig2.clear()
                        ax2 = fig2.add_axes([0.1,0.1,0.85,0.85])
                        _,exportlat,exportlon,exportrelief = oci.getoceandepth(lat,lon,6,self.bathymetrydata)
                        tplot.makelocationplot(fig2,ax2,lat,lon,dtg,exportlon,exportlat,exportrelief,6)
                        fig2.savefig(outdir + slash + filename + '_loc.png',format='png')
                    except Exception:
                        traceback.print_exc()
                        self.posterror("Failed to save location image")
                    finally:
                        plt.close('fig2')

                    
            elif alltabdata[curtabstr]["tabtype"] == "SignalProcessor_completed":
                
                try:
                    #pulling prof data
                    rawtemperature = alltabdata[curtabstr]["rawdata"]["temperature"]
                    rawdepth = alltabdata[curtabstr]["rawdata"]["depth"]
                    frequency = alltabdata[curtabstr]["rawdata"]["frequency"]
                    timefromstart = alltabdata[curtabstr]["rawdata"]["time"]

                    #pulling profile metadata if necessary
                    try:
                        lat = alltabdata[curtabstr]["rawdata"]["lat"]
                        lon = alltabdata[curtabstr]["rawdata"]["lon"]
                        year = alltabdata[curtabstr]["rawdata"]["year"]
                        month = alltabdata[curtabstr]["rawdata"]["month"]
                        day = alltabdata[curtabstr]["rawdata"]["day"]
                        time = alltabdata[curtabstr]["rawdata"]["droptime"]
                        hour = alltabdata[curtabstr]["rawdata"]["hour"]
                        minute = alltabdata[curtabstr]["rawdata"]["minute"]
                    except:
                        # pulling data from inputs
                        latstr = alltabdata[curtabstr]["tabwidgets"]["latedit"].text()
                        lonstr = alltabdata[curtabstr]["tabwidgets"]["lonedit"].text()
                        profdatestr = alltabdata[curtabstr]["tabwidgets"]["dateedit"].text()
                        timestr = alltabdata[curtabstr]["tabwidgets"]["timeedit"].text()

                        #only checks validity of necessary data
                        try:
                            if self.saveedf:
                                lat, lon, year, month, day, time, hour, minute = self.parsestringinputs(latstr, lonstr,profdatestr,timestr, True, True)
                            else:
                                _, _, year, month, day, time, hour, minute = self.parsestringinputs(latstr, lonstr,profdatestr,timestr, False, True)
                        except:
                            self.postwarning("Failed to save raw data files!")
                            QApplication.restoreOverrideCursor()
                            return False

                    #date and time strings for LOG file
                    initdatestr = str(year) + '/' + str(month).zfill(2) + '/' + str(day).zfill(2)
                    inittimestr = str(hour).zfill(2) + ':' + str(minute).zfill(2) + ':00'
                    
                    filename = str(year) + str(month).zfill(2) + str(day).zfill(2) + str(time).zfill(4)

                except Exception:
                    traceback.print_exc()
                    self.posterror("Failed to pull raw profile data")
                    QApplication.restoreOverrideCursor()
                    return False
                
                if self.savelog:
                    try:
                        tfio.writelogfile(outdir + slash + filename + '.DTA',initdatestr,inittimestr,timefromstart,rawdepth,frequency,rawtemperature)
                    except Exception:
                        traceback.print_exc()
                        self.posterror("Failed to save LOG file")
                if self.saveedf:
                    try:
                        tfio.writeedffile(outdir + slash + filename + '.edf',rawtemperature,rawdepth,year,month,day,hour,minute,0,lat,lon)
                    except Exception:
                        traceback.print_exc()
                        self.posterror("Failed to save EDF file")

                if self.savewav:
                    try:
                        oldfile = 'tempwav_' + str(alltabdata[curtabstr]["tabnum"]) + '.WAV'
                        newfile = outdir + slash + filename + '.WAV'

                        if os.path.exists(newfile):
                            os.remove(newfile)

                        shutil.copy(oldfile,newfile)
                    except Exception:
                        traceback.print_exc()
                        self.posterror("Failed to save WAV file")

                if self.savesig:
                    try:
                        oldfile = 'sigdata_' + str(alltabdata[curtabstr]["tabnum"]) + '.txt'
                        newfile = outdir + slash + filename + '.sigdata'

                        if os.path.exists(newfile):
                            os.remove(newfile)

                        shutil.copy(oldfile, newfile)
                    except Exception:
                        traceback.print_exc()

            else:
                self.postwarning('You must process the profile before attempting to save data!')
                
        except Exception:
            traceback.print_exc() #if something else in the file save code broke
            self.posterror("Filed to save files")
            QApplication.restoreOverrideCursor()
            return False
        finally:
            QApplication.restoreOverrideCursor()
            return True
        
    #warning message
    def postwarning(self,warningtext):
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Warning)
        msg.setText(warningtext)
        msg.setWindowTitle("Warning")
        msg.setStandardButtons(QMessageBox.Ok)
        msg.exec_()
        
    #error message
    def posterror(self,errortext):
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Critical)
        msg.setText(errortext)
        msg.setWindowTitle("Error")
        msg.setStandardButtons(QMessageBox.Ok)
        msg.exec_()
    
    #warning message with options (Okay or Cancel)
    def postwarning_option(self,warningtext):
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

            event.accept()
            #delete all temporary wav files
            allfilesanddirs = os.listdir()
            for cfile in allfilesanddirs:
                if len(cfile) >= 5:
                    cfilestart = cfile[:4]
                    cfileext = cfile[-3:]
                    if cfilestart.lower() == 'temp' and cfileext.lower() == 'wav':
                        os.remove(cfile)
                    elif cfilestart.lower() == 'sigd' and cfileext.lower() == 'txt':
                        os.remove(cfile)
        else:
            event.ignore() 
    
    
# =============================================================================
#    PARSE STRING INPUTS/CHECK VALIDITY WHEN TRANSITIONING TO PROFILE EDITOR
# =============================================================================
    def parsestringinputs(self,latstr,lonstr,profdatestr,timestr,checkcoords,checktime):
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

                if year < 1000:
                    self.postwarning('Invalid Year Entered (< 1000 AD)!')
                    return

                #making sure the profile is within 12 hours and not in the future, warning if otherwise
                curtime = timemodule.gmtime()
                deltat = dt.datetime(curtime[0],curtime[1],curtime[2],curtime[3],curtime[4],curtime[5]) - dt.datetime(year,month,day,hour,minute,0)
                option = ''
                if self.dtgwarn:
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
                
            return lat,lon,year,month,day,time,hour,minute
        except Exception:
            traceback.print_exc()
            self.posterror("Unspecified error in reading profile information!")
            return

    
# =============================================================================
# EXECUTE PROGRAM
# =============================================================================
if __name__ == '__main__':  
    app = QApplication(sys.argv)
    ex = RunProgram()
    sys.exit(app.exec_())
    
    