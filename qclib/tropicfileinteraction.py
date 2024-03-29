# =============================================================================
#     Code: tropicfileinteraction.py
#     Author: ENS Casey R. Densmore, 20JUN2019
#    
#     Purpose: Provides functions to write/read various AXBT data file formats
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
#	General Variable Definitions:
#		o xxxfile (e.g. logfile, finfile): filename to read or write
#		o temperature, depth: temperature-profile from file (raw or QC-ed 
#			depending on filetype)
#		o frequency, time: frequency/time from start used to generate raw profile
#		o lat, lon, year, day, month, hour, minute, time: all position/time
#			variables corresponding to AXBT drop. All values are formatted as
#			int, float, or float64 (no strings!). Time information is 24-hr UTC
#		o identifier: identifier for platform that launched AXBT (e.g. tail number,
#			such as AF309 for aircraft)
#
#   Functions:
#       o temperature,depth = readlogfile(logfile): read only T-D profile from
#			raw LOG file
#		o temperature,depth = readlogfile_alldata(logfile): read T-D profile, 
#			raw frequency, and corresponding time from raw Mk21-style LOG file
#		o rawtemperature,rawdepth,year,month,day,hour,minute,second,lat,lon = ...
#			readedffile(edffile): reads raw data from EDF file
#		o writeedffile(edffile,rawtemperature,rawdepth,year,month,day,hour,...
#			minute,second,lat,lon): writes raw data to EDF file *no sound speed
#		o temperature,depth,day,month,year,time,lat,lon,identifier = ...
#			readjjvvfile(jjvvfile,decade): read data from JJVV file
#		o writejjvvfile(jjvvfile,temperature,depth,day,month,year,time,lat,lon,...
#			identifier,isbtmstrike): read data from JJVV file
#		o temperature,depth,day,month,year,time,lat,lon,num = readfinfile(finfile):
#			reads QC'ed profile data from a FIN (1-m resolution) file
#			NOTE: "num" is the drop number for the current mission (FIN file only)
#		o writefinfile(finfile,temperature,depth,day,month,year,time,lat,lon,num):
#			writes QC'ed profile data to a FIN (1-m resolution) file
#			NOTE: ARES does not record drop number, and specifies "num"=99 for all drops
#		o writebufrfile(bufrfile,temperature,depth,year,month,day,time,lon,lat,...
#			identifier,originatingcenter,hasoptionalsection,optionalinfo):
#			Writes BUFR files following WMO format. Configured to use FXY option 
#			3,15,001 (ocean temperature sounding w/ coarse lat/lon) to write data
#			Additional Inputs:
#				> originatingcenter: Center via which data is transmitted to GTS (WMO  
#					Table C). With ARES this selection is made in the settings window
#				> hasoptionalsection, optionalinfo: Optional additional binary data
#					(either bytes or UTF-8 encoded string) to be included in the optional
#					section 2 in the BUFR message
#			NOTE: BUFR format version is adjusted within the function, but either BUFR 
#				versions 3 or 4 may be used.
#       o writekmlfile(kmlfile, lon, lat, year, month, day, time)
#            writes kml file that creates placemarks on google earth
#       o readkmlfile(kmlfile)
#            reads a kml file and returns the kml object
# =============================================================================

import numpy as np
from datetime import date, datetime
import chardet

from pykml import parser
from pykml.factory import KML_ElementMaker as kml
import lxml


#read raw temperature/depth profile from LOGXX.DTA file
def readlogfile(logfile):

    with open(logfile,'r') as f_in:
        depth = []
        temperature = []

        for line in f_in:

            line = line.strip().split() #get rid of \n character, split by spaces

            try:
                curfreq = np.double(line[2])
                cdepth = np.double(line[1])
                ctemp = np.double(line[3])
            except:
                curfreq = np.NaN

            if ~np.isnan(curfreq) and curfreq != 0: #if it is a valid frequency, save the datapoint
                depth.append(cdepth)
                temperature.append(ctemp)
    
    #convert to numpy arrays
    depth = np.asarray(depth)
    temperature = np.asarray(temperature)
    
    return [temperature,depth]
    

    

#read raw temperature/depth profile with all other data from LOGXX.DTA file
def readlogfile_alldata(logfile):

    with open(logfile,'r') as f_in:
        time = []
        depth = []
        frequency = []
        temperature = []

        #read in header lines
        for i in range(6):
            f_in.readline()

        #read data lines
        for line in f_in:
            line = line.strip().split() #get rid of \n character, split by spaces

            try:
                curfreq = np.double(line[2])
            except:
                curfreq = np.NaN

            if ~np.isnan(curfreq) and curfreq != 0: #if it is a valid frequency, save the datapoint
                depth.append(np.double(line[1]))
                temperature.append(np.double(line[3]))
            else:
                depth.append(np.NaN)
                temperature.append(np.NaN)

            time.append(np.double(line[0]))
            frequency.append(np.double(line[2]))
    
    #convert to numpy arrays
    time = np.asarray(time)
    depth = np.asarray(depth)
    frequency = np.asarray(frequency)
    temperature = np.asarray(temperature)
    
    return [temperature,depth,time,frequency]
    
    
    
    
def writelogfile(logfile,initdatestr,inittimestr,timefromstart,depth,frequency,tempc):
    with open(logfile,'w') as f_out:

        #write header
        f_out.write('     Probe Type = AXBT\n')
        f_out.write('       Date = ' + initdatestr + '\n')
        f_out.write('       Time = ' + inittimestr + '\n\n')
        f_out.write('    Time     Depth    Frequency    (C)       (F) \n\n')

        #temperature (degF) conversion
        tempf = tempc*1.8+32

        #writing data
        for t,d,f,tc,tf in zip(timefromstart,depth,frequency,tempc,tempf):

            #formatting strings
            tstr = str(round(t,1)).zfill(4)
            fstr = str(round(f,3)).zfill(5)
            if np.isnan(d):
                dstr = '-10.0'
            else:
                dstr = str(round(d,1)).zfill(4)
            if np.isnan(tc):
                tcstr = '******'
            else:
                tcstr = str(round(tc,2)).zfill(4)
            if np.isnan(tf):
                tfstr = '******'
            else:
                tfstr = str(round(tf,2)).zfill(4)

            line = tstr.rjust(7) + dstr.rjust(10) + fstr.rjust(11) + tcstr.rjust(10) + tfstr.rjust(10) + '\n'
            f_out.write(line)
    
            

    
def readedffile(edffile):
    
    encoding = 'utf-8'
    
    lon = lat = day = month = year = hour = minute = second = False #variables will be returned as 0 if unsuccessfully parsed
    
    depthcolumn = 0
    tempcolumn = 1
    
    rawtemperature = []
    rawdepth = []
    
    with open(edffile,'rb') as f_in:
        
        for line in f_in:
            try:
                line = line.decode(encoding).strip()
            except:
                fileinfo = chardet.detect(line)
                encoding = fileinfo['encoding']
                line = line.decode(encoding).strip()
                
            try:
                if ":" in line: #input parameter- parse appropriately
                    line = line.strip().split(':')
                    
                    
                    if "time" in line[0].lower(): #assumes time is in "HH", "HH:MM", or "HH:MM:SS" format
                        hour = int(line[1].strip())
                        minute = int(line[2].strip())
                        second = int(line[3].strip())
                        
                        
                    elif "date" in line[0].lower():
                        line = line[1].strip() #should be eight digits long
                        if "/" in line and len(line) <= 8: #mm/dd/yy format
                            line = line.split('/')
                            month = int(line[0])
                            day = int(line[1])
                            year = int(line[2]) + 2000
                        elif "/" in line and len(line) <= 10: #mm/dd/yyyy, or yyyy/mm/dd (assuming not dd/mm/yyyy)
                            line = line.split('/')
                            if len(line[0]) == 4:
                                year = int(line[0])
                                month = int(line[1])
                                day = int(line[2])
                            elif len(line[2]) == 4:
                                month = int(line[0])
                                day = int(line[1])
                                year = int(line[2])
                                
                        elif "-" in line and len(line) <= 8: #mm-dd-yy format
                            line = line.split('-')
                            month = int(line[0])
                            day = int(line[1])
                            year = int(line[2]) + 2000
                        elif "-" in line and len(line) <= 10: #mm-dd-yyyy, or yyyy-mm-dd (assuming not dd-mm-yyyy)
                            line = line.split('-')
                            if len(line[0]) == 4:
                                year = int(line[0])
                                month = int(line[1])
                                day = int(line[2])
                            elif len(line[2]) == 4:
                                year = int(line[2])
                                month = int(line[1])
                                day = int(line[0])
                        
                        else: #trying YYYYMMDD format instead
                            year = int(line[:4])
                            month = int(line[4:6])
                            day = int(line[6:8])
                            
                    
                    elif "latitude" in line[0].lower(): 
                        if 'n' in line[-1].lower() or 's' in line[-1].lower():
                            if len(line) == 2: #XX.XXXH format
                                lat = float(line[1][:-1])
                                if line[1][-1].lower() == 's':
                                    lat = -1.*lat
                            elif len(line) == 3: #XX:XX.XXXH format
                                lat = float(line[1]) + float(line[2][:-1])/60
                                if line[2][-1].lower() == 's':
                                    lat = -1.*lat
                            elif len(line) == 4: #XX:XX:XXH format
                                lat = float(line[1]) + float(line[2])/60 + float(line[3][:-1])/3600
                                if line[3][-1].lower() == 's':
                                    lat = -1.*lat
                        else:
                            if len(line) == 2: #XX.XXX format
                                lat = float(line[1])
                            elif len(line) == 3: #XX:XX.XXX format
                                lat = float(line[1]) + float(line[2])/60
                            elif len(line) == 4: #XX:XX:XX format
                                lat = float(line[1]) + float(line[2])/60 + float(line[3])/3600
                            
                    elif "longitude" in line[0].lower():
                        if 'e' in line[-1].lower() or 'w' in line[-1].lower():
                            if len(line) == 2: #XX.XXXH format
                                lon = float(line[1][:-1])
                                if line[1][-1].lower() == 'w':
                                    lon = -1.*lon
                            elif len(line) == 3: #XX:XX.XXXH format
                                lon = float(line[1]) + float(line[2][:-1])/60
                                if line[2][-1].lower() == 'w':
                                    lon = -1.*lon
                            elif len(line) == 4: #XX:XX:XXH format
                                lon = float(line[1]) + float(line[2])/60 + float(line[3][:-1])/3600
                                if line[3][-1].lower() == 'w':
                                    lon = -1.*lon
                        else:
                            if len(line) == 2: #XX.XXX format
                                lon = float(line[1])
                            elif len(line) == 3: #XX:XX.XXX format
                                lon = float(line[1]) + float(line[2])/60
                            elif len(line) == 4: #XX:XX:XX format
                                lon = float(line[1]) + float(line[2])/60 + float(line[3])/3600
                                
                                
                    elif "field" in line[0].lower(): #specifying which column contains temperature and depth
                        if "temperature" in line[1].lower():
                            tempcolumn = int(line[0].strip()[5]) - 1
                        elif "depth" in line[1].lower():
                            depthcolumn = int(line[0].strip()[5]) - 1
                        
                                
                #space-delimited temperature-depth obs or comments- attempt to parse as profile data, error will raise/function will move to next line if not
                else: 
                    line = line.strip().split() 
                    cdepth = float(line[depthcolumn])
                    ctemp = float(line[tempcolumn])
                    if cdepth >= 0 and ctemp >= -10 and ctemp <= 50:
                        rawdepth.append(cdepth)
                        rawtemperature.append(ctemp)
                    
            except (ValueError, IndexError, AttributeError):
                pass
            
    #converting to numpy arrays
    rawtemperature = np.asarray(rawtemperature)
    rawdepth = np.asarray(rawdepth)
    
    return rawtemperature,rawdepth,year,month,day,hour,minute,second,lat,lon

    
    
    
def writeedffile(edffile,temperature,depth,year,month,day,hour,minute,second,lat,lon,tcoeff,zcoeff,comments):
    with open(edffile,'w') as f_out:
    
        #writing header, date and time, drop # (bad value)
        f_out.write("// This is an AXBT EXPORT DATA FILE  (EDF)\n//\n")
        f_out.write(f"Date of Launch:  {month:02d}/{day:02d}/{year-2000}\n")
        f_out.write(f"Time of Launch:  {hour:02d}:{minute:02d}:{second:02d}\n")
        
        #latitude and longitude
        if lat >= 0:
            nsh = 'N'
        else:
            nsh = 'S'
        if lon >= 0:
            ewh = 'E'
        else:
            ewh = 'W'
        lon = abs(lon)
        lat = abs(lat)
        latdeg = int(np.floor(lat))
        londeg = int(np.floor(lon))
        latmin = (lat - latdeg)*60
        lonmin = (lon - londeg)*60
        f_out.write(f"Latitude      :  {latdeg:02d}:{latmin:06.3f}{nsh}\n")
        f_out.write(f"Longitude     :  {londeg:03d}:{lonmin:06.3f}{ewh}\n")

        f_out.write(f"""//
// Drop Settings Information:
Probe Type       :  AXBT
Terminal Depth   :  800 m
Depth Coeff. 1   :  {zcoeff[0]}
Depth Coeff. 2   :  {zcoeff[1]}
Depth Coeff. 3   :  {zcoeff[2]}
Depth Coeff. 4   :  {zcoeff[3]}
Pressure Pt Correction:  N/A
Temp. Coeff. 1   :  {tcoeff[0]}
Temp. Coeff. 2   :  {tcoeff[1]}
Temp. Coeff. 3   :  {tcoeff[2]}
Temp. Coeff. 4   :  {tcoeff[3]}
Display Units    :  Metric
Field0           :  Temperature (C)
Field1           :  Depth (m)
//
// This profile has not been quality-controlled.
""" + comments + """
//
Depth (m)  - Temperature (°C)\n""")

        #removing NaNs from T-D profile
        ind = []
        for t,d in zip(temperature,depth):
            ind.append(not np.isnan(t) and not np.isnan(d))
        depth = depth[ind]
        temperature = temperature[ind]

        #adding temperature-depth data now
        for d,t in zip(depth,temperature):
            f_out.write(f"{round(d,1):05.1f}\t{round(t,2):05.2f}\n")

    
    
    
#read data from JJVV file
def readjjvvfile(jjvvfile):
    with open(jjvvfile,'r') as f_in:

        depth = []
        temperature = []

        line = f_in.readline()
        line = line.strip().split()
        
        #date and time info
        datestr = line[1]
        day = int(datestr[:2])
        month = int(datestr[2:4])
        yeardigit = int(datestr[4])
        time = int(line[2][:4])
        
        #determining year (drop must have been within last 10 years)
        curyear = datetime.utcnow().year
        decade = int(np.floor(curyear/10)*10)
        if yeardigit + decade > curyear:
            decade -= 1
        year = decade + yeardigit

        #latitude and longitude
        latstr = line[3]
        lonstr = line[4]
        quad = int(latstr[0])
        lat = np.double(latstr[1:3]) + np.double(latstr[3:])/10**(len(latstr)-3)
        lon = np.double(lonstr[:3]) + np.double(lonstr[3:])/10**(len(lonstr)-3)
        if quad == 3:#hemisphere (if quad == 1, no need to change anything)
            lat = -1*lat
        elif quad == 5:
            lon = -1*lon
            lat = -1*lat
        elif quad == 7:
            lon = -1*lon
            
        lastdepth = -1
        hundreds = 0
        l = 0

        identifier = 'UNKNOWN'

        for line in f_in:
            l = l + 1

            #removing non-data entry from first column, 2nd line of JJVV
            line = line.strip().split()
            if l == 1: line = line[1:]

            for curentry in line:

                try:
                    int(curentry) #won't execute if curentry has non-numbers in it (e.g. the current entry is the identifier)

                    if int(curentry[:3]) == 999 and int(curentry[3:])*100 == hundreds + 100:
                        hundreds = hundreds + 100
                    else:
                        if int(curentry[:2]) + hundreds != lastdepth:
                            cdepth = int(curentry[:2]) + hundreds
                            lastdepth = cdepth
                            depth.append(cdepth)
                            temperature.append(np.double(curentry[2:])/10)

                except: identifier = curentry
    
    #converting to numpy arrays
    depth = np.asarray(depth)
    temperature = np.asarray(temperature)
    
    return [temperature,depth,day,month,year,time,lat,lon,identifier]




#write data to JJVV file
def writejjvvfile(jjvvfile,temperature,depth,day,month,year,time,lat,lon,identifier,isbtmstrike):
    
    #open file for writing
    with open(jjvvfile,'w') as f_out:
    
        #first line- header information
        if lon >= 0 and lat >= 0:
            quad = '1'
        elif lon >= 0 and lat < 0:
            quad = '3'
        elif lon < 0 and lat >= 0:
            quad = '7'
        else:
            quad = '5'

        f_out.write(f"JJVV {day:02d}{month:02d}{str(year)[3]} {time:04d}/ {quad}{int(abs(lat)*1000):05d} {int(abs(lon)*1000):06d} 88888\n")

        #create a list with all of the entries for the file
        filestrings = []
        filestrings.append('51099')
        hundreds = 0
        i = 0
        lastdepth = -1

        # appending data to list, adding hundreds increment counters where necessary (while loop necessary in case a gap > 100m exists)
        while i < len(depth):
            cdepth = round(depth[i])
            ctemp = temperature[i]
            
            if cdepth - hundreds > 99:  # need to increment hundreds counter in file
                hundreds = hundreds + 100
                filestrings.append(f'999{int(hundreds/100):02d}')
            else:
                if cdepth - lastdepth >= 1 and cdepth - hundreds <= 99:  # depth must be increasing, not outside of current hundreds range
                    lastdepth = cdepth
                    filestrings.append(f"{int(round(cdepth-hundreds)):02d}{int(round(ctemp,1)*10):03d}")
                    
                i += 1

        if isbtmstrike: #note if the profile struck the bottom
            filestrings.append('00000')

        identifier = identifier[:5] #concatenates if larger than 5 digits
        filestrings.append(identifier) #tack identifier onto end of file entries

        #writing all data to file
        i = 0
        while i < len(filestrings):
            if i == 0 and len(filestrings) >= 6: #first line has six columns (only if there is enough data)
                line = f"{filestrings[i]} {filestrings[i+1]} {filestrings[i+2]} {filestrings[i+3]} {filestrings[i+4]} {filestrings[i+5]}\n"
                i += 6
            elif i+5 < len(filestrings): #remaining full lines have five columns
                line = f"{filestrings[i]} {filestrings[i+1]} {filestrings[i+2]} {filestrings[i+3]} {filestrings[i+4]}\n"
                i += 5
            else: #remaining data on last line
                line = ''
                while i < len(filestrings):
                    line += filestrings[i]
                    if i == len(filestrings) - 1:
                        line += '\n'
                    else:
                        line += ' '
                    i += 1
            f_out.write(line)
            



#read data from FIN file
def readfinfile(finfile):
    
    with open(finfile,'r') as f_in:

        line = f_in.readline()
        line = line.strip().split()

        #pulling relevant header information
        year = int(line[0])
        dayofyear = int(line[1])
        curdate = date.fromordinal(date.toordinal(date(year-1,12,31)) + dayofyear)
        day = curdate.day
        month = curdate.month
        time = int(line[2])
        lat = np.double(line[3])
        lon = np.double(line[4])
        num = int(line[5])

        #setting up lists
        temperature = []
        depth = []

        #reading temperature depth profiles
        for line in f_in:

            line = line.strip().split()

            i = 0
            while i < len(line)/2:
                depth.append(np.double(line[2*i+1]))
                temperature.append(np.double(line[2*i]))
                i = i + 1

    #converting data to arrays
    depth = np.asarray(depth)
    temperature = np.asarray(temperature)
    
    return [temperature,depth,day,month,year,time,lat,lon,num]




#write data to FIN file
def writefinfile(finfile,temperature,depth,day,month,year,time,lat,lon,num):
    
    with open(finfile,'w') as f_out:
    
        dayofyear = date.toordinal(date(year,month,day)) - date.toordinal(date(year-1,12,31))

        #formatting latitude string
        if lat >= 0:
            latsign = ' '
        else:
            latsign = '-'
            lat = abs(lat)

        #formatting longitude string
        if lon >= 0:
            lonsign = ' '
        else:
            lonsign = '-'
            lon = abs(lon)

        #writing header data
        f_out.write(f"{year}   {dayofyear:03d}   {time:04d}   {latsign}{lat:06.3f}   {lonsign}{lon:07.3f}   {num:02d}   6   {len(depth)}   0   0   \n")

        #writing profile data
        i = 0
        while i < len(depth):

            if i+5 < len(depth):
                line = f"{temperature[i]: 8.3f}{depth[i]: 8.1f}{temperature[i+1]: 8.3f}{depth[i+1]: 8.1f}{temperature[i+2]: 8.3f}{depth[i+2]: 8.1f}{temperature[i+3]: 8.3f}{depth[i+3]: 8.1f}{temperature[i+4]: 8.3f}{depth[i+4]: 8.1f}\n"

            else:
                line = ''
                while i < len(depth):
                    line += f"{temperature[i]: 8.3f}{depth[i]: 8.1f}"
                    i += 1
                line = line + '\n'

            f_out.write(line)
            i = i + 5



            
def writebufrfile(bufrfile, temperature, depth, year, month, day, time, lon, lat,identifier, originatingcenter, hasoptionalsection, optionalinfo):

    #convert time into hours and minutes
    hour = int(np.floor(time / 100))
    minute = int(time - hour * 100)

    binarytype = 'big'  # big-endian
    reserved = 0
    version = 4  # BUFR version number (3 or 4 supported)

    # section 1 info
    if version == 3:
        sxn1len = 18
    elif version == 4:
        sxn1len = 22

    mastertable = 0  # For standard WMO FM 94-IX BUFR table
    originatingsubcenter = 0
    updatesequencenum = 0  # first iteration
    if hasoptionalsection:
        hasoptionalsectionnum = int('10000000', 2)
    else:
        hasoptionalsectionnum = int('00000000', 2)
    datacategory = 31  # oceanographic data (Table A)
    datasubcategory = 3 #bathy (JJVV) message
    versionofmaster = 32
    versionoflocal = 0
    yearofcentury = int(year - 100 * np.floor(year / 100))  # year of the current century

    # section 2 info
    if hasoptionalsection:
        sxn2len = len(optionalinfo) + 4
    else:
        sxn2len = 0

    # Section 3 info
    sxn3len = 25  # 3 length + 1 reserved + 2 numsubsets + 1 flag + 2 FXY = 9 octets
    numdatasubsets = 1
    
    # whether data is observed, compressed (bits 1/2), bits 3-8 reserved (=0)
    s3oct7 = int('10000000', 2)
    
    fxy_all = [int('0000000100001011', 2),int('1100000100001011', 2),int('1100000100001100', 2),int('1100000100010111', 2),int('0000001000100000', 2),int('0100001000000000', 2),int('0001111100000010', 2),int('0000011100111110', 2),int('0001011000101010', 2),] #WITH DELAYED (8-bit) REPLICATION

    # Section 4 info (data)
    identifier = identifier[:9] #concatenates identifier if necessary
    idtobuffer = 9 - len(identifier) # padding and encoding station identifier
    id_utf = identifier.encode('utf-8')
    for i in range(0, idtobuffer):
        id_utf = id_utf + b'\0' #pads with null character (\0 in python)

    # setting up data array
    bufrarray = ''

    # year/month/day (3,01,011)
    bufrarray = bufrarray + format(year, '012b')  # year (0,04,001)
    bufrarray = bufrarray + format(month, '04b')  # month (0,04,002)
    bufrarray = bufrarray + format(day, '06b')  # day (0,04,003)

    # hour/minute (3,01,012)
    bufrarray = bufrarray + format(hour, '05b')  # hour (0,04,004)
    bufrarray = bufrarray + format(minute, '06b')  # min (0,04,005)

    # lat/lon (3,01,023)
    bufrarray = bufrarray + format(int(np.round((lat * 100)) + 9000), '015b')  # lat (0,05,002)
    bufrarray = bufrarray + format(int(np.round((lon * 100)) + 18000), '016b')  # lon (0,06,002)

    # temperature-depth profile (3,06,001)
    bufrarray = bufrarray + '00'  # indicator for digitization (0,02,032): 'values at selected depths' = 0
    bufrarray = bufrarray + format(len(temperature),'16b')  # delayed descripter replication factor(0,31,001) = length
    
    #converting temperature and depth and writing
    for t,d in zip(temperature,depth):
        d_in = int(np.round(d*10)) # depth (0,07,062)
        bufrarray = bufrarray + format(d_in,'017b')
        t_in = int(np.round(10 * (t + 273.15)))  # temperature (0,22,042)
        bufrarray = bufrarray + format(t_in,'012b')

    #padding zeroes to get even octet number, determining total length
    bufrrem = len(bufrarray)%8
    for i in range(8-bufrrem):
        bufrarray = bufrarray + '0'
    bufrarraylen = int(len(bufrarray)/8)
    sxn4len = 4 + 9 + bufrarraylen  # length/reserved + identifier + bufrarraylen (lat/lon, dtg, t/d profile)
    
    # total length of file in octets
    num_octets = 8 + sxn1len + sxn2len + sxn3len + sxn4len + 4  # sxn's 0 and 5 always have 8 and 4 octets, respectively

    # writing the file
    with open(bufrfile, 'wb') as bufr:

        # Section 0 (indicator)
        bufr.write(b'BUFR')  # BUFR
        bufr.write(num_octets.to_bytes(3, byteorder=binarytype, signed=False))  # length (in octets)
        bufr.write(version.to_bytes(1, byteorder=binarytype, signed=False))

        # Section 1 (identifier) ***BUFR version 3 or 4 ****
        bufr.write(sxn1len.to_bytes(3, byteorder=binarytype, signed=False))
        bufr.write(mastertable.to_bytes(1, byteorder=binarytype, signed=False))
        if version == 3:
            bufr.write(originatingsubcenter.to_bytes(1, byteorder=binarytype, signed=False))
            bufr.write(originatingcenter.to_bytes(1, byteorder=binarytype, signed=False))
        elif version == 4:
            bufr.write(originatingcenter.to_bytes(2, byteorder=binarytype, signed=False))
            bufr.write(originatingsubcenter.to_bytes(2, byteorder=binarytype, signed=False))
        bufr.write(updatesequencenum.to_bytes(1, byteorder=binarytype, signed=False))
        bufr.write(hasoptionalsectionnum.to_bytes(1, byteorder=binarytype, signed=False))
        bufr.write(datacategory.to_bytes(1, byteorder=binarytype, signed=False))
        bufr.write(datasubcategory.to_bytes(1, byteorder=binarytype, signed=False))
        if version == 4:
            bufr.write(datasubcategory.to_bytes(1, byteorder=binarytype, signed=False)) #write again for local data subcategory in version 4
        bufr.write(versionofmaster.to_bytes(1, byteorder=binarytype, signed=False))
        bufr.write(versionoflocal.to_bytes(1, byteorder=binarytype, signed=False))
        if version == 3:
            bufr.write(yearofcentury.to_bytes(1, byteorder=binarytype, signed=False))
        elif version == 4:
            bufr.write(year.to_bytes(2, byteorder=binarytype, signed=False))
        bufr.write(month.to_bytes(1, byteorder=binarytype, signed=False))
        bufr.write(day.to_bytes(1, byteorder=binarytype, signed=False))
        bufr.write(hour.to_bytes(1, byteorder=binarytype, signed=False))
        bufr.write(minute.to_bytes(1, byteorder=binarytype, signed=False))
        bufr.write(int(0).to_bytes(1, byteorder=binarytype, signed=False)) #seconds for v4, oct18 = 0 (reserved) for v3

        # Section 2 (optional)
        if hasoptionalsection:
            bufr.write(sxn2len.to_bytes(3, byteorder=binarytype, signed=False))
            bufr.write(reserved.to_bytes(1, byteorder=binarytype, signed=False))
            bufr.write(optionalinfo)

        # Section 3 (Data description)
        bufr.write(sxn3len.to_bytes(3, byteorder=binarytype, signed=False))
        bufr.write(reserved.to_bytes(1, byteorder=binarytype, signed=False))
        bufr.write(numdatasubsets.to_bytes(2, byteorder=binarytype, signed=False))
        bufr.write(s3oct7.to_bytes(1, byteorder=binarytype, signed=False))
        for fxy in fxy_all:
            bufr.write(fxy.to_bytes(2, byteorder=binarytype, signed=False))

        # Section 4
        bufr.write(sxn4len.to_bytes(3, byteorder=binarytype, signed=False))
        bufr.write(reserved.to_bytes(1, byteorder=binarytype, signed=False))
        bufr.write(id_utf)

        #writing profile data- better option- converts and writes 1 byte at a time
        for cbit in np.arange(0,len(bufrarray),8):
            bufr.write(int(bufrarray[cbit:cbit+8],2).to_bytes(1,byteorder=binarytype,signed=False)) #writing profile data

        # Section 5 (End)
        bufr.write(b'7777')

        
        
def writekmlfile(kmlfile, lon, lat, year, month, day, time):
    #create the name and coordinate strings of the placemark that will be used
    pointname = f'{year}{month}{day}{time}.kml'
    coordstring = f'{lon} {lat}'

    #create a placemark
    plm = kml.Placemark(kml.Name(pointname), kml.Point(kml.coordinates(coordstring)))

    #get the string of the placemark
    plm_string = lxml.etree.tostring(plm, pretty_print = True)

    #write the file
    with open(kmlfile, 'wb') as file:
        file.write(plm_string)

        
        
def readkmlfile(kmlfile):
    with open(kmlfile, 'rb') as file:
        data = parser.parse(file)

    #return the kml file object
    return data
