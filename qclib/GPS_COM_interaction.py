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

from serial import Serial
from serial.tools import list_ports
from pynmea2 import parse
from traceback import print_exc as trace_error
from time import sleep




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
    


    
def streamgpsdata(port):
    try:

        #open/configure port
        with Serial(port, 4800, timeout=1) as ser:
            ii = 0
            while ii <= 100:
                ii += 1

                try:  # exceptions raised if line doesn't include lat/lon
                    #get and decode current line
                    try:
                        nmeaobj = parse(ser.readline().decode('ascii', errors='replace').strip())
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
                    sleep(0.1)

    except KeyboardInterrupt:
        print('Terminated with keyboard interrupt!')
    except Exception:
        trace_error()




def getcurrentposition(port,numattempts):

    try:
        # try to read a line of data from the serial port and parse
        with Serial(port, 4800, timeout=1) as ser:

            ii = 0
            while True: #infinite loop

                ii += 1
                try:
                    #decode the line
                    nmeaobj = parse(ser.readline().decode('ascii', errors='replace').strip())

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
        trace_error()
        return 0,0,0,2