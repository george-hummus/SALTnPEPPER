"""
Follow-up script that sends targets from the priorty score lists to be observed with the LT during the the night after the list is made.

Author: George Hume
2023
"""

### IMPORTS ###
import datetime as dt
import json
import sys
import glob
sys.path.append('..')
from SnP_funcs import csv2list, request

now = dt.datetime.now()
td_str = now.strftime('%Y-%m-%d')

#load in obs_requests.json - will exist as request A runs before this
with open("../xOUTPUTS/request_records.json","r") as fp:
    allreqs = json.load(fp)


#check if request B for today has already been made
if td_str in allreqs.keys(): #will have been if today's date is in records json
    print("Request B has already been made to LT today.")

else:
    ## load in the black list ##
    blist = csv2list("blacklist.csv")


    ## Set up start and end times of observations ##

    # open file containing the times sunset/rise and twilight times for the night ahead
    with open('../xOUTPUTS/solar_times.json') as json_file:
        sdict = json.load(json_file)

    #empty dict to add times to
    req_times = {}

    # start date and time (after evening twilight)
    req_times["start_date"] = sdict["nightstart_date"]
    req_times["start_time"] = sdict["darkstart"]

    # end date and time (when morning twilight starts)
    req_times["end_date"] = sdict["nightend_date"]
    req_times["end_time"] = sdict["darkend"]


    ## try to make requests using the most recent PEPPER fast list ##
    pep_fast = glob.glob("../xOUTPUTS/TransientList_F*.csv")[0]
    req_night = request(pep_fast,blist,req_times)

    #write out new request record
    reqB = {}
    reqB["Request-1"] = req_night
    allreqs[td_str] = reqB
    with open("../xOUTPUTS/request_records.json","w") as fp:
        json.dump(allreqs, fp, indent=4)
