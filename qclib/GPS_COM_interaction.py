# =============================================================================
#     Code: GPS_COM_interaction.py
#     Author: ENS Casey R. Densmore, 24SEP2019
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


import sys
import serial.tools.list_ports
import pynmea2
import traceback
import time

def listcomports():
    portnums = []
    portinfo = []
    ports = serial.tools.list_ports.comports()
    for pnum, sdesc, details in sorted(ports):
        portnums.append(pnum)
        portinfo.append("{}: {}".format(pnum, sdesc)) #short description
        # portinfo.append("{}: {} [{}]".format(port, desc, details)) #long description
    return portnums,portinfo



def streamgpsdata(port):
    try:

        #open/configure port
        with serial.Serial(port, 4800, timeout=1) as ser:
            ii = 0
            while ii <= 100:
                ii += 1

                try:  # exceptions raised if line doesn't include lat/lon
                    #get and decode current line
                    try:
                        nmeaobj = pynmea2.parse(ser.readline().decode('ascii', errors='replace').strip())
                        isgood = True
                    except:
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

                except:
                    pass
                finally:
                    time.sleep(0.1)

    except KeyboardInterrupt:
        print('Terminated with keyboard interrupt!')
    except Exception:
        traceback.print_exc()




def getcurrentposition(port,numattempts):

    try:
        # try to read a line of data from the serial port and parse
        with serial.Serial(port, 4800, timeout=1) as ser:

            ii = 0
            while True: #infinite loop

                ii += 1
                try:
                    #decode the line
                    nmeaobj = pynmea2.parse(ser.readline().decode('ascii', errors='replace').strip())

                    try: #exceptions raised if line doesn't include lat/lon
                        lat = round(nmeaobj.latitude,3)
                        lon = round(nmeaobj.longitude,3)
                        dt = nmeaobj.datetime

                        if lon != 0 or lat != 0: #success
                            return lat,lon,dt,0

                    except: #no lat/lon
                        pass
                except: #failed to parse line (partial line or non-NMEA feed)
                    pass

                if ii > numattempts: #timeout
                    return 0, 0, 0, 1

        return 0,0,0,2 #somehow exits loop successfully and ends "with" statement w/t getting position

    except Exception: #fails to connect to serial port
        traceback.print_exc()
        return 0,0,0,2