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
    

    
def streamserialdata(port,baudrate):
    try:
        
        #open/configure port
        with Serial(port, baudrate, timeout=1) as ser:
            ii = 0
            while ii <= 100:
                ii += 1

                print(ser.readline(96).decode('ascii', errors='replace').strip())
                    
                sleep(0.1)

    except KeyboardInterrupt:
        print('Terminated with keyboard interrupt!')
    except Exception:
        trace_error()


    
    
###############################################################################################################        
#                                           GPS COM PORT INTERACTION                                          #
###############################################################################################################    

#parse input GPS data (returns success flag and tuple with data)
def parsegpsdata(nmeaobj):
    dt = datetime(1,1,1)
    lat = 0
    lon = 0
    nsat = -1
    qual = -1
    alt = -1E7
    
    try:
        
        #lat/lon required for function to return success
        lat = nmeaobj.latitude
        lon = nmeaobj.longitude
                        
        #pull datetime (required- tries 2 ways, if both fail then skips round)
        try: #get date and time from NMEA message
            dt = nmeaobj.datetime
        except (AttributeError, KeyError): #only get time from NMEA message, requires that GPS day = system day (UTC)
            systemdt = datetime.utcnow()
            dt = datetime.combine(systemdt.date(),nmeaobj.timestamp)
        
        #trying to get each additional parameter separately
        try:
            alt = float(nmeaobj.altitude)
        except (AttributeError, KeyError, TypeError):
            pass
        try:
            nsat = int(nmeaobj.num_sats)
        except (AttributeError, KeyError, TypeError):
            pass
        try:
            qual = int(nmeaobj.gps_qual)
        except (AttributeError, KeyError, TypeError):
            pass
            
        return True, (lat,lon,dt,nsat,qual,alt)
            
    except (AttributeError, KeyError, TypeError):
        return False, (lat,lon,dt,nsat,qual,alt)

        
        
        
        
        

#stream GPS data to command line
def streamgpsdata(port,baudrate):
    try:
        
        fixtypes = ["Not Valid", "GPS", "DGPS", "PPS", "RTK", "Float RTK", "Estimated", "Manual Input", "Simulation"]
        
        #initialize fields
        curdatetime = datetime(1,1,1)
        lat = 0
        latsign = 'N'
        lon = 0
        lonsign = 'E'
        
        alt = -1E7
        nsat = 0
        qual = 0
        
        

        #open/configure port
        with Serial(port, baudrate, timeout=1) as ser:
            ii = 0
            while ii <= 100:
                ii += 1

                try:  # exceptions raised if line doesn't include lat/lon
                    #get and decode current line
                    
                    isgood = False
                    success = False
                    
                    try:
                        nmeaobj = parse(ser.readline(96).decode('ascii', errors='replace').strip())
                        isgood = True
                        success, data = parsegpsdata(nmeaobj)
                        
                    except nmea.ParseError:
                        print("Bad NMEA sentence!")

                    if isgood and success:
                        
                        #required fields
                        lat = data[0]
                        lon = data[1]
                        curdatetime = data[2]
                        
                        #optional fields
                        if data[3] >= 0:
                            nsat = data[3]
                        if data[4] >= 0:
                            qual = data[4]
                        if data[5] >= -1E3:
                            alt = data[5]
                        
                        #prep lat/lon strings
                        lat = round(lat,3)
                        lon = round(lat,3)
                        if lat > 0:
                            latsign = 'N'
                        else:
                            latsign = 'S'
                        if lon > 0:
                            lonsign = 'E'
                        else:
                            lonsign = 'W'
                            
                        #printing current data
                        print(f"Date: {curdatetime},  Latitude: {abs(lat)}{latsign},  Longitude: {abs(lon)}{lonsign}  , Altitude: {alt} m,  #sat: {nsat},  GPS quality: {fixtypes[qual]}")
                        ii = 0

                except (AttributeError, KeyError):
                    pass
                finally:
                    sleep(0.1)
        
        print("Device timeout")
        
    except KeyboardInterrupt:
        print('Terminated with keyboard interrupt!')
    except Exception:
        trace_error()


        
        
        
        
#get one fix
def getcurrentposition(port,baudrate,numattempts):

    try:
        
        alt = -1E7
        nsat = 0
        qual = 0
                        
        # try to read a line of data from the serial port and parse
        with Serial(port, baudrate, timeout=1) as ser:

            ii = 0
            while True: #infinite loop

                ii += 1
                try:
                    #decode the line
                    nmeaobj = parse(ser.readline(96).decode('ascii', errors='replace').strip())
                    success, data = parsegpsdata(nmeaobj)
                    
                    if success:
                        
                        #required fields
                        lat = data[0]
                        lon = data[1]
                        dt = data[2]
                        
                        #optional fields
                        if data[3] >= 0:
                            nsat = data[3]
                        if data[4] >= 0:
                            qual = data[4]
                        if data[5] >= -1E3:
                            alt = data[5]
                        
                        #success, give a chance to pull GPS metadata as well
                        if (lon != 0 or lat != 0) and ii > 5: 
                            return 0,(lat,lon,dt,nsat,qual,alt)
                            
                except nmea.ParseError: #failed to parse line (partial line or non-NMEA feed)
                    pass

                if ii > numattempts: #timeout
                    return 1, (0, 0, 0, 0, 0, 0)

        return 2, (0,0,0,0,0,0) #somehow exits loop successfully and ends "with" statement w/t getting position

    except Exception: #fails to connect to serial port
        trace_error()
        return 2, (0,0,0,0,0,0)
        
        
        
        
        
        

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
        
        self.lat = 0
        self.lon = 0
        self.datetime = datetime(1,1,1)
        self.nsat = -1
        self.alt = -1E7
        self.qual = -1
        
        self.signals = GPSthreadsignals()
        
        
        
    def run(self):
        
        try:
            while True: #outer loop- always running
                
                self.goodConnection = False
                        
                if self.comport.lower() == "n":
                    self.keepGoing = True
                    self.goodConnection = True
                    while self.keepGoing: #loop indefinitely, do nothing, wait for signal to attempt connection with valid GPS receiver
                        sleep(0.5)
                
                else: #different port listed- attempt to connect
                    isGood, data = getcurrentposition(self.comport, self.baudrate, 15) #data -> (lat,lon,dt,nsat,qual,alt)
                    
                    self.keepGoing = True
                    
                    if isGood == 0: #got a valid position/time
                        self.goodConnection = True
                        self.lat = data[0]
                        self.lon = data[1]
                        self.datetime = data[2] #only write to self.datetime if cdt is a valid datetime otherwise causes error w/ slot
                        self.nsat = data[3]
                        self.qual = data[4]
                        self.alt = data[5]
                        
                    self.signals.update.emit(isGood, self.lat, self.lon, self.datetime, self.nsat, self.qual, self.alt) #bad connection
                        
                    c = 0
                    if isGood <= 1: #good connection or request timeout
                        with Serial(self.comport, self.baudrate, timeout=1) as ser:
                            while self.keepGoing: #until interrupted
                            
                                try:
                                    nmeaobj = parse(ser.readline(96).decode('ascii', errors='replace').strip())
                                    success, data = parsegpsdata(nmeaobj)
                                    
                                    if success and (self.lat != 0 or self.lon != 0):
                                        self.lat = data[0]
                                        self.lon = data[1]
                                        self.datetime = data[2]
                                        if data[3] >= 0:
                                            self.nsat = data[3]
                                        if data[4] >= 0:
                                            self.qual = data[4]
                                        if data[5] >= -1E3:
                                            self.alt = data[5]
                                    
                                    if c%10 == 0: #every 5 seconds b/c should be reading 2 sentences per second
                                        self.signals.update.emit(0, self.lat, self.lon, self.datetime, self.nsat, self.qual, self.alt)
                                    c += 1
                                    
                                except (AttributeError, KeyError, nmea.ParseError, OSError):
                                    pass
                                    
                    else:
                        self.comport = 'n'
                        
        except Exception: #fails to connect to serial port
            trace_error()
            self.signals.update.emit(2, 0, 0, datetime(1,1,1), 0, 0, 0)
            
                            
    @pyqtSlot(str,int)
    def changeConfig(self,comport,baudrate):
        self.comport = comport
        self.baudrate = baudrate
        self.keepGoing = False #interrupt inner loop to restart connection to different comport
        