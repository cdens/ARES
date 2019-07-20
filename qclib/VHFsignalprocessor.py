#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import numpy as np
from scipy.io import wavfile #for wav
from pydub import AudioSegment #for mp3

from PyQt5.QtCore import pyqtSlot, pyqtSignal, QObject
from PyQt5.Qt import QRunnable

import qclib.tropicfileinteraction as tfio

import time as timemodule
import datetime as dt

import traceback

from sys import getsizeof
from os import remove
from ctypes import (Structure, pointer, c_int, c_ulong, c_ulonglong, c_char,
                    c_char_p, c_void_p, POINTER, c_int16, cast, WINFUNCTYPE, CFUNCTYPE)

#convert time(s) into depth (m)
def timetodepth(time):
    depth = 1.52*time
    return depth
    
#convert frequency (Hz) to temperature (C)
def freqtotemp(frequency):
    temp = (frequency - 1440)/36
    return temp

#function to run fft here
def dofft(pcmdata,fs):
    # conducting fft, converting to real space
    rawfft = np.fft.fft(pcmdata)
    fftdata = np.abs(rawfft)

    N = len(pcmdata)
    T = N/fs
    df = 1 / T
    f = np.array([df * n if n < N / 2 else df * (n - N) for n in range(N)])
    ind = np.greater_equal(f, 0)
    f = f[ind]
    fftdata = fftdata[ind]

    # pulls max frequency, appends
    freq = f[np.argmax(fftdata)]

    # constraining by realistic temperatures (-3 to 35 C)
    if freq > 2800 or freq < 1300:
        freq = 0

    return freq
    
#table lookup for VHF channels and frequencies
def channelandfrequencylookup(value,direction):
    
    allfreqs = np.arange(136,173.51,0.375)
    allfreqs = np.delete(allfreqs,np.where(allfreqs == 161.5)[0][0])
    allfreqs = np.delete(allfreqs,np.where(allfreqs == 161.875)[0][0])
    
    allchannels = np.arange(32,99.1,1)
    cha = np.arange(1,16.1,1)
    chb = np.arange(17,31.1,1)
    for i in range(len(chb)):
        allchannels = np.append(allchannels,cha[i])
        allchannels = np.append(allchannels,chb[i])
    allchannels = np.append(allchannels,cha[15])

    if direction == 'findfrequency':
        try:
            outval = allfreqs[np.where(allchannels == value)[0][0]]
            correctedval = value
        except:
            correctedval = allchannels[np.argmin(abs(allchannels-value))]
            outval = allfreqs[np.where(allchannels == correctedval)[0][0]]
            
    elif direction == 'findchannel':
        try:
            outval = allchannels[np.where(allfreqs == value)[0][0]]
            correctedval = value
        except:
            correctedval = allfreqs[np.argmin(abs(allfreqs-value))]
            outval = allchannels[np.where(allfreqs == correctedval)[0][0]]

    else: #incorrect option
        print("Incorrect channel/frequency lookup selection!")
        outval = 0
        correctedval = 0
    
    return outval,correctedval


# =============================================================================
#  READ SIGNAL FROM WINRADIO, OUTPUT TO PLOT, TABLE, AND DATA
# =============================================================================


class ThreadProcessor(QRunnable):

    @CFUNCTYPE(None, c_void_p, c_void_p, c_ulong, c_ulong)
    def updateaudiobuffer(streampointer_int, bufferpointer_int, size, samplerate):
        bufferlength = int(size / 2)
        bufferpointer = cast(bufferpointer_int, POINTER(c_int16 * bufferlength))
        bufferdata = bufferpointer.contents
        audiostream.extend(bufferdata[:])
        # self.f_s = samplerate
        # self.audiostream.extend(bufferdata[:])

    def __init__(self, wrdll, datasource, vhffreq, curtabnum, starttime, istriggered, firstpointtime, *args, **kwargs):
        super(ThreadProcessor, self).__init__()

        #UI inputs
        self.curtabnum = curtabnum
        self.starttime = starttime
        self.istriggered = istriggered
        self.firstpointtime = firstpointtime

        self.keepgoing = True  # signal connections
        self.signals = ThreadProcessorSignals()

        # initialize audio data variables
        self.f_s = 64000  # default value
        global audiostream
        audiostream = [0] * 64000
        self.audiostream = [0] * 64000

        #saves library
        self.wrdll = wrdll

        #initialize winradio
        self.serial = datasource  # translate winradio identifier
        self.serialnum_2WR = c_char_p(self.serial.encode('utf-8'))

        self.hradio = self.wrdll.Open(self.serialnum_2WR)
        if self.hradio == 0:
            self.keepgoing = False
            self.signals.failed.emit(0)
            return

        try:
            #power on- kill if failed
            if wrdll.SetPower(self.hradio, True) == 0:
                self.keepgoing = False
                self.signals.failed.emit(1)
                self.wrdll.CloseRadioDevice(self.hradio)
                return

            #initialize demodulator- kill if failed
            if wrdll.InitializeDemodulator(self.hradio) == 0:
                self.keepgoing = False
                self.signals.failed.emit(2)
                self.wrdll.CloseRadioDevice(self.hradio)
                return

            #change frequency- kill if failed
            self.vhffreq_2WR = c_ulong(int(vhffreq * 1E6))
            if self.wrdll.SetFrequency(self.hradio, self.vhffreq_2WR) == 0:
                self.keepgoing = False
                self.signals.failed.emit(3)
                self.wrdll.CloseRadioDevice(self.hradio)
                return

            #set volume- warn if failed
            if self.wrdll.SetVolume(self.hradio, 31) == 0:
                self.signals.failed.emit(5)

        except Exception:
            self.keepgoing = False
            self.signals.failed.emit(4)
            self.wrdll.SetupStreams(self.hradio, None, None, None, None)
            self.wrdll.CloseRadioDevice(self.hradio) #closes the radio if initialization fails
            traceback.print_exc()
    
    @pyqtSlot()
    def run(self):
        curtabnum = self.curtabnum

        # initializes audio callback function
        # if self.wrdll.SetupStreams(self.hradio, None, None, None, None) == 0:
        if self.wrdll.SetupStreams(self.hradio, None, None, self.updateaudiobuffer, c_int(self.curtabnum)) == 0:
            self.signals.failed.emit(6)
            self.wrdll.CloseRadioDevice(self.hradio)
        else:
            timemodule.sleep(0.3)  # gives the buffer time to populate

        global audiostream

        try:
            #setting up while loop- terminates when user clicks "STOP"
            i= -1
            while self.keepgoing:
                i += 1
                
                #listens to current frequency, gets sound level and corresponding time
                sigstrength = self.wrdll.GetSignalStrengthdBm(self.hradio)
                if sigstrength == int(-1):
                    sigstrength = -15000
                sigstrength = float(sigstrength)/10 #signal strength in dBm
                if sigstrength >= -75:
                    cfreq = dofft(audiostream[-int(self.f_s * 0.1):], self.f_s)
                else:
                    cfreq = 0

                curtime = dt.datetime.utcnow() #current time
                
                #finds time from profile start in seconds
                deltat = curtime - self.starttime
                ctime = deltat.total_seconds()
                
                #if statement to trigger reciever after first frequency arrives
                if (not self.istriggered) and cfreq != 0:
                    self.istriggered = True
                    self.firstpointtime = ctime
                    self.signals.triggered.emit(curtabnum,ctime)
                
                if self.istriggered:
                    timefromtrigger = ctime - self.firstpointtime
                    cdepth = timetodepth(timefromtrigger)
                
                    if cfreq != 0:
                        ctemp = freqtotemp(cfreq)
                    else:
                        ctemp = np.NaN
                        
                else: #if processor hasnt been triggered yet
                    cdepth = np.NaN
                    ctemp = np.NaN
                
                #tells GUI to update data structure, plot, and table
                ctemp = np.round(ctemp,2)
                cdepth = np.round(cdepth,1)
                cfreq = np.round(cfreq,2)
                ctime = np.round(ctime,1)
                sigstrength = np.round(sigstrength,2)
                self.signals.iterated.emit(curtabnum,ctemp,cdepth,cfreq,sigstrength,ctime,i)
                timemodule.sleep(0.1) #pauses before getting next point
                
        except Exception:
            self.keepgoing = False
            self.wrdll.SetupStreams(self.hradio, None, None, None, None)
            self.wrdll.CloseRadioDevice(self.hradio)
            self.signals.failed.emit(4)
            traceback.print_exc() #if there is an error, terminates processing
            self.signals.terminated.emit(curtabnum)


    @pyqtSlot()
    def abort(self):
        curtabnum = self.curtabnum
        self.keepgoing = False #kills while loop
        self.wrdll.SetupStreams(self.hradio, None, None, None, None)
        self.wrdll.CloseRadioDevice(self.hradio)
        self.signals.terminated.emit(curtabnum) #emits signal that processor has been terminated
        
    @pyqtSlot(float)
    def changecurrentfrequency(self,newfreq):
        # change frequency- kill if failed
        self.vhffreq_2WR = c_ulong(int(newfreq * 1E6))
        if self.wrdll.SetFrequency(self.hradio, self.vhffreq_2WR) == 0:
            self.signals.failed.emit(3)
            self.wrdll.SetupStreams(self.hradio, None, None, None, None)
            self.wrdll.CloseRadioDevice(self.hradio)
            return
        
        
class ThreadProcessorExample(QRunnable): #tests signal processor tab with LOG file data
    def __init__(self, curtabnum, *args, **kwargs):
        super(ThreadProcessorExample, self).__init__()
        #UI inputs
        self.curtabnum = curtabnum

        self.keepgoing = True #signal connections
        self.signals = ThreadProcessorSignals()

    @pyqtSlot()
    def run(self):
        curtabnum = self.curtabnum
        try:
            logfile = 'testdata/201508261140.DTA' #temp code
            temperature,depth,time,frequency = tfio.readlogfile_alldata(logfile)
            
            #setting up while loop- terminates when user clicks "STOP"
            i= -1
            while self.keepgoing:
                i += 1
                
                ctime = time[i]
                cfreq = frequency[i]
                cdepth = depth[i]
                ctemp = temperature[i]

                #tells GUI to update data structure, plot, and table
                self.signals.iterated.emit(curtabnum,ctemp,cdepth,cfreq,-125.0,ctime,i)
                timemodule.sleep(0.05) #pauses before getting next point

        except Exception:
            traceback.print_exc() #if there is an error, terminates processing
            self.signals.terminated.emit(curtabnum)

    @pyqtSlot()
    def abort(self):
        curtabnum = self.curtabnum
        self.keepgoing = False #kills while loop
        self.signals.terminated.emit(curtabnum) #emits signal that processor has been terminated
    
class ThreadProcessorSignals(QObject):
    iterated = pyqtSignal(int,float,float,float,float,float,int) #signal to add another entry to raw data arrays
    triggered = pyqtSignal(int,float) #signal that the first tone has been detected
    terminated = pyqtSignal(int) #signal that the loop has been terminated (by user input or program error)
    failed = pyqtSignal(int)



# =============================================================================
# C++ INTEGRATED FUNCTIONS FOR WINRADIO:
# =============================================================================
# initialize radioinfo structure
class Radiofeatures(Structure):
    _fields_ = [("ExtRef", c_int), ("FMWEnabled", c_int), ("Reserved", c_int)]

class RADIO_INFO2(Structure):
    _fields_ = [("bLength", c_ulong), ("szSerNum", c_char*9), ("szProdName", c_char*9), ("MinFreq", c_ulonglong),("MaxFreq", c_ulonglong), ("Features", Radiofeatures)]


#gets list of current winradios
def listwinradios(wrdll):

    # creating array of RADIO_INFO2 structures to load info from GetRadioList() command
    radiolistarray = (RADIO_INFO2 * 50)()
    radiolistpointer = pointer(radiolistarray)
    radiolistsize = getsizeof(radiolistarray)
    radiolistinfosize = c_int(0)
    radiolistinfosizepointer = pointer(radiolistinfosize)

    # getting list of all connected winradio info
    winradioserials = []
    numradios = wrdll.GetRadioList(radiolistpointer, radiolistsize, radiolistinfosizepointer)
    lenradiolist = radiolistarray.__len__()
    if numradios > lenradiolist:
        numradios = lenradiolist
        print("Warning: Buffered array has insufficient size to return information for all winradios")
    for i in range(numradios):
        currentserial = radiolistarray[i].szSerNum.decode('utf-8')
        winradioserials.append(currentserial)

    return winradioserials



#gets current tone from specified winradio
def listentowinradio(wrdll,hradio):
    frequency = 0
    return frequency







# =============================================================================
# AUDIO FILE PROCESSOR
# =============================================================================
class AudioProcessor(QRunnable): #processes data from audio file
    def __init__(self, curtabnum, res, filename, *args, **kwargs):
        
        super(AudioProcessor, self).__init__()
        
        #UI inputs
        self.curtabnum = curtabnum
        self.res = res
        self.filename = filename

        self.keepgoing = True #signal connections
        self.signals = AudioProcessorSignals()
    
    @pyqtSlot()
    def run(self):
        try:
            res = self.res


            
            #reading file, getting raw times/sound amplitude
            if self.filename[-4:].lower() == '.wav':
                f_s, snd = wavfile.read(self.filename)
                x = snd[:,0]
            elif self.filename[-4:].lower() == '.pcm':
                f_s, snd = wavfile.read(self.filename)
                x = snd[:,0]
            elif self.filename[-4:].lower() == '.mp3':
                sound = AudioSegment.from_mp3(self.filename)
                sound.export("tempaudio.wav", format="wav")
                f_s, snd = wavfile.read('tempaudio.wav')
                x = snd[:, 0]
                remove('tempaudio.wav')
            else:
                self.signals.aborted.emit(self.curtabnum, 2)
                return

            # initializing values
            alltime = np.arange(0, len(x), 1) / f_s
            time = np.array([])
            frequency = np.array([])
            maxtime = np.floor(max(alltime))
            dT = 1/f_s
            
            np.warnings.filterwarnings('ignore')
            
            #running fast fourier transform to get maximum frequency
            for ctrtime in np.arange(0,maxtime,res):
                ind = np.all([np.greater_equal(alltime,ctrtime-0.15),np.less_equal(alltime,ctrtime + 0.15)],axis=0)
                curx = x[ind]
    
                #conducting fft, converting to real space
                rawfft = np.fft.fft(curx)
                fftdata = np.abs(rawfft)

                N = len(curx)
                T = dT*N
                df = 1/T
                f = np.array([df*n if n<N/2 else df*(n-N) for n in range(N)])
                ind = np.greater_equal(f,0)
                f = f[ind]
                fftdata = fftdata[ind]
                
                #pulls max frequency, appends
                curfreq = f[np.argmax(fftdata)]
                time = np.append(time,ctrtime,axis=None)
                frequency = np.append(frequency,curfreq,axis=None)

                #emits a progress update every 10 iterations
                if ctrtime%(res*10) == 0:
                    self.signals.updateprogress.emit(self.curtabnum,int(ctrtime/maxtime*100)) #emit progress update
                    
                #checks to make sure user hasn't aborted the program
                if not self.keepgoing:
                    self.signals.aborted.emit(self.curtabnum,0)
                    return
            
            #constraining by realistic temperatures (-3 to 35 C)
            frequency[frequency > 2800] = np.NaN
            frequency[frequency < 1300] = np.NaN
            
            temperature = freqtotemp(frequency)
            depth = timetodepth(time)
        
            #identifying profile start
            percent = []
            for i in range(len(temperature)):
                ind = np.all([np.greater_equal(depth,depth[i]-10),np.less_equal(depth,depth[i]+10)],axis=0)
                curtemp = temperature[ind]
                isnan = np.isnan(curtemp)
                percent.append(1-np.sum(isnan)/len(curtemp))
            firstdepth = depth[np.where(np.asarray(percent) >= 0.7)[0][0]]
            ind = depth >= firstdepth
            depth = depth - firstdepth

            for i in range(len(ind)):
                if not ind[i]:
                    depth[i] = np.NaN
                    temperature[i] = np.NaN
                    frequency[i] = 0

            temperature = np.round(temperature, 2)
            depth = np.round(depth, 1)
            frequency = np.round(frequency, 2)
            time = np.round(time, 1)

            self.signals.finished.emit(self.curtabnum,temperature,depth,frequency,time)
        except Exception:
            traceback.print_exc() #if there is an error, terminates processing
            self.signals.aborted.emit(self.curtabnum,1)
    
    @pyqtSlot()
    def abort(self):
        self.keepgoing = False


class AudioProcessorSignals(QObject):
    updateprogress = pyqtSignal(int,int) #signal to add another entry to raw data arrays
    aborted = pyqtSignal(int,int) #signal that the loop has been terminated (by user input or program error)
    finished = pyqtSignal(int,np.ndarray,np.ndarray,np.ndarray,np.ndarray)