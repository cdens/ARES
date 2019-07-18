import numpy as np
from datetime import date

#read raw temperature/depth profile from LOGXX.DTA file
def readlogfile(logfile):
    f_in = open(logfile,'r')

    depth = []
    temperature = []

    for line in f_in:
    
        line = line.strip().split() #get rid of \n character, split by spaces
    
        try:
            curfreq = np.double(line[2])
        except:
            curfreq = np.NaN
        
        if ~np.isnan(curfreq) and curfreq != 0: #if it is a valid frequency, save the datapoint
            depth.append(np.double(line[1]))
            temperature.append(np.double(line[3]))
            
    f_in.close()
    
    depth = np.asarray(depth)
    temperature = np.asarray(temperature)
    
    return [temperature,depth]


#read raw temperature/depth profile with all other data from LOGXX.DTA file
def readlogfile_alldata(logfile):
    f_in = open(logfile,'r')

    time = []
    depth = []
    frequency = []
    temperature = []
    
    for i in range(6):
        f_in.readline()

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
            
    f_in.close()
    
    time = np.asarray(time)
    depth = np.asarray(depth)
    frequency = np.asarray(frequency)
    temperature = np.asarray(temperature)
    
    return [temperature,depth,time,frequency]
    
    
def writelogfile(logfile,initdatestr,inittimestr,timefromstart,depth,frequency,tempc):
    f_out = open(logfile,'w')
    f_out.write('     Probe Type = AXBT\n')
    f_out.write('       Date = ' + initdatestr + '\n')
    f_out.write('       Time = ' + inittimestr + '\n\n')
    f_out.write('    Time     Depth    Frequency    (C)       (F) \n\n')
    
    tempf = tempc*1.8+32
    
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
        
    f_out.close()
    
    
    
    
    
def readedffile(edffile):
    f_in = open(edffile,'rb')
    
    #trash lines
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
    
    #trash line
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
    
    #lots of trash lines
    for i in range(25):
        line = f_in.readline()
        
    #reading temperature-depth profile
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
    f_in.close()
    
    
    
def writeedffile(edffile,rawtemperature,rawdepth,year,month,day,hour,minute,second,lat,lon):
    f_out = open(edffile,'wb')
    
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
Depth Equation   :  Standard
Depth Coeff. 1   :  0.0
Depth Coeff. 2   :  1.610300
Depth Coeff. 3   :  -0.000163
Depth Coeff. 4   :  0.0
Pressure Pt Correction:  N/A
//
Raw Data Filename:  23
//
Display Units    :  Metric
//
// This XBT export file has not been noise reduced or averaged.
//
// Sound velocity derived with assumed salinity: 0.00 ppt
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
        line = str(round(d,1))+"\t"+str(round(t,2))+"\n"
        line = bytes(line,'utf-8')
        f_out.write(line)
    
    
    
    
#read data from JJVV file
def readjjvvfile(jjvvfile,decade):
    f_in = open(jjvvfile,'r')

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
    for line in f_in:
        l = l + 1
        
        #removing non-data entry from first column, 2nd line of JJVV
        line = line.strip().split() 
        if l == 1: line = line[1:]
        
        for curentry in line:
            
            try:
                int(curentry) #won't execute if curentry has non-numbers in it (e.g. the current entry is the identifier)
                
                if (int(curentry[:3]) == 999 and int(curentry[3:])*100 == hundreds + 100):
                    hundreds = hundreds + 100
                else:
                    if int(curentry[:2]) + hundreds != lastdepth:
                        cdepth = int(curentry[:2]) + hundreds
                        lastdepth = cdepth
                        depth.append(cdepth)
                        temperature.append(np.double(curentry[2:])/10)
                    
            except: identifier = curentry

    identifier = 'AF309'
    
    f_in.close()
    
    depth = np.asarray(depth)
    temperature = np.asarray(temperature)
    
    return [temperature,depth,day,month,year,time,lat,lon,identifier]





#write data to JJVV file
def writejjvvfile(jjvvfile,temperature,depth,day,month,year,time,lat,lon,identifier):
    
    #open file for writing
    f_out = open(jjvvfile,'w')
    
    #first line- header information
    lonstr = str(int(abs(lon*1000))).zfill(6)
    latstr = str(int(abs(lat*1000))).zfill(5)
    if (lon >= 0 and lat >= 0):
        quad = '1'
    elif (lon >= 0 and lat < 0):
        quad = '3'
    elif (lon < 0 and lat >= 0):
        quad = '7'
    else:
        quad = '5'
        
    line = 'JJVV ' + str(day).zfill(2)+str(month).zfill(2)+str(year)[3] + ' ' + str(time).zfill(4)+'/ ' + quad + latstr + ' ' + lonstr + ' 8888\n'
    f_out.write(line)
    
    #create a list with all of the entries for the file
    filestrings = []
    filestrings.append('51099')
    hundreds = 0
    i = 0
    while i < len(depth):
        if depth[i]-hundreds > 99:
            hundreds = hundreds + 100
            filestrings.append('999' + str(int(hundreds/100)).zfill(2))        
        filestrings.append(str(int(depth[i]-hundreds)).zfill(2) + str(int(round(temperature[i],1)*10)).zfill(3))
        i = i + 1
    filestrings.append(identifier) #tack identifier onto end of file entries
        
    #writing all data to file
    i = 0
    while i < len(filestrings):
        if i == 0: #first line has six columns
            line = (filestrings[i] + ' ' + filestrings[i+1] + ' ' + filestrings[i+2] + ' ' + filestrings[i+3]
                     + ' ' + filestrings[i+4] + ' ' + filestrings[i+5] + '\n')
        elif i+5 < len(filestrings): #remaining full lines have five columns
            line = (filestrings[i] + ' ' + filestrings[i+1] + ' ' + filestrings[i+2] + ' ' 
                     + filestrings[i+3] + ' ' + filestrings[i+4] + ' ' + '\n')
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
        i = i + 5
    
    #closing file
    f_out.close()
        





#read data from FIN file
def readfinfile(finfile):
    
    f_in = open(finfile,'r')
    
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
            
    f_in.close()
    
    depth = np.asarray(depth)
    temperature = np.asarray(temperature)
    
    return [temperature,depth,day,month,year,time,lat,lon,num]






#write data to FIN file
def writefinfile(finfile,temperature,depth,day,month,year,time,lat,lon,num):
    
    f_out = open(finfile,'w')
    
    dayofyear = date.toordinal(date(year,month,day)) - date.toordinal(date(year-1,12,31))
    
    line = (str(year) + '   ' + str(dayofyear) + '   ' + str(time) + '   ' + str(lat) + '   ' +
            str(lon) + '   ' + str(num) + '   6   ' + str(len(depth)) + '   0   0   \n')
    f_out.write(line)
    
    
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

    f_out.close()