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
from datetime import datetime

import multiprocessing
from PyQt5.QtCore import pyqtSlot, pyqtSignal, QObject
from PyQt5.Qt import QRunnable



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
    


    
def streamgpsdata(port,baudrate):
    try:

        #open/configure port
        with Serial(port, baudrate, timeout=1) as ser:
            ii = 0
            while ii <= 100:
                ii += 1

                try:  # exceptions raised if line doesn't include lat/lon
                    #get and decode current line
                    try:
                        nmeaobj = parse(ser.readline().decode('ascii', errors='replace').strip())
                        isgood = True
                    except nmea.ParseError:
                        print("Bad NMEA sentence!")
                        isgood = False

                    if isgood:
                        lat = round(nmeaobj.latitude,3)
                        lon = round(nmeaobj.longitude,3)
                        if lat > 0:
                            latsign = 'N'
                        else:
                            latsign = 'S'
                        if lon > 0:
                            lonsign = 'E'
                        else:
                            lonsign = 'W'
                        print('Date: {}     Latitude: {}{}     Longitude: {}{}'.format(nmeaobj.datetime,abs(lat),latsign,abs(lon),lonsign))
                        ii = 0

                except (AttributeError, KeyError):
                    pass
                finally:
                    sleep(0.1)

    except KeyboardInterrupt:
        print('Terminated with keyboard interrupt!')
    except Exception:
        trace_error()




def getcurrentposition(port,baudrate,numattempts):

    try:
        # try to read a line of data from the serial port and parse
        with Serial(port, baudrate, timeout=1) as ser:

            ii = 0
            while True: #infinite loop

                ii += 1
                try:
                    #decode the line
                    nmeaobj = parse(ser.readline(96).decode('ascii', errors='replace').strip())

                    try: #exceptions raised if line doesn't include lat/lon
                        lat = nmeaobj.latitude
                        lon = nmeaobj.longitude
                        dt = nmeaobj.datetime

                        if lon != 0 or lat != 0: #success
                            return lat,lon,dt,0

                    except (AttributeError, KeyError): #no lat/lon
                        pass
                except nmea.ParseError: #failed to parse line (partial line or non-NMEA feed)
                    pass

                if ii > numattempts: #timeout
                    return 0, 0, 0, 1

        return 0,0,0,2 #somehow exits loop successfully and ends "with" statement w/t getting position

    except Exception: #fails to connect to serial port
        trace_error()
        return 0,0,0,2
        
        
        
        
        
        

###############################################################################################################        
#                                           GPS COM PORT INTERACTION                                          #
###############################################################################################################

class GPSthreadsignals(QObject): 
    update = pyqtSignal(int,float,float, datetime) #signal to update postion and time


class GPSthread(QRunnable):
    
    def __init__(self, comport, baudrate):
        super(GPSthread, self).__init__()
        
        self.comport = comport
        self.baudrate = baudrate
        self.keepGoing = True
        
        self.lat = 0
        self.lon = 0
        self.datetime = datetime(1,1,1)
        
        self.signals = GPSthreadsignals()
        
        
        
    def run(self):
        
        while True: #outer loop- always running
            
            self.goodConnection = False
                    
            if self.comport.lower() == "n":
                self.keepGoing = True
                self.goodConnection = True
                while self.keepGoing: #loop indefinitely, do nothing, wait for signal to attempt connection with valid GPS receiver
                    sleep(0.5)
            
            else: #different port listed- attempt to connect
                self.lat, self.lon, cdt, isGood = getcurrentposition(self.comport, self.baudrate, 5)
                    
                self.keepGoing = True
                
                if isGood == 0: #got a valid position/time
                    self.goodConnection = True
                    self.datetime = cdt #only write to self.datetime if cdt is a valid datetime otherwise causes error w/ slot
                    self.signals.update.emit(isGood, self.lat, self.lon, self.datetime)
                    
                else: #failed to get valid points
                    self.signals.update.emit(isGood, 0,0, datetime(1,1,1)) #bad connection
                    
                c = 0
                if isGood <= 1: #good connection or request timeout
                    with Serial(self.comport, self.baudrate, timeout=1) as ser:
                        while self.keepGoing: #until interrupted
                        
                            try:
                                nmeaobj = parse(ser.readline(96).decode('ascii', errors='replace').strip())
                                clat = nmeaobj.latitude
                                clon = nmeaobj.longitude
                                
                                if self.lat != 0 or self.lon != 0:
                                    self.lat = clat
                                    self.lon = clon
                                    clon = self.lon
                                    self.datetime = nmeaobj.datetime
                                
                                if c%5 == 0:
                                    self.signals.update.emit(0, self.lat, self.lon, self.datetime)
                                c += 1
                                
                            except (AttributeError, KeyError, nmea.ParseError):
                                pass
                                
                            except OSError:
                                pass
                                
                else:
                    self.comport = 'n'
                            
    @pyqtSlot(str,int)
    def changeConfig(self,comport,baudrate):
        self.comport = comport
        self.baudrate = baudrate
        self.keepGoing = False #interrupt inner loop to restart connection to different comport
        