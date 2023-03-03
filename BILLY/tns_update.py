"""
Script that updates the local TNS database with the updates downloaded via curl from the TNS.

Author: George Hume
2023
"""

import json
import datetime as dt
import sys
sys.path.append('..')
from PAFUP_funcs import loadDB, dload, UPdate

#TNS bot info
with open('bot_info.json') as json_file:
    info = json.load(json_file)

if len(glob.glob("../xOUTPUTS/tns_public_objects.csv")) == 0:
	#if there is no local database present download it from the TNS
	dload("tns_public_objects.csv",info)

else:
	#database already exisits so load it in
	DBdate, headers, database = loadDB("../xOUTPUTS/tns_public_objects.csv")

	#datetime dates
	DB_date = dt.datetime.strptime(DBdate, '%Y-%m-%d %H:%M:%S') #date from tns database
	today = dt.datetime.combine(dt.datetime.now(), dt.datetime.min.time()) #today's data at turn of the day

	#time difference between the dates
	deltaT = (today - DB_date).days #time diff in days

	if deltaT == 0:
		print("TNS database is already up to date")

	elif deltaT == 1:
		#if only 1 day diff then download yesterday's updates and add to database
		ufile = f"tns_public_objects_{DB_date.strftime('%Y%m%d')}.csv"
		dload(ufile,info)
		UPdate(ufile,today,database)

	elif (deltaT>1) & (deltaT<=25):
		#if between 2 and 25days difference then download all previous updates and add then to database

		for i in range(deltaT):
	    	#go from last to most current update

			#date as string to find update file
			ufile = f"tns_public_objects_{DB_date.strftime('%Y%m%d')}.csv"
			next_day = DB_date+dt.timedelta(days=1)

	    	#do the update for that date
			UPdate(ufile,next_day,database)

	    	#load new database that was just saved so it can be overwritten again
			DBdate, headers, database = loadDB(DBname)
			DB_date = dt.datetime.strptime(DBdate, '%Y-%m-%d %H:%M:%S') #convert next date into datetime object

	else:
		#if over 25days difference then redownload the whole database from the TNS
		dload("tns_public_objects.csv",info)
