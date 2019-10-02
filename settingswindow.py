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

from PyQt5.QtWidgets import (QMainWindow, QLabel, QSpinBox, QCheckBox, QPushButton, 
    QMessageBox, QWidget, QTabWidget, QGridLayout, QSlider, QComboBox, QLineEdit)
from PyQt5.QtCore import Qt, pyqtSlot, pyqtSignal, QObject
from PyQt5.QtGui import QIcon, QColor, QPalette, QBrush, QLinearGradient, QFont

import qclib.GPS_COM_interaction as gps

from ctypes import windll



#   DEFINE CLASS FOR SETTINGS (TO BE CALLED IN THREAD)
class RunSettings(QMainWindow):

    # =============================================================================
    #   INITIALIZE WINDOW, INTERFACE
    # =============================================================================
    def __init__(self,autodtg, autolocation, autoid, platformID, savelog, saveedf, savewav, savesig, dtgwarn,
                 renametabstodtg, autosave, fftwindow, minfftratio, minsiglev, triggerfftratio, triggersiglev, useclimobottom, overlayclimo,
                 comparetoclimo, savefin, savejjvv, savebufr, saveprof, saveloc, useoceanbottom, checkforgaps, maxderiv, profres, originatingcenter, comport):
        super().__init__()

        try:
            self.initUI()

            self.signals = SettingsSignals()

            #records current settings received from main loop
            self.saveinputsettings(autodtg, autolocation, autoid, platformID, savelog, saveedf, savewav, savesig,
                                   dtgwarn, renametabstodtg, autosave, fftwindow, minfftratio, minsiglev, triggerfftratio, triggersiglev,
                                   useclimobottom, overlayclimo, comparetoclimo, savefin, savejjvv, savebufr, saveprof, saveloc,
                                   useoceanbottom, checkforgaps, maxderiv, profres, originatingcenter, comport)

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
    #     SAVE INPUT SETTINGS TO CLASS
    # =============================================================================
    def saveinputsettings(self, autodtg, autolocation, autoid, platformID, savelog, saveedf, savewav, savesig, dtgwarn,
                           renametabstodtg, autosave, fftwindow, minfftratio, minsiglev, triggerfftratio, triggersiglev, useclimobottom, overlayclimo,
                           comparetoclimo, savefin, savejjvv, savebufr, saveprof, saveloc, useoceanbottom, checkforgaps, maxderiv,
                           profres, originatingcenter, comport):

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
        self.renametabstodtg = renametabstodtg # auto rename tab to dtg when loading profile editor
        self.autosave = autosave  # automatically save raw data before opening profile editor (otherwise brings up prompt asking if want to save)
        self.fftwindow = fftwindow  # window to run FFT (in seconds)
        self.minfftratio = minfftratio  # minimum signal to noise ratio to ID data
        self.minsiglev = minsiglev  # minimum total signal level to receive data
        self.triggerfftratio = triggerfftratio  # minimum signal to noise ratio to ID data
        self.triggersiglev = triggersiglev  # minimum total signal level to receive data

        # profeditorpreferences
        self.useclimobottom = useclimobottom  # use climatology to ID bottom strikes
        self.overlayclimo = overlayclimo  # overlay the climatology on the plot
        self.comparetoclimo = comparetoclimo  # check for climatology mismatch and display result on plot
        self.savefin = savefin  # file types to save
        self.savejjvv = savejjvv
        self.savebufr = savebufr
        self.saveprof = saveprof
        self.saveloc = saveloc
        self.useoceanbottom = useoceanbottom  # use ETOPO1 bathymetry data to ID bottom strikes
        self.checkforgaps = checkforgaps  # look for/correct gaps in profile due to false starts from VHF interference
        self.maxderiv = maxderiv  # d2Tdz2 threshold to call a point an inflection point
        self.profres = profres  # profile minimum vertical resolution (m)
        self.originatingcenter = originatingcenter #originating center for BUFR message

        self.comport = comport # COM port for GPS feed



    # =============================================================================
    #     DECLARE DEFAULT VARIABLES, GLOBAL PARAMETERS
    # =============================================================================
    def setdefaultsettings(self):
        # processor preferences
        self.autodtg = True  # auto determine profile date/time as system date/time on clicking "START"
        self.autolocation = True #auto determine location with GPS
        self.autoid = True #autopopulate platform ID
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

        #profeditorpreferences
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
        self.profres = 8.0 #profile minimum vertical resolution (m)
        self.originatingcenter #BUFR table code for NAVO


    def updatepreferences(self): #records current configuration before exporting to main loop

        self.autodtg = self.processortabwidgets["autodtg"].isChecked()
        self.autolocation = self.processortabwidgets["autolocation"].isChecked()
        self.autoid = self.processortabwidgets["autoID"].isChecked()

        self.savelog = self.processortabwidgets["savelog"].isChecked()
        self.saveedf = self.processortabwidgets["saveedf"].isChecked()
        self.savewav = self.processortabwidgets["savewav"].isChecked()
        self.savesig = self.processortabwidgets["savesig"].isChecked()

        self.dtgwarn = self.processortabwidgets["dtgwarn"].isChecked()
        self.renametabstodtg = self.processortabwidgets["renametab"].isChecked()
        self.autosave = self.processortabwidgets["autosave"].isChecked()

        self.fftwindow = float(self.processortabwidgets["fftwindow"].value())/100
        self.minsiglev = 10**(float(self.processortabwidgets["fftsiglev"].value())/100)
        self.minfftratio = float(self.processortabwidgets["fftratio"].value())/100

        self.triggersiglev = 10**(float(self.processortabwidgets["triggersiglev"].value())/100)
        self.triggerfftratio = float(self.processortabwidgets["triggerratio"].value())/100

        self.platformID = self.processortabwidgets["IDedit"].text()

        self.useclimobottom = self.profeditortabwidgets["useclimobottom"].isChecked()
        self.comparetoclimo =  self.profeditortabwidgets["comparetoclimo"].isChecked()
        self.overlayclimo = self.profeditortabwidgets["overlayclimo"].isChecked()

        self.savefin = self.profeditortabwidgets["savefin"].isChecked()
        self.savejjvv = self.profeditortabwidgets["savejjvv"].isChecked()
        self.savebufr = self.profeditortabwidgets["savebufr"].isChecked()
        self.saveprof = self.profeditortabwidgets["saveprof"].isChecked()
        self.saveloc = self.profeditortabwidgets["saveloc"].isChecked()

        self.useoceanbottom = self.profeditortabwidgets["useoceanbottom"].isChecked()
        self.checkforgaps = self.profeditortabwidgets["checkforgaps"].isChecked()

        self.profres = float(self.profeditortabwidgets["profres"].value())/10
        self.maxderiv = float(self.profeditortabwidgets["maxderiv"].value())/100

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
            self.processortabwidgets["autodtg"].setChecked(self.autodtg)
            self.processortabwidgets["autolocation"] = QCheckBox('Autopopulate Location') #3
            self.processortabwidgets["autolocation"].setChecked(self.autolocation)
            self.processortabwidgets["autoID"] = QCheckBox('Autopopulate Platform Identifier') #4
            self.processortabwidgets["autoID"].setChecked(self.autoid)
            self.processortabwidgets["IDlabel"] = QLabel('Platform Identifier:') #5
            self.processortabwidgets["IDedit"] = QLineEdit(self.platformID) #6

            self.processortabwidgets["filesavetypes"] = QLabel('Filetypes to save:       ') #7
            self.processortabwidgets["savelog"] = QCheckBox('LOG File') #8
            self.processortabwidgets["savelog"].setChecked(self.savelog)
            self.processortabwidgets["saveedf"] = QCheckBox('EDF File') #9
            self.processortabwidgets["saveedf"].setChecked(self.saveedf)
            self.processortabwidgets["savewav"] = QCheckBox('WAV File') #10
            self.processortabwidgets["savewav"].setChecked(self.savewav)
            self.processortabwidgets["savesig"] = QCheckBox('Signal Data') #11
            self.processortabwidgets["savesig"].setChecked(self.savesig)

            self.processortabwidgets["dtgwarn"] = QCheckBox('Warn if DTG is not within past 12 hours') #12
            self.processortabwidgets["dtgwarn"].setChecked(self.dtgwarn)
            self.processortabwidgets["renametab"] = QCheckBox('Auto-rename tab to DTG on transition to profile editing mode') #13
            self.processortabwidgets["renametab"].setChecked(self.renametabstodtg)
            self.processortabwidgets["autosave"] = QCheckBox('Autosave raw data files when transitioning to profile editor mode') #14
            self.processortabwidgets["autosave"].setChecked(self.autosave)

            self.processortabwidgets["fftwindowlabel"] = QLabel('FFT Window (s): ' +str(self.fftwindow).ljust(4,'0')) #15
            self.processortabwidgets["fftwindow"] = QSlider(Qt.Horizontal) #16
            self.processortabwidgets["fftwindow"].setValue(int(self.fftwindow * 100))
            self.processortabwidgets["fftwindow"].setMinimum(10)
            self.processortabwidgets["fftwindow"].setMaximum(100)
            self.processortabwidgets["fftwindow"].valueChanged[int].connect(self.changefftwindow)

            sigsliderval = np.log10(self.minsiglev)
            self.processortabwidgets["fftsiglevlabel"] = QLabel('Minimum Signal Level (log[x]): ' + str(np.round(sigsliderval,2)).ljust(4,'0'))  # 17
            self.processortabwidgets["fftsiglev"] = QSlider(Qt.Horizontal)  # 18
            self.processortabwidgets["fftsiglev"].setMinimum(400)
            self.processortabwidgets["fftsiglev"].setMaximum(900)
            self.processortabwidgets["fftsiglev"].setValue(int(sigsliderval * 100))
            self.processortabwidgets["fftsiglev"].valueChanged[int].connect(self.changefftsiglev)

            self.processortabwidgets["fftratiolabel"] = QLabel('Minimum Signal Ratio (%): ' + str(np.round(self.minfftratio*100)).ljust(4,'0'))  # 19
            self.processortabwidgets["fftratio"] = QSlider(Qt.Horizontal)  # 20
            self.processortabwidgets["fftratio"].setValue(int(self.minfftratio * 100))
            self.processortabwidgets["fftratio"].setMinimum(0)
            self.processortabwidgets["fftratio"].setMaximum(100)
            self.processortabwidgets["fftratio"].valueChanged[int].connect(self.changefftratio)

            trigsigsliderval = np.log10(self.triggersiglev)
            self.processortabwidgets["triggersiglevlabel"] = QLabel(
                'Trigger Signal Level (log[x]): ' + str(np.round(trigsigsliderval, 2)).ljust(4, '0'))  # 17
            self.processortabwidgets["triggersiglev"] = QSlider(Qt.Horizontal)  # 18
            self.processortabwidgets["triggersiglev"].setMinimum(400)
            self.processortabwidgets["triggersiglev"].setMaximum(900)
            self.processortabwidgets["triggersiglev"].setValue(int(sigsliderval * 100))
            self.processortabwidgets["triggersiglev"].valueChanged[int].connect(self.changetriggersiglev)

            self.processortabwidgets["triggerratiolabel"] = QLabel(
                'Trigger Signal Ratio (%): ' + str(np.round(self.triggerfftratio * 100)).ljust(4, '0'))  # 19
            self.processortabwidgets["triggerratio"] = QSlider(Qt.Horizontal)  # 20
            self.processortabwidgets["triggerratio"].setValue(int(self.minfftratio * 100))
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

            self.gpstabwidgets["comporttitle"] = QLabel('COM Port Options:')  # 6
            self.gpstabwidgets["comport"] = QComboBox()  # 7
            self.gpstabwidgets["comport"].clear()
            self.gpstabwidgets["comport"].addItem('No COM Port Selected')
            self.gpstabwidgets["comport"].currentIndexChanged.connect(self.updatecomport)
            self.updatecomport()

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
        #won't overwrite existing com port settings if no port is selected
        if curcomnum > 0:
            self.comport = self.comports[curcomnum - 1]
        self.refreshgpsdata()

    #refreshing the list of available COM ports
    def updategpslist(self):
        self.gpstabwidgets["comport"].clear()
        self.gpstabwidgets["comport"].addItem('No COM Port Selected')
        self.comports,comportoptions = gps.listcomports()
        for curport in comportoptions:
            self.gpstabwidgets["comport"].addItem(curport)

    #attempt to refresh GPS data with currently selected COM port
    def refreshgpsdata(self):
        if self.comport != 'n':
            lat,lon,curdate,flag = gps.getcurrentposition(self.comport,5)
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
            self.profeditortabwidgets["useclimobottom"].setChecked(self.useclimobottom)
            self.profeditortabwidgets["comparetoclimo"] = QCheckBox('Autocompare profile to climatology')  # 3
            self.profeditortabwidgets["comparetoclimo"].setChecked(self.comparetoclimo)
            self.profeditortabwidgets["overlayclimo"] = QCheckBox('Overlay climatology in saved plots')  # 4
            self.profeditortabwidgets["overlayclimo"].setChecked(self.overlayclimo)

            self.profeditortabwidgets["filesavetypes"] = QLabel('Filetypes to save:     ')  # 5
            self.profeditortabwidgets["savefin"] = QCheckBox('FIN File')  # 6
            self.profeditortabwidgets["savefin"].setChecked(self.savefin)
            self.profeditortabwidgets["savejjvv"] = QCheckBox('JJVV File')  # 7
            self.profeditortabwidgets["savejjvv"].setChecked(self.savejjvv)
            self.profeditortabwidgets["savebufr"] = QCheckBox('BUFR File')  # 8
            self.profeditortabwidgets["savebufr"].setChecked(self.savebufr)
            self.profeditortabwidgets["saveprof"] = QCheckBox('Profile PNG')  # 9
            self.profeditortabwidgets["saveprof"].setChecked(self.saveprof)
            self.profeditortabwidgets["saveloc"] = QCheckBox('Location PNG')  # 10
            self.profeditortabwidgets["saveloc"].setChecked(self.saveloc)

            self.profeditortabwidgets["useoceanbottom"] = QCheckBox(
                'ID bottom strikes with NOAA ETOPO1 bathymetry data')  # 11
            self.profeditortabwidgets["useoceanbottom"].setChecked(self.useoceanbottom)
            self.profeditortabwidgets["checkforgaps"] = QCheckBox('ID false starts due to VHF interference')  # 12
            self.profeditortabwidgets["checkforgaps"].setChecked(self.checkforgaps)

            self.profres = float(self.profres)
            self.profeditortabwidgets["profreslabel"] = QLabel(
                'Minimum Profile Resolution (m): ' + str(float(self.profres)).ljust(4,'0'))  # 13
            self.profeditortabwidgets["profres"] = QSlider(Qt.Horizontal)  # 14
            self.profeditortabwidgets["profres"].setValue(int(self.profres * 10))
            self.profeditortabwidgets["profres"].setMinimum(0)
            self.profeditortabwidgets["profres"].setMaximum(500)
            self.profeditortabwidgets["profres"].valueChanged[int].connect(self.changeprofres)

            self.profeditortabwidgets["maxderivlabel"] = QLabel(
                'Inflection Point Threshold (C/m<sup>2</sup>): ' + str(self.maxderiv).ljust(4,'0'))  # 15
            self.profeditortabwidgets["maxderiv"] = QSlider(Qt.Horizontal)  # 16
            self.profeditortabwidgets["maxderiv"].setMinimum(0)
            self.profeditortabwidgets["maxderiv"].setMaximum(400)
            self.profeditortabwidgets["maxderiv"].setValue(int(self.maxderiv * 100))
            self.profeditortabwidgets["maxderiv"].valueChanged[int].connect(self.changemaxderiv)


            self.profeditortabwidgets["originatingcentername"] = QLabel("")  # 15
            self.profeditortabwidgets["originatingcenter"] = QSpinBox()  # 16
            self.profeditortabwidgets["originatingcenter"].setMinimum(0)
            self.profeditortabwidgets["originatingcenter"].setMaximum(255)
            self.profeditortabwidgets["originatingcenter"].setSingleStep(1)
            self.profeditortabwidgets["originatingcenter"].setValue(self.originatingcenter)
            self.profeditortabwidgets["originatingcenter"].valueChanged[int].connect(self.updateoriginatingcenter)
            try:
                curcentername = self.allcenters[str(self.originatingcenter).zfill(3)]
            except:
                curcentername = "Center ID not recognized!"
            self.profeditortabwidgets["originatingcentername"].setText("Center "+str(self.originatingcenter).zfill(3)+": "+curcentername)

            # should be 19 entries
            widgetorder = ["climotitle", "useclimobottom", "comparetoclimo", "overlayclimo", "filesavetypes", "savefin",
                           "savejjvv", "savebufr", "saveprof", "saveloc", "useoceanbottom", "checkforgaps", "profreslabel",
                           "profres", "maxderivlabel", "maxderiv","originatingcentername","originatingcenter"]

            wcols = [1, 1, 1, 1, 4, 4, 4, 4, 4, 4, 1, 1, 5, 5, 5, 5, 1, 1]
            wrows = [1, 2, 3, 4, 1, 2, 3, 4, 5, 6, 8, 9, 2, 3, 5, 6, 11, 12]
            wrext = [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]
            wcolext = [2, 2, 2, 2, 1, 1, 1, 1, 1, 1, 4, 4, 1, 1, 1, 1, 4, 4]

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
        self.originatingcenter = int(self.profeditortabwidgets["originatingcenter"].value())
        ctrkey = str(self.originatingcenter).zfill(3)
        if ctrkey in self.allcenters:
            curcentername = self.allcenters[ctrkey]
        else:
            curcentername = self.allcenters["xxx"]
        self.profeditortabwidgets["originatingcentername"].setText("Center "+ctrkey+": "+curcentername)

    #lookup table for originating centers
    def buildcentertable(self):
        self.allcenters = {"000":"       WMO Secretariat               ",
                           "007":"       US NWS: NCEP                  ",
                           "008":"       US NWS: NWSTG                 ",
                           "009":"       US NWS: Other                 ",
                           "051":"       Miami (RSMC)                  ",
                           "052":"       Miami (RSMC) NHC              ",
                           "052":"       MSC Monitoring                ",
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
        self.fftwindow = float(value) / 100
        self.processortabwidgets["fftwindowlabel"].setText('FFT Window (s): ' +str(self.fftwindow).ljust(4,'0'))

    def changefftsiglev(self, value):
        sigsliderval = float(value) / 100
        self.minsiglev = 10**sigsliderval
        self.processortabwidgets["fftsiglevlabel"].setText('Minimum Signal Level (log[x]): ' + str(np.round(sigsliderval,2)).ljust(4,'0'))

    def changefftratio(self, value):
        self.minfftratio = float(value) / 100
        self.processortabwidgets["fftratiolabel"].setText('Minimum Signal Ratio (%): ' + str(np.round(self.minfftratio*100)).ljust(4,'0'))

    def changetriggersiglev(self, value):
        trigsigsliderval = float(value) / 100
        self.triggersiglev = 10**trigsigsliderval
        self.processortabwidgets["triggersiglevlabel"].setText('Trigger Signal Level (log[x]): ' + str(np.round(trigsigsliderval,2)).ljust(4,'0'))

    def changetriggerratio(self, value):
        self.triggerfftratio = float(value) / 100
        self.processortabwidgets["triggerratiolabel"].setText('Trigger Signal Ratio (%): ' + str(np.round(self.triggerfftratio*100)).ljust(4,'0'))


    def changeprofres(self, value):
        self.profres = float(value) / 10
        self.profeditortabwidgets["profreslabel"].setText('Minimum Profile Resolution (m): ' + str(float(self.profres)).ljust(4,'0'))

    def changemaxderiv(self, value):
        self.maxderiv = float(value) / 100
        self.profeditortabwidgets["maxderivlabel"].setText('Inflection Point Threshold (C/m<sup>2</sup>): ' + str(self.maxderiv).ljust(4,'0'))


    # =============================================================================
    #   EXPORT AND/OR RESET ALL SETTINGS
    # =============================================================================
    def applychanges(self):
        self.updatepreferences()
        self.signals.exported.emit(self.autodtg, self.autolocation, self.autoid, self.platformID, self.savelog,
                                   self.saveedf, self.savewav, self.savesig, self.dtgwarn, self.renametabstodtg,
                                   self.autosave, self.fftwindow, self.minfftratio, self.minsiglev, self.triggerfftratio, self.triggersiglev, self.useclimobottom,
                                   self.overlayclimo, self.comparetoclimo, self.savefin, self.savejjvv, self.savebufr, self.saveprof,
                                   self.saveloc, self.useoceanbottom, self.checkforgaps, self.maxderiv, self.profres, self.originatingcenter, self.comport)


    def resetdefaults(self):
        self.setdefaultsettings()

        self.processortabwidgets["autodtg"].setChecked(self.autodtg)
        self.processortabwidgets["autolocation"].setChecked(self.autolocation)
        self.processortabwidgets["autoID"].setChecked(self.autoid)

        self.processortabwidgets["savelog"].setChecked(self.savelog)
        self.processortabwidgets["saveedf"].setChecked(self.saveedf)
        self.processortabwidgets["savewav"].setChecked(self.savewav)
        self.processortabwidgets["savesig"].setChecked(self.savesig)

        self.processortabwidgets["dtgwarn"].setChecked(self.dtgwarn)
        self.processortabwidgets["renametab"].setChecked(self.renametabstodtg)
        self.processortabwidgets["autosave"].setChecked(self.autosave)

        self.processortabwidgets["fftwindowlabel"].setText('FFT Window (s): ' + str(self.fftwindow))  # 15
        self.processortabwidgets["fftwindow"].setValue(int(self.fftwindow * 100))

        sigsliderval = np.log10(self.minsiglev)
        self.processortabwidgets["fftsiglevlabel"].setText('Minimum Signal Level (log[x]): ' + str(np.round(sigsliderval, 2)).ljust(4, '0'))  # 17
        self.processortabwidgets["fftsiglev"].setValue(int(sigsliderval * 100))

        self.processortabwidgets["fftratiolabel"].setText('Minimum Signal Ratio (%): ' + str(np.round(self.minfftratio * 100)))  # 19
        self.processortabwidgets["fftratio"].setValue(int(self.minfftratio * 100))

        trigsigsliderval = np.log10(self.triggersiglev)
        self.processortabwidgets["triggersiglevlabel"].setText(
            'Trigger Signal Level (log[x]): ' + str(np.round(trigsigsliderval, 2)).ljust(4, '0'))  # 17
        self.processortabwidgets["triggersiglev"].setValue(int(trigsigsliderval * 100))

        self.processortabwidgets["triggerratiolabel"].setText(
            'Trigger Signal Ratio (%): ' + str(np.round(self.triggerfftratio * 100)))  # 19
        self.processortabwidgets["triggerratio"].setValue(int(self.triggerfftratio * 100))

        self.profeditortabwidgets["useclimobottom"].setChecked(self.useclimobottom)
        self.profeditortabwidgets["comparetoclimo"].setChecked(self.comparetoclimo)
        self.profeditortabwidgets["overlayclimo"].setChecked(self.overlayclimo)

        self.profeditortabwidgets["savefin"].setChecked(self.savefin)
        self.profeditortabwidgets["savejjvv"].setChecked(self.savejjvv)
        self.profeditortabwidgets["savebufr"].setChecked(self.savebufr)
        self.profeditortabwidgets["saveprof"].setChecked(self.saveprof)
        self.profeditortabwidgets["saveloc"].setChecked(self.saveloc)

        self.profeditortabwidgets["useoceanbottom"].setChecked(self.useoceanbottom)
        self.profeditortabwidgets["checkforgaps"].setChecked(self.checkforgaps)

        self.profeditortabwidgets["profreslabel"].setText('Minimum Profile Resolution (m): ' + str(self.profres).ljust(4, '0'))  # 15
        self.profeditortabwidgets["profres"].setValue(int(self.profres * 10))

        self.profeditortabwidgets["maxderivlabel"].setText('Inflection Point Threshold (C/m<sup>2</sup>): ' + str(self.maxderiv).ljust(4, '0'))  # 17
        self.profeditortabwidgets["maxderiv"].setValue(int(self.maxderiv * 100))

        self.profeditortabwidgets["originatingcenter"].setText(str(self.originatingcenter).zfill(3))

    # =============================================================================
    #     TAB MANIPULATION OPTIONS, OTHER GENERAL FUNCTIONS
    # =============================================================================
    def whatTab(self):
        currentIndex = self.tabWidget.currentIndex()
        return currentIndex

    def setnewtabcolor(self, tab):
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

    def posterror(self,errortext):
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Critical)
        msg.setText(errortext)
        msg.setWindowTitle("Error")
        msg.setStandardButtons(QMessageBox.Ok)
        msg.exec_()


# SIGNAL SETUP HERE
class SettingsSignals(QObject):
    exported = pyqtSignal(bool,bool,bool,str,bool,bool,bool,bool,bool,bool,bool,float,float,float,float,float,bool,bool,
                          bool,bool,bool,bool,bool,bool,bool,bool,float,float,int,str)
    closed = pyqtSignal(bool)