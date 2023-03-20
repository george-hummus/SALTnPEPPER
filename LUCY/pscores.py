"""
Script to filter targets from the TNS database, calaculate how long they're visible for on the night
in question and uses this information along with their transit altitude, lunar separation, time
discovered, time modified, and magnitude to calculate a priorty score for observing them with the
Liverpool Telescope on La Palma, España.
Produces two priority lists taliored to the aims of the PEPPER Fast and Slow surveys.

Author: George Hume
2023
"""

### IMPORTS ###
import csv
import numpy as np
import datetime as dt
import sys
sys.path.append('..')
from SnP_funcs import loadDB, flatten, priority_list


# loads in the tns database as numpy array along with the date it was released as a string and a list of the headers
date, headers, database = loadDB("../xOUTPUTS/tns_public_objects.csv")
#create a new list of headers for the new database (as have removed columns and added new ones)
newHeaders = flatten([headers[0:5], [headers[12], headers[-1],headers[13], "observable_time", "lunar_sep", "galactic_latitude", "priority_score", "fink_url"]])

#line to go before headers to give context in CSV
Tday = dt.datetime.combine(dt.datetime.now(), dt.datetime.min.time()) #today's data at turn of the day
todaySTR = Tday.strftime('%Y-%m-%d %H:%M:%S')
topline = [f"List calculated for {todaySTR} using TNS database from {date}"]


# PEPPER FAST #
fastDB = priority_list(database,date,False)

#save out fast database CSV
filename = f"../xOUTPUTS/TransientList_F_{Tday.strftime('%Y%m%d')}.csv"
with open(filename, 'w') as file:
    csvwriter = csv.writer(file,delimiter=",") # create a csvwriter object
    csvwriter.writerow(topline)
    csvwriter.writerow(newHeaders) #add headers first row
    csvwriter.writerows(fastDB) # write the rest of the data


# PEPPER SLOW #
slowDB = priority_list(database,date)

#save out the slow database CSV
filename = f"../xOUTPUTS/TransientList_S_{Tday.strftime('%Y%m%d')}.csv"
with open(filename, 'w') as file:
    csvwriter = csv.writer(file,delimiter=",") # create a csvwriter object
    csvwriter.writerow(topline)
    csvwriter.writerow(newHeaders) #add headers first row
    csvwriter.writerows(slowDB) # write the rest of the data
