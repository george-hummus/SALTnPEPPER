"""
The functions that are used in all the modules of PAF-UP.

Author: George Hume
2023
"""

### IMPORTS ###
import csv
import json
import numpy as np
import datetime as dt
from skyfield import almanac
from skyfield.api import N, E, wgs84, load, utc, Star
import subprocess
from astropy import units as u
from astropy.coordinates import SkyCoord

################# FUNCTIONS FOR UPDATING TNS DATABASE ##########################

def loadDB(filename):
    """
    Function to load in the TNS database from its CSV file
    Arguments:
        - filename: A string representing file name of the TNS database (usually 'tns_public_objects.csv')
    Outputs:
        - date: the date the TNS database was updated as a string in the format '%Y-%m-%d %H:%M:%S'
        - headers: the first row of the database containing the column headers as a list
        - database: numpy object array containg all the entries of the TNS database
    """

    file=open(filename)
    csvreader = csv.reader(file) #openfile as csv
    date = next(csvreader) #save the date
    headers = next(csvreader) #save headers
    database = []
    for row in csvreader:
            database.append(row) #save all rows into a list
    #convert list into numpy array
    database = np.array(database,dtype="object")

    file.close()

    return date[0], headers, database

################################################################################

def dload(file, creds):
    """
    Function to download CSV files from the TNS via a TNS bot with an API key.
    Arguments:
        - file: A string representing file name on the TNS database (e.g., 'tns_public_objects.csv')
        - creds: A JSON file containing the tns_id, name, and api_key of the TNS bot
    Outputs:
        - Saves the file to the xOUTPUTS directory
    """

    #string that consitutues the curl commnad for downloading
    cmd1 = '''curl -X POST -H 'user-agent: tns_marker{"tns_id":'''
    cmd2 = ''',"type": "bot", "name":"'''
    cmd3 = '''"}' -d 'api_key='''
    cmd4 = '''' https://www.wis-tns.org/system/files/tns_public_objects/'''
    cmd5 = '''.zip > ../xOUTPUTS/'''
    cmd6 = '''.zip'''
    cmd = f'{cmd1}{creds["tns_id"]}{cmd2}{creds["name"]}{cmd3}{creds["api_key"]}{cmd4}{file}{cmd5}{file}{cmd6}'

    #do the curl command to download the update file
    subprocess.call(cmd,shell=True)

    #unzip the csv and delete the zip file
    uzip = f"unzip ../xOUTPUTS/{file}.zip -d ../xOUTPUTS/"
    rem = f"rm ../xOUTPUTS/{file}.zip"
    subprocess.call(uzip,shell=True)
    subprocess.call(rem,shell=True)

################################################################################

def UPdate(ufile,date,database):
    """
    This function updates the local TNS database using update files from the TNS server.
    Arguments:
        - ufile: a string representing the name of the update file from the TNS. Form is 'tns_public_objects_YYYYMMDD.csv'.
        - date: todays date as a datetime object.
        - database: the values of the tns database (minus the date and headers) as numpy array.
    Outputs:
        - a newly updated tns_public_objects.csv file
    """

    #load in update entries (skip date and headers tho)
    UDname = f"../xOUTPUTS/{ufile}"
    dummy,headers,updates = loadDB(UDname)

    #now need to loop through each entry in the updates  and find match/ or add if new to the database
    #need to loop from bottom to top so to add newest entries to the top of the database
    for i in range(len(updates)):
        row = updates[-(i+1)] #extarcts rows from bottom upwards (index -1 -> -len)
        ID = row[0] #get the id of the update
        IDrow = np.where(database == ID)[0] # looks for row corresponding to ID in the database

        if IDrow.size == 0: #if id is not in database then this is a new ID
            database = np.vstack([row,database]) #inserts new ID at the top of the database
        else: #if it is in database then we need to update the entry
            database[IDrow[0]] = row

    database = np.vstack([headers,database]) #add the headers back to the top

    #save out the database
    filename = "../xOUTPUTS/tns_public_objects.csv"
    with open(filename, 'w') as file:
        csvwriter = csv.writer(file,delimiter=",") # create a csvwriter object
        csvwriter.writerow([date.strftime('%Y-%m-%d %H:%M:%S')]) #add date to first row
        csvwriter.writerows(database) # write the headers and rest of the data


################# FUNCTIONS FOR CALCULATING PRIORITY SCORES ##########################

def TNSlice(database,date):
    """
    Function that slices the TNS database so only the transients discovered in the last 3 months
    and modified in the last 2 weeks are left.
    Arguments:
        - database: numpy object array contining the TNS database
        - date: string representing the date that the TNS database was released (in format '%Y-%m-%d %H:%M:%S')
    Outputs:
        - sliceDB: numpy object array of the sliced TNS database
    """

    #extract the time modified and the time discovered
    t_mod = database.T[-1]
    t_disc = database.T[12]

    #convert the date csv was released as datetime object
    rdate = dt.datetime.strptime(date, '%Y-%m-%d %H:%M:%S')
    #datetime limits for the time modified and time discovered
    fortnight = rdate - dt.timedelta(weeks=2) #2 weeks ago
    threemonths = rdate - dt.timedelta(weeks=12) #3 months ago (or 12 weeks)

    good_tars = [] #empty list to save rows which pass the slicing to

    for i in range(t_mod.size):
        #convert times to datetime objects
        tMOD = dt.datetime.strptime(t_mod[i], '%Y-%m-%d %H:%M:%S')
        tDISC = dt.datetime.strptime(t_disc[i][:-4], '%Y-%m-%d %H:%M:%S')
        #slice [:-4] is to remove fractions of secs

        #if the discovery date is less than 3 months ago then can include
        if tDISC > threemonths:
            #if the time modified is less than a fortnight ago then can add it to new array
            if tMOD > fortnight:
                good_tars.append(database[i])

    sliceDB = np.array(good_tars,dtype=object)

    return sliceDB

################################################################################

def Visibility(ra, dec, lat, long, elv, ephm = 'de421.bsp'):
    """
    Function that calaculates the observable time, lunar separation and transit altitude
    of a list of targets given their right ascension and declination, the latitude
    longitude and elevation of the elevation, and the date of the start of the night.
    Arguments:
        - ra: list of right ascensions of the targets (in decimal degrees)
        - dec: list of declinations of the targets (in decimal degrees)
        - lat: the latitude of the location (in decimal degrees)
        - long: the eastwards longitude of the location (in decimal degrees)
        - elv: the elevation of the location (in metres)
        - ephm: the path to the ephemerides file for skyfield (default is 'de421.bsp')
    Outputs:
        - tObs: the time in hours that the target is above 35 altitude in dark time
        - tAlt: the altitude of the target when it transits the meridian (in decimal degrees)
        - lSep: the average separation between the moon and the target during the night (in decimal degrees)
    """

    #convert date to datetime object at midday
    today = dt.datetime.combine(dt.datetime.now(), dt.datetime.min.time()) + dt.timedelta(days=0.5)
    today =today.replace(tzinfo=utc)
    tomorrow = today + dt.timedelta(days=1) #next day at midday
    tomorrow = tomorrow.replace(tzinfo=utc)


    ### Set-up sky-field observing ##
    location = wgs84.latlon(lat * N, long * E, elevation_m = elv) #location of observatory
    ts = load.timescale() #loads in timescale
    eph = load(ephm)  #loads in ephemerides
    #sets up sun, earth (needed for calculating dark time and our location respectivly) and moon (for illumination, etc.)
    earth, sun, moon = eph['earth'], eph['sun'], eph['moon']
    Epos = earth + location #sets up observing position (i.e., the postion of the follow-up telescope)

    #makes time objects from today and tomorrow
    t0 = ts.from_datetime(today)
    t1 = ts.from_datetime(tomorrow)


    ### Find the dark time start and end ###
    f = almanac.dark_twilight_day(eph, location)
    times, events = almanac.find_discrete(t0, t1, f)

    sunset = times[0]
    darkstart = times[3]
    darkend = times[4]
    sunrise = times[7] #using the indcies to extract the different times of night

    #save the sunset/rise and twilight times as JSON the use in visplots and follow-up script
    solar_times = {
        "nightstart_date": today.strftime('%Y-%m-%d'),
        "sunset": sunset.utc_datetime().strftime('%H:%M:%S'),
        "darkstart": darkstart.utc_datetime().strftime('%H:%M:%S'),
        "darkend": darkend.utc_datetime().strftime('%H:%M:%S'),
        "sunrise": sunrise.utc_datetime().strftime('%H:%M:%S'),
        "nightend_date": sunrise.utc_datetime().strftime('%Y-%m-%d')
    }
    with open(f'../xOUTPUTS/solar_times.json', 'w') as fp:
            json.dump(solar_times, fp,indent=4)

    #find the UTC time at the middle of the night
    middark = ts.from_datetime(darkstart.utc_datetime()+((darkend.utc_datetime() - darkstart.utc_datetime())/2))
    darktimes = [darkstart,middark,darkend] #list of the time at the start, middle, and end of dark time

    ## calculate moon's alt, phase, and illumination ##
    midnight = t0 + dt.timedelta(hours=12)
    mastro = Epos.at(midnight).observe(moon)
    mapp = mastro.apparent()
    malt, maz, mdst = mapp.altaz()
    mphase = almanac.moon_phase(eph, t0)
    mill = almanac.fraction_illuminated(eph,"moon",midnight)
    malt, mphase = malt.degrees, mphase.degrees

    ## FUNCTIONS FOR CALCULATING OBSERVABLE TIME OF TARGET ##
    def transit_time(tar,t_start,t_end):
        """
        Function that finds the transit time (in UTC) of a target between two times (need to be 24hrs apart)
        and the altitude of this transit in degrees.
        Arguments:
            - tar: the target as a skyfield Star object.
            - t0: start time as a skyfield time object.
            - t1: end time (should be ~24hrs later) as a skyfield time object.
        Output:
            t_time: time that the object transits in UTC as a skyfield time object.
            t_alt: altitude in degrees that the object transits (float).
        """
        #function that calculates transit
        f = almanac.meridian_transits(eph, tar, location)
        t, y = almanac.find_discrete(t_start, t_end, f)
        #t is times of transit,
        #y is array with 0 for antimerdian transit and 1 for meridian transit (which we are intrested in)

        #so t_time is the element at the same index as 1 in y in the t array
        meridian_index = np.where(y==1)[0]
        t_time = t[meridian_index]

        #now need to find altitude of star at this time
        astro = Epos.at(t_time).observe(tar)
        app = astro.apparent()
        alt, az, distance = app.altaz()
        t_alt = alt.degrees

        return t_time[0], t_alt[0]

    def alt2HA(alt,lt,dec):
        '''
        Function that calculates the absolute value of the hour angle of a target for at a specified altitude, given the latitude of the location and the declination of the target.
        Arguments:
            - alt: the altitude you want to find the value of the HA at, in decimal degrees (float).
            - lt: the latitude of the location you are observing the target, in decimal degrees (float).
            - dec: the declination of the target, in decimal degrees (float)
        Output:
            - HA: the absolute value of the HA of the target at the specified altitude in decimal hours (float).
        '''

        #convert dec, lat and alt into radian
        altR = np.radians(alt)
        latR = np.radians(lt)
        decR = np.radians(dec)

        #find the hour angle of the
        cosHAnum = np.sin(altR) - (np.sin(latR)*np.sin(decR)) #numerator of cos(HA)
        cosHAden = np.cos(latR)*np.cos(decR) #denominator of cos(HA)
        cosHA = cosHAnum/cosHAden

        if cosHA > 1: #i.e., target never reaches 35 degs
            HA = None
        else:
            #find the hour angle using arccos
            HAdeg = np.degrees(np.arccos(cosHA)) #hour angle in degrees
            HA = HAdeg/15 #hour angle in hours

        return HA

    def obs_time(dt_start,dt_end,rise_t,set_t):
        """
        Function that calculates how long a target is visible given the times dark time starts and ends, and
        the times the target rises above and sets below a certain altitude. Note all times need to be in
        the same timezone, idealy UTC.
        Arguments:
            - dt_start: the time dark time starts as a skyfield time object.
            - dt_end: the time dark time ends as a skyfield time object.
            - rise_t: the time the target rises above the certain altitude.
            - set_t: the time the target sets below the certain altitude.
        Output:
            t_obs: the time the target is obserable in dark time, as a decimal hour (float).
        """

        #convert the times into datetime objects
        dt_start, dt_end = dt_start.utc_datetime(), dt_end.utc_datetime()
        rise_t, set_t = rise_t.utc_datetime(), set_t.utc_datetime()

        ## Now need to carry out the flow chart described above ##
        #first check is rise_t greater than dt_start
        if rise_t > dt_start:
            #if true then target rises after dark time starts
            #next check: is rise_t greater than dt_end
            if rise_t > dt_end:
                #if true target rises and sets after dark time, so cant observe
                t_obs = 0
            else:
                #if false the target rises in dark time
                #next check: is set_t greater than dt_end
                if set_t > dt_end:
                    #if true then target rises in dark time and then sets after
                    #so observable time is end of dark time minus rise time
                    t_obs = (dt_end - rise_t).seconds/3600 #have to divide by 3600 to get in hours
                else:
                    #if false then target rises and sets in dark time
                    #so observable time is just the time it is above the certain altitude
                    t_obs = (set_t - rise_t).seconds/3600
        else:
            #if false target rises before dark time
            #next check: is set_t greater than dt_start
            if set_t > dt_start:
                #if true then the target sets in dark time
                #next check: is set_t greater than dt_end
                if set_t > dt_end:
                    #if true then target rises before dark time and sets after it
                    #so observable time is the length of dark time
                    t_obs = (dt_end - dt_start).seconds/3600
                else:
                    #if false then target rises before dark time and sets in dark time
                    #so observable time is the set time minus the start of dark time
                    t_obs = (set_t - dt_start).seconds/3600
            else:
                #if false then target rises and sets before dark time starts, so cant observe
                t_obs = 0

        return t_obs

    ## CALCULATING OUTPUTS ##
    #empty lists to fill
    tObs, lSep = [], []

    #find altitude of each transient at sunset, start of dark time, end of darktime, and sunrise
    for k in range(ra.size):
        #RA and Dec of target in decimal degrees converted from string
        RA = float(ra[k])
        Dec = float(dec[k])

        #convert RA in decimal degrees to RA in hrs, mins, secs
        raH = RA/15 #RA decimal degrees to decimal hours
        ra_hours = int(raH) #hours of RA
        raM = (raH-ra_hours)*60 #decimal mintues of RA
        ra_mins = int(raM) #mintues of RA
        ra_secs = (raM-ra_mins)*60 #seconds of RA

        #convert DEC in decimal degrees to dec in degs, arcmins, arcsecs
        dec_degs = int(Dec) #degs of dec
        decM = (Dec-dec_degs)*60 #decimal arcmintues of dec
        dec_mins = int(decM) #arcmintues of dec
        dec_secs = (decM-dec_mins)*60 #arcseconds of dec

        #cretes star object from RA and Dec which represents the transient
        target =  Star(ra_hours=(ra_hours, ra_mins, ra_secs),dec_degrees=(dec_degs, dec_mins, dec_secs))

        #finding the UTC time the target transits the meridian
        trans_time, trans_alt = transit_time(target,t0,t1)

        # if the transit altitude is less than 35 then cant observe it #
        if trans_alt < 35:
            t_obs = 0
            asep = 0 #set lunar separation to be zero also
        else: #otherwise can continue

            # find the HA of target at 35 degs
            HA = alt2HA(35,lat,Dec)

            if HA == None: #target never rises above 35 degrees
                t_obs = 0
                asep = 0 #set lunar separation to be zero also
            else:
                ## Find the time target rises above 35 and then sets below 35 using the HA and transit time ##
                rise35 = trans_time - dt.timedelta(hours=HA)
                set35 = trans_time + dt.timedelta(hours=HA)
                above35 = ((set35.utc_datetime()-rise35.utc_datetime()).seconds)/3600 #time above 35 degs

                #find the observable time f the target
                t_obs = obs_time(darkstart,darkend,rise35,set35)

                if t_obs > 0: #if non zero time for observing then can calculate the lunar separation
                    a_seps = []
                    for DT in darktimes:
                        # angular separation doesn't depend on location on earth just time
                        e = earth.at(DT) #set earth as centre
                        m = e.observe(moon) #observe moon at time DT
                        T = e.observe(target) #observe target at time DT
                        a_sep = m.separation_from(T).degrees #find angular separation in degrees
                        a_seps.append(a_sep) #append to list

                    asep = np.mean(a_seps) #find mean angular separation during darktime

                else: #if no observable time then don't need to calculate the angular sep
                    asep = 0

        # add to the lists
        tObs.append(t_obs)
        lSep.append(asep)

    #return and convert to numpy arrays, along with lunar illumination
    return np.array(tObs), np.array(lSep), mill

################################################################################

def thresholds(DB,mill):
    """
    Removes targets from a database if they don't meet the thresholds of 3 different variables - observable time, lunar separation, and discovery magnitude.
	Arguments:
    	- DB: numpy object array of the list of targets with discovery magnitude, observable time, and lunar separation in column indices -4, -3, and -2 respectively.
    	- mill: the illumination percentage of the moon as a float
	Output:
    	- t_array: same database as ingested but with transients removed that don't meet the thresholds set.
    """
    #set observable time threshold (min exp time is ~15mins so cant observe
    #anything with obs time less than this)
    to_th = 0.25

    #set lunar separation the threshold (depends on lunar illumination)
    if mill < 0.25 : #dark sky
        m_th = 10
    elif (0.25 <= mill < 0.65): #grey sky
        m_th = 20
    else: #bright sky
        m_th = 40

    #set magnitude thresholds
    ml_th = 16 #lower threshold
    mu_th = 18.5 #upper threshold

    #remove all entries which dont meet the thresholds
    bad_idx = []
    for idx, entry in enumerate(DB):
        if entry[-3] <= to_th: #check the observable time of the target
            bad_idx.append(idx)
        elif entry[-2] < m_th: #check the lunar separation
            bad_idx.append(idx)
        elif (float(entry[-4]) <= ml_th) or (float(entry[-4]) >= mu_th): #check magnitudes
            bad_idx.append(idx)
    t_array = np.delete(DB,bad_idx,0) #deletes rows with no observable time

    return t_array

################################################################################

def pscore(database,weights,moon_per):
    """
	Filters a database of targets by removing all those with zero observable time and then calculates the rest's priority score, which depends on the target's ranking in observable time, transit altitude, lunar separation, brightness and time since discovery. The filtered database is then saved  as a numpy array with the priority scores as the final column.
	Arguments:
    	- database: numpy object array of the list of targets (ID first column and the observable time, and lunar separation in last 3 columns)
    	- weights: list of numbers to weight the contributions towards the priority score for the  observable time, transit altitude, and lunar separation
        - moon_per: percentage illumination of the moon used to set threshold for the lunar separation
	Outputs:
    	- t_targets: new numpy object array with the remaining targets and their priority scores in the final column
    """

    #remove all entries that don't fit within the thresholds
    t_array = thresholds(database,moon_per)

    #check the lenth of the thresholded array
    if t_array.size == 0:
        #if all targets were removed just return none and end function
        print("none")
        return t_array

    #save remaining IDs
    IDs = t_array.T[0]

    #convert strings into useable quantities
    disc = np.array([dt.datetime.strptime(date, "%Y-%m-%d %H:%M:%S.%f") for date in t_array.T[5]])
    #discovery dates as datetime objects

    mag = np.array(t_array.T[-4],dtype="float") #magnitudes as floats
    tobs = np.array(t_array.T[-3],dtype="float") #observable time as decimal hour
    lsep = np.array(t_array.T[-2],dtype="float") #lunar separation as decimal angle

    varbs = [tobs,lsep,mag,disc] #list containing the variables needed to calculate the pscores

    #makes a ordered list of each variable with their ID
    ivarbs = []
    for varb in varbs:
    	I = np.concatenate((np.resize(IDs,(IDs.size,1)),np.resize(varb,(varb.size,1))),axis=1)
    	#sort the array by ascending priority score (column index = -1)
    	I = I[I[:, -1].argsort()]
    	ivarbs.append(I)

    #calculate the pscores
    pscores = []
    sz = IDs.size
    for ID in IDs:
    	#looks for where the ID is in each of the sorted lists
    	#then calculates its score by doing (size of the array - index)
    	#this is so that high index IDs (i.e., higher values) get lower pscore which = higher priority
    	scores = []
    	scores.append(sz-np.where(ivarbs[0]==ID)[0][0])
    	scores.append(sz-np.where(ivarbs[1]==ID)[0][0])
    	scores.append(np.where(ivarbs[2]==ID)[0][0]) #no subtraction as we want the brightest objects (low mag)
    	scores.append(sz-np.where(ivarbs[3]==ID)[0][0])

    	#combine scores for different variables into one and apply weightings
    	score = sum(np.array(scores)*np.array(weights))
    	#weights applied by multiplication so some variables will contribute more to the final score

    	pscores.append(score)
    pscores = np.array(pscores,dtype=int)

    #normalise so scores are between 0 (high) and 5 (low)
    pscores=((pscores-np.min(pscores))/np.max(pscores-np.min(pscores)) * 5)

    #concatenate the IDs, variables and the pscores
    t_targets = np.concatenate((t_array,np.resize(pscores,(pscores.size,1))),axis=1)

    #order concatenated list by pscore in descending order
    t_targets = t_targets[t_targets[:, -1].argsort()]

    return t_targets

################################################################################

def flatten(l):
    "Flattens a list of lists, l"
    return [item for sublist in l for item in sublist]

################################################################################

def priority_list(database,date,Slow=True):
    """
    Slices the TNS database to extract only the targets discovered or modififed in a certain time frame in the past. It then calculates the observable time and lunar separation of these targets which along with their discovery magnitude and date are used to calculate their priority scores.
    Arguments:
        - database: numpy array of the data from TNS database which holds one entry per line
        - date: the date extracted from the top of the TNS database CSV file (string with format YY-MM-DD HH:MM:SS)
        - Slow: string dictating if calculating priority scores for PEPPER Fast or PEPPER Slow surveys (default is True - i.e., PEPPER Slow. Set to False for PEPPER Fast)
    Outputs:
        - targets: numpy array consisiting of the revelant targets and their priority scores
            - Rows are: ['objid','name_prefix','name','ra','declination','discoverydate','lastmodified',
 'discoverymag','observable_time','lunar_sep','priority_score']
    """

    if type(Slow) != bool:
        print("Priority score list not created - variable Slow was not set to a is boolean value.")
        exit()
    else:
        # slice the database accordingly #

        #extarct modification date and discovery date
        t_mod = database.T[-1]
        t_disc = database.T[12]

        #set different times since modification/discovery for PEPPER Fast and Slow
        if Slow == False:
            rdate = dt.datetime.strptime(date, '%Y-%m-%d %H:%M:%S') #slice from date TNS updated
            moddiff = rdate - dt.timedelta(days=2) #2 days ago
            discdiff = rdate - dt.timedelta(weeks=8) #2 months ago (aka 8 weeks)
        else: #i.e., slow
            rdate = dt.datetime.combine(dt.datetime.now(), dt.datetime.min.time()) #slice from today at midnight
            moddiff = rdate - dt.timedelta(weeks=2) #2 weeks ago
            discdiff = rdate - dt.timedelta(weeks=12) #3 months ago (aka 12 weeks)

        #slice
        good_tars = [] #empty list to save rows which pass the slicing to
        for i in range(len(t_mod)):
            #convert times to datetime objects
            tMOD = dt.datetime.strptime(t_mod[i], '%Y-%m-%d %H:%M:%S')
            tDISC = dt.datetime.strptime(t_disc[i], '%Y-%m-%d %H:%M:%S.%f')
            #if the modification date is less than 2days ago then can include
            if tMOD > moddiff:
                if tDISC > discdiff:
                    good_tars.append(database[i])
        DB = np.array(good_tars,dtype=object)


        # calculate priority scores from weightings #

        #variables of relevant info from sliced database
        IDs = DB.T[0] #TNS IDs
        prefix, name = DB.T[1], DB.T[2] #TNS name and prefix
        ra, dec = DB.T[3], DB.T[4] #RA and dec of targets
        t_disc, t_mod = DB.T[12],DB.T[-1] #time of discovery and modification of targets
        mags = DB.T[13] #disoovery magnitudes of targets
        it_names = DB.T[-3] #internal names of the targets

        #location of Liverpool Telescope
        lat = 28.6468866 #latitude in degs
        long = -17.7742491 #longitude in degs
        elv = 2326.0 #elevation in metres


        #calculate observable time and lunar separation of targets
        t_obs, l_sep, l_per = Visibility(ra, dec, lat, long, elv)

        #new databse with all relevant information
        newDB = np.array([IDs,prefix,name,ra,dec,t_disc,t_mod,mags,t_obs,l_sep,it_names]).T

        #different weightings for PEPPER Fast and Slow
        if Slow == False:
            wghts = [2,3,8,10] #priortise discovery date and magnitude; least obs_time
        else: #i.e., slow
            wghts = [10,7,8,3] #priortise observable time and magnitude

        #create database with pscores
        pDB = pscore(newDB,wghts,l_per)

        #check pDB to see if none value
        if pDB.size == 0:
            return pDB


        # urls to last column #
        int_names = pDB.T[-2] # locally saved internal names of targets


        #make the url by finding the ZTF name (if it exsists)
        urls = []
        for entry in int_names:

            #check the target has ZTF internal name at all
            if "ZTF" in entry:
                if "," not in entry: #i.e., only internal name is ZTF name
                    url = "https://fink-portal.org/"+entry

                else: #if it has multiple internal names
                    stidx = entry.index("ZTF")+3 #find index where ZTF names starts (after ZTF bit)

                    letter = entry[stidx] #first character of ZTF name
                    name = "ZTF"

                    #loop through name until get to comma which indicates it has ended
                    while (letter != ",") and (stidx < len(entry)-1):
                        name += letter
                        stidx +=1
                        letter = entry[stidx]

                        url = "https://fink-portal.org/"+name


            else:
                url = ""

            urls.append(url)

        urls = np.array(urls)


        # combine together and array #
        targets = np.delete(pDB.T,-2,0).T #remove internal name column
        targets = np.concatenate((targets,np.resize(urls,(urls.size,1))),axis=1) #add urls to databse

        return targets

######################### FUNCTIONS FOR FOLLOW-UP ##############################

def LTcoords(RA, DEC):
    """
    Converts RA and DEC in decimal degrees to a format that the ltrtml can understand, which is HH:MM:SS.SS and +/-DD:MM:SS.SS.
    Arguments:
        - RA: numpy array of RA values in decimal degrees
        - DEC: numpy array of declination values in decimal degrees
    Outputs:
        - ra: list of the original RA values in format HH:MM:SS.SS
        - dec: list of the original declination values in format +/-DD:MM:SS.SS
    """

    #convert all coords into a astropy coordinates object
    coords = SkyCoord(RA,DEC,unit="deg")

    #convert all coordinates into strings with units hmsdms
    cstr = coords.to_string("hmsdms")

    Ra, Dec = [], [] #empty lists to newly formatted RA and DEC to

    for i in range(RA.size):

        #split apart the string to isolate ra and dec
        splt = cstr[i].index(" ")
        ra = list(cstr[i][0:splt-1])
        dec = list(cstr[i][splt+1:-1])

        #had to convert ra and dec into lists so could change the elements
        #chnaging from HhMmSs DdMmSs to H:M:S D:M:S as this is format ltrtml needs
        ra[2]=":"
        ra[5]=":"
        dec[3]=":"
        dec[6]=":"
        ra = "".join(ra)
        dec = "".join(dec)

        #add to lists
        Ra.append(ra)
        Dec.append(dec)

    return Ra, Dec

################################################################################
