# =============================================================================
#     Code: settingswindow.py
#     Author: ENS Casey R. Densmore, 25AUG2019
#     
#     Purpose: Creates window for advanced ARES settings, handles signals/slots
#       with main event loop in order to update settings.
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

            #building window/tabs
            self.buildcentertable()
            self.makeprocessorsettingstab()  # processor settings
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

        #adding widgets to main tab
        self.mainLayout.addWidget(self.tabWidget,0,0,1,5)
        self.applysettings = QPushButton('Apply Changes')
        self.applysettings.clicked.connect(self.applychanges)
        self.resetchanges = QPushButton('Reset Defaults')
        self.resetchanges.clicked.connect(self.resetdefaults)
        self.mainLayout.addWidget(self.applysettings,1,1,1,1)
        self.mainLayout.addWidget(self.resetchanges,1,3,1,1)
        for i in range(0,5):
            self.mainLayout.setRowStretch(i,1)
        self.show()

        
        
        
    # =============================================================================
    #   FUNCTIONS TO UPDATE/EXPORT/RESET SETTINGS
    # =============================================================================
    def applychanges(self):
        self.updatepreferences()
        self.signals.exported.emit(self.settingsdict)


    def resetdefaults(self):
        #pull default settings
        self.settingsdict = setdefaultsettings()
        
        
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

        self.processortabwidgets["fftwindowlabel"].setText('FFT Window (s): ' + str(self.settingsdict["fftwindow"]))  # 15
        self.processortabwidgets["fftwindow"].setValue(int(self.settingsdict["fftwindow"] * 100))

        sigsliderval = np.log10(self.settingsdict["minsiglev"])
        self.processortabwidgets["fftsiglevlabel"].setText('Minimum Signal Level (log[x]): ' + str(np.round(self.settingsdict["sigsliderval"], 2)).ljust(4, '0'))  # 17
        self.processortabwidgets["fftsiglev"].setValue(int(self.settingsdict["sigsliderval"] * 100))

        self.processortabwidgets["fftratiolabel"].setText('Minimum Signal Ratio (%): ' + str(np.round(self.settingsdict["minfftratio"] * 100)))  # 19
        self.processortabwidgets["fftratio"].setValue(int(self.settingsdict["minfftratio"] * 100))

        trigsigsliderval = np.log10(self.settingsdict["triggersiglev"])
        self.processortabwidgets["triggersiglevlabel"].setText(
            'Trigger Signal Level (log[x]): ' + str(np.round(self.settingsdict["trigsigsliderval"], 2)).ljust(4, '0'))  # 17
        self.processortabwidgets["triggersiglev"].setValue(int(self.settingsdict["trigsigsliderval"] * 100))

        self.processortabwidgets["triggerratiolabel"].setText(
            'Trigger Signal Ratio (%): ' + str(np.round(self.settingsdict["triggerfftratio"] * 100)))  # 19
        self.processortabwidgets["triggerratio"].setValue(int(self.settingsdict["triggerfftratio"] * 100))

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
        self.settingsdict["minsiglev"] = 10**(float(self.processortabwidgets["fftsiglev"].value())/100)
        self.settingsdict["minfftratio"] = float(self.processortabwidgets["fftratio"].value())/100

        self.settingsdict["triggersiglev"] = 10**(float(self.processortabwidgets["triggersiglev"].value())/100)
        self.settingsdict["triggerfftratio"] = float(self.processortabwidgets["triggerratio"].value())/100

        self.settingsdict["platformID"] = self.processortabwidgets["IDedit"].text()

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
        self.updatecomport()
        
    
    


    # =============================================================================
    #     SIGNAL PROCESSOR TAB AND INPUTS HERE
    # =============================================================================
    def makeprocessorsettingstab(self):
        try:

            self.processortab = QWidget()
            self.processortablayout = QGridLayout()
            self.setnewtabcolor(self.processortab)

            self.processortablayout.setSpacing(10)

            self.tabWidget.addTab(self.processortab,'Processor Settings')
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
            self.processortabwidgets["IDedit"] = QLineEdit(self.settingsdict["platformID"]) #6

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

            self.processortabwidgets["fftwindowlabel"] = QLabel('FFT Window (s): ' +str(self.settingsdict["fftwindow"]).ljust(4,'0')) #15
            self.processortabwidgets["fftwindow"] = QSlider(Qt.Horizontal) #16
            self.processortabwidgets["fftwindow"].setValue(int(self.settingsdict["fftwindow"] * 100))
            self.processortabwidgets["fftwindow"].setMinimum(10)
            self.processortabwidgets["fftwindow"].setMaximum(100)
            self.processortabwidgets["fftwindow"].valueChanged[int].connect(self.changefftwindow)

            sigsliderval = np.log10(self.settingsdict["minsiglev"])
            self.processortabwidgets["fftsiglevlabel"] = QLabel('Minimum Signal Level (log[x]): ' + str(np.round(sigsliderval,2)).ljust(4,'0'))  # 17
            self.processortabwidgets["fftsiglev"] = QSlider(Qt.Horizontal)  # 18
            self.processortabwidgets["fftsiglev"].setMinimum(400)
            self.processortabwidgets["fftsiglev"].setMaximum(900)
            self.processortabwidgets["fftsiglev"].setValue(int(sigsliderval * 100))
            self.processortabwidgets["fftsiglev"].valueChanged[int].connect(self.changefftsiglev)

            self.processortabwidgets["fftratiolabel"] = QLabel('Minimum Signal Ratio (%): ' + str(np.round(self.settingsdict["minfftratio"]*100)).ljust(4,'0'))  # 19
            self.processortabwidgets["fftratio"] = QSlider(Qt.Horizontal)  # 20
            self.processortabwidgets["fftratio"].setValue(int(self.settingsdict["minfftratio"] * 100))
            self.processortabwidgets["fftratio"].setMinimum(0)
            self.processortabwidgets["fftratio"].setMaximum(100)
            self.processortabwidgets["fftratio"].valueChanged[int].connect(self.changefftratio)

            trigsigsliderval = np.log10(self.settingsdict["triggersiglev"])
            self.processortabwidgets["triggersiglevlabel"] = QLabel(
                'Trigger Signal Level (log[x]): ' + str(np.round(trigsigsliderval, 2)).ljust(4, '0'))  # 17
            self.processortabwidgets["triggersiglev"] = QSlider(Qt.Horizontal)  # 18
            self.processortabwidgets["triggersiglev"].setMinimum(400)
            self.processortabwidgets["triggersiglev"].setMaximum(900)
            self.processortabwidgets["triggersiglev"].setValue(int(trigsigsliderval * 100))
            self.processortabwidgets["triggersiglev"].valueChanged[int].connect(self.changetriggersiglev)

            self.processortabwidgets["triggerratiolabel"] = QLabel(
                'Trigger Signal Ratio (%): ' + str(np.round(self.settingsdict["triggerfftratio"] * 100)).ljust(4, '0'))  # 19
            self.processortabwidgets["triggerratio"] = QSlider(Qt.Horizontal)  # 20
            self.processortabwidgets["triggerratio"].setValue(int(self.settingsdict["minfftratio"] * 100))
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

            self.gpstabwidgets["refreshgpsdata"] = QPushButton("Refresh GPS Info") # 2
            self.gpstabwidgets["refreshgpsdata"].clicked.connect(self.refreshgpsdata)

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
                    self.gpstabwidgets["comport"].setCurrentIndex(self.settingsdict["comports"]. index(self.settingsdict["comport"])+1)
                #if the listed receiver is not connected, set setting and current index to N/A
                else:
                    self.settingsdict["comport"] = 'n'    
            #if no receiver is selected, set current index to top
            else:
                self.gpstabwidgets["comport"].setCurrentIndex(0)
                
                
            #connect comport change to function
            self.gpstabwidgets["comport"].currentIndexChanged.connect(self.updatecomport)
            
            # should be 7 entries
            widgetorder = ["updateports", "refreshgpsdata", "gpsdate", "gpslat", "gpslon","comporttitle","comport"]

            wcols = [1, 2, 1, 1, 1, 1, 1]
            wrows = [1, 1, 5, 6, 7, 2, 3]
            wrext = [1, 1, 1, 1, 1, 1, 1]
            wcolext = [1, 1, 1, 1, 1, 1, 2]

            # adding user inputs
            for i, r, c, re, ce in zip(widgetorder, wrows, wcols, wrext, wcolext):
                self.gpstablayout.addWidget(self.gpstabwidgets[i], r, c, re, ce)

            # Applying spacing preferences to grid layout
            self.gpstablayout.setRowStretch(0,4)
            self.gpstablayout.setRowStretch(4,4)
            self.gpstablayout.setRowStretch(8,4)
            self.gpstablayout.setColumnStretch(0,4)
            self.gpstablayout.setColumnStretch(3,4)

            # making the current layout for the tab
            self.gpstab.setLayout(self.gpstablayout)

        except Exception:
            trace_error()
            self.posterror("Failed to build new GPS tab")

    #updating the selected COM port from the menu
    def updatecomport(self):
        curcomnum = self.gpstabwidgets["comport"].currentIndex()
        if curcomnum > 0:
            self.settingsdict["comport"] = self.settingsdict["comports"][curcomnum - 1]
        else:
            self.settingsdict["comport"] = 'n'

    #refreshing the list of available COM ports
    def updategpslist(self):
        self.gpstabwidgets["comport"].clear()
        self.gpstabwidgets["comport"].addItem('No COM Port Selected')
        self.settingsdict["comports"],self.settingsdict["comportdetails"] = gps.listcomports()
        for curport in self.settingsdict["comportdetails"]:
            self.gpstabwidgets["comport"].addItem(curport)

    #attempt to refresh GPS data with currently selected COM port
    def refreshgpsdata(self):
        if self.settingsdict["comport"] != 'n':
            lat,lon,curdate,flag = gps.getcurrentposition(self.settingsdict["comport"],5)
            if flag == 0:
                if lat > 0:
                    latsign = 'N'
                else:
                    latsign = 'S'
                if lon > 0:
                    lonsign = 'E'
                else:
                    lonsign = 'W'
                self.gpstabwidgets["gpsdate"].setText("Date/Time: {} UTC".format(curdate))
                self.gpstabwidgets["gpslat"].setText("Latitude: {}{}".format(abs(lat),latsign))
                self.gpstabwidgets["gpslon"].setText("Longitude: {}{}".format(abs(lon),lonsign))
            elif flag == 1:
                self.posterror("GPS request timed out!")
            elif flag == 2:
                self.posterror("Unable to communicate with specified COM port!")
        else:
            self.gpstabwidgets["gpsdate"].setText("Date/Time:")
            self.gpstabwidgets["gpslat"].setText("Latitude:")
            self.gpstabwidgets["gpslon"].setText("Longitude:")
    
    
    


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
        self.processortabwidgets["fftwindowlabel"].setText('FFT Window (s): ' +str(self.settingsdict["fftwindow"]).ljust(4,'0'))

    def changefftsiglev(self, value):
        sigsliderval = float(value) / 100
        self.settingsdict["minsiglev"] = 10**sigsliderval
        self.processortabwidgets["fftsiglevlabel"].setText('Minimum Signal Level (log[x]): ' + str(np.round(sigsliderval,2)).ljust(4,'0'))

    def changefftratio(self, value):
        self.settingsdict["minfftratio"] = float(value) / 100
        self.processortabwidgets["fftratiolabel"].setText('Minimum Signal Ratio (%): ' + str(np.round(self.minfftratio*100)).ljust(4,'0'))

    def changetriggersiglev(self, value):
        trigsigsliderval = float(value) / 100
        self.settingsdict["triggersiglev"] = 10**trigsigsliderval
        self.processortabwidgets["triggersiglevlabel"].setText('Trigger Signal Level (log[x]): ' + str(np.round(trigsigsliderval,2)).ljust(4,'0'))

    def changetriggerratio(self, value):
        self.settingsdict["triggerfftratio"] = float(value) / 100
        self.processortabwidgets["triggerratiolabel"].setText('Trigger Signal Ratio (%): ' + str(np.round(self.settingsdict["triggerfftratio"]*100)).ljust(4,'0'))
        
    
        
    
        

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


#Default settings for program
def setdefaultsettings():
    
    settingsdict = {}
    
    # processor preferences
    settingsdict["autodtg"] = True  # auto determine profile date/time as system date/time on clicking "START"
    settingsdict["autolocation"] = True #auto determine location with GPS
    settingsdict["autoid"] = True #autopopulate platform ID
    settingsdict["platformID"] = 'AFNNN'
    settingsdict["savelog"] = True
    settingsdict["saveedf"] = False
    settingsdict["savewav"] = True
    settingsdict["savesig"] = True
    settingsdict["dtgwarn"] = True  # warn user if entered dtg is more than 12 hours old or after current system time (in future)
    settingsdict["renametabstodtg"] = True  # auto rename tab to dtg when loading profile editor
    settingsdict["autosave"] = False  # automatically save raw data before opening profile editor (otherwise brings up prompt asking if want to save)
    settingsdict["fftwindow"] = 0.3  # window to run FFT (in seconds)
    settingsdict["minfftratio"] = 0.42  # minimum signal to noise ratio to ID data
    settingsdict["minsiglev"] = 6.3E5  # minimum total signal level to receive data

    settingsdict["triggerfftratio"] = 0.8  # minimum signal to noise ratio to ID data
    settingsdict["triggersiglev"] = 1E7  # minimum total signal level to receive data

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
    settingsdict["smoothlev"] = 2  # Smoothing Window size (m)
    settingsdict["profres"] = 1 #profile minimum vertical resolution (m)
    settingsdict["maxstdev"] = 1 #profile standard deviation coefficient for despiker (autoQC)
    settingsdict["originatingcenter"] = 62 #BUFR table code for NAVO

    settingsdict["comport"] = 'n' #default com port is none
    

    return settingsdict


#Read settings from txt file
def readsettings(filename):
    try:
        
        settingsdict = {}
        
        #read settings from file
        with open(filename) as file:
            line = file.readline()
            settingsdict["autodtg"] = bool(line.strip().split()[1]) 
            line = file.readline()
            settingsdict["autolocation"] = bool(line.strip().split()[1]) 
            line = file.readline()
            settingsdict["autoid"] = bool(line.strip().split()[1]) 
            line = file.readline()
            settingsdict["platformID"] = str(line.strip().split()[1]) 
            line = file.readline()
            settingsdict["savelog"] = bool(line.strip().split()[1]) 
            line = file.readline()
            settingsdict["saveedf"] = bool(line.strip().split()[1]) 
            line = file.readline()
            settingsdict["savewav"] = bool(line.strip().split()[1]) 
            line = file.readline()
            settingsdict["savesig"] = bool(line.strip().split()[1]) 
            line = file.readline()
            settingsdict["dtgwarn"] = bool(line.strip().split()[1]) 
            line = file.readline()
            settingsdict["renametabstodtg"] = bool(line.strip().split()[1])
            line = file.readline() 
            settingsdict["autosave"] = bool(line.strip().split()[1]) 
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
            line = file.readline()
            settingsdict["useclimobottom"] = bool(line.strip().split()[1]) 
            line = file.readline()
            settingsdict["overlayclimo"] = bool(line.strip().split()[1]) 
            line = file.readline()
            settingsdict["comparetoclimo"] = bool(line.strip().split()[1]) 
            line = file.readline()
            settingsdict["savefin"] = bool(line.strip().split()[1]) 
            line = file.readline()
            settingsdict["savejjvv"] = bool(line.strip().split()[1]) 
            line = file.readline()
            settingsdict["savebufr"] = bool(line.strip().split()[1]) 
            line = file.readline()
            settingsdict["saveprof"] = bool(line.strip().split()[1]) 
            line = file.readline()
            settingsdict["saveloc"] = bool(line.strip().split()[1]) 
            line = file.readline()
            settingsdict["useoceanbottom"] = bool(line.strip().split()[1]) 
            line = file.readline()
            settingsdict["checkforgaps"] = bool(line.strip().split()[1]) 
            line = file.readline()
            settingsdict["smoothlev"] = float(line.strip().split()[1]) 
            line = file.readline()
            settingsdict["profres"] = float(line.strip().split()[1]) 
            line = file.readline()
            settingsdict["maxstdev"] = float(line.strip().split()[1])
            line = file.readline()
            settingsdict["originatingcenter"] = int(line.strip().split()[1]) 
            line = file.readline()
            settingsdict["comport"] = str(line.strip().split()[1]) 
            

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
        file.write('autodtg: '+str(settingsdict["autodtg"]) + '\n')
        file.write('autolocation: '+str(settingsdict["autolocation"]) + '\n')
        file.write('autoid: '+str(settingsdict["autoid"]) + '\n')
        file.write('platformID: '+str(settingsdict["platformID"]) + '\n')
        file.write('savelog: '+str(settingsdict["savelog"]) + '\n')
        file.write('saveedf: '+str(settingsdict["saveedf"]) + '\n')
        file.write('savewav: '+str(settingsdict["savewav"]) + '\n')
        file.write('savesig: '+str(settingsdict["savesig"]) + '\n')
        file.write('dtgwarn: '+str(settingsdict["dtgwarn"]) + '\n')
        file.write('renametabstodtg: '+str(settingsdict["renametabstodtg"]) + '\n')
        file.write('autosave: '+str(settingsdict["autosave"]) + '\n')
        file.write('fftwindow: '+str(settingsdict["fftwindow"]) + '\n')
        file.write('minfftratio: '+str(settingsdict["minfftratio"]) + '\n')
        file.write('minsiglev: '+str(settingsdict["minsiglev"]) + '\n')
        file.write('triggerfftratio: '+str(settingsdict["triggerfftratio"]) + '\n')
        file.write('triggersiglev: '+str(settingsdict["triggersiglev"]) + '\n')
        file.write('useclimobottom: '+str(settingsdict["useclimobottom"]) + '\n')
        file.write('overlayclimo: '+str(settingsdict["overlayclimo"]) + '\n')
        file.write('comparetoclimo: '+str(settingsdict["comparetoclimo"]) + '\n')
        file.write('savefin: '+str(settingsdict["savefin"]) + '\n')
        file.write('savejjvv: '+str(settingsdict["savejjvv"]) + '\n')
        file.write('savebufr: '+str(settingsdict["savebufr"]) + '\n')
        file.write('saveprof: '+str(settingsdict["saveprof"]) + '\n')
        file.write('saveloc: '+str(settingsdict["saveloc"]) + '\n')
        file.write('useoceanbottom: '+str(settingsdict["useoceanbottom"]) + '\n')
        file.write('checkforgaps: '+str(settingsdict["checkforgaps"]) + '\n')
        file.write('smoothlev: '+str(settingsdict["smoothlev"]) + '\n')
        file.write('profres: '+str(settingsdict["profres"]) + '\n')
        file.write('maxstdev: '+str(settingsdict["maxstdev"]) + '\n')
        file.write('originatingcenter: '+str(settingsdict["originatingcenter"]) + '\n')
        file.write('comport: '+str(settingsdict["comport"]) + '\n')
        
        

        