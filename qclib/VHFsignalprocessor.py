#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import numpy as np
from scipy.io import wavfile #for wav
import wave

from PyQt5.QtCore import pyqtSlot, pyqtSignal, QObject
from PyQt5.Qt import QRunnable

import qclib.tropicfileinteraction as tfio

import time as timemodule
import datetime as dt

import traceback

import shutil
from sys import getsizeof
from os import remove
from ctypes import (Structure, pointer, c_int, c_ulong, c_ulonglong, c_char, c_uint32,
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
def dofft(pcmdata,fs,minratio,minsiglev):

    # conducting fft, converting to real space
    rawfft = np.fft.fft(pcmdata)
    fftdata = np.abs(rawfft)

    #building corresponding frequency array
    N = len(pcmdata)
    T = N/fs
    df = 1 / T
    f = np.array([df * n if n < N / 2 else df * (n - N) for n in range(N)])

    #limiting frequencies, converting to ratio
    maxf = np.max(fftdata)
    ind = np.all((np.greater_equal(f,1300),np.less_equal(f,2800)),axis=0)
    f = f[ind]
    fftdata = fftdata[ind]/maxf

    # pulls max frequency if criteria are met
    if np.max(fftdata) >= minratio and maxf >= minsiglev:
        freq = f[np.argmax(fftdata)]
    else:
        freq = 0

    return freq, maxf, np.max(fftdata)
    
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

    def __init__(self, wrdll, datasource, vhffreq, curtabnum, starttime, istriggered, firstpointtime, fftwindow, minfftratio, minsiglev, *args,**kwargs):
        super(ThreadProcessor, self).__init__()


        # UI inputs
        self.curtabnum = curtabnum
        self.starttime = starttime
        self.istriggered = istriggered
        self.firstpointtime = firstpointtime

        self.keepgoing = True  # signal connections
        self.signals = ThreadProcessorSignals()

        self.fftwindow = fftwindow
        self.minfftratio = minfftratio
        self.minsiglev = minsiglev

        self.txtfilename = "sigdata_" + str(self.curtabnum) + '.txt'
        self.txtfile = open(self.txtfilename, 'w')
        self.wavfilename = "tempwav_" + str(self.curtabnum) + '.WAV'

        # identifying whether tab is audio, test, or other format
        self.isfromaudio = False
        self.isfromtest = False
        if datasource[:5] == 'Audio':
            self.audiofile = datasource[6:]
            self.isfromaudio = True
            self.f_s, snd = wavfile.read(self.audiofile)
            try: #if left/right stereo
                self.audiostream = snd[:, 0]
            except:
                self.audiostream = snd
        elif datasource == 'Test':
            self.audiofile = 'testdata/MZ000006.WAV'
            self.isfromtest = True
            self.f_s, snd = wavfile.read(self.audiofile)
            self.audiostream = snd[:, 0]


        if not self.isfromaudio and not self.isfromtest:

            self.disconnectcount = 0
            self.bufferlen = 0

            # initialize audio data variables
            self.f_s = 64000  # default value
            self.audiostream = [0] * 64000

            # saves library
            self.wrdll = wrdll

            # initialize winradio
            self.serial = datasource  # translate winradio identifier
            self.serialnum_2WR = c_char_p(self.serial.encode('utf-8'))

            #setup wave file
            self.wavfile = wave.open(self.wavfilename,'wb')
            wave.Wave_write.setnchannels(self.wavfile,1)
            wave.Wave_write.setsampwidth(self.wavfile,2)
            wave.Wave_write.setframerate(self.wavfile,self.f_s)
            wave.Wave_write.writeframes(self.wavfile,bytearray(self.audiostream))

            self.hradio = self.wrdll.Open(self.serialnum_2WR)
            if self.hradio == 0:
                self.keepgoing = False
                self.txtfile.close()
                wave.Wave_write.close(self.wavfile)
                self.signals.failed.emit(0)
                return

            try:
                # power on- kill if failed
                if wrdll.SetPower(self.hradio, True) == 0:
                    self.keepgoing = False
                    self.signals.failed.emit(1)
                    self.txtfile.close()
                    wave.Wave_write.close(self.wavfile)
                    self.signals.terminated.emit(curtabnum)
                    self.wrdll.CloseRadioDevice(self.hradio)
                    return

                # initialize demodulator- kill if failed
                if wrdll.InitializeDemodulator(self.hradio) == 0:
                    self.keepgoing = False
                    self.signals.failed.emit(2)
                    self.txtfile.close()
                    wave.Wave_write.close(self.wavfile)
                    self.signals.terminated.emit(curtabnum)
                    self.wrdll.CloseRadioDevice(self.hradio)
                    return

                # change frequency- kill if failed
                self.vhffreq_2WR = c_ulong(int(vhffreq * 1E6))
                if self.wrdll.SetFrequency(self.hradio, self.vhffreq_2WR) == 0:
                    self.keepgoing = False
                    self.txtfile.close()
                    wave.Wave_write.close(self.wavfile)
                    self.signals.failed.emit(3)
                    self.signals.terminated.emit(curtabnum)
                    self.wrdll.CloseRadioDevice(self.hradio)
                    return

                # set volume- warn if failed
                if self.wrdll.SetVolume(self.hradio, 31) == 0:
                    self.signals.failed.emit(5)

            except Exception:
                self.keepgoing = False
                self.signals.failed.emit(4)
                self.signals.terminated.emit(curtabnum)
                self.txtfile.close()
                wave.Wave_write.close(self.wavfile)
                self.wrdll.SetupStreams(self.hradio, None, None, None, None)
                self.wrdll.CloseRadioDevice(self.hradio)  # closes the radio if initialization fails
                traceback.print_exc()

        else:
            shutil.copy(self.audiofile, self.wavfilename)


    @pyqtSlot()
    def run(self):

        if not self.isfromaudio and not self.isfromtest:
            #Declaring the callbuck function to update the audio buffer
            @CFUNCTYPE(None, c_void_p, c_void_p, c_ulong, c_ulong)
            def updateaudiobuffer(streampointer_int, bufferpointer_int, size, samplerate):
                bufferlength = int(size / 2)
                bufferpointer = cast(bufferpointer_int, POINTER(c_int16 * bufferlength))
                bufferdata = bufferpointer.contents
                self.f_s = samplerate
                self.audiostream.extend(bufferdata[:])
                wave.Wave_write.writeframes(self.wavfile,bytearray(bufferdata))

            curtabnum = self.curtabnum

            # initializes audio callback function
            if self.wrdll.SetupStreams(self.hradio, None, None, updateaudiobuffer, c_int(self.curtabnum)) == 0:
                self.signals.failed.emit(6)
                self.signals.terminated.emit(curtabnum)
                self.txtfile.close()
                wave.Wave_write.close(self.wavfile)
                self.wrdll.CloseRadioDevice(self.hradio)
            else:
                timemodule.sleep(0.3)  # gives the buffer time to populate

            self.audiostream.extend([0] * 64000)

        else:
            self.alltimes = np.arange(0, len(self.audiostream), 1) / self.f_s
            self.maxtime = np.max(self.alltimes)
            self.sampletimes = np.arange(0,self.maxtime,0.1)


        try:
            # setting up while loop- terminates when user clicks "STOP"
            i = -1

            while self.keepgoing:
                i += 1

                # finds time from profile start in seconds
                curtime = dt.datetime.utcnow()  # current time
                deltat = curtime - self.starttime
                ctime = deltat.total_seconds()

                if not self.isfromaudio and not self.isfromtest:

                    #protocal to kill thread if connection with WiNRADIO is lost
                    if len(self.audiostream) == self.bufferlen:
                        self.disconnectcount += 1
                    else:
                        self.disconnectcount = 0
                        self.bufferlen = len(self.audiostream)
                    if self.disconnectcount >= 30: # and not self.wrdll.IsDeviceConnected(self.hradio):
                        self.wrdll.SetupStreams(self.hradio, None, None, None, None)
                        self.wrdll.CloseRadioDevice(self.hradio)
                        self.signals.failed.emit(7)
                        self.txtfile.close()
                        wave.Wave_write.close(self.wavfile)
                        self.signals.terminated.emit(self.curtabnum)
                        self.keepgoing = False
                        return

                    # listens to current frequency, gets sound level, set audio stream, and corresponding time
                    sigstrength = self.wrdll.GetSignalStrengthdBm(self.hradio)
                    currentdata = self.audiostream[-int(self.f_s * self.fftwindow):]
                else:

                    #getting current time to sample from audio file
                    if self.isfromaudio:
                        ctime = self.sampletimes[i]
                        if i % 10 == 0: #updates progress every 10 data points
                            self.signals.updateprogress.emit(self.curtabnum,int(ctime / self.maxtime * 100))

                    #kill test threads once time exceeds the max time of the audio file
                    if self.isfromtest and ctime > self.maxtime:
                        self.txtfile.close()
                        self.signals.terminated.emit(self.curtabnum)
                        return


                    ind = np.all([np.greater_equal(self.alltimes,ctime-self.fftwindow/2),np.less_equal(self.alltimes,ctime + self.fftwindow/2)],axis=0)
                    currentdata = self.audiostream[ind]
                    sigstrength = 0


                #conducting FFT or skipping, depending on signal strength
                if sigstrength == int(-1):
                    sigstrength = -15000
                sigstrength = float(sigstrength) / 10  # signal strength in dBm
                if sigstrength >= -150:
                    cfreq,actmax,ratiomax = dofft(currentdata, self.f_s, self.minfftratio, self.minsiglev)
                else:
                    cfreq = 0
                    actmax = 0
                    ratiomax = 0


                cline = str(ctime) + ',' + str(cfreq) + ',' + str(actmax) + ',' + str(ratiomax) + '\n'

                if self.keepgoing:
                    self.txtfile.write(cline)

                # if statement to trigger reciever after first frequency arrives
                if (not self.istriggered) and cfreq != 0:
                    self.istriggered = True
                    self.firstpointtime = ctime
                    self.signals.triggered.emit(self.curtabnum, ctime)

                if self.istriggered:
                    timefromtrigger = ctime - self.firstpointtime
                    cdepth = timetodepth(timefromtrigger)

                    if cfreq != 0:
                        ctemp = freqtotemp(cfreq)
                    else:
                        ctemp = np.NaN

                else:  # if processor hasnt been triggered yet
                    cdepth = np.NaN
                    ctemp = np.NaN

                # tells GUI to update data structure, plot, and table
                ctemp = np.round(ctemp, 2)
                cdepth = np.round(cdepth, 1)
                cfreq = np.round(cfreq, 2)
                ctime = np.round(ctime, 1)
                sigstrength = np.round(sigstrength, 2)
                self.signals.iterated.emit(self.curtabnum, ctemp, cdepth, cfreq, sigstrength, ctime, i)

                if not self.isfromaudio and not self.isfromtest:
                    timemodule.sleep(0.1)  # pauses before getting next point

        except Exception:
            self.keepgoing = False
            self.txtfile.close()

            if not self.isfromaudio and not self.isfromtest:
                wave.Wave_write.close(self.wavfile)
                self.wrdll.SetupStreams(self.hradio, None, None, None, None)
                self.wrdll.CloseRadioDevice(self.hradio)

            self.signals.failed.emit(4)
            traceback.print_exc()  # if there is an error, terminates processing
            self.signals.terminated.emit(self.curtabnum)

    @pyqtSlot()
    def abort(self):
        curtabnum = self.curtabnum
        self.keepgoing = False  # kills while loop

        if not self.isfromaudio and not self.isfromtest:
            wave.Wave_write.close(self.wavfile)
            self.wrdll.SetupStreams(self.hradio, None, None, None, None)
            self.wrdll.CloseRadioDevice(self.hradio)
        self.signals.terminated.emit(curtabnum)  # emits signal that processor has been terminated
        self.txtfile.close()
        return

    @pyqtSlot(float)
    def changecurrentfrequency(self, newfreq):
        # change frequency- kill if failed
        self.vhffreq_2WR = c_ulong(int(newfreq * 1E6))
        if self.wrdll.SetFrequency(self.hradio, self.vhffreq_2WR) == 0:
            self.txtfile.close()
            wave.Wave_write.close(self.wavfile)
            self.signals.failed.emit(3)
            self.wrdll.SetupStreams(self.hradio, None, None, None, None)
            self.wrdll.CloseRadioDevice(self.hradio)
            return

    @pyqtSlot(float,float,int)
    def changethresholds(self,fftwindow,minfftratio,minsiglev):
        if fftwindow <= 1:
            self.fftwindow = fftwindow
        else:
            self.fftwindow = 1
        self.minfftratio = minfftratio
        self.minsiglev = minsiglev
        

class ThreadProcessorSignals(QObject):
    iterated = pyqtSignal(int,float,float,float,float,float,int) #signal to add another entry to raw data arrays
    triggered = pyqtSignal(int,float) #signal that the first tone has been detected
    terminated = pyqtSignal(int) #signal that the loop has been terminated (by user input or program error)
    failed = pyqtSignal(int)
    updateprogress = pyqtSignal(int,int) #signal to add another entry to raw data arrays



# =============================================================================
# C++ INTEGRATED FUNCTIONS FOR WINRADIO:
# =============================================================================
# initialize radioinfo structure
class Features(Structure):
    _pack_ = 1
    _fields_ = [("ExtRef", c_uint32), ("FMWEnabled", c_uint32), ("Reserved", c_uint32)]
class RADIO_INFO2(Structure):
    _pack_ = 1
    _fields_ = [("bLength", c_uint32), ("szSerNum", c_char*9), ("szProdName", c_char*9), ("MinFreq", c_uint32),("MaxFreq", c_uint32), ("Features", Features)]

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