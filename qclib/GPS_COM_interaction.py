import sys
import serial.tools.list_ports
import pynmea2
import traceback
import time

def listcomports():
    portnums = []
    portinfo = []
    ports = serial.tools.list_ports.comports()
    for port, desc, hwid in sorted(ports):
        portnums.append(port)
        portinfo.append("{}: {} [{}]".format(port, desc, hwid))
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
            while True:

                ii += 1
                try:
                    #decode the line
                    nmeaobj = pynmea2.parse(ser.readline().decode('ascii', errors='replace').strip())

                    try: #exceptions raised if line doesn't include lat/lon
                        lat = round(nmeaobj.latitude,3)
                        lon = round(nmeaobj.longitude,3)
                        dt = nmeaobj.datetime

                        if lon != 0 or lat != 0:
                            return lat,lon,dt,0
                    except:
                        pass

                    if ii > numattempts:
                        return 0, 0, 0, 1
                except:
                    pass

    except Exception:
        traceback.print_exc()
        return 0,0,0,2