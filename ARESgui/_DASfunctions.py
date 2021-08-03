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
#   Signal Processor functions 
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


from platform import system as cursys

from os import path
from traceback import print_exc as trace_error

from PyQt5.QtWidgets import (QLineEdit, QLabel, QSpinBox, QPushButton, QWidget, QFileDialog, QComboBox, QGridLayout, QDoubleSpinBox, QTableWidget, QTableWidgetItem, QHeaderView, QProgressBar, QApplication, QMessageBox, QVBoxLayout)
from PyQt5.QtCore import QObjectCleanupHandler, Qt, pyqtSlot, pyqtSignal, QObject
from PyQt5.QtGui import QColor

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.pyplot as plt

import time as timemodule
import datetime as dt
import numpy as np
import wave

import qclib.VHFsignalprocessor as vsp
import qclib.GPS_COM_interaction as gps

from ._globalfunctions import (addnewtab, whatTab, renametab, setnewtabcolor, closecurrenttab, savedataincurtab, postwarning, posterror, postwarning_option, closeEvent, parsestringinputs)
from ._PEfunctions import continuetoqc

            
# =============================================================================
#     SIGNAL PROCESSOR TAB AND INPUTS HERE
# =============================================================================
def makenewprocessortab(self):     
    try:

        newtabnum,curtabstr = self.addnewtab()

        #also creates proffig and locfig so they will both be ready to go when the tab transitions from signal processor to profile editor
        self.alltabdata[curtabstr] = {"tab":QWidget(),"tablayout":QGridLayout(),"ProcessorFig":plt.figure(),"profileSaved":True,
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
        self.tabWidget.setTabText(newtabnum, "New Drop #" + str(self.totaltabs-1)) #-1 because first tab is misison tracker
        self.alltabdata[curtabstr]["tabnum"] = self.totaltabs #assigning unique, unchanging number to current tab
        self.alltabdata[curtabstr]["tablayout"].setSpacing(10)
        
        #ADDING FIGURE TO GRID LAYOUT
        self.alltabdata[curtabstr]["ProcessorCanvas"] = FigureCanvas(self.alltabdata[curtabstr]["ProcessorFig"]) 
        self.alltabdata[curtabstr]["tablayout"].addWidget(self.alltabdata[curtabstr]["ProcessorCanvas"],0,0,11,1)
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
        
        #default receiver selection if 1+ receivers are connected and not actively processing
        self.alltabdata[curtabstr]["datasource"] = "Initializing" #filler value for loop, overwritten after active receivers identified
        if len(winradiooptions) > 0:
            isnotbusy = [True]*len(winradiooptions)
            for iii,serialnum in enumerate(winradiooptions):
                for ctab in self.alltabdata:
                    if ctab != curtabstr and  self.alltabdata[ctab]["isprocessing"] and self.alltabdata[ctab]["datasource"] == serialnum:
                        isnotbusy[iii] = False
            if sum(isnotbusy) > 0:
                self.alltabdata[curtabstr]["tabwidgets"]["datasource"].setCurrentIndex(np.where(isnotbusy)[0][0]+2)
        
        #connect datasource dropdown to changer function, pull current datasource
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
        
        self.alltabdata[curtabstr]["tabwidgets"]["startprocessing"] = QPushButton('Start') #8
        self.alltabdata[curtabstr]["tabwidgets"]["startprocessing"].clicked.connect(self.startprocessor)
        self.alltabdata[curtabstr]["tabwidgets"]["stopprocessing"] = QPushButton('Stop') #9
        self.alltabdata[curtabstr]["tabwidgets"]["stopprocessing"].clicked.connect(self.stopprocessor)
        self.alltabdata[curtabstr]["tabwidgets"]["processprofile"] = QPushButton('Process Profile') #10
        self.alltabdata[curtabstr]["tabwidgets"]["processprofile"].clicked.connect(self.processprofile)
        self.alltabdata[curtabstr]["tabwidgets"]["saveprofile"] = QPushButton('Save Profile') #21
        self.alltabdata[curtabstr]["tabwidgets"]["saveprofile"].clicked.connect(self.savedataincurtab)
        
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
        widgetorder = ["datasourcetitle","refreshdataoptions","datasource","channeltitle","freqtitle","vhfchannel","vhffreq","startprocessing","stopprocessing","processprofile","saveprofile","datetitle","dateedit","timetitle","timeedit","lattitle","latedit","lontitle","lonedit","idtitle","idedit"]
        wrows     = [1,1,2,3,4,3,4,5,6,7,6,1,1,2,2,3,3,4,4,5,5]
        wcols     = [3,4,3,3,3,4,4,3,3,6,6,6,7,6,7,6,7,6,7,6,7]
        wrext     = [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1]
        wcolext   = [1,1,2,1,1,1,1,2,2,2,2,1,1,1,1,1,1,1,1,1,1]
        

        #adding user inputs
        for i,r,c,re,ce in zip(widgetorder,wrows,wcols,wrext,wcolext):
            self.alltabdata[curtabstr]["tabwidgets"][i].setFont(self.labelfont)
            self.alltabdata[curtabstr]["tablayout"].addWidget(self.alltabdata[curtabstr]["tabwidgets"][i],r,c,re,ce)
                
        #adding table widget after all other buttons populated
        self.alltabdata[curtabstr]["tabwidgets"]["table"] = QTableWidget() #19
        self.alltabdata[curtabstr]["tabwidgets"]["table"].setColumnCount(6)
        self.alltabdata[curtabstr]["tabwidgets"]["table"].setRowCount(0) 
        self.alltabdata[curtabstr]["tabwidgets"]["table"].setHorizontalHeaderLabels(('Time (s)', 'Fp (Hz)', 'Sp (dB)', 'Rp (%)' ,'Depth (m)','Temp (C)'))
        self.alltabdata[curtabstr]["tabwidgets"]["table"].setFont(self.labelfont)
        self.alltabdata[curtabstr]["tabwidgets"]["table"].verticalHeader().setVisible(False)
        self.alltabdata[curtabstr]["tabwidgets"]["table"].setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff) #removes scroll bars
        self.alltabdata[curtabstr]["tabwidgets"]["tableheader"] = self.alltabdata[curtabstr]["tabwidgets"]["table"].horizontalHeader() 
        self.alltabdata[curtabstr]["tabwidgets"]["tableheader"].setFont(self.labelfont)
        for ii in range(0,6):
            self.alltabdata[curtabstr]["tabwidgets"]["tableheader"].setSectionResizeMode(ii, QHeaderView.Stretch)  
        self.alltabdata[curtabstr]["tabwidgets"]["table"].setEditTriggers(QTableWidget.NoEditTriggers)
        self.alltabdata[curtabstr]["tablayout"].addWidget(self.alltabdata[curtabstr]["tabwidgets"]["table"],9,2,2,7)

        #adjusting stretch factors for all rows/columns
        colstretch = [8,0,1,1,1,1,1,1,1]
        for col,cstr in enumerate(colstretch):
            self.alltabdata[curtabstr]["tablayout"].setColumnStretch(col,cstr)
        rowstretch = [1,1,1,1,1,1,1,1,1,10]
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
                if ctab != curtabstr and  self.alltabdata[ctab]["isprocessing"] and self.alltabdata[ctab]["datasource"] == woption:
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
        #updates fft settings for any active tabs
        for ctab in self.alltabdata:
            if self.alltabdata[ctab]["isprocessing"]: 
                self.alltabdata[ctab]["processor"].changethresholds(self.settingsdict["fftwindow"], self.settingsdict["minfftratio"], self.settingsdict["minsiglev"], self.settingsdict["triggerfftratio"], self.settingsdict["triggersiglev"], self.settingsdict["tcoeff"], self.settingsdict["zcoeff"], self.settingsdict["flims"])
    except Exception:
        trace_error()
        self.posterror("Error updating FFT settings!")
        
        
        
#starting signal processing thread
def startprocessor(self):
    try:
        curtabstr = "Tab " + str(self.whatTab())
        if not self.alltabdata[curtabstr]["isprocessing"]:
            
            status, datasource, newsource = self.prepprocessor(curtabstr)
            if status:
                self.runprocessor(curtabstr, datasource, newsource)
                self.alltabdata[curtabstr]["profileSaved"] = False
                self.add_asterisk()
                
    except Exception:
        trace_error()
        self.posterror("Failed to start processor!")
        
        
        
        
def prepprocessor(self, curtabstr):
    datasource = self.alltabdata[curtabstr]["datasource"]
    #running processor here
    
    #if too many signal processor threads are already running
    if self.threadpool.activeThreadCount() + 1 > self.threadpool.maxThreadCount():
        self.postwarning("The maximum number of simultaneous processing threads has been exceeded. This processor will automatically begin collecting data when STOP is selected on another tab.")
        return False,"No","No"
        
    #checks to make sure that this tab hasn't been used to process from a different source (e.g. user is attempting to switch from "Test" to "Audio" or a receiver), raise error if so
    if datasource == 'Audio':
        newsource = "audio"
    elif datasource == "Test":
        newsource = "test"
    else:
        newsource = "rf"
        
    oldsource = self.alltabdata[curtabstr]["source"]
    if oldsource == "none":
        pass #wait to change source until method has made it past possible catching points (so user can restart in same tab)
        
    elif oldsource == "audio": #once you have stopped an audio processing tab, ARES won't let you restart it
        self.postwarning(f"You cannot restart an audio processing instance after stopping. Please open a new tab to process additional audio files.")
        return False,"No","No"
        
    elif oldsource != newsource: #if "Start" has been selected previously and a source type (test, audio, or rf) was assigned
        self.postwarning(f"You cannot switch between Test, Audio, and RF data sources after starting processing. Please open a new tab to process a profile from a different source and reset this profile's source to {oldsource} to continue processing.")
        return False,"No","No"

    if datasource == 'Audio': #gets audio file to process
        try:
            # getting filename
            fname, ok = QFileDialog.getOpenFileName(self, 'Open file',self.defaultfilereaddir,"Source Data Files (*.WAV *.Wav *.wav *PCM *Pcm *pcm *MP3 *Mp3 *mp3)","",self.fileoptions)
            if not ok or fname == "":
                self.alltabdata[curtabstr]["isprocessing"] = False
                return False,"No","No"
            else:
                splitpath = path.split(fname)
                self.defaultfilereaddir = splitpath[0]
                
            #determining which channel to use
            #selec-2=no box opened, -1 = box opened, 0 = box closed w/t selection, > 0 = selected channel
            try:
                file_info = wave.open(fname)
            except:
                self.postwarning("Unable to read audio file")
                return False,"No","No"
                
            nchannels = file_info.getnchannels()
            if nchannels == 1:
                datasource = f"Audio-0001{fname}"
            else:
                if self.selectedChannel >= -1: #active tab already opened 
                    self.postwarning("An audio channel selector dialog box has already been opened in another tab. Please close that box before processing an audio file with multiple channels in this tab.")
                    return False,"No","No"
                    
                else:
                    self.audioChannelSelector = AudioWindow(nchannels, curtabstr, fname) #creating and connecting window
                    self.audioChannelSelector.signals.closed.connect(self.audioWindowClosed)
                    self.audioChannelSelector.show() #bring window to front
                    self.audioChannelSelector.raise_()
                    self.audioChannelSelector.activateWindow()
                    
                    return False,"No","No"
            
        except Exception:
            self.posterror("Failed to execute audio processor!")
            trace_error()

    elif datasource != "Test":
        
        #checks to make sure current receiver isn't busy
        for ctab in self.alltabdata:
            if ctab != curtabstr and self.alltabdata[ctab]["isprocessing"] and self.alltabdata[ctab]["datasource"] == datasource:
                self.posterror("This WINRADIO appears to currently be in use! Please stop any other active tabs using this device before proceeding.")
                return False,"No"
    
    #success            
    return True, datasource, newsource
    
    
    
    
def runprocessor(self, curtabstr, datasource, newsource):
                
    #gets current tab number
    curtabnum = self.alltabdata[curtabstr]["tabnum"]
    
    #gets rid of scroll bar on table
    self.alltabdata[curtabstr]["tabwidgets"]["table"].setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    
    autopopulate = False #tracking whether to autopopulate fields (waits until after thread has been started to prevent from hanging on GPS stream)

    #saving start time for current drop
    if self.alltabdata[curtabstr]["rawdata"]["starttime"] == 0:
        starttime = dt.datetime.utcnow()
        self.alltabdata[curtabstr]["rawdata"]["starttime"] = starttime
        
        #autopopulating selected fields
        if datasource[:5] != 'Audio': #but not if reprocessing from audio file
            autopopulate = True
                
    else:
        starttime = self.alltabdata[curtabstr]["rawdata"]["starttime"]
        
    #this should never happen (if there is no DLL loaded there shouldn't be any receivers detected), but just in case
    if self.wrdll == 0 and datasource != 'Test' and datasource[:5] != 'Audio':
        self.postwarning("The WiNRADIO driver was not successfully loaded! Please restart the program in order to initiate a processing tab with a connected WiNRADIO")
        return
    elif datasource[:5] == 'Audio': #build audio progress bar
        # building progress bar
        self.alltabdata[curtabstr]["tabwidgets"]["audioprogressbar"] = QProgressBar()
        self.alltabdata[curtabstr]["tablayout"].addWidget(
            self.alltabdata[curtabstr]["tabwidgets"]["audioprogressbar"], 8, 2, 1, 7)
        self.alltabdata[curtabstr]["tabwidgets"]["audioprogressbar"].setValue(0)
        QApplication.processEvents()
        
        
    #initializing thread, connecting signals/slots
    self.alltabdata[curtabstr]["source"] = newsource #assign current source as processor if previously unassigned (no restarting in this tab beyond this point)
    vhffreq = self.alltabdata[curtabstr]["tabwidgets"]["vhffreq"].value()
    self.alltabdata[curtabstr]["processor"] = vsp.ThreadProcessor(self.wrdll, datasource, vhffreq, curtabnum,  starttime, self.alltabdata[curtabstr]["rawdata"]["istriggered"], self.alltabdata[curtabstr]["rawdata"]["firstpointtime"], self.settingsdict["fftwindow"], self.settingsdict["minfftratio"],self.settingsdict["minsiglev"], self.settingsdict["triggerfftratio"],self.settingsdict["triggersiglev"], self.settingsdict["tcoeff"], self.settingsdict["zcoeff"], self.settingsdict["flims"], self.slash, self.tempdir)
    
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
    
    #autopopulating fields if necessary
    if autopopulate:
        if self.settingsdict["autodtg"]:#populates date and time if requested
            curdatestr = str(starttime.year) + str(starttime.month).zfill(2) + str(starttime.day).zfill(2)
            self.alltabdata[curtabstr]["tabwidgets"]["dateedit"].setText(curdatestr)
            curtimestr = str(starttime.hour).zfill(2) + str(starttime.minute).zfill(2)
            self.alltabdata[curtabstr]["tabwidgets"]["timeedit"].setText(curtimestr)
        if self.settingsdict["autolocation"] and self.settingsdict["comport"] != 'n':
            if abs((self.datetime - starttime).total_seconds()) <= 30: #GPS ob within 30 seconds
                self.alltabdata[curtabstr]["tabwidgets"]["latedit"].setText(str(round(self.lat,3)))
                self.alltabdata[curtabstr]["tabwidgets"]["lonedit"].setText(str(round(self.lon,3)))
            else:
                self.postwarning("Last GPS fix expired (> 30 seconds old)!")
        if self.settingsdict["autoid"]:
            self.alltabdata[curtabstr]["tabwidgets"]["idedit"].setText(self.settingsdict["platformid"])
            
    
        
#aborting processor
def stopprocessor(self):
    try:
        curtabstr = "Tab " + str(self.whatTab())
        if self.alltabdata[curtabstr]["isprocessing"]:
            curtabstr = "Tab " + str(self.whatTab())
            datasource = self.alltabdata[curtabstr]["datasource"]
            
            self.alltabdata[curtabstr]["isprocessing"] = False #processing is done
            self.alltabdata[curtabstr]["processor"].abort()
            self.alltabdata[curtabstr]["tabwidgets"]["table"].setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
                
    except Exception:
        trace_error()
        self.posterror("Failed to stop processor!")
            



# =============================================================================
#        POPUP WINDOW FOR AUDIO CHANNEL SELECTION
# =============================================================================

class AudioWindow(QWidget):
    
    def __init__(self, nchannels, curtabstr, fname):
        super(AudioWindow, self).__init__()
        
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)
        
        self.selectedChannel = 1
        self.wasClosed = False
        self.nchannels = nchannels
        self.fname = fname
        self.curtabstr = curtabstr
        
        self.signals = AudioWindowSignals()
        
        self.title = QLabel("Select channel to read\n(for 2-channel WAV files,\nCh1 = left and Ch2 = right):")
        self.spinbox = QSpinBox()
        self.spinbox.setMinimum(1)
        self.spinbox.setMaximum(self.nchannels)
        self.spinbox.setSingleStep(1)
        self.spinbox.setValue(self.selectedChannel)
        self.finish = QPushButton("Select Channel")
        self.finish.clicked.connect(self.selectChannel)
        
        self.layout.addWidget(self.title)
        self.layout.addWidget(self.spinbox)
        self.layout.addWidget(self.finish)
        
        self.show()
                
        
    def selectChannel(self):
        self.selectedChannel = self.spinbox.value()
        
        #format is Audio<channel#><filename> e.g. Audio0002/My/File.WAV
        #allowing for 5-digit channels since WAV file channel is a 16-bit integer, can go to 65,536
        self.datasource = f"Audio{self.selectedChannel:05d}{self.fname}" 
        
        #emit signal
        self.signals.closed.emit(True, self.curtabstr, self.datasource)
        
        #close dialogue box
        self.wasClosed = True
        self.close()
        
        
    # add warning message on exit
    def closeEvent(self, event):
        event.accept()
        if not self.wasClosed:
            self.signals.closed.emit(False, "No", "No")
            self.wasClosed = True
            
#initializing signals for data to be passed back to main loop
class AudioWindowSignals(QObject): 
    closed = pyqtSignal(int, str, str)


#slot in main program to close window (only one channel selector window can be open at a time)
@pyqtSlot(int, str, str)
def audioWindowClosed(self, wasGood, curtabstr, datasource):
    if wasGood:
        self.runprocessor(curtabstr, datasource, "audio")
    
    



    
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
@pyqtSlot(int,float,float,float,float,float,float,int)
def updateUIinfo(self,plottabnum,ctemp,cdepth,cfreq,cact,cratio,ctime,i):
    try:
        plottabstr = self.gettabstrfromnum(plottabnum)
        
        if self.alltabdata[plottabstr]["isprocessing"]:
            
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
                    except IndexError:
                        pass
                        
                    self.alltabdata[plottabstr]["ProcessorAx"].plot(self.alltabdata[plottabstr]["rawdata"]["temperature"],self.alltabdata[plottabstr]["rawdata"]["depth"],color='k')
                    self.alltabdata[plottabstr]["ProcessorCanvas"].draw()
    
                #coloring new cell based on whether or not it has good data
                stars = '------'
                if np.isnan(ctemp):
                    ctemp = stars
                    cdepth = stars
                    curcolor = QColor(200, 200, 200) #light gray
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
                tableact = QTableWidgetItem(str(cact))
                tableact.setBackground(curcolor)
                tablerat = QTableWidgetItem(str(cratio))
                tablerat.setBackground(curcolor)
    
                table = self.alltabdata[plottabstr]["tabwidgets"]["table"]
                crow = table.rowCount()
                table.insertRow(crow)
                table.setItem(crow, 0, tabletime)
                table.setItem(crow, 1, tablefreq)
                table.setItem(crow, 2, tableact)
                table.setItem(crow, 3, tablerat)
                table.setItem(crow, 4, tabledepth)
                table.setItem(crow, 5, tabletemp)
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
        self.alltabdata[plottabstr]["isprocessing"] = False
        timemodule.sleep(0.25)
        self.alltabdata[plottabstr]["tabwidgets"]["table"].setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)

        if "audioprogressbar" in self.alltabdata[plottabstr]["tabwidgets"]:
            self.alltabdata[plottabstr]["tabwidgets"]["audioprogressbar"].deleteLater()

    except Exception:
        self.posterror("Failed to complete final UI update!")
        trace_error()

        
        
#posts message in main GUI if thread processor fails for some reason
@pyqtSlot(int,int)
def failedWRmessage(self,plottabnum,messagenum):
    try:
        plottabstr = self.gettabstrfromnum(plottabnum)
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
            
        #reset data source if signal processor failed to start
        if messagenum in [1,2,3,4,5,6,7,9,11,12]:
            self.alltabdata[plottabstr]["source"] = "none"
    
    except Exception:
        trace_error()
        self.posterror("Error in signal processor thread triggered secondary error in handling!")

        
        
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
        if not self.alltabdata[curtabstr]["profileSaved"]: #only if it hasn't been saved
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
        
    