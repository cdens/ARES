# =============================================================================
#     Code: tropicfileinteraction.py
#     Author: ENS Casey R. Densmore, 20JUN2019
#    
#     Purpose: Provides functions to write/read various AXBT data file formats
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
#		
# =============================================================================

import numpy as np
from datetime import date

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
    with open(edffile,'rb') as f_in:
    
        #misc. header lines
        line = f_in.readline()
        line = f_in.readline()

        #date of launch
        line = f_in.readline()
        line = line.decode('utf-8')
        day = int(line[17:19])
        month = int(line[20:22])
        year = int(line[23:42]) + 2000

        #time of launch
        line = f_in.readline()
        line = line.decode('utf-8')
        hour = int(line[17:19])
        minute = int(line[20:22])
        second = int(line[23:42])

        #misc. header line
        line = f_in.readline()

        #latitude
        line = f_in.readline()
        line = line.decode('utf-8')
        lat = float(line[17:19]) + float(line[20:-3])/60
        if line[-3].lower() == 's':
            lat = -1.*lat

        #longitude
        line = f_in.readline()
        line = line.decode('utf-8')
        lon = float(line[17:20]) + float(line[21:-3])/60
        if line[-3].lower() == 'w':
            lon = -1.*lon

        #lots of misc. header lines
        for i in range(25):
            line = f_in.readline()

        #reading temperature-depth profile (ignoring sound speed if present)
        rawtemperature = []
        rawdepth = []
        for line in f_in:
            try:
                line = line.decode('utf-8')
                line = line.strip().split() #get rid of \n character, split by spaces
                rawdepth.append(float(line[0]))
                rawtemperature.append(float(line[1]))
            except:
                break

        #converting to numpy arrays
        rawtemperature = np.asarray(rawtemperature)
        rawdepth = np.asarray(rawdepth)
    
    return rawtemperature,rawdepth,year,month,day,hour,minute,second,lat,lon

    
    
def writeedffile(edffile,rawtemperature,rawdepth,year,month,day,hour,minute,second,lat,lon):
    with open(edffile,'wb') as f_out:
    
        #writing header, date and time, drop # (bad value)
        f_out.write(b"// This is a MK21 EXPORT DATA FILE  (EDF)\n//\n")
        line = "Date of Launch:  " + str(day).zfill(2) +'/'+str(month).zfill(2)+'/'+str(year-2000).zfill(2)+'\n'
        line = bytes(line,'utf-8')
        f_out.write(line)
        line = "Time of Launch:  " + str(hour).zfill(2) +':'+str(minute).zfill(2)+':'+str(second).zfill(2)+'\n'
        line = bytes(line,'utf-8')
        f_out.write(line)
        f_out.write(bytes("Sequence #    :  99\n","utf-8"))

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
        latminstr = '%06.4f'%latmin
        latminstr = latminstr.rjust(7,'0')
        lonminstr = '%05.3f'%lonmin
        lonminstr = lonminstr.rjust(6,'0')
        line = "Latitude      :  " + str(latdeg).zfill(2) + ':' + latminstr + nsh + "\n"
        line = bytes(line,'utf-8')
        f_out.write(line)
        line = "Longitude     :  " + str(londeg).zfill(3) + ':' + lonminstr + ewh + "\n"
        line = bytes(line,'utf-8')
        f_out.write(line)

        line = """Serial #      :  99
//
// Here are the contents of the memo fields.
// Depth 6000 Sst -99.00 Sssv -99.00 SssvSst -99.00
//
// Here is some probe information for this drop.
//
Probe Type       :  AXBT
Terminal Depth   :  800 m
Depth Equation   :  Simple
Depth Coeff. 1   :  0.0
Depth Coeff. 2   :  1.5
Depth Coeff. 3   :  0.0
Depth Coeff. 4   :  0.0
Pressure Pt Correction:  N/A
//
Raw Data Filename:  N/A
//
Display Units    :  Metric
//
// This XBT export file has not been noise reduced or averaged.
//
// Sound velocity not included.
//
Depth (m)  - Temperature (°C)\n"""
    
        line = bytes(line,'utf-8')
        f_out.write(line)

        #removing NaNs from T-D profile
        ind = []
        for i in range(len(rawtemperature)):
            ind.append(not np.isnan(rawtemperature[i]) and not np.isnan(rawdepth[i]))
        rawdepth = rawdepth[ind]
        rawtemperature = rawtemperature[ind]

        #adding temperature-depth data now
        for d,t in zip(rawdepth,rawtemperature):
            line = str(round(d,1)).zfill(5) +"\t"+str(round(t,2)).zfill(4)+"\n"
            line = bytes(line,'utf-8')
            f_out.write(line)
    
    
    
    
#read data from JJVV file
def readjjvvfile(jjvvfile,decade):
    with open(jjvvfile,'r') as f_in:

        depth = []
        temperature = []

        line = f_in.readline()
        line = line.strip().split()

        #date and time info
        datestr = line[1]
        day = int(datestr[:2])
        month = int(datestr[2:4])
        year = int(datestr[4])+decade
        time = int(line[2][:4])

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
        lonstr = str(int(abs(lon*1000))).zfill(6)
        latstr = str(int(abs(lat*1000))).zfill(5)
        if lon >= 0 and lat >= 0:
            quad = '1'
        elif lon >= 0 and lat < 0:
            quad = '3'
        elif lon < 0 and lat >= 0:
            quad = '7'
        else:
            quad = '5'

        line = 'JJVV ' + str(day).zfill(2)+str(month).zfill(2)+str(year)[3] + ' ' + str(time).zfill(4)+'/ ' + quad + latstr + ' ' + lonstr + ' 88888\n'
        f_out.write(line)

        #create a list with all of the entries for the file
        filestrings = []
        filestrings.append('51099')
        hundreds = 0
        i = 0
        lastdepth = -1

        # appending data to list, adding hundreds increment counters where necessary
        while i < len(depth):
            curdepth = int(depth[i])
            if curdepth - hundreds > 99:  # need to increment hundreds counter in file
                hundreds = hundreds + 100
                filestrings.append('999' + str(int(hundreds / 100)).zfill(2))
            else:
                if curdepth - lastdepth >= 1 and curdepth - hundreds <= 99:  # depth must be increasing, not outside of current hundreds range
                    filestrings.append(
                        str(curdepth - hundreds).zfill(2) + str(int(round(temperature[i], 1) * 10)).zfill(3))
                    lastdepth = curdepth
                i += 1

        if isbtmstrike: #note if the profile struck the bottom
            filestrings.append('00000')

        identifier = identifier[:5] #concatenates if larger than 5 digits
        filestrings.append(identifier) #tack identifier onto end of file entries

        #writing all data to file
        i = 0
        while i < len(filestrings):
            if i == 0 and len(filestrings) >= 6: #first line has six columns (only if there is enough data)
                line = (filestrings[i] + ' ' + filestrings[i+1] + ' ' + filestrings[i+2] + ' ' + filestrings[i+3]
                         + ' ' + filestrings[i+4] + ' ' + filestrings[i+5] + '\n')
                i = i + 6
            elif i+5 < len(filestrings): #remaining full lines have five columns
                line = (filestrings[i] + ' ' + filestrings[i+1] + ' ' + filestrings[i+2] + ' '
                         + filestrings[i+3] + ' ' + filestrings[i+4] + ' ' + '\n')
                i = i + 5
            else: #remaining data on last line
                line = ''
                while i < len(filestrings):
                    line = line + filestrings[i]
                    if i == len(filestrings) - 1:
                        line = line + '\n'
                    else:
                        line = line + ' '
                    i = i + 1
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
            signstr = ' '
        else:
            signstr = '-'
            lat = abs(lat)
        latfloor = np.floor(lat)
        latrem = np.round((lat - latfloor)*1000)
        latstr = signstr + str(int(latfloor)).zfill(2) + '.' + str(int(latrem)).rjust(3,'0')

        #formatting longitude string
        if lon >= 0:
            signstr = ' '
        else:
            signstr = '-'
            lon = abs(lon)
        lonfloor = np.floor(lon)
        lonrem = np.round((lon - lonfloor)*1000)
        lonstr = signstr + str(int(lonfloor)).zfill(3) + '.' + str(int(lonrem)).rjust(3,'0')

        #writing header data
        line = (str(year).zfill(4) + '   ' + str(dayofyear).zfill(3) + '   ' + str(time).zfill(4) + '   ' + latstr + '   ' +
                lonstr + '   ' + str(num).zfill(2) + '   6   ' + str(len(depth)) + '   0   0   \n')
        f_out.write(line)

        #writing profile data
        i = 0
        while i < len(depth):

            if i+5 < len(depth):
                line = ('{: 8.3f}'.format(temperature[i]) + '{: 8.1f}'.format(depth[i])
                + '{: 8.3f}'.format(temperature[i+1]) + '{: 8.1f}'.format(depth[i+1])
                + '{: 8.3f}'.format(temperature[i+2]) + '{: 8.1f}'.format(depth[i+2])
                + '{: 8.3f}'.format(temperature[i+3]) + '{: 8.1f}'.format(depth[i+3])
                + '{: 8.3f}'.format(temperature[i+4]) + '{: 8.1f}'.format(depth[i+4]) + '\n')

            else:
                line = ''
                while i < len(depth):
                    line = line + '{: 8.3f}'.format(temperature[i]) + '{: 8.1f}'.format(depth[i])
                    i = i + 1
                line = line + '\n'

            f_out.write(line)
            i = i + 5




def writebufrfile(bufrfile, temperature, depth, year, month, day, time, lon, lat, identifier, originatingcenter, hasoptionalsection, optionalinfo):

    #convert time into hours and minutes
    hour = int(np.floor(time / 100))
    minute = int(time - hour * 100)

    binarytype = 'big'  # big-endian
    reserved = 0
    version = 4  # BUFR version number (3 or 4 supported)

    # section 1 info
    if version == 4:
        sxn1len = 22
    else: #including versions 1-3
        sxn1len = 18

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
    sxn3len = 9  # 3 length + 1 reserved + 2 numsubsets + 1 flag + 2 FXY = 9 octets
    numdatasubsets = 1
    # whether data is observed, compressed (bits 1/2), bits 3-8 reserved (=0)
    s3oct7 = int('10000000', 2)
    # FXY = 3,15,001 (base 10) = 11, 001111, 00000001 (binary) corresponds to underwater sounding w/t optional fields
    fxy = int('1100111100000001', 2)

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
    bufrarray = bufrarray + format(len(temperature),'08b')  # delayed descripter replication factor(0,31,001) = length

    #converting temperature and depth and writing
    for t,d in zip(temperature,depth):
        d = int(np.round(d*10)) # depth (0,07,062)
        bufrarray = bufrarray + format(d,'017b')
        t = int(np.round(10 * (t + 273.15)))  # temperature (0,22,042)
        bufrarray = bufrarray + format(t,'012b')

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
        bufr.write(fxy.to_bytes(2, byteorder=binarytype, signed=False))

        # Section 4
        bufr.write(sxn4len.to_bytes(3, byteorder=binarytype, signed=False))
        bufr.write(reserved.to_bytes(1, byteorder=binarytype, signed=False))
        bufr.write(id_utf)

        #writing profile data- bad option as the base 10 integer for the bufrarray may be huge if the profile is long enought
        # bufr.write(int(bufrarray,2).to_bytes(bufrarraylen,byteorder=binarytype,signed=False)) 

        #writing profile data- better option- converts and writes 1 byte at a time
        for cbit in np.arange(0,len(bufrarray),8):
            bufr.write(int(bufrarray[cbit:cbit+8],2).to_bytes(1,byteorder=binarytype,signed=False)) #writing profile data

        # Section 5 (End)
        bufr.write(b'7777')

