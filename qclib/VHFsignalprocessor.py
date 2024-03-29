# ==================================================================================================================
#     Code: VHFsignalprocessor.py
#     Author: ENS Casey R. Densmore, DDMMYYYY
#     
#     Purpose: Handles all signal processing functions related to receiving and
#       converting AXBT data into temperature/depth information, either in real-
#       time with WiNRADIO receivers, or reprocessing raw audio data from WAV files
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
#       **NOTE 1**: This module handles all communication with the WiNRADIO receivers
#       through the WiNRADIO DLL/API, directly in Python using the Ctypes module.
#       Due to platform limitations for the WiNRADIO, several of the functions/
#       thread options are only compatible with Windows machines that have the 
#       WiNRADIO driver installed and DLL file loaded with the ctypes.windll module.
#       This compatibility is checked in main.py, and if any of the above criteria
#       are not met, the loaded WiNRADIO DLL variable wrdll (often seen as self.wrdll) 
#       is set equal to zero. The ARES program main file (main.py) is configured
#       to check these criteria, and only start signal processor threads that use
#       WiNRADIO receiver data if the criteria are met.
#
#       **NOTE 2**: This module works with both WiNRADIOs and audio data. The "test"
#       option that may be selected simply reads a hard-coded audio file and reprocesses that
#       data with a normal time delay, configured to replicate the datastream one
#       would receive from the WiNRADIO. The same functions are used to process data
#       from both WiNRADIOs and audio files, with occasional if/else statements to 
#       handle differences betwen the two.
#
#       **NOTE 3** All of the functions in this file are called from the ThreadProcessor
#       class of type QRunnable. ThreadProcessor is a class for the threads that are called
#       from main.py to process AXBT signal data either from a WiNRADIO or audio file. Threads
#       are handled (started, stopped, and modified) in main.py, but this file contains all of
#       the functions necessary for the thread to run, as well as all slots and signals by which
#       data is passed back/forth between the thread and the main event loop.
#
#   General Functions:
#       o depth = timetodepth(time): Calculates profile depths using probe fall rate equation
#       o temp = freqtotemp(frequency): General frequency-temperature conversion for AXBTs
#       o freq,maxf,ratio = dofft(pcmdata,fs,minratio,minlev): Determines frequency with max
#           power using an FFT on raw audio data array "pcmdata" collected at sampling
#           frequency "fs". If the ratio between the peak frequency in the AXBT temperature
#           band (1300 Hz - 2800 Hz) normalized by the maximum total power is greater than
#           "minratio" and the maximum total power is greater than "minlev", then the peak frequency
#           is returned as "freq". Otherwise, 0 Hz is returned. "maxf" and "ratio" are the actual
#           maximum total power and normalized max power within the AXBT band. This function is
#           used to process both WiNRADIO signal and reprocessed audio file data.
#       o outval, correctedval = channelandfrequencylookup(value,direction): VHF channel/frequency
#           lookup table. "value" is the input value to be converted to either frequency or channel
#           and "direction" specifies which conversion is occuring. "outval" is the converted value
#           (so if "value" is a VHF frequency, "outval" is the corresponding channel and vice versa).
#           If an invalid channel/frequency is entered, the nearest option ("correctedval") is selected,
#           and the corresponding channel/frequency is returned.
#
#   C++ Interactivity Functions/Variables:
#       o RADIO_INFO2 and Features Structures: C++ style structures declared to allow the
#           WiNRADIO to populate them with important information (e.g. fs, serial numbers)
#           when using the WRDLL.GetRadioList() command in listwinradios()
#       o winradioserials = listwinradios(wrdll): Returns a Python list of serial numbers
#           for all connected receivers using the WiNRADIO programmer's API/DLL.
#
#   ThreadProcessor Functions:
#       o __init__(wrdll, datasource, vhffreq, curtabnum, starttime, istriggered, firstpointtime, 
#           fftwindow, minfftratio, minsiglev, triggerfftratio, triggersiglev): This is where necessary
#           information is passed to the thread to initialize it. If the data source is an audio file, 
#           the audio file is read into a list here. If the datasource is a receiver, the receiver is 
#           initialized and set to the correct frequency here (but the audio stream is not configured).
#           Inputs are:
#               > wrdll: Variable containing the loaded WiNRADIO DLL/API, or "0" if the criteria
#                   in Note 1 are not satisfied.
#               > datasource: Either a WiNRADIO serial number or concatenation of "Audio" and the 
#                   file to be read, depending on data source type. "Test" reads the default WAV file
#                   but causes the Thread to handle all signals/slots as if it is receiving data
#                   from a receiver.
#               > vhffreq: VHF radio frequency that the WiNRADIO receiver will demodulate and sample
#                   for AXBT data. Only relevant if an actual WiNRADIO is selected
#               > curtabnum: Unique tab number (doesn't change if tabs are opened and closed) corresponding
#                   to the current thread that enables the GUI to update data sent back via a pyqtSignal in
#                   the appropriate tab
#               > starttime: The start date/time of processing (DTG, UTC) which is used to calculate a dT (and 
#                   depth) for all data in that thread
#               > istriggered: Logical value indicating whether or not AXBT data has been detected and the fall
#                   rate equations are being applied
#               > firstpointtime: Time at which the first AXBT data was collected: data collected at this time
#                   is assumed to be at the surface (0m) and the depth of all future data is determined with the
#                   fall rate equation in timetodepth()
#               > fftwindow: Window (seconds) over which the FFT is conducted and peak frequency is calculated
#               > minfftratio, minsiglev: Minimum signal ratio and level necessary for a datapoint to be 
#                   considered valid
#               > triggerfftratio, triggersiglev: As with minfftratio, minsiglev, but higher thresholds necessary 
#                   for the first data point, in order to 'trigger' data collection
#       o Run(): A separate function called from main.py immediately after initializing the thread to start data 
#           collection. Here, the callback function which updates the audio stream for WiNRADIO threads is declared
#           and the stream is directed to this callback function. This also contains the primary thread loop which 
#           updates data from either the WiNRADIO or audio file continuously using dofft() and the conversion eqns.
#       o abort(): Aborts the thread, sends final data to the event loop and notifies the event loop that the
#           thread has been terminated
#       o changecurrentfrequency(newfreq): Updates the VHF frequency being demodulated (affects WiNRADIO threads only)
#       o changethresholds(fftwindow,minfftratio,minsiglev,triggerfftratio,triggersiglev): Changes the thresholds
#           described for __init__() required for data to be considered valid.
#
#   ThreadProcessorSignals:
#       o iterated(ctabnum,ctemp, cdepth, fp, sigstrength, ctime, i): Passes information collected on the current
#           iteration of the thread loop back to the main program, in order to update the corresponding tab. "i" is
#           the iteration number- plots and tables are updated in the main loop every N iterations, with N specified
#           independently for plots/tables in main.py
#       o terminated(ctabnum): Notifies the main loop that the thread has been terminated/aborted
#       o triggered(ctabnum, time): Notifies the main loop that the current thread has detected data in order
#           to record the trigger time for that tab (enables stopping/restarting processing in a tab)
#       o failed(flag): Notifies the main loop that an error (corresponding to the value of flag) occured, causing an
#           error message to be posted in the GUI
#       o updateprogress(ctabnum, progress): **For audio files only** updates the main loop with the progress 
#           (displayed in progress bar) for the current thread
#
# ==================================================================================================================

import numpy as np
from scipy.io import wavfile #for wav file reading
from scipy.signal import tukey #taper generation

import wave #WAV file writing

from PyQt5.QtCore import pyqtSlot, pyqtSignal, QObject
from PyQt5.Qt import QRunnable

import time as timemodule
import datetime as dt

from traceback import print_exc as trace_error

from shutil import copy as shcopy
from sys import getsizeof
from ctypes import (Structure, pointer, c_int, c_ulong, c_char, c_uint32,
                    c_char_p, c_void_p, POINTER, c_int16, cast, CFUNCTYPE)

                    

#convert time to depth, freq to temp given coefficient lists
def btconvert(input,coefficients):
    output = 0
    for (i,c) in enumerate(coefficients):
        output += c*input**i
    return output
    

#function to run fft here
def dofft(pcmdata,fs,flims):
    
    # apply taper- alpha=0.25
    taper = tukey(len(pcmdata), alpha=0.25)
    pcmdata = taper * pcmdata

    # conducting fft, converting to real space
    fftdata = np.abs(np.fft.fft(pcmdata))

    #building corresponding frequency array
    N = len(pcmdata)
    T = N/fs
    df = 1 / T
    f = np.array([df * n if n < N / 2 else df * (n - N) for n in range(N)])

    #constraining peak frequency options to frequencies in specified band
    ind = np.all((np.greater_equal(f,flims[0]),np.less_equal(f,flims[1])),axis=0)
    f = f[ind]
    
    #frequency of max signal within band (AXBT-transmitted frequency)
    fp = f[np.argmax(fftdata[ind])] 
    
    #maximum signal strength in band
    Sp = 10*np.log10(np.max(fftdata[ind]))

    #ratio of maximum signal in band to max signal total (SNR)
    Rp = np.max(fftdata[ind])/np.max(fftdata) 
        
    return fp, Sp, Rp
    
    
    
    
#table lookup for VHF channels and frequencies
def channelandfrequencylookup(value,direction):
    
    #list of frequencies
    allfreqs = np.arange(136,173.51,0.375)
    allfreqs = np.delete(allfreqs,np.where(allfreqs == 161.5)[0][0])
    allfreqs = np.delete(allfreqs,np.where(allfreqs == 161.875)[0][0])
    
    #liwst of corresponding channels
    allchannels = np.arange(32,99.1,1)
    cha = np.arange(1,16.1,1)
    chb = np.arange(17,31.1,1)
    for i in range(len(chb)):
        allchannels = np.append(allchannels,cha[i])
        allchannels = np.append(allchannels,chb[i])
    allchannels = np.append(allchannels,cha[15])

    if direction == 'findfrequency': #find frequency given channel
        try:
            outval = allfreqs[np.where(allchannels == value)[0][0]]
            correctedval = value
        except:
            correctedval = allchannels[np.argmin(abs(allchannels-value))]
            outval = allfreqs[np.where(allchannels == correctedval)[0][0]]
            
    elif direction == 'findchannel': #find channel given frequency
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

    #initializing current thread (saving variables, reading audio data or contacting/configuring receiver)
    def __init__(self, wrdll, datasource, vhffreq, curtabnum, starttime, istriggered, firstpointtime, 
        fftwindow, minfftratio, minsiglev, triggerfftratio, triggersiglev, tcoeff, zcoeff, flims, slash,tempdir, *args,**kwargs):
        super(ThreadProcessor, self).__init__()

        #prevents Run() method from starting before init is finished (value must be changed to 100 at end of __init__)
        self.startthread = 0 
        
        # UI inputs
        self.curtabnum = curtabnum
        self.starttime = starttime
        self.istriggered = istriggered
        self.firstpointtime = firstpointtime

        self.keepgoing = True  # signal connections
        self.waittoterminate = False #whether to pause on termination of run loop for kill process to complete
        self.signals = ThreadProcessorSignals()

        #FFT thresholds
        self.fftwindow = fftwindow
        self.minfftratio = minfftratio
        self.minsiglev = minsiglev
        self.triggerfftratio = triggerfftratio
        self.triggersiglev = triggersiglev
        
        #conversion coefficients + parameters
        self.tcoeff = tcoeff
        self.zcoeff = zcoeff
        self.flims = flims

        #output file names
        self.txtfilename = tempdir + slash + "sigdata_" + str(self.curtabnum) + '.txt'
        self.txtfile = open(self.txtfilename, 'w')
        self.wavfilename = tempdir + slash +  "tempwav_" + str(self.curtabnum) + '.WAV'
        
        #to prevent ARES from consuming all computer's resources- this limits the size of WAV files used by the signal processor to a number of PCM datapoints corresponding to 1 hour of audio @ fs=64 kHz, that would produce a wav file of ~0.5 GB for 16-bit PCM data
        self.maxsavedframes = 2.5E8
        self.isrecordingaudio = True #initialized to True for all cases (RF, test, and audio) but only matters in the callback function assigned for RF receivers

        # identifying whether tab is audio, test, or other format
        self.isfromaudio = False
        self.isfromtest = False
        
        
        if datasource[:5] == 'Audio':
            self.chselect = int(datasource[5:10])
            self.audiofile = datasource[10:]
            self.isfromaudio = True
            
            #checking file length- wont process files with more frames than max size
            try: #exception if unable to read audio file if it doesn't exist or isn't WAV formatted
                file_info = wave.open(self.audiofile)
            except:
                self.startthread = 11
                return
                
            if file_info.getnframes() > self.maxsavedframes:
                self.startthread = 9
                return
            
            self.f_s, snd = wavfile.read(self.audiofile) #reading file
            
            #if multiple channels, sum them together
            sndshape = np.shape(snd) #array size (tuple)
            ndims = len(sndshape) #number of dimensions
            if ndims == 1: #if one channel, use that
                self.audiostream = snd
            elif ndims == 2: #if two channels, pick selected channel, otherwise sum
                if self.chselect >= 1:
                    self.audiostream = snd[:,self.chselect-1]
                else:
                    self.audiostream = np.sum(snd,axis=1)
                    
            else: #if more than 2D- not a valid file
                self.audiostream = [0]*10000
                self.startthread = 11
                
        elif datasource == 'Test': #test run- use included audio file
            self.audiofile = 'testdata/MZ000006.WAV'
            self.isfromtest = True
            
            try: #exception if unable to read audio file if it doesn't exist or isn't WAV formatted
                self.f_s, snd = wavfile.read(self.audiofile)
            except:
                self.startthread = 11
                return
                
            self.audiostream = snd[:, 0]
                

        #if thread is to be connected to a WiNRADIO
        if not self.isfromaudio and not self.isfromtest:

            #initializing variables to check if WiNRADIO remains connected
            self.disconnectcount = 0
            self.numcontacts = 0
            self.lastcontacts = 0
            self.nframes = 0
            
            # initialize audio stream data variables
            self.f_s = 64000  # default value
            self.audiostream = [0] * 2 * self.f_s #initializes the buffer with 2 seconds of zeros

            # saves WiNRADIO DLL/API library
            self.wrdll = wrdll

            # initialize winradio
            self.serial = datasource  # translate winradio identifier
            self.serialnum_2WR = c_char_p(self.serial.encode('utf-8'))

            #setup WAV file to write (if audio or test, source file is copied instead)
            self.wavfile = wave.open(self.wavfilename,'wb')
            wave.Wave_write.setnchannels(self.wavfile,1)
            wave.Wave_write.setsampwidth(self.wavfile,2)
            wave.Wave_write.setframerate(self.wavfile,self.f_s)
            wave.Wave_write.writeframes(self.wavfile,bytearray(self.audiostream))

            #opening current WiNRADIO/establishing contact
            self.hradio = self.wrdll.Open(self.serialnum_2WR)
            if self.hradio == 0:
                self.startthread = 1
                return

            try:
                # power on- kill if failed
                if wrdll.SetPower(self.hradio, True) == 0:
                    self.startthread = 2
                    return

                # initialize demodulator- kill if failed
                if wrdll.InitializeDemodulator(self.hradio) == 0:
                    self.startthread = 3
                    return

                # change frequency- kill if failed
                self.vhffreq_2WR = c_ulong(int(vhffreq * 1E6))
                if self.wrdll.SetFrequency(self.hradio, self.vhffreq_2WR) == 0:
                    self.startthread = 4
                    return

                # set volume- warn if failed
                if self.wrdll.SetVolume(self.hradio, 31) == 0:
                    self.startthread = 5
                    return

            except Exception: #if any WiNRADIO comms/initialization attempts failed, terminate thread
                trace_error()
                self.startthread = 6
                return
        else:
            shcopy(self.audiofile, self.wavfilename) #copying audio file if datasource = Test or Audio
        
        self.startthread = 100

            
    @pyqtSlot()
    def run(self):
        
        #barrier to prevent signal processor loop from starting before __init__ finishes
        counts = 0
        while self.startthread != 100:
            counts += 1
            if counts > 100 or not self.keepgoing: #give up and terminate after 10 seconds waiting for __init__
                self.kill(12)
                return
            elif self.startthread != 0 and self.startthread != 100: #if the audio file couldn't be read in properly
                self.kill(self.startthread) #waits to run kill commands due to errors raised in __init__ until run() since slots+signals may not be connected to parent thread during init
                return
            timemodule.sleep(0.1)
        #if the Run() method gets this far, __init__ has completed successfully (and set self.startthread = 100)

        
        try:
        
            if not self.isfromaudio and not self.isfromtest: #if source is a receiver
            
                #Declaring the callbuck function to update the audio buffer
                @CFUNCTYPE(None, c_void_p, c_void_p, c_ulong, c_ulong)
                def updateaudiobuffer(streampointer_int, bufferpointer_int, size, samplerate):
                    
                    try:
                        self.numcontacts += 1 #note that the buffer has been pulled again
                        bufferlength = int(size / 2)
                        bufferpointer = cast(bufferpointer_int, POINTER(c_int16 * bufferlength))
                        bufferdata = bufferpointer.contents
                        self.f_s = samplerate
                        self.nframes += bufferlength
                        self.audiostream.extend(bufferdata[:]) #append data to end
                        del self.audiostream[:bufferlength] #remove data from start
                        
                        #recording to wav file: this terminates if the file exceeds a certain length
                        if self.isrecordingaudio and self.nframes > self.maxsavedframes:
                            self.isrecordingaudio = False
                            self.killaudiorecording()
                        elif self.isrecordingaudio:
                            wave.Wave_write.writeframes(self.wavfile,bytearray(bufferdata))
                            
                    except Exception: #error handling for callback
                        trace_error()  
                        self.kill(10)
                #end of callback function
                        
                        
                # initializes audio callback function
                if self.wrdll.SetupStreams(self.hradio, None, None, updateaudiobuffer, c_int(self.curtabnum)) == 0:
                    self.kill(7)
                else:
                    timemodule.sleep(0.3)  # gives the buffer time to populate
    
                    
            else: #if source is an audio file
                #configuring sample times for the audio file
                self.lensignal = len(self.audiostream)
                self.maxtime = self.lensignal/self.f_s
                self.sampletimes = np.arange(0.1,self.maxtime-0.1,0.1)
    
                
            # setting up thread while loop- terminates when user clicks "STOP" or audio file finishes processing
            i = -1
                
            #MAIN PROCESSOR LOOP
            while self.keepgoing:
                i += 1

                # finds time from profile start in seconds
                curtime = dt.datetime.utcnow()  # current time
                deltat = curtime - self.starttime
                ctime = deltat.total_seconds()

                if not self.isfromaudio and not self.isfromtest:

                    #protocal to kill thread if connection with WiNRADIO is lost
                    if self.numcontacts == self.lastcontacts: #checks if the audio stream is receiving new data
                        self.disconnectcount += 1
                    else:
                        self.disconnectcount = 0
                        self.lastcontacts = self.numcontacts

                    #if the audio stream hasn't received new data for several iterations and checking device connection fails
                    if self.disconnectcount >= 30 and not self.wrdll.IsDeviceConnected(self.hradio):
                        self.kill(8)

                    # listens to current frequency, gets sound level, set audio stream, and corresponding time
                    currentdata = self.audiostream[-int(self.f_s * self.fftwindow):]
                else:


                    #kill test/audio threads once time exceeds the max time of the audio file
                    #NOTE: need to do this on the cycle before hitting the max time when processing from audio because
                    #       the WAV file processes faster than the thread can kill itself
                    if (self.isfromtest and ctime >= self.maxtime - self.fftwindow) or (self.isfromaudio and i >= len(self.sampletimes)-1):
                        self.keepgoing = False
                        self.kill(0)
                        return
                        
                    #getting current time to sample from audio file
                    if self.isfromaudio:
                        ctime = self.sampletimes[i]
                        if i % 10 == 0: #updates progress every 10 data points
                            self.signals.updateprogress.emit(self.curtabnum,int(ctime / self.maxtime * 100))

                    #getting current data to sample from audio file- using indices like this is much more efficient than calculating times and using logical arrays
                    ctrind = int(np.round(ctime*self.f_s))
                    pmind = int(np.min([np.round(self.f_s*self.fftwindow/2),ctrind,self.lensignal-ctrind-1])) #uses minimum value so no overflow
                    currentdata = self.audiostream[ctrind-pmind:ctrind+pmind]
                    

                #conducting FFT or skipping, depending on signal strength
                fp,Sp,Rp = dofft(currentdata, self.f_s, self.flims)        
        
                #rounding before comparisons happen
                ctime = np.round(ctime, 1)
                fp = np.round(fp, 2)
                Sp = np.round(Sp, 2)
                Rp = np.round(Rp, 3)        
                

                #writing raw data to sigdata file (ASCII) for current thread- before correcting for minratio/minsiglev
                if self.keepgoing: #only writes if thread hasn't been stopped since start of current segment
                    self.txtfile.write(f"{ctime},{fp},{Sp},{Rp}\n")
                    
                #logic to determine whether or not profile is triggered
                if not self.istriggered and Sp >= self.triggersiglev and Rp >= self.triggerfftratio:
                    self.istriggered = True
                    self.firstpointtime = ctime
                    if self.keepgoing: #won't send if keepgoing stopped since current iteration began
                        self.signals.triggered.emit(self.curtabnum, ctime)
                        
                #logic to determine whether or not point is valid
                if self.istriggered and Sp >= self.minsiglev and Rp >= self.minfftratio:
                    cdepth = btconvert(ctime - self.firstpointtime, self.zcoeff)
                    ctemp = btconvert(fp, self.tcoeff)
                
                else:
                    fp = 0
                    ctemp = cdepth = np.NaN
                

                # tells GUI to update data structure, plot, and table
                ctemp = np.round(ctemp, 2)
                cdepth = np.round(cdepth, 1)
                if self.keepgoing: #won't send if keepgoing stopped since current iteration began
                    self.signals.iterated.emit(self.curtabnum, ctemp, cdepth, fp, Sp, np.round(100*Rp,1), ctime, i)

                if not self.isfromaudio: 
                    timemodule.sleep(0.1)  #pauses when processing in realtime (fs ~ 10 Hz)
                else:
                    timemodule.sleep(0.001) #slight pause to free some resources when processing from audio

        except Exception: #if the thread encounters an error, terminate
            trace_error()  # if there is an error, terminates processing
            if self.keepgoing:
                self.kill(10)
                
        while self.waittoterminate: #waits for kill process to complete to avoid race conditions with audio buffer callback
            timemodule.sleep(0.1)
            
            
            
    def kill(self,reason):
        #NOTE: function contains 0.3 seconds of sleep to prevent race conditions between the processor loop, callback function and main GUI event loop
        try:
            self.waittoterminate = True #keeps run method from terminating until kill process completes
            self.keepgoing = False  # kills while loop
            curtabnum = self.curtabnum
            
            timemodule.sleep(0.3) #gives thread 0.1 seconds to finish current segment
            
            if reason != 0: #notify event loop that processor failed if non-zero exit code provided
                self.signals.failed.emit(self.curtabnum, reason)
            
            self.isrecordingaudio = False
            if not self.isfromaudio and not self.isfromtest:
                self.wrdll.SetupStreams(self.hradio, None, None, None, None)
                timemodule.sleep(0.3) #additional 0.1 seconds after stream directed to null before closing wav file
                wave.Wave_write.close(self.wavfile)
                self.wrdll.CloseRadioDevice(self.hradio)
                
            self.signals.terminated.emit(curtabnum)  # emits signal that processor has been terminated
            self.txtfile.close()
            
        except Exception:
            trace_error()
            self.signals.failed.emit(self.curtabnum, 10)
            
        self.waittoterminate = False #allow run method to terminate
        
        
    #terminate the audio file recording (for WINRADIO processor tabs) if it exceeds a certain length set by maxframenum
    def killaudiorecording(self):
        try:
            self.isrecordingaudio = False
            wave.Wave_write.close(self.wavfile) #close WAV file
            self.signals.failed.emit(self.curtabnum, 13) #pass warning message back to GUI
        except Exception:
            trace_error()
            self.kill(10)
        
        
    @pyqtSlot()
    def abort(self): #executed when user selects "Stop" button
        self.kill(0) #tell processor to terminate with 0 (success) exit code
        
        
    @pyqtSlot(float)
    def changecurrentfrequency(self, newfreq): #update VHF frequency for WiNRADIO
        # change frequency- kill if failed
        try:
            self.vhffreq_2WR = c_ulong(int(newfreq * 1E6))
            if self.wrdll.SetFrequency(self.hradio, self.vhffreq_2WR) == 0:
                self.kill(4)
        except Exception:
            trace_error()
            self.kill(4)
            

    @pyqtSlot(float,float,int,float,int,list,list,list)
    def changethresholds(self,fftwindow,minfftratio,minsiglev,triggerfftratio,triggersiglev,tcoeff,zcoeff,flims): #update data thresholds for FFT
        if fftwindow <= 1:
            self.fftwindow = fftwindow
        else:
            self.fftwindow = 1
        self.minfftratio = minfftratio
        self.minsiglev = minsiglev 
        self.triggerfftratio = triggerfftratio
        self.triggersiglev = triggersiglev 
        self.tcoeff = tcoeff
        self.zcoeff = zcoeff
        self.flims = flims       
        

        
        
#initializing signals for data to be passed back to main loop
class ThreadProcessorSignals(QObject): 
    iterated = pyqtSignal(int,float,float,float,float,float,float,int) #signal to add another entry to raw data arrays
    triggered = pyqtSignal(int,float) #signal that the first tone has been detected
    terminated = pyqtSignal(int) #signal that the loop has been terminated (by user input or program error)
    failed = pyqtSignal(int,int)
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