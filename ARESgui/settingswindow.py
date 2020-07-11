# =============================================================================
#     Code: settingswindow.py
#     Author: ENS Casey R. Densmore, 25AUG2019
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
#     Purpose: Creates window for advanced ARES settings, handles signals/slots
#       with main event loop in order to update settings. All settings are stored within
#       a dictionary (both in this script and in main.py) to improve readability and 
#       simplify function calls.
#
#   Settings Tabs:
#       o Signal Processor Settings: Contains all settings for the signal processor
#           style tabs in the main GUI, including FFT thresholds and auto population
#           preferences. Initialized with makeprocessorsettingstab()
#       o Profile Editor Tab: Contains all settings for the profile editor tab
#           including profile resolution/inflection point threshold, considerations
#           for climatology, NOAA bathymetry data and VHF interference auto-detection.
#           Initialized with makeprofileeditorsettingstab()
#       o GPS Communication: Allows the user to select a COM port to listen for GPS
#           data and auto-populate lat/lon data if a valid port is selected. Also
#           allows the user to test COM port connection/get current position.
#
#   Signals:
#       o exported(all,of,the,settings): Passes the updated settings back to the main loop
#       o closed(True): Notifies the main loop that the settings window was closed,
#           so it will open a new window (vice bringing the current window to front)
#           if the "Preferences" option is selected again
#
#   Functions outside of RunSettings class:
#       o setdefaultsettings: returns a dictionary containing default ARES settings 
#           hard-coded in the function (settings optimized based on research with AXBT data)
#       o readsettings(file): returns a dictionary containing ARES settings stored in file
#       o writesettings(settingdict,file): writes settings in dictionary to specified file
#       
# =============================================================================



# =============================================================================
#   CALL NECESSARY MODULES HERE
# =============================================================================
from traceback import print_exc as trace_error
import numpy as np
from os import remove, path

from PyQt5.QtWidgets import (QMainWindow, QLabel, QSpinBox, QDoubleSpinBox, QCheckBox, QPushButton,
    QMessageBox, QWidget, QTabWidget, QGridLayout, QSlider, QComboBox, QLineEdit)
from PyQt5.QtCore import Qt, pyqtSlot, pyqtSignal, QObject
from PyQt5.QtGui import QIcon, QColor, QPalette, QBrush, QLinearGradient, QFont

import qclib.GPS_COM_interaction as gps
import qclib.VHFsignalprocessor as vsp #for temperature conversion for flims

from platform import system as cursys
if cursys() == 'Windows':
    from ctypes import windll



#   DEFINE CLASS FOR SETTINGS (TO BE CALLED IN THREAD)
class RunSettings(QMainWindow):

    # =============================================================================
    #   INITIALIZE WINDOW, INTERFACE
    # =============================================================================
    def __init__(self,settingsdict):
        super().__init__()

        try:
            self.initUI()

            self.signals = SettingsSignals()

            #records current settings received from main loop
            self.settingsdict = settingsdict
            
            #defining constants for labels called from multiple points
            self.defineconstants()

            #building window/tabs
            self.buildcentertable()
            self.makeprocessorsettingstab()  # processor settings
            self.maketzconvertsettingstab() #temperature/depth conversion eqn settings
            self.makeprofileeditorsettingstab() #profile editor tab
            self.makegpssettingstab() #add GPS settings

        except Exception:
            trace_error()
            self.posterror("Failed to initialize the settings menu.")

            
            
    def initUI(self):

        # setting title/icon, background color
        self.setWindowTitle('AXBT Realtime Editing System Settings')
        self.setWindowIcon(QIcon('qclib/dropicon.png'))
        p = self.palette()
        p.setColor(self.backgroundRole(), QColor(255, 255, 255))
        self.setPalette(p)

        myappid = 'ARES_v1.0'  # arbitrary string
        if cursys() == 'Windows':
            windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

        # changing font size
        font = QFont()
        font.setPointSize(11)
        font.setFamily("Arial")
        self.setFont(font)

        # prepping to include tabs
        self.mainWidget = QWidget()
        self.setCentralWidget(self.mainWidget)
        self.mainLayout = QGridLayout()
        self.mainWidget.setLayout(self.mainLayout)
        self.tabWidget = QTabWidget()

        #adding widgets to main tab, setting spacing
        self.mainLayout.addWidget(self.tabWidget,1,1,1,5)
        self.applysettings = QPushButton('Apply Changes')
        self.applysettings.clicked.connect(self.applychanges)
        self.resetchanges = QPushButton('Reset Defaults')
        self.resetchanges.clicked.connect(self.resetdefaults)
        self.mainLayout.addWidget(self.applysettings,2,2,1,1)
        self.mainLayout.addWidget(self.resetchanges,2,4,1,1)
        colstretches = [3,1,1,1,1,1,3]
        rowstretches = [3,1,1,3]
        for i,r in enumerate(rowstretches):
            self.mainLayout.setRowStretch(i,r)
        for i,c in enumerate(colstretches):
            self.mainLayout.setColumnStretch(i,c)
        self.show()
        
    
    def defineconstants(self):
        #defining constants for labels called from multiple points
        self.label_fftwindow = "FFT Window (s): "
        self.label_minsiglev = "Minimum Signal Level (dB): "
        self.label_minsigrat = "Minimum Signal Ratio (%): "
        self.label_trigsiglev = "Trigger Signal Level (dB): "
        self.label_trigsigrat = "Trigger Signal Ratio (%): "
        
        
        
    # =============================================================================
    #   FUNCTIONS TO UPDATE/EXPORT/RESET SETTINGS
    # =============================================================================
    def applychanges(self):
        self.updatepreferences()
        self.signals.exported.emit(self.settingsdict)

        

    def resetdefaults(self):
        
        #pull default settings, but preserve selected serial port (for GPS) and list of available ports
        comport = self.settingsdict["comport"] #selected port
        comports = self.settingsdict["comports"] #list of available ports
        comportdetails = self.settingsdict["comportdetails"] #list of available port details
        self.settingsdict = setdefaultsettings()
        self.settingsdict["comport"] = comport
        self.settingsdict["comports"] = comports
        self.settingsdict["comportdetails"] = comportdetails
        
        
        self.processortabwidgets["autodtg"].setChecked(self.settingsdict["autodtg"])
        self.processortabwidgets["autolocation"].setChecked(self.settingsdict["autolocation"])
        self.processortabwidgets["autoID"].setChecked(self.settingsdict["autoid"])

        self.processortabwidgets["savelog"].setChecked(self.settingsdict["savelog"])
        self.processortabwidgets["saveedf"].setChecked(self.settingsdict["saveedf"])
        self.processortabwidgets["savewav"].setChecked(self.settingsdict["savewav"])
        self.processortabwidgets["savesig"].setChecked(self.settingsdict["savesig"])

        self.processortabwidgets["dtgwarn"].setChecked(self.settingsdict["dtgwarn"])
        self.processortabwidgets["renametab"].setChecked(self.settingsdict["renametabstodtg"])
        self.processortabwidgets["autosave"].setChecked(self.settingsdict["autosave"])

        self.processortabwidgets["fftwindowlabel"].setText(self.label_fftwindow + str(self.settingsdict["fftwindow"]))  # 15
        self.processortabwidgets["fftwindow"].setValue(int(self.settingsdict["fftwindow"] * 100))

        self.processortabwidgets["fftsiglevlabel"].setText(self.label_minsiglev + str(np.round(self.settingsdict["minsiglev"], 2)).ljust(4, '0'))  # 17
        self.processortabwidgets["fftsiglev"].setValue(int(self.settingsdict["minsiglev"]*10))

        self.processortabwidgets["fftratiolabel"].setText(self.label_minsigrat + str(np.round(self.settingsdict["minfftratio"] * 100)))  # 19
        self.processortabwidgets["fftratio"].setValue(int(self.settingsdict["minfftratio"] * 100))

        self.processortabwidgets["triggersiglevlabel"].setText(
            self.label_trigsiglev + str(np.round(self.settingsdict["triggersiglev"], 2)).ljust(4, '0'))  # 17
        self.processortabwidgets["triggersiglev"].setValue(int(self.settingsdict["triggersiglev"]*10))

        self.processortabwidgets["triggerratiolabel"].setText(
            self.label_trigsigrat + str(np.round(self.settingsdict["triggerfftratio"] * 100)))  # 19
        self.processortabwidgets["triggerratio"].setValue(int(self.settingsdict["triggerfftratio"] * 100))
        
        tc = self.settingsdict["tcoeff"]
        self.tzconverttabwidgets["F2Tb0"].setText(str(tc[0]))
        self.tzconverttabwidgets["F2Tb1"].setText(str(tc[1]))
        self.tzconverttabwidgets["F2Tb2"].setText(str(tc[2]))
        self.tzconverttabwidgets["F2Tb3"].setText(str(tc[3]))
        self.updateF2Teqn()
        
        zc = self.settingsdict["zcoeff"]
        self.tzconverttabwidgets["t2zb0"].setText(str(zc[0]))
        self.tzconverttabwidgets["t2zb1"].setText(str(zc[1]))
        self.tzconverttabwidgets["t2zb2"].setText(str(zc[2]))
        self.tzconverttabwidgets["t2zb3"].setText(str(zc[3]))
        self.updatet2zeqn()
        
        flims = self.settingsdict["flims"]
        self.tzconverttabwidgets["flow"].setValue(flims[0])
        self.tzconverttabwidgets["fhigh"].setValue(flims[1])
        self.updateflims()

        self.profeditortabwidgets["useclimobottom"].setChecked(self.settingsdict["useclimobottom"])
        self.profeditortabwidgets["comparetoclimo"].setChecked(self.settingsdict["comparetoclimo"])
        self.profeditortabwidgets["overlayclimo"].setChecked(self.settingsdict["overlayclimo"])

        self.profeditortabwidgets["savefin"].setChecked(self.settingsdict["savefin"])
        self.profeditortabwidgets["savejjvv"].setChecked(self.settingsdict["savejjvv"])
        self.profeditortabwidgets["savebufr"].setChecked(self.settingsdict["savebufr"])
        self.profeditortabwidgets["saveprof"].setChecked(self.settingsdict["saveprof"])
        self.profeditortabwidgets["saveloc"].setChecked(self.settingsdict["saveloc"])

        self.profeditortabwidgets["useoceanbottom"].setChecked(self.settingsdict["useoceanbottom"])
        self.profeditortabwidgets["checkforgaps"].setChecked(self.settingsdict["checkforgaps"])
        
        self.profeditortabwidgets["profres"].setValue(self.settingsdict["profres"])
        self.profeditortabwidgets["smoothlev"].setValue(self.settingsdict["smoothlev"])
        self.profeditortabwidgets["maxstdev"].setValue(self.settingsdict["maxstdev"])

        self.profeditortabwidgets["originatingcenter"].setValue(self.settingsdict["originatingcenter"])
        self.updateoriginatingcenter()
        


    def updatepreferences(self): #records current configuration before exporting to main loop

        self.settingsdict["autodtg"] = self.processortabwidgets["autodtg"].isChecked()
        self.settingsdict["autolocation"] = self.processortabwidgets["autolocation"].isChecked()
        self.settingsdict["autoid"] = self.processortabwidgets["autoID"].isChecked()

        self.settingsdict["savelog"] = self.processortabwidgets["savelog"].isChecked()
        self.settingsdict["saveedf"] = self.processortabwidgets["saveedf"].isChecked()
        self.settingsdict["savewav"] = self.processortabwidgets["savewav"].isChecked()
        self.settingsdict["savesig"] = self.processortabwidgets["savesig"].isChecked()

        self.settingsdict["dtgwarn"] = self.processortabwidgets["dtgwarn"].isChecked()
        self.settingsdict["renametabstodtg"] = self.processortabwidgets["renametab"].isChecked()
        self.settingsdict["autosave"] = self.processortabwidgets["autosave"].isChecked()

        self.settingsdict["fftwindow"] = float(self.processortabwidgets["fftwindow"].value())/100
        self.settingsdict["minsiglev"] = float(self.processortabwidgets["fftsiglev"].value())/10
        self.settingsdict["minfftratio"] = float(self.processortabwidgets["fftratio"].value())/100

        self.settingsdict["triggersiglev"] = float(self.processortabwidgets["triggersiglev"].value())/10
        self.settingsdict["triggerfftratio"] = float(self.processortabwidgets["triggerratio"].value())/100
        
        #T/Z coefficients and frequency ranges are recorded on every update to their respective fields

        self.settingsdict["platformid"] = self.processortabwidgets["IDedit"].text()

        self.settingsdict["useclimobottom"] = self.profeditortabwidgets["useclimobottom"].isChecked()
        self.settingsdict["comparetoclimo"] =  self.profeditortabwidgets["comparetoclimo"].isChecked()
        self.settingsdict["overlayclimo"] = self.profeditortabwidgets["overlayclimo"].isChecked()

        self.settingsdict["savefin"] = self.profeditortabwidgets["savefin"].isChecked()
        self.settingsdict["savejjvv"] = self.profeditortabwidgets["savejjvv"].isChecked()
        self.settingsdict["savebufr"] = self.profeditortabwidgets["savebufr"].isChecked()
        self.settingsdict["saveprof"] = self.profeditortabwidgets["saveprof"].isChecked()
        self.settingsdict["saveloc"] = self.profeditortabwidgets["saveloc"].isChecked()

        self.settingsdict["useoceanbottom"] = self.profeditortabwidgets["useoceanbottom"].isChecked()
        self.settingsdict["checkforgaps"] = self.profeditortabwidgets["checkforgaps"].isChecked()

        self.settingsdict["profres"] = self.profeditortabwidgets["profres"].value()
        self.settingsdict["smoothlev"] = self.profeditortabwidgets["smoothlev"].value()
        self.settingsdict["maxstdev"] = self.profeditortabwidgets["maxstdev"].value()

        self.updateoriginatingcenter()
        self.updateportandbaud()
        
    
    

    # =============================================================================
    #     SIGNAL PROCESSOR TAB AND INPUTS HERE
    # =============================================================================
    def makeprocessorsettingstab(self):
        try:

            self.processortab = QWidget()
            self.processortablayout = QGridLayout()
            self.setnewtabcolor(self.processortab)

            self.processortablayout.setSpacing(10)

            self.tabWidget.addTab(self.processortab,'Data Acquisition System Settings')
            self.tabWidget.setCurrentIndex(0)

            # and add new buttons and other widgets
            self.processortabwidgets = {}

            # making widgets
            self.processortabwidgets["autopopulatetitle"] = QLabel('Autopopulate Drop Entries:') #1
            self.processortabwidgets["autodtg"] = QCheckBox('Autopopulate DTG (UTC)') #2
            self.processortabwidgets["autodtg"].setChecked(self.settingsdict["autodtg"])
            self.processortabwidgets["autolocation"] = QCheckBox('Autopopulate Location') #3
            self.processortabwidgets["autolocation"].setChecked(self.settingsdict["autolocation"])
            self.processortabwidgets["autoID"] = QCheckBox('Autopopulate Platform Identifier') #4
            self.processortabwidgets["autoID"].setChecked(self.settingsdict["autoid"])
            self.processortabwidgets["IDlabel"] = QLabel('Platform Identifier:') #5
            self.processortabwidgets["IDedit"] = QLineEdit(self.settingsdict["platformid"]) #6

            self.processortabwidgets["filesavetypes"] = QLabel('Filetypes to save:       ') #7
            self.processortabwidgets["savelog"] = QCheckBox('LOG File') #8
            self.processortabwidgets["savelog"].setChecked(self.settingsdict["savelog"])
            self.processortabwidgets["saveedf"] = QCheckBox('EDF File') #9
            self.processortabwidgets["saveedf"].setChecked(self.settingsdict["saveedf"])
            self.processortabwidgets["savewav"] = QCheckBox('WAV File') #10
            self.processortabwidgets["savewav"].setChecked(self.settingsdict["savewav"])
            self.processortabwidgets["savesig"] = QCheckBox('Signal Data') #11
            self.processortabwidgets["savesig"].setChecked(self.settingsdict["savesig"])

            self.processortabwidgets["dtgwarn"] = QCheckBox('Warn if DTG is not within past 12 hours') #12
            self.processortabwidgets["dtgwarn"].setChecked(self.settingsdict["dtgwarn"])
            self.processortabwidgets["renametab"] = QCheckBox('Auto-rename tab to DTG on transition to profile editing mode') #13
            self.processortabwidgets["renametab"].setChecked(self.settingsdict["renametabstodtg"])
            self.processortabwidgets["autosave"] = QCheckBox('Autosave raw data files when transitioning to profile editor mode') #14
            self.processortabwidgets["autosave"].setChecked(self.settingsdict["autosave"])

            self.processortabwidgets["fftwindowlabel"] = QLabel(self.label_fftwindow +str(self.settingsdict["fftwindow"]).ljust(4,'0')) #15
            self.processortabwidgets["fftwindow"] = QSlider(Qt.Horizontal) #16
            self.processortabwidgets["fftwindow"].setValue(int(self.settingsdict["fftwindow"] * 100))
            self.processortabwidgets["fftwindow"].setMinimum(10)
            self.processortabwidgets["fftwindow"].setMaximum(100)
            self.processortabwidgets["fftwindow"].valueChanged[int].connect(self.changefftwindow)

            self.processortabwidgets["fftsiglevlabel"] = QLabel(self.label_minsiglev + str(np.round(self.settingsdict["minsiglev"],2)).ljust(4,'0'))  # 17
            self.processortabwidgets["fftsiglev"] = QSlider(Qt.Horizontal)  # 18
            self.processortabwidgets["fftsiglev"].setMinimum(400)
            self.processortabwidgets["fftsiglev"].setMaximum(900)
            self.processortabwidgets["fftsiglev"].setValue(int(self.settingsdict["minsiglev"] * 10))
            self.processortabwidgets["fftsiglev"].valueChanged[int].connect(self.changefftsiglev)

            self.processortabwidgets["fftratiolabel"] = QLabel(self.label_minsigrat + str(np.round(self.settingsdict["minfftratio"]*100)).ljust(4,'0'))  # 19
            self.processortabwidgets["fftratio"] = QSlider(Qt.Horizontal)  # 20
            self.processortabwidgets["fftratio"].setValue(int(self.settingsdict["minfftratio"] * 100))
            self.processortabwidgets["fftratio"].setMinimum(0)
            self.processortabwidgets["fftratio"].setMaximum(100)
            self.processortabwidgets["fftratio"].valueChanged[int].connect(self.changefftratio)

            self.processortabwidgets["triggersiglevlabel"] = QLabel(
                self.label_trigsiglev + str(np.round(self.settingsdict["triggersiglev"], 2)).ljust(4, '0'))  # 17
            self.processortabwidgets["triggersiglev"] = QSlider(Qt.Horizontal)  # 18
            self.processortabwidgets["triggersiglev"].setMinimum(400)
            self.processortabwidgets["triggersiglev"].setMaximum(900)
            self.processortabwidgets["triggersiglev"].setValue(int(self.settingsdict["triggersiglev"] * 10))
            self.processortabwidgets["triggersiglev"].valueChanged[int].connect(self.changetriggersiglev)

            self.processortabwidgets["triggerratiolabel"] = QLabel(
                self.label_trigsigrat + str(np.round(self.settingsdict["triggerfftratio"] * 100)).ljust(4, '0'))  # 19
            self.processortabwidgets["triggerratio"] = QSlider(Qt.Horizontal)  # 20
            self.processortabwidgets["triggerratio"].setValue(int(self.settingsdict["triggerfftratio"] * 100))
            self.processortabwidgets["triggerratio"].setMinimum(0)
            self.processortabwidgets["triggerratio"].setMaximum(100)
            self.processortabwidgets["triggerratio"].valueChanged[int].connect(self.changetriggerratio)

            # formatting widgets
            self.processortabwidgets["IDlabel"].setAlignment(Qt.AlignCenter | Qt.AlignVCenter)

            # should be 24 entries
            widgetorder = ["autopopulatetitle", "autodtg", "autolocation", "autoID", "IDlabel",
                           "IDedit", "filesavetypes", "savelog", "saveedf","savewav", "savesig",
                           "dtgwarn", "renametab", "autosave", "fftwindowlabel", "fftwindow",
                           "fftsiglevlabel", "fftsiglev", "fftratiolabel","fftratio", "triggersiglevlabel",
                           "triggersiglev","triggerratiolabel","triggerratio"]

            wcols = [1, 1, 1, 1, 1, 2, 4, 4, 4, 4, 4, 1, 1, 1, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5]
            wrows = [1, 2, 3, 4, 5, 5, 1, 2, 3, 4, 5, 7, 8, 9, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

            wrext = [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]
            wcolext = [2, 2, 2, 2, 1, 1, 1, 1, 1, 1, 1, 4, 4, 4, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]

            # adding user inputs
            for i, r, c, re, ce in zip(widgetorder, wrows, wcols, wrext, wcolext):
                self.processortablayout.addWidget(self.processortabwidgets[i], r, c, re, ce)

            # Applying spacing preferences to grid layout
            self.processortablayout.setColumnStretch(0, 0)
            self.processortablayout.setColumnStretch(1, 1)
            self.processortablayout.setColumnStretch(2, 1)
            self.processortablayout.setColumnStretch(3, 2)
            self.processortablayout.setColumnStretch(4, 3)
            for i in range(0,12):
                self.processortablayout.setRowStretch(i, 1)
            self.processortablayout.setRowStretch(11, 4)

            # applying the current layout for the tab
            self.processortab.setLayout(self.processortablayout)

        except Exception:
            trace_error()
            self.posterror("Failed to build new processor tab")
            
            
            
            
            
    # =============================================================================
    #     TEMPERATURE-DEPTH CONVERSION EQNS + LIMITATIONS HERE
    # =============================================================================
    def maketzconvertsettingstab(self):
        try:

            self.tzconverttab = QWidget()
            self.tzconverttablayout = QGridLayout()
            self.setnewtabcolor(self.tzconverttab)

            self.tzconverttablayout.setSpacing(10)

            self.tabWidget.addTab(self.tzconverttab,'Temperature/Depth Conversion')
            self.tabWidget.setCurrentIndex(0)

            # and add new buttons and other widgets
            self.tzconverttabwidgets = {}

            # making widgets
            tc = self.settingsdict["tcoeff"]
            self.tzconverttabwidgets["F2Tlabel"] = QLabel('Frequency to Temperature Conversion:') #1
            self.tzconverttabwidgets["F2Teqn"] = QLabel(f"T = {tc[0]} + {tc[1]}*f + {tc[2]}*f<sup>2</sup> + {tc[3]}*f<sup>3</sup>") #2
            self.tzconverttabwidgets["F2Tb0"] = QLineEdit(str(tc[0])) #3
            self.tzconverttabwidgets["F2Tb0"].textChanged.connect(self.updateF2Teqn)
            self.tzconverttabwidgets["F2Tb1"] = QLineEdit(str(tc[1])) #4
            self.tzconverttabwidgets["F2Tb1"].textChanged.connect(self.updateF2Teqn)
            self.tzconverttabwidgets["F2Tb2"] = QLineEdit(str(tc[2])) #5
            self.tzconverttabwidgets["F2Tb2"].textChanged.connect(self.updateF2Teqn)
            self.tzconverttabwidgets["F2Tb3"] = QLineEdit(str(tc[3])) #6
            self.tzconverttabwidgets["F2Tb3"].textChanged.connect(self.updateF2Teqn)
            self.tzconverttabwidgets["F2Ts0"] = QLabel(" + ") #7
            self.tzconverttabwidgets["F2Ts1"] = QLabel("* f + ") #8
            self.tzconverttabwidgets["F2Ts2"] = QLabel("* f<sup>2</sup> + ") #9
            self.tzconverttabwidgets["F2Ts3"] = QLabel("* f<sup>3</sup> ") #10
            
            zc = self.settingsdict["zcoeff"]
            self.tzconverttabwidgets["t2zlabel"] = QLabel('Time Elapsed to Depth Conversion:') #11
            self.tzconverttabwidgets["t2zeqn"] = QLabel(f"z = {zc[0]} + {zc[1]}*t + {zc[2]}*t<sup>2</sup> + {zc[3]}*t<sup>3</sup>") #12
            self.tzconverttabwidgets["t2zb0"] = QLineEdit(str(zc[0])) #13
            self.tzconverttabwidgets["t2zb0"].textChanged.connect(self.updatet2zeqn)
            self.tzconverttabwidgets["t2zb1"] = QLineEdit(str(zc[1])) #14
            self.tzconverttabwidgets["t2zb1"].textChanged.connect(self.updatet2zeqn)
            self.tzconverttabwidgets["t2zb2"] = QLineEdit(str(zc[2])) #15
            self.tzconverttabwidgets["t2zb2"].textChanged.connect(self.updatet2zeqn)
            self.tzconverttabwidgets["t2zb3"] = QLineEdit(str(zc[3])) #16
            self.tzconverttabwidgets["t2zb3"].textChanged.connect(self.updatet2zeqn)
            self.tzconverttabwidgets["t2zs0"] = QLabel(" + ") #17
            self.tzconverttabwidgets["t2zs1"] = QLabel("* t + ") #18
            self.tzconverttabwidgets["t2zs2"] = QLabel("* t<sup>2</sup> + ") #19
            self.tzconverttabwidgets["t2zs3"] = QLabel("* t<sup>3</sup> ") #20
            
            flims = self.settingsdict["flims"]
            self.tzconverttabwidgets["flimlabel"] = QLabel('Valid Frequency/Temperature Limits:') #21
            self.tzconverttabwidgets["flowlabel"] = QLabel('Minimum Valid Frequency (Hz):') #22
            self.tzconverttabwidgets["fhighlabel"] = QLabel('Maximum Valid Frequency (Hz):') #23
            
            self.tzconverttabwidgets["flow"] = QSpinBox() #24
            self.tzconverttabwidgets["flow"].setMinimum(0)
            self.tzconverttabwidgets["flow"].setMaximum(5000)
            self.tzconverttabwidgets["flow"].setSingleStep(1)
            self.tzconverttabwidgets["flow"].setValue(flims[0])
            self.tzconverttabwidgets["flow"].valueChanged.connect(self.updateflims)
            self.tzconverttabwidgets["fhigh"] = QSpinBox() #25
            self.tzconverttabwidgets["fhigh"].setMinimum(0)
            self.tzconverttabwidgets["fhigh"].setMaximum(5000)
            self.tzconverttabwidgets["fhigh"].setSingleStep(1)
            self.tzconverttabwidgets["fhigh"].setValue(flims[1])
            self.tzconverttabwidgets["fhigh"].valueChanged.connect(self.updateflims)
            
            self.tzconverttabwidgets["Tlowlabel"]  = QLabel(f"Minimum Valid Temperature (\xB0C): {vsp.btconvert(flims[0],tc):5.2f}") #26
            self.tzconverttabwidgets["Thighlabel"] = QLabel(f"Maximum Valid Temperature (\xB0C): {vsp.btconvert(flims[1],tc):5.2f}") #27
            
            
            # formatting widgets 
            self.tzconverttabwidgets["F2Tlabel"].setAlignment(Qt.AlignCenter | Qt.AlignVCenter)
            self.tzconverttabwidgets["t2zlabel"].setAlignment(Qt.AlignCenter | Qt.AlignVCenter)
            self.tzconverttabwidgets["flimlabel"].setAlignment(Qt.AlignCenter | Qt.AlignVCenter)
            self.tzconverttabwidgets["flowlabel"].setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.tzconverttabwidgets["fhighlabel"].setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            

            # should be XX entries
            widgetorder = ["F2Tlabel","F2Teqn","F2Tb0","F2Tb1","F2Tb2","F2Tb3","F2Ts0","F2Ts1","F2Ts2","F2Ts3","t2zlabel", "t2zeqn", "t2zb0","t2zb1", "t2zb2","t2zb3", "t2zs0", "t2zs1", "t2zs2", "t2zs3", "flimlabel", "flowlabel", "fhighlabel", "flow", "fhigh", "Tlowlabel", "Thighlabel"]

            wcols = [1,1,1,1,1,1,2,2,2,2,4,4,4,4,4,4,5,5,5,5,1,0,0,2,2,4,4]
            wrows = [1,2,3,4,5,6,3,4,5,6,1,2,3,4,5,6,3,4,5,6,9,10,11,10,11,10,11]

            wrext = [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1]
            wcolext = [2,2,1,1,1,1,1,1,1,1,2,2,1,1,1,1,1,1,1,1,5,2,2,1,1,2,2]

            # adding user inputs
            for i, r, c, re, ce in zip(widgetorder, wrows, wcols, wrext, wcolext):
                self.tzconverttablayout.addWidget(self.tzconverttabwidgets[i], r, c, re, ce)

            # Applying spacing preferences to grid layout
            colstretches = [1,2,1,1,2,1,1]
            for i,s in enumerate(colstretches):
                self.tzconverttablayout.setColumnStretch(i, s)
            for i in range(12):
                self.tzconverttablayout.setRowStretch(i, 1)
                
            # applying the current layout for the tab
            self.tzconverttab.setLayout(self.tzconverttablayout)

        except Exception:
            trace_error()
            self.posterror("Failed to build new temperature/depth conversion settings tab")
            
            
            
            
            
            
    def updateF2Teqn(self):
        
        try: #only updates if the values are numeric
            tc = [float(self.tzconverttabwidgets["F2Tb0"].text()), float(self.tzconverttabwidgets["F2Tb1"].text()), float(self.tzconverttabwidgets["F2Tb2"].text()), float(self.tzconverttabwidgets["F2Tb3"].text())]
            self.tzconverttabwidgets["F2Teqn"].setText(f"T = {tc[0]} + {tc[1]}*f + {tc[2]}*f<sup>2</sup> + {tc[3]}*f<sup>3</sup>")
            self.settingsdict["tcoeff"] = tc
        except ValueError:
            pass

       
    def updatet2zeqn(self):
        
        try: #only updates if the values are numeric
            zc = [float(self.tzconverttabwidgets["t2zb0"].text()), float(self.tzconverttabwidgets["t2zb1"].text()), float(self.tzconverttabwidgets["t2zb2"].text()), float(self.tzconverttabwidgets["t2zb3"].text())]
            self.tzconverttabwidgets["t2zeqn"].setText(f"z = {zc[0]} + {zc[1]}*t + {zc[2]}*t<sup>2</sup> + {zc[3]}*t<sup>3</sup>")
            self.settingsdict["zcoeff"] = zc
        except ValueError:
            pass
            
            
    def updateflims(self):
        
        flims = [self.tzconverttabwidgets["flow"].value(), self.tzconverttabwidgets["fhigh"].value()]
        tc = self.settingsdict["tcoeff"]
        
        if flims[1] > flims[0]: #valid min frequency must be less than valid max frequency
            self.tzconverttabwidgets["Tlowlabel"].setText(f"Minimum Valid Temperature (\xB0C): {vsp.btconvert(flims[0],tc):5.2f}")
            self.tzconverttabwidgets["Thighlabel"].setText(f"Maximum Valid Temperature (\xB0C): {vsp.btconvert(flims[1],tc):5.2f}")
            
            self.settingsdict["flims"] = flims
            
        #else: #reset previous setting
        #    self.postwarning("Minimum valid frequency must be less than maximum valid frequency!")
        #    self.tzconverttabwidgets["flow"].setValue(self.settingsdict["flims"][0])
        #    self.tzconverttabwidgets["fhigh"].setValue(self.settingsdict["flims"][1])
            
            
        
        
            
            

    # =============================================================================
    #     GPS COM PORT SELECTION TAB AND INPUTS HERE
    # =============================================================================

    def makegpssettingstab(self):
        try:

            self.gpstab = QWidget()
            self.gpstablayout = QGridLayout()
            self.setnewtabcolor(self.gpstab)

            self.gpstablayout.setSpacing(10)

            self.tabWidget.addTab(self.gpstab, 'GPS COM Selection')
            self.tabWidget.setCurrentIndex(0)

            # and add new buttons and other widgets
            self.gpstabwidgets = {}

            # making widgets
            self.gpstabwidgets["updateports"] = QPushButton("Update COM Port List") # 1
            self.gpstabwidgets["updateports"].clicked.connect(self.updategpslist)

            # self.gpstabwidgets["refreshgpsdata"] = QPushButton("Refresh GPS Info") # 2
            # self.gpstabwidgets["refreshgpsdata"].clicked.connect(self.refreshgpsdata)

            self.gpstabwidgets["gpsdate"] = QLabel("Date/Time: ") # 3
            self.gpstabwidgets["gpslat"] = QLabel("Latitude: ") # 4
            self.gpstabwidgets["gpslon"] = QLabel("Longitude: ") # 5
            
            #creating drop-down selection menu for available serial connections
            self.gpstabwidgets["comporttitle"] = QLabel('Available Serial Connections:')  # 6
            self.gpstabwidgets["comport"] = QComboBox()  # 7
            self.gpstabwidgets["comport"].clear()
            self.gpstabwidgets["comport"].addItem('No Serial Connection Selected')
            for cport in self.settingsdict["comportdetails"]: #adding previously detected ports
                self.gpstabwidgets["comport"].addItem(cport)
                
            #includes comport from settings on list if it isn't 'None selected'
            if self.settingsdict["comport"] != 'n':
                #if the listed receiver is connected, keep setting and set dropdown box to select that receiver
                if self.settingsdict["comport"] in self.settingsdict["comports"]: 
                    self.gpstabwidgets["comport"].setCurrentIndex(self.settingsdict["comports"].index(self.settingsdict["comport"])+1)
                #if the listed receiver is not connected, set setting and current index to N/A
                else:
                    self.settingsdict["comport"] = 'n'    
            #if no receiver is selected, set current index to top
            else:
                self.gpstabwidgets["comport"].setCurrentIndex(0)
                
                
            self.gpstabwidgets["baudtitle"] = QLabel('GPS BAUD Rate:')  # 6
            self.gpstabwidgets["baudrate"] = QComboBox()  # 7
            self.gpstabwidgets["baudrate"].clear()
            
            self.baudrates = [110, 300, 600, 1200, 2400, 4800, 9600, 14400, 19200, 38400, 57600, 115200, 128000, 256000]
            for rate in self.baudrates: #adding previously detected ports
                self.gpstabwidgets["baudrate"].addItem(str(rate))
            if not self.settingsdict["gpsbaud"] in self.baudrates:
                self.settingsdict["gpsbaud"] = 4800
            self.gpstabwidgets["baudrate"].setCurrentIndex(self.baudrates.index(self.settingsdict["gpsbaud"]))
            
            #connect comport change to function
            self.gpstabwidgets["comport"].currentIndexChanged.connect(self.updateportandbaud)
            self.gpstabwidgets["baudrate"].currentIndexChanged.connect(self.updateportandbaud)
            
            # should be 7 entries
            widgetorder = ["updateports", "gpsdate", "gpslat", "gpslon","comporttitle","comport", "baudtitle", "baudrate"]

            wcols = [1, 1, 1, 1, 1, 1, 1, 2]
            wrows = [1, 6, 7, 8, 2, 3, 4, 4]
            wrext = [1, 1, 1, 1, 1, 1, 1, 1]
            wcolext = [1, 1, 1, 1, 1, 2, 1, 1]

            # adding user inputs
            for i, r, c, re, ce in zip(widgetorder, wrows, wcols, wrext, wcolext):
                self.gpstablayout.addWidget(self.gpstabwidgets[i], r, c, re, ce)

            # Applying spacing preferences to grid layout
            self.gpstablayout.setRowStretch(0,4)
            self.gpstablayout.setRowStretch(5,4)
            self.gpstablayout.setRowStretch(9,4)
            self.gpstablayout.setColumnStretch(0,4)
            self.gpstablayout.setColumnStretch(3,4)

            # making the current layout for the tab
            self.gpstab.setLayout(self.gpstablayout)

        except Exception:
            trace_error()
            self.posterror("Failed to build new GPS tab")

            
            
    #updating the selected COM port and baud rate from the menu
    def updateportandbaud(self):
        curcomnum = self.gpstabwidgets["comport"].currentIndex()
        if curcomnum > 0:
            self.settingsdict["comport"] = self.settingsdict["comports"][curcomnum - 1]
        else:
            self.settingsdict["comport"] = 'n'
            
        self.settingsdict['gpsbaud'] = self.baudrates[self.gpstabwidgets["baudrate"].currentIndex()]
            
        self.signals.updateGPS.emit(self.settingsdict["comport"], self.settingsdict["gpsbaud"])
            
            

    #refreshing the list of available COM ports
    def updategpslist(self):
        self.gpstabwidgets["comport"].clear()
        self.gpstabwidgets["comport"].addItem('No COM Port Selected')
        self.settingsdict["comports"],self.settingsdict["comportdetails"] = gps.listcomports()
        for curport in self.settingsdict["comportdetails"]:
            self.gpstabwidgets["comport"].addItem(curport)
            
            

    #attempt to refresh GPS data with currently selected COM port
    def refreshgpsdata(self, lat, lon, curdate, isgood):
        if isgood:
            if lat > 0:
                latsign = 'N'
            else:
                latsign = 'S'
            if lon > 0:
                lonsign = 'E'
            else:
                lonsign = 'W'
            self.gpstabwidgets["gpsdate"].setText("Date/Time: {} UTC".format(curdate))
            self.gpstabwidgets["gpslat"].setText("Latitude: {}{}".format(abs(round(lat,3)),latsign))
            self.gpstabwidgets["gpslon"].setText("Longitude: {}{}".format(abs(round(lon,3)),lonsign))
            
        else:
            self.gpstabwidgets["gpsdate"].setText("Date/Time:")
            self.gpstabwidgets["gpslat"].setText("Latitude:")
            self.gpstabwidgets["gpslon"].setText("Longitude:")
            
    
    #receive warning message about GPS connection     
    def postGPSissue(self,flag):
        if flag == 1:
            self.posterror("GPS request timed out!")
        elif flag == 2:
            self.posterror("Unable to communicate with specified COM port!")
    


    # =============================================================================
    #         PROFILE EDITOR TAB
    # =============================================================================
    def makeprofileeditorsettingstab(self):
        try:

            self.profeditortab = QWidget()
            self.profeditortablayout = QGridLayout()
            self.setnewtabcolor(self.profeditortab)

            self.profeditortablayout.setSpacing(10)

            self.tabWidget.addTab(self.profeditortab, 'Profile Editor Settings')
            self.tabWidget.setCurrentIndex(0)

            # and add new buttons and other widgets
            self.profeditortabwidgets = {}

            # making widgets
            self.profeditortabwidgets["climotitle"] = QLabel('Climatology Options:')  # 1
            self.profeditortabwidgets["useclimobottom"] = QCheckBox('Use climatology to detect bottom strikes')  # 2
            self.profeditortabwidgets["useclimobottom"].setChecked(self.settingsdict["useclimobottom"])
            self.profeditortabwidgets["comparetoclimo"] = QCheckBox('Autocompare profile to climatology')  # 3
            self.profeditortabwidgets["comparetoclimo"].setChecked(self.settingsdict["comparetoclimo"])
            self.profeditortabwidgets["overlayclimo"] = QCheckBox('Overlay climatology in saved plots')  # 4
            self.profeditortabwidgets["overlayclimo"].setChecked(self.settingsdict["overlayclimo"])

            self.profeditortabwidgets["filesavetypes"] = QLabel('Filetypes to save:     ')  # 5
            self.profeditortabwidgets["savefin"] = QCheckBox('FIN File')  # 6
            self.profeditortabwidgets["savefin"].setChecked(self.settingsdict["savefin"])
            self.profeditortabwidgets["savejjvv"] = QCheckBox('JJVV File')  # 7
            self.profeditortabwidgets["savejjvv"].setChecked(self.settingsdict["savejjvv"])
            self.profeditortabwidgets["savebufr"] = QCheckBox('BUFR File')  # 8
            self.profeditortabwidgets["savebufr"].setChecked(self.settingsdict["savebufr"])
            self.profeditortabwidgets["saveprof"] = QCheckBox('Profile PNG')  # 9
            self.profeditortabwidgets["saveprof"].setChecked(self.settingsdict["saveprof"])
            self.profeditortabwidgets["saveloc"] = QCheckBox('Location PNG')  # 10
            self.profeditortabwidgets["saveloc"].setChecked(self.settingsdict["saveloc"])

            self.profeditortabwidgets["useoceanbottom"] = QCheckBox(
                'ID bottom strikes with NOAA ETOPO1 bathymetry data')  # 11
            self.profeditortabwidgets["useoceanbottom"].setChecked(self.settingsdict["useoceanbottom"])
            self.profeditortabwidgets["checkforgaps"] = QCheckBox('ID false starts due to VHF interference')  # 12
            self.profeditortabwidgets["checkforgaps"].setChecked(self.settingsdict["checkforgaps"])

            self.settingsdict["profres"] = float(self.settingsdict["profres"])
            if self.settingsdict["profres"]%0.25 != 0:
                self.settingsdict["profres"] = np.round(self.settingsdict["profres"]*4)/4
            self.profeditortabwidgets["profreslabel"] = QLabel("Minimum Profile Resolution (m)")  # 13
            self.profeditortabwidgets["profres"] = QDoubleSpinBox()  # 14
            self.profeditortabwidgets["profres"].setMinimum(0)
            self.profeditortabwidgets["profres"].setMaximum(50)
            self.profeditortabwidgets["profres"].setSingleStep(0.25)
            self.profeditortabwidgets["profres"].setValue(self.settingsdict["profres"])

            if self.settingsdict["smoothlev"]%0.25 != 0:
                self.settingsdict["smoothlev"] = np.round(self.settingsdict["smoothlev"]*4)/4
            self.profeditortabwidgets["smoothlevlabel"] = QLabel("Smoothing Window (m)")  # 15
            self.profeditortabwidgets["smoothlev"] = QDoubleSpinBox()  # 16
            self.profeditortabwidgets["smoothlev"].setMinimum(0)
            self.profeditortabwidgets["smoothlev"].setMaximum(100)
            self.profeditortabwidgets["smoothlev"].setSingleStep(0.25)
            self.profeditortabwidgets["smoothlev"].setValue(self.settingsdict["smoothlev"])

            if self.settingsdict["maxstdev"]%0.1 != 0:
                self.settingsdict["maxstdev"] = np.round(self.settingsdict["maxstdev"]*10)/10
            self.profeditortabwidgets["maxstdevlabel"] = QLabel("Despiking Coefficient")  # 17
            self.profeditortabwidgets["maxstdev"] = QDoubleSpinBox()  # 18
            self.profeditortabwidgets["maxstdev"].setMinimum(0)
            self.profeditortabwidgets["maxstdev"].setMaximum(2)
            self.profeditortabwidgets["maxstdev"].setSingleStep(0.05)
            self.profeditortabwidgets["maxstdev"].setValue(self.settingsdict["maxstdev"])


            self.profeditortabwidgets["originatingcentername"] = QLabel("")  # 19
            self.profeditortabwidgets["originatingcenter"] = QSpinBox()  # 20
            self.profeditortabwidgets["originatingcenter"].setMinimum(0)
            self.profeditortabwidgets["originatingcenter"].setMaximum(255)
            self.profeditortabwidgets["originatingcenter"].setSingleStep(1)
            self.profeditortabwidgets["originatingcenter"].setValue(self.settingsdict["originatingcenter"])
            self.profeditortabwidgets["originatingcenter"].valueChanged[int].connect(self.updateoriginatingcenter)
            
            try:
                curcentername = self.allcenters[str(self.settingsdict["originatingcenter"]).zfill(3)]
            except:
                curcentername = "Center ID not recognized!"
            self.profeditortabwidgets["originatingcentername"].setText("Center "+str(self.settingsdict["originatingcenter"]).zfill(3)+": "+curcentername)

            # should be 18 entries
            widgetorder = ["climotitle", "useclimobottom", "comparetoclimo", "overlayclimo", "filesavetypes", "savefin",
                           "savejjvv", "savebufr", "saveprof", "saveloc", "useoceanbottom", "checkforgaps", "profreslabel",
                           "profres","smoothlevlabel", "smoothlev", "maxstdevlabel", "maxstdev", "originatingcentername","originatingcenter"]

            wcols = [1, 1, 1, 1, 4, 4, 4, 4, 4, 4, 1, 1, 5, 5, 5, 5, 5, 5, 1, 1]
            wrows = [1, 2, 3, 4, 1, 2, 3, 4, 5, 6, 8, 9, 2, 3, 5, 6, 9, 10, 11, 12]
            wrext = [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]
            wcolext = [2, 2, 2, 2, 1, 1, 1, 1, 1, 1, 4, 4, 1, 1, 1, 1, 1, 1, 4, 4]

            # adding user inputs
            for i, r, c, re, ce in zip(widgetorder, wrows, wcols, wrext, wcolext):
                self.profeditortablayout.addWidget(self.profeditortabwidgets[i], r, c, re, ce)

            # Applying spacing preferences to grid layout
            self.profeditortablayout.setColumnStretch(0, 0)
            self.profeditortablayout.setColumnStretch(1, 1)
            self.profeditortablayout.setColumnStretch(2, 1)
            self.profeditortablayout.setColumnStretch(3, 2)
            self.profeditortablayout.setColumnStretch(4, 3)
            for i in range(0, 14):
                self.profeditortablayout.setRowStretch(i, 1)
            self.profeditortablayout.setRowStretch(12, 4)

            # making the current layout for the tab
            self.profeditortab.setLayout(self.profeditortablayout)

        except Exception:
            trace_error()
            self.posterror("Failed to build profile editor tab!")

    
    
    
    # =============================================================================
    #         UPDATE BUFR FORMAT ORIGINATING CENTER ACCORDING TO TABLE
    # =============================================================================
    def updateoriginatingcenter(self):
        self.settingsdict["originatingcenter"] = int(self.profeditortabwidgets["originatingcenter"].value())
        ctrkey = str(self.settingsdict["originatingcenter"]).zfill(3)
        if ctrkey in self.allcenters:
            curcentername = self.allcenters[ctrkey]
        else:
            curcentername = self.allcenters["xxx"]
        self.profeditortabwidgets["originatingcentername"].setText("Center " + ctrkey + ": " + curcentername)
        
        

    #lookup table for originating centers
    def buildcentertable(self):
        self.allcenters = {"000":"       WMO Secretariat               ",
                           "007":"       US NWS: NCEP                  ",
                           "008":"       US NWS: NWSTG                 ",
                           "009":"       US NWS: Other                 ",
                           "051":"       Miami (RSMC)                  ",
                           "052":"       Miami (RSMC) NHC              ",
                           "053":"       MSC Monitoring                ",
                           "054":"       Montreal (RSMC)               ",
                           "055":"       San Francisco                 ",
                           "056":"       ARINC Center                  ",
                           "057":"       USAF: Global Weather Central  ",
                           "058":"       USN: FNMOC                    ",
                           "059":"       NOAA FSL                      ",
                           "060":"       NCAR                          ",
                           "061":"       Service ARGOS- Landover       ",
                           "062":"       USN: NAVO                     ",
                           "063":"       IRI: Climate and Society      ",
                           "xxx":"       Center ID not recognized!     "}


                           


    # =============================================================================
    #         SLIDER CHANGE FUNCTION CALLS
    # =============================================================================
    def changefftwindow(self, value):
        self.settingsdict["fftwindow"] = float(value) / 100
        self.processortabwidgets["fftwindowlabel"].setText(self.label_fftwindow +str(self.settingsdict["fftwindow"]).ljust(4,'0'))
        

    def changefftsiglev(self, value):
        self.settingsdict["minsiglev"] = float(value) / 10
        self.processortabwidgets["fftsiglevlabel"].setText(self.label_minsiglev + str(np.round(self.settingsdict["minsiglev"],2)).ljust(4,'0'))

        
    def changefftratio(self, value):
        self.settingsdict["minfftratio"] = float(value) / 100
        self.processortabwidgets["fftratiolabel"].setText(self.label_minsigrat + str(np.round(self.settingsdict["minfftratio"]*100)).ljust(4,'0'))
        

    def changetriggersiglev(self, value):
        self.settingsdict["triggersiglev"] = float(value) / 10
        self.processortabwidgets["triggersiglevlabel"].setText(self.label_trigsiglev + str(np.round(self.settingsdict["triggersiglev"],2)).ljust(4,'0'))

        
    def changetriggerratio(self, value):
        self.settingsdict["triggerfftratio"] = float(value) / 100
        self.processortabwidgets["triggerratiolabel"].setText(self.label_trigsigrat + str(np.round(self.settingsdict["triggerfftratio"]*100)).ljust(4,'0'))
        

    
        

    # =============================================================================
    #     TAB MANIPULATION OPTIONS, OTHER GENERAL FUNCTIONS
    # =============================================================================
    def whatTab(self):
        currentIndex = self.tabWidget.currentIndex()
        return currentIndex
        

    @staticmethod
    def setnewtabcolor(tab):
        p = QPalette()
        gradient = QLinearGradient(0, 0, 0, 400)
        gradient.setColorAt(0.0, QColor(255, 255, 255))
        gradient.setColorAt(1.0, QColor(248, 248, 255))
        p.setBrush(QPalette.Window, QBrush(gradient))
        tab.setAutoFillBackground(True)
        tab.setPalette(p)
        

    # add warning message on exit
    def closeEvent(self, event):
        event.accept()
        self.signals.closed.emit(True)
        

    @staticmethod
    def posterror(errortext):
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Critical)
        msg.setText(errortext)
        msg.setWindowTitle("Error")
        msg.setStandardButtons(QMessageBox.Ok)
        msg.exec_()

        
        

# SIGNAL SETUP HERE
class SettingsSignals(QObject):
    exported = pyqtSignal(dict)
    closed = pyqtSignal(bool)
    updateGPS = pyqtSignal(str,int)
    
    

#Default settings for program
def setdefaultsettings():
    
    settingsdict = {}
    
    # processor preferences
    settingsdict["autodtg"] = True  # auto determine profile date/time as system date/time on clicking "START"
    settingsdict["autolocation"] = True #auto determine location with GPS
    settingsdict["autoid"] = True #autopopulate platform ID
    settingsdict["platformid"] = 'AFNNN'
    settingsdict["savelog"] = True
    settingsdict["saveedf"] = False
    settingsdict["savewav"] = True
    settingsdict["savesig"] = True
    settingsdict["dtgwarn"] = True  # warn user if entered dtg is more than 12 hours old or after current system time (in future)
    settingsdict["renametabstodtg"] = True  # auto rename tab to dtg when loading profile editor
    settingsdict["autosave"] = False  # automatically save raw data before opening profile editor (otherwise brings up prompt asking if want to save)
    settingsdict["fftwindow"] = 0.3  # window to run FFT (in seconds)
    settingsdict["minfftratio"] = 0.42  # minimum signal to noise ratio to ID data
    settingsdict["minsiglev"] = 58.  # minimum total signal level to receive data

    settingsdict["triggerfftratio"] = 0.8  # minimum signal to noise ratio to ID data
    settingsdict["triggersiglev"] = 70.  # minimum total signal level to receive data
    
    settingsdict["tcoeff"] = [-40,0.02778,0,0] #temperature conversion coefficients
    settingsdict["zcoeff"] = [0,1.524,0,0] #depth conversion coefficients
    settingsdict["flims"] = [1300, 2800] #valid frequency range limits

    #profeditorpreferences
    settingsdict["useclimobottom"] = True  # use climatology to ID bottom strikes
    settingsdict["overlayclimo"] = True  # overlay the climatology on the plot
    settingsdict["comparetoclimo"] = True  # check for climatology mismatch and display result on plot
    settingsdict["savefin"] = True  # file types to save
    settingsdict["savejjvv"] = True
    settingsdict["savebufr"] = True
    settingsdict["saveprof"] = True
    settingsdict["saveloc"] = True
    settingsdict["useoceanbottom"] = True  # use NTOPO1 bathymetry data to ID bottom strikes
    settingsdict["checkforgaps"] = True  # look for/correct gaps in profile due to false starts from VHF interference
    settingsdict["smoothlev"] = 8.  # Smoothing Window size (m)
    settingsdict["profres"] = 1. #profile minimum vertical resolution (m)
    settingsdict["maxstdev"] = 1.5 #profile standard deviation coefficient for despiker (autoQC)
    settingsdict["originatingcenter"] = 62 #BUFR table code for NAVO

    settingsdict["comport"] = 'n' #default com port is none
    settingsdict["gpsbaud"] = 4800 #baud rate for GPS- default to 4800
    
    settingsdict["fontsize"] = 14 #font size for general UI
    

    return settingsdict


    
    
#Read settings from txt file
def readsettings(filename):
    try:
        
        settingsdict = {}
        
        #read settings from file
        with open(filename) as file:
            
            #Data Acquisition System Settings
            line = file.readline()
            settingsdict["autodtg"] = bool(int(line.strip().split()[1])) 
            line = file.readline()
            settingsdict["autolocation"] = bool(int(line.strip().split()[1])) 
            line = file.readline()
            settingsdict["autoid"] = bool(int(line.strip().split()[1])) 
            line = file.readline()
            settingsdict["platformid"] = str(line.strip().split()[1]) 
            line = file.readline()
            settingsdict["savelog"] = bool(int(line.strip().split()[1])) 
            line = file.readline()
            settingsdict["saveedf"] = bool(int(line.strip().split()[1])) 
            line = file.readline()
            settingsdict["savewav"] = bool(int(line.strip().split()[1])) 
            line = file.readline()
            settingsdict["savesig"] = bool(int(line.strip().split()[1])) 
            line = file.readline()
            settingsdict["dtgwarn"] = bool(int(line.strip().split()[1])) 
            line = file.readline()
            settingsdict["renametabstodtg"] = bool(int(line.strip().split()[1]))
            line = file.readline() 
            settingsdict["autosave"] = bool(int(line.strip().split()[1]))             
            line = file.readline()
            settingsdict["fftwindow"] = float(line.strip().split()[1]) 
            line = file.readline()
            settingsdict["minfftratio"] = float(line.strip().split()[1]) 
            line = file.readline()
            settingsdict["minsiglev"] = float(line.strip().split()[1]) 
            line = file.readline()
            settingsdict["triggerfftratio"] = float(line.strip().split()[1]) 
            line = file.readline()
            settingsdict["triggersiglev"] = float(line.strip().split()[1]) 
            
            #DAS F2T and dt2z conversion equations- multiple values per setting, forward slash delimited
            line = file.readline()
            settingsdict["tcoeff"] = []
            tcstr = line.strip().split()[1].split('/')
            for val in tcstr:
                settingsdict["tcoeff"].append(float(val))
                
            line = file.readline()
            settingsdict["zcoeff"] = []
            zcstr = line.strip().split()[1].split('/')
            for val in zcstr:
                settingsdict["zcoeff"].append(float(val))
                
            line = file.readline()
            settingsdict["flims"] = []
            for val in line.strip().split()[1].split('/'):
                settingsdict["flims"].append(int(val)) #frequency limits must be whole numbers
            
            #Profile Editing System Settings
            line = file.readline()
            settingsdict["useclimobottom"] = bool(int(line.strip().split()[1])) 
            line = file.readline()
            settingsdict["overlayclimo"] = bool(int(line.strip().split()[1])) 
            line = file.readline()
            settingsdict["comparetoclimo"] = bool(int(line.strip().split()[1])) 
            line = file.readline()
            settingsdict["savefin"] = bool(int(line.strip().split()[1])) 
            line = file.readline()
            settingsdict["savejjvv"] = bool(int(line.strip().split()[1])) 
            line = file.readline()
            settingsdict["savebufr"] = bool(int(line.strip().split()[1])) 
            line = file.readline()
            settingsdict["saveprof"] = bool(int(line.strip().split()[1])) 
            line = file.readline()
            settingsdict["saveloc"] = bool(int(line.strip().split()[1])) 
            line = file.readline()
            settingsdict["useoceanbottom"] = bool(int(line.strip().split()[1])) 
            line = file.readline()
            settingsdict["checkforgaps"] = bool(int(line.strip().split()[1])) 
            line = file.readline()
            settingsdict["smoothlev"] = float(line.strip().split()[1]) 
            line = file.readline()
            settingsdict["profres"] = float(line.strip().split()[1]) 
            line = file.readline()
            settingsdict["maxstdev"] = float(line.strip().split()[1])
            line = file.readline()
            settingsdict["originatingcenter"] = int(line.strip().split()[1]) 
            line = file.readline()
            settingsdict["comport"] = str(line.strip().split()[1]) #GPS setting
            line = file.readline()
            settingsdict["gpsbaud"] = str(line.strip().split()[1]) #GPS setting
            line = file.readline()
            settingsdict["fontsize"] = int(line.strip().split()[1]) 
            
    #if settings file doesn't exist or is invalid, rewrites file with default settings
    except:
        settingsdict = setdefaultsettings()
        writesettings(filename, settingsdict)
        trace_error() #report issue

    return settingsdict

    
    
#Write settings from txt file
def writesettings(filename,settingsdict):
    
    #overwrites file by deleting if it exists
    if path.exists(filename):
        remove(filename)

    #writes settings to file
    with open(filename,'w') as file:
        
        #Data Acquisition System settings
        file.write('autodtg: '+str(int(settingsdict["autodtg"])) + '\n')
        file.write('autolocation: '+str(int(settingsdict["autolocation"])) + '\n')
        file.write('autoid: '+str(int(settingsdict["autoid"])) + '\n')
        file.write('platformid: '+str(settingsdict["platformid"]) + '\n')
        file.write('savelog: '+str(int(settingsdict["savelog"])) + '\n')
        file.write('saveedf: '+str(int(settingsdict["saveedf"])) + '\n')
        file.write('savewav: '+str(int(settingsdict["savewav"])) + '\n')
        file.write('savesig: '+str(int(settingsdict["savesig"])) + '\n')
        file.write('dtgwarn: '+str(int(settingsdict["dtgwarn"])) + '\n')
        file.write('renametabstodtg: '+str(int(settingsdict["renametabstodtg"])) + '\n')
        file.write('autosave: '+str(int(settingsdict["autosave"])) + '\n')
        file.write('fftwindow: '+str(settingsdict["fftwindow"]) + '\n')
        file.write('minfftratio: '+str(settingsdict["minfftratio"]) + '\n')
        file.write('minsiglev: '+str(settingsdict["minsiglev"]) + '\n')
        file.write('triggerfftratio: '+str(settingsdict["triggerfftratio"]) + '\n')
        file.write('triggersiglev: '+str(settingsdict["triggersiglev"]) + '\n')
        
        #writing coefficient settings is a bit more complicated
        tcoeffstr = ""
        zcoeffstr = ""
        for t in settingsdict["tcoeff"]:
            tcoeffstr += f"{t}/"
        for z in settingsdict["zcoeff"]:
            zcoeffstr += f"{z}/"
        file.write('tcoeff: ' + tcoeffstr[:-1] + '\n')
        file.write('zcoeff: ' + zcoeffstr[:-1] + '\n')
        file.write(f"flims: {settingsdict['flims'][0]}/{settingsdict['flims'][1]}\n")
        
        
        #Profile Editing System settings
        file.write('useclimobottom: '+str(int(settingsdict["useclimobottom"])) + '\n')
        file.write('overlayclimo: '+str(int(settingsdict["overlayclimo"])) + '\n')
        file.write('comparetoclimo: '+str(int(settingsdict["comparetoclimo"])) + '\n')
        file.write('savefin: '+str(int(settingsdict["savefin"])) + '\n')
        file.write('savejjvv: '+str(int(settingsdict["savejjvv"])) + '\n')
        file.write('savebufr: '+str(int(settingsdict["savebufr"])) + '\n')
        file.write('saveprof: '+str(int(settingsdict["saveprof"])) + '\n')
        file.write('saveloc: '+str(int(settingsdict["saveloc"])) + '\n')
        file.write('useoceanbottom: '+str(int(settingsdict["useoceanbottom"])) + '\n')
        file.write('checkforgaps: '+str(int(settingsdict["checkforgaps"])) + '\n')
        file.write('smoothlev: '+str(settingsdict["smoothlev"]) + '\n')
        file.write('profres: '+str(settingsdict["profres"]) + '\n')
        file.write('maxstdev: '+str(settingsdict["maxstdev"]) + '\n')
        file.write('originatingcenter: '+str(settingsdict["originatingcenter"]) + '\n')
        file.write('comport: '+str(settingsdict["comport"]) + '\n') #GPS settings
        file.write('gpsbaud: '+str(settingsdict["gpsbaud"]) + '\n') #GPS settings
        file.write('fontsize: '+str(settingsdict["fontsize"]) + '\n')
        
        

        