#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
main.py
Author: ENS Casey R. Densmore

Purpose: Builds user interface for AXBT data processing and quality-control
with PyQT5.
"""
# =============================================================================
#   CALL NECESSARY MODULES HERE
# =============================================================================
import sys
import platform
import os
import traceback
import numpy as np

from PyQt5.QtWidgets import (QMainWindow, QAction, QApplication, QMenu, QLineEdit, QLabel, QSpinBox, QCheckBox,
                             QPushButton, QMessageBox, QActionGroup, QWidget, QFileDialog, QComboBox, QTextEdit,
                             QTabWidget, QVBoxLayout, QInputDialog, QGridLayout, QSlider, QDoubleSpinBox,
                             QTableWidget, QTableWidgetItem, QHeaderView, QProgressBar, QDesktopWidget, QStyle,
                             QStyleOptionTitleBar)
from PyQt5.QtCore import QObjectCleanupHandler, Qt, pyqtSlot, pyqtSignal, QObject
from PyQt5.QtGui import QIcon, QColor, QPalette, QBrush, QLinearGradient, QFont
from PyQt5.Qt import QRunnable

from ctypes import windll



#   DEFINE CLASS FOR SETTINGS (TO BE CALLED IN THREAD)
class RunSettings(QMainWindow):

    # =============================================================================
    #   INITIALIZE WINDOW, INTERFACE
    # =============================================================================
    def __init__(self,autodtg, autolocation, autoid, platformID, savelog, saveedf, savewav, savesig, dtgwarn,
                 renametabstodtg, autosave, fftwindow, minfftratio, minsiglev, useclimobottom, overlayclimo,
                 comparetoclimo, savefin, savejjvv, saveprof, saveloc, useoceanbottom, checkforgaps, maxderiv, profres):
        super().__init__()

        try:
            self.initUI()

            self.signals = SettingsSignals()

            self.saveinputsettings(autodtg, autolocation, autoid, platformID, savelog, saveedf, savewav, savesig,
                                   dtgwarn, renametabstodtg, autosave, fftwindow, minfftratio, minsiglev,
                                   useclimobottom, overlayclimo, comparetoclimo, savefin, savejjvv, saveprof, saveloc,
                                   useoceanbottom, checkforgaps, maxderiv, profres)
            # self.setdefaultsettings()  # Default autoQC preferences

            self.makeprocessorsettingstab()  # processor settings
            self.makeprofileeditorsettingstab() #profile editor tab

        except Exception:
            traceback.print_exc()
            self.posterror("Failed to initialize the settings menu.")

    def initUI(self):

        # setting window size
        # cursize = QDesktopWidget().availableGeometry(self).size()
        # self.resize(int(cursize.width()/3), int(cursize.height()/2))

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
                           renametabstodtg, autosave, fftwindow, minfftratio, minsiglev, useclimobottom, overlayclimo,
                           comparetoclimo, savefin, savejjvv, saveprof, saveloc, useoceanbottom, checkforgaps, maxderiv,
                           profres):

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

        # profeditorpreferences
        self.useclimobottom = useclimobottom  # use climatology to ID bottom strikes
        self.overlayclimo = overlayclimo  # overlay the climatology on the plot
        self.comparetoclimo = comparetoclimo  # check for climatology mismatch and display result on plot
        self.savefin = savefin  # file types to save
        self.savejjvv = savejjvv
        self.saveprof = saveprof
        self.saveloc = saveloc
        self.useoceanbottom = useoceanbottom  # use ETOPO1 bathymetry data to ID bottom strikes
        self.checkforgaps = checkforgaps  # look for/correct gaps in profile due to false starts from VHF interference
        self.maxderiv = maxderiv  # d2Tdz2 threshold to call a point an inflection point
        self.profres = profres  # profile minimum vertical resolution (m)




    # =============================================================================
    #     DECLARE DEFAULT VARIABLES, GLOBAL PARAMETERS
    # =============================================================================
    def setdefaultsettings(self):
        # processor preferences
        self.autodtg = 1  # auto determine profile date/time as system date/time on clicking "START"
        self.autolocation = 1 #auto determine location with GPS
        self.autoid = 1 #autopopulate platform ID
        self.platformID = 'AFNNN'
        self.savelog = 1
        self.saveedf = 0
        self.savewav = 1
        self.savesig = 1
        self.dtgwarn = 1  # warn user if entered dtg is more than 12 hours old or after current system time (in future)
        self.renametabstodtg = 1  # auto rename tab to dtg when loading profile editor
        self.autosave = 0  # automatically save raw data before opening profile editor (otherwise brings up prompt asking if want to save)
        self.fftwindow = 0.3  # window to run FFT (in seconds)
        self.minfftratio = 0.5  # minimum signal to noise ratio to ID data
        self.minsiglev = 5E6  # minimum total signal level to receive data

        #profeditorpreferences
        self.useclimobottom = 1  # use climatology to ID bottom strikes
        self.overlayclimo = 1  # overlay the climatology on the plot
        self.comparetoclimo = 1  # check for climatology mismatch and display result on plot
        self.savefin = 1  # file types to save
        self.savejjvv = 1
        self.saveprof = 1
        self.saveloc = 1
        self.useoceanbottom = 1  # use NTOPO1 bathymetry data to ID bottom strikes
        self.checkforgaps = 1  # look for/correct gaps in profile due to false starts from VHF interference
        self.maxderiv = 1.5  # d2Tdz2 threshold to call a point an inflection point
        self.profres = 8 #profile minimum vertical resolution (m)

    def updatepreferences(self):

        if self.processortabwidgets["autodtg"].isChecked():
            self.autodtg = 1
        else:
            self.autodtg = 0

        if self.processortabwidgets["autolocation"].isChecked():
            self.autolocation = 1
        else:
            self.autolocation = 0

        if self.processortabwidgets["autoID"].isChecked():
            self.autoid = 1
        else:
            self.autoid = 0

        if self.processortabwidgets["savelog"].isChecked():
            self.savelog = 1
        else:
            self.savelog = 0

        if self.processortabwidgets["saveedf"].isChecked():
            self.saveedf = 1
        else:
            self.saveedf = 0

        if self.processortabwidgets["savewav"].isChecked():
            self.savewav = 1
        else:
            self.savewav = 0

        if self.processortabwidgets["savesig"].isChecked():
            self.savesig = 1
        else:
            self.savesig = 0

        if self.processortabwidgets["dtgwarn"].isChecked():
            self.dtgwarn = 1
        else:
            self.dtgwarn = 0

        if self.processortabwidgets["renametab"].isChecked():
            self.renametab = 1
        else:
            self.renametab = 0

        if self.processortabwidgets["autosave"].isChecked():
            self.autosave = 1
        else:
            self.autosave = 0

        self.fftwindow = float(self.processortabwidgets["fftwindow"].value())/100
        self.minsiglev = 10**(float(self.processortabwidgets["fftsiglev"].value())/100)
        self.minfftratio = float(self.processortabwidgets["fftratio"].value())/100

        self.platformID = self.processortabwidgets["IDedit"].text()

        if self.profeditortabwidgets["useclimobottom"].isChecked():
            self.useclimobottom = 1
        else:
            self.useclimobottom = 0

        if self.profeditortabwidgets["comparetoclimo"].isChecked():
            self.comparetoclimo = 1
        else:
            self.comparetoclimo = 0

        if self.profeditortabwidgets["overlayclimo"].isChecked():
            self.overlayclimo = 1
        else:
            self.overlayclimo = 0

        if self.profeditortabwidgets["savefin"].isChecked():
            self.savefin = 1
        else:
            self.savefin = 0

        if self.profeditortabwidgets["savejjvv"].isChecked():
            self.savejjvv = 1
        else:
            self.savejjvv = 0

        if self.profeditortabwidgets["saveprof"].isChecked():
            self.saveprof = 1
        else:
            self.saveprof = 0

        if self.profeditortabwidgets["saveloc"].isChecked():
            self.saveloc = 1
        else:
            self.saveloc = 0

        if self.profeditortabwidgets["useoceanbottom"].isChecked():
            self.useoceanbottom = 1
        else:
            self.useoceanbottom = 0

        if self.profeditortabwidgets["checkforgaps"].isChecked():
            self.checkforgaps = 1
        else:
            self.checkforgaps = 0

        self.profres = float(self.profeditortabwidgets["profres"].value())/10
        self.maxderiv = float(self.profeditortabwidgets["maxderiv"].value())/100


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
            if self.autodtg == 1:
                self.processortabwidgets["autodtg"].setChecked(True)
            self.processortabwidgets["autolocation"] = QCheckBox('Autopopulate Location') #3
            if self.autolocation == 1:
                self.processortabwidgets["autolocation"].setChecked(True)
            self.processortabwidgets["autoID"] = QCheckBox('Autopopulate Platform Identifier') #4
            if self.autoid == 1:
                self.processortabwidgets["autoID"].setChecked(True)
            self.processortabwidgets["IDlabel"] = QLabel('Platform Identifier:') #5
            self.processortabwidgets["IDedit"] = QLineEdit(self.platformID) #6

            self.processortabwidgets["filesavetypes"] = QLabel('Filetypes to save:       ') #7
            self.processortabwidgets["savelog"] = QCheckBox('LOG File') #8
            if self.savelog == 1:
                self.processortabwidgets["savelog"].setChecked(True)
            self.processortabwidgets["saveedf"] = QCheckBox('EDF File') #9
            if self.saveedf == 1:
                self.processortabwidgets["saveedf"].setChecked(True)
            self.processortabwidgets["savewav"] = QCheckBox('WAV File') #10
            if self.savewav == 1:
                self.processortabwidgets["savewav"].setChecked(True)
            self.processortabwidgets["savesig"] = QCheckBox('Signal Data') #11
            if self.savesig == 1:
                self.processortabwidgets["savesig"].setChecked(True)

            self.processortabwidgets["dtgwarn"] = QCheckBox('Warn if DTG is not within past 12 hours') #12
            if self.dtgwarn == 1:
                self.processortabwidgets["dtgwarn"].setChecked(True)
            self.processortabwidgets["renametab"] = QCheckBox('Auto-rename tab to DTG on transition to profile editing mode') #13
            if self.renametab == 1:
                self.processortabwidgets["renametab"].setChecked(True)
            self.processortabwidgets["autosave"] = QCheckBox('Autosave raw data files when transitioning to profile editor mode') #14
            if self.autosave == 1:
                self.processortabwidgets["autosave"].setChecked(True)

            self.processortabwidgets["fftwindowlabel"] = QLabel('FFT Window (s): ' +str(self.fftwindow).ljust(4,'0')) #15
            self.processortabwidgets["fftwindow"] = QSlider(Qt.Horizontal) #16
            self.processortabwidgets["fftwindow"].setValue(int(self.fftwindow * 100))
            self.processortabwidgets["fftwindow"].setMinimum(0)
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
            # formatting widgets
            self.processortabwidgets["IDlabel"].setAlignment(Qt.AlignCenter | Qt.AlignVCenter)

            # should be 19 entries
            widgetorder = ["autopopulatetitle", "autodtg", "autolocation", "autoID", "IDlabel",
                           "IDedit", "filesavetypes", "savelog", "saveedf","savewav", "savesig",
                           "dtgwarn", "renametab", "autosave", "fftwindowlabel", "fftwindow",
                           "fftsiglevlabel", "fftsiglev", "fftratiolabel","fftratio"]

            wcols = [1, 1, 1, 1, 1, 2, 4, 4, 4, 4, 4, 1, 1, 1, 5, 5, 5, 5, 5, 5]
            wrows = [1, 2, 3, 4, 5, 5, 1, 2, 3, 4, 5, 7, 8, 9, 2, 3, 5, 6, 8, 9]

            wrext = [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]
            wcolext = [2, 2, 2, 2, 1, 1, 1, 1, 1, 1, 1, 4, 4, 4, 1, 1, 1, 1, 1, 1]

            # adding user inputs
            for i, r, c, re, ce in zip(widgetorder, wrows, wcols, wrext, wcolext):
                self.processortablayout.addWidget(self.processortabwidgets[i], r, c, re, ce)

            # Applying other preferences to grid layout
            self.processortablayout.setColumnStretch(0, 0)
            self.processortablayout.setColumnStretch(1, 1)
            self.processortablayout.setColumnStretch(2, 1)
            self.processortablayout.setColumnStretch(3, 2)
            self.processortablayout.setColumnStretch(4, 3)
            for i in range(0,12):
                self.processortablayout.setRowStretch(i, 1)
            self.processortablayout.setRowStretch(11, 4)

            # making the current layout for the tab
            self.processortab.setLayout(self.processortablayout)

        except Exception:
            traceback.print_exc()
            self.posterror("Failed to build new processor tab")



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
            if self.useclimobottom == 1:
                self.profeditortabwidgets["useclimobottom"].setChecked(True)
            self.profeditortabwidgets["comparetoclimo"] = QCheckBox('Autocompare profile to climatology')  # 3
            if self.comparetoclimo == 1:
                self.profeditortabwidgets["comparetoclimo"].setChecked(True)
            self.profeditortabwidgets["overlayclimo"] = QCheckBox('Overlay climatology in saved plots')  # 4
            if self.overlayclimo == 1:
                self.profeditortabwidgets["overlayclimo"].setChecked(True)

            self.profeditortabwidgets["filesavetypes"] = QLabel('Filetypes to save:     ')  # 7
            self.profeditortabwidgets["savefin"] = QCheckBox('FIN File')  # 8
            if self.savefin == 1:
                self.profeditortabwidgets["savefin"].setChecked(True)
            self.profeditortabwidgets["savejjvv"] = QCheckBox('JJVV File')  # 9
            if self.savejjvv == 1:
                self.profeditortabwidgets["savejjvv"].setChecked(True)
            self.profeditortabwidgets["saveprof"] = QCheckBox('Profile PNG')  # 10
            if self.saveprof == 1:
                self.profeditortabwidgets["saveprof"].setChecked(True)
            self.profeditortabwidgets["saveloc"] = QCheckBox('Location PNG')  # 11
            if self.saveloc == 1:
                self.profeditortabwidgets["saveloc"].setChecked(True)

            self.profeditortabwidgets["useoceanbottom"] = QCheckBox(
                'ID bottom strikes with NOAA ETOPO1 bathymetry data')  # 12
            if self.useoceanbottom == 1:
                self.profeditortabwidgets["useoceanbottom"].setChecked(True)
            self.profeditortabwidgets["checkforgaps"] = QCheckBox('ID false starts due to VHF interference')  # 13
            if self.checkforgaps == 1:
                self.profeditortabwidgets["checkforgaps"].setChecked(True)

            self.profeditortabwidgets["profreslabel"] = QLabel(
                'Minimum Profile Resolution (m): ' + str(float(self.profres)).ljust(4,'0'))  # 15
            self.profeditortabwidgets["profres"] = QSlider(Qt.Horizontal)  # 16
            self.profeditortabwidgets["profres"].setValue(int(self.profres * 10))
            self.profeditortabwidgets["profres"].setMinimum(0)
            self.profeditortabwidgets["profres"].setMaximum(500)
            self.profeditortabwidgets["profres"].valueChanged[int].connect(self.changeprofres)

            self.profeditortabwidgets["maxderivlabel"] = QLabel(
                'Inflection Point Threshold (C/m<sup>2</sup>): ' + str(self.maxderiv).ljust(4,'0'))  # 17
            self.profeditortabwidgets["maxderiv"] = QSlider(Qt.Horizontal)  # 18
            self.profeditortabwidgets["maxderiv"].setMinimum(0)
            self.profeditortabwidgets["maxderiv"].setMaximum(400)
            self.profeditortabwidgets["maxderiv"].setValue(int(self.maxderiv * 100))
            self.profeditortabwidgets["maxderiv"].valueChanged[int].connect(self.changemaxderiv)

            # should be 19 entries
            widgetorder = ["climotitle", "useclimobottom", "comparetoclimo", "overlayclimo", "filesavetypes", "savefin",
                           "savejjvv",
                           "saveprof", "saveloc", "useoceanbottom", "checkforgaps", "profreslabel", "profres",
                           "maxderivlabel", "maxderiv"]

            wcols = [1, 1, 1, 1, 4, 4, 4, 4, 4, 1, 1, 5, 5, 5, 5]
            wrows = [1, 2, 3, 4, 1, 2, 3, 4, 5, 7, 8, 2, 3, 5, 6]

            wrext = [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]
            wcolext = [2, 2, 2, 2, 1, 1, 1, 1, 1, 4, 4, 1, 1, 1, 1]

            # adding user inputs
            for i, r, c, re, ce in zip(widgetorder, wrows, wcols, wrext, wcolext):
                self.profeditortablayout.addWidget(self.profeditortabwidgets[i], r, c, re, ce)

            # Applying other preferences to grid layout
            self.profeditortablayout.setColumnStretch(0, 0)
            self.profeditortablayout.setColumnStretch(1, 1)
            self.profeditortablayout.setColumnStretch(2, 1)
            self.profeditortablayout.setColumnStretch(3, 2)
            self.profeditortablayout.setColumnStretch(4, 3)
            for i in range(0, 12):
                self.profeditortablayout.setRowStretch(i, 1)
            self.profeditortablayout.setRowStretch(11, 4)

            # making the current layout for the tab
            self.profeditortab.setLayout(self.profeditortablayout)

        except Exception:
            traceback.print_exc()
            self.posterror("Failed to build profile editor tab!")
        finally:
            QApplication.restoreOverrideCursor()

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
                                   self.autosave, self.fftwindow, self.minfftratio, self.minsiglev, self.useclimobottom,
                                   self.overlayclimo, self.comparetoclimo, self.savefin, self.savejjvv, self.saveprof,
                                   self.saveloc, self.useoceanbottom, self.checkforgaps, self.maxderiv, self.profres)


    def resetdefaults(self):
        self.setdefaultsettings()

        if self.autodtg == 1:
            self.processortabwidgets["autodtg"].setChecked(True)
        else:
            self.processortabwidgets["autodtg"].setChecked(False)

        if self.autolocation == 1:
            self.processortabwidgets["autolocation"].setChecked(True)
        else:
            self.processortabwidgets["autolocation"].setChecked(False)

        if self.autoid == 1:
            self.processortabwidgets["autoID"].setChecked(True)
        else:
            self.processortabwidgets["autoID"].setChecked(False)

        if self.savelog == 1:
            self.processortabwidgets["savelog"].setChecked(True)
        else:
            self.processortabwidgets["savelog"].setChecked(False)

        if self.saveedf == 1:
            self.processortabwidgets["saveedf"].setChecked(True)
        else:
            self.processortabwidgets["saveedf"].setChecked(False)

        if self.savewav == 1:
            self.processortabwidgets["savewav"].setChecked(True)
        else:
            self.processortabwidgets["savewav"].setChecked(False)

        if self.savesig == 1:
            self.processortabwidgets["savesig"].setChecked(True)
        else:
            self.processortabwidgets["savesig"].setChecked(False)

        if self.dtgwarn == 1:
            self.processortabwidgets["dtgwarn"].setChecked(True)
        else:
            self.processortabwidgets["dtgwarn"].setChecked(False)

        if self.renametab == 1:
            self.processortabwidgets["renametab"].setChecked(True)
        else:
            self.processortabwidgets["renametab"].setChecked(False)

        if self.autosave == 1:
            self.processortabwidgets["autosave"].setChecked(True)
        else:
            self.processortabwidgets["autosave"].setChecked(False)

        self.processortabwidgets["fftwindowlabel"].setText('FFT Window (s): ' + str(self.fftwindow))  # 15
        self.processortabwidgets["fftwindow"].setValue(int(self.fftwindow * 100))

        sigsliderval = np.log10(self.minsiglev)
        self.processortabwidgets["fftsiglevlabel"].setText('Minimum Signal Level (log[x]): ' + str(np.round(sigsliderval, 2)).ljust(4, '0'))  # 17
        self.processortabwidgets["fftsiglev"].setValue(int(sigsliderval * 100))

        self.processortabwidgets["fftratiolabel"].setText('Minimum Signal Ratio (%): ' + str(np.round(self.minfftratio * 100)))  # 19
        self.processortabwidgets["fftratio"].setValue(int(self.minfftratio * 100))

        if self.useclimobottom == 1:
            self.profeditortabwidgets["useclimobottom"].setChecked(True)
        else:
            self.profeditortabwidgets["useclimobottom"].setChecked(False)

        if self.comparetoclimo == 1:
            self.profeditortabwidgets["comparetoclimo"].setChecked(True)
        else:
            self.profeditortabwidgets["comparetoclimo"].setChecked(False)

        if self.overlayclimo == 1:
            self.profeditortabwidgets["overlayclimo"].setChecked(True)
        else:
            self.profeditortabwidgets["overlayclimo"].setChecked(False)

        if self.savefin == 1:
            self.profeditortabwidgets["savefin"].setChecked(True)
        else:
            self.profeditortabwidgets["savefin"].setChecked(False)

        if self.savejjvv == 1:
            self.profeditortabwidgets["savejjvv"].setChecked(True)
        else:
            self.profeditortabwidgets["savejjvv"].setChecked(False)

        if self.saveprof == 1:
            self.profeditortabwidgets["saveprof"].setChecked(True)
        else:
            self.profeditortabwidgets["saveprof"].setChecked(False)

        if self.saveloc == 1:
            self.profeditortabwidgets["saveloc"].setChecked(True)
        else:
            self.profeditortabwidgets["saveloc"].setChecked(False)

        if self.useoceanbottom == 1:
            self.profeditortabwidgets["useoceanbottom"].setChecked(True)
        else:
            self.profeditortabwidgets["useoceanbottom"].setChecked(False)

        if self.checkforgaps == 1:
            self.profeditortabwidgets["checkforgaps"].setChecked(True)
        else:
            self.profeditortabwidgets["checkforgaps"].setChecked(False)

        self.profeditortabwidgets["profreslabel"].setText('Minimum Profile Resolution (m): ' + str(self.profres).ljust(4, '0'))  # 15
        self.profeditortabwidgets["profres"].setValue(int(self.profres * 10))

        self.profeditortabwidgets["maxderivlabel"].setText('Inflection Point Threshold (C/m<sup>2</sup>): ' + str(self.maxderiv).ljust(4, '0'))  # 17
        self.profeditortabwidgets["maxderiv"].setValue(int(self.maxderiv * 100))



    # =============================================================================
    #     TAB MANIPULATION OPTIONS, OTHER GENERAL FUNCTIONS
    # =============================================================================
    def whatTab(self):
        currentIndex = self.tabWidget.currentIndex()
        return currentIndex

    def renametab(self):
        try:
            curtab = int(self.whatTab())
            name, ok = QInputDialog.getText(self, 'Rename Current Tab', 'Enter new tab name:', QLineEdit.Normal,
                                            str(self.tabWidget.tabText(curtab)))
            if ok:
                self.tabWidget.setTabText(curtab, name)
        except Exception:
            traceback.print_exc()
            self.posterror("Failed to rename the current tab")

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


# SIGNAL SETUP HERE
class SettingsSignals(QObject):
    exported = pyqtSignal(int,int,int,str,int,int,int,int,int,int,int,float,float,float,int,int,int,int,int,int,int,int,int,float,float)
    closed = pyqtSignal(bool)