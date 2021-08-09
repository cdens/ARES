# =============================================================================
#     Code: GPS_COM_interaction.py
#     Author: ENS Casey R. Densmore, 24SEP2019
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
#     Purpose: Provides code necessary to detect/list COM ports, attempt to connect
#           to COM port and listen to GPS NMEA feed, if one exists
#
#   Functions:
#       o portnums,portinfo = listcomports(): detects all available COM ports,
#           Returns: "portnums": list of port numbers
#                    "portinfo": list of descriptors for each COM port
#       o streamgpsdata(port)- attempts to connect to specified port and print
#           live stream of GPS time/lat/lon to command line
#       o lat,lon,dt,flag = getcurrentposition(port,numattempts)- attempts to
#           connect to COM port specified by "port" and get GPS lat/lon/time data,
#           stops after attempting "numattempts" times.
#           Returns: "lat", "lon": current coordinates, 0 if unsuccessful
#                    "dt" python datetime corresponding to lat/lon fix
#                    "flag": 0 if successful, 1 if timeout, 2 if unable to connect
# =============================================================================

from serial import Serial
from serial.tools import list_ports
from pynmea2 import parse, nmea
from traceback import print_exc as trace_error
from time import sleep
from datetime import datetime, timedelta

import multiprocessing
from PyQt5.QtCore import pyqtSlot, pyqtSignal, QObject
from PyQt5.Qt import QRunnable



###############################################################################################################        
#                                         BASIC COM PORT INTERACTION                                          #
###############################################################################################################

def listcomports():
    portnums = []
    portinfo = []
    ports = list_ports.comports()
    for pnum, sdesc, details in sorted(ports):
        portnums.append(pnum)
        portinfo.append(f"{pnum}: {sdesc}") #short description
        # portinfo.append("{}: {} [{}]".format(port, desc, details)) #long description
    return portnums,portinfo
    
    
    

def listcomports_verbose():
    portnums = []
    portinfo = []
    ports = list_ports.comports()
    for pnum, sdesc, details in sorted(ports):
        portnums.append(pnum)
        portinfo.append(f"{pnum}: {sdesc}, {details}") #short description
        # portinfo.append("{}: {} [{}]".format(port, desc, details)) #long description
    return portnums,portinfo
    
    

        
        

###############################################################################################################        
#                                           GPS THREAD FOR ARES                                               #
###############################################################################################################

class GPSthreadsignals(QObject): 
    update = pyqtSignal(int,float,float, datetime, int, int, float) #signal to update postion and time


class GPSthread(QRunnable):
    
    def __init__(self, comport, baudrate):
        super(GPSthread, self).__init__()
        
        self.comport = comport
        self.baudrate = baudrate
        self.keepGoing = True
        
        self.default_lat = 0
        self.default_lon = 0
        self.default_datetime = datetime(1,1,1)
        self.default_nsat = -1
        self.default_alt = -1E7
        self.default_qual = -1
        
        self.updatenseconds = 3 #updates GUI/ARES position every N seconds
        self.statusflag = 3 #0=good, 1=no signal, 2 = bad connection/error, 3 = not yet initialized
        
        self.lat = self.default_lat
        self.lon = self.default_lon
        self.datetime = self.default_datetime
        self.nsat = self.default_nsat
        self.alt = self.default_alt
        self.qual = self.default_qual
        
        self.badsiglimit = 10
        
        self.signals = GPSthreadsignals()
        
        
    
    #parse input GPS data (returns success flag and tuple with data)
    def parsegpsdata(self,nmeaobj):
        
        success = False
        
        clat = self.default_lat
        clon = self.default_lon
        cdt = self.default_datetime
        cnsat = self.default_nsat
        calt = self.default_alt
        cqual = self.default_qual
        
        try:
            
            #lat/lon required for function to return success
            clat = nmeaobj.latitude
            clon = nmeaobj.longitude
                            
            #pull datetime (required- tries 2 ways, if both fail then skips round)
            try: #get date and time from NMEA message
                cdt = nmeaobj.datetime
            except (AttributeError, KeyError): #only get time from NMEA message, requires that GPS day = system day (UTC)
                systemdt = datetime.utcnow()
                cdt = datetime.combine(systemdt.date(),nmeaobj.timestamp)
                
            success = True #if lat/lon/datetime collected, it's successful (everything else is optional)
                
            #trying to get each additional parameter separately
            try:
                calt = float(nmeaobj.altitude)
            except (AttributeError, KeyError, TypeError, ValueError):
                pass
            try:
                cnsat = int(nmeaobj.num_sats)
            except (AttributeError, KeyError, TypeError, ValueError):
                pass
            try:
                cqual = int(nmeaobj.gps_qual)
            except (AttributeError, KeyError, TypeError, ValueError):
                pass
                
        except (AttributeError, KeyError, TypeError):
            pass
                
        return success,(clat,clon,cdt,cnsat,cqual,calt)
        
        
        
        
    def run(self):
        #initialize lastgooddata. This is overwritten if a good fix is achieved and is reinitialized every time the signal is emitted
        lastgooddata = (1, self.default_lat, self.default_lon, self.default_datetime, self.default_nsat, self.default_qual, self.default_alt)
        while True: #outer loop- always running
            try:
                if self.comport.lower() == "n":
                    self.keepGoing = True
                    while self.keepGoing: #loop indefinitely, do nothing, wait for signal to attempt connection with GPS receiver
                        sleep(0.5)
                
                else: #different port listed- attempt to connect
                    self.keepGoing = True
                    last_time = self.default_datetime
                    self.nbadsig = 0
                    
                    with Serial(self.comport, self.baudrate, timeout=1) as ser:
                        while self.keepGoing: #until interrupted
                        
                            try:
                                nmeaobj = parse(ser.readline(96).decode('ascii', errors='replace').strip())
                                success, data = self.parsegpsdata(nmeaobj)
                            except (nmea.ParseError, OSError):
                                success = False
                                data = (self.default_lat, self.default_lon, self.default_datetime, self.default_nsat, self.default_qual, self.default_alt)
                            
                            #if all of the data is acceptable overwrite the lastgooddata with the most recent fix info
                            if success and (data[0] != 0 and data[1] != 0 and data[3] > -1 and data[4] > -1 and data[5] > -1):
                                lastgooddata = (0, data[0], data[1], data[2], data[3], data[4], data[5])
                                

                                                                    
                            cdt = datetime.utcnow()
                            #only transmit an update if a certain amount of time has passed and it was a good signal
                            if (cdt - last_time).total_seconds() >= self.updatenseconds:
                                last_time = cdt
                                #if the lastgooddata has contains a good fix
                                if lastgooddata[0] == 0:
                                    #emit the data
                                    print('updating gps position')
                                    self.signals.update.emit(lastgooddata[0], lastgooddata[1], lastgooddata[2], lastgooddata[3], lastgooddata[4], lastgooddata[5], lastgooddata[6])
                                    #reset lastgooddata after the signal is emitted
                                    lastgooddata = (1, self.default_lat, self.default_lon, self.default_datetime, self.default_nsat, self.default_qual, self.default_alt)
                                    #reset the number of bad signals (counted based off the number of failed updates)
                                    self.nbadsig = 0 

                                else:
                                    #change the 
                                    print('bad signal')
                                    self.nbadsig += 1 #add one to the number of bad signals if the update 
                                    
                            #if there have been too many consecutive failed signals, return to the default
                            if self.nbadsig > self.badsiglimit:
                                print('signal timeout')
                                self.signals.update.emit(lastgooddata[0], lastgooddata[1], lastgooddata[2], lastgooddata[3], lastgooddata[4], lastgooddata[5], lastgooddata[6])
                                #reset lastgooddata after the info is emitted
                                lastgooddata = (1, self.default_lat, self.default_lon, self.default_datetime, self.default_nsat, self.default_qual, self.default_alt)
                                self.nbadsig = 0
                        
                        
            except Exception: #fails to connect to serial port
                trace_error()
                self.comport = "n"
                self.signals.update.emit(2, 0, 0, datetime(1,1,1), 0, 0, 0)
            
                            
    @pyqtSlot(str,int)
    def changeConfig(self,comport,baudrate):
        self.comport = comport
        self.baudrate = baudrate
        self.keepGoing = False #interrupt inner loop to restart connection to different comport
        