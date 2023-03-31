"""
Follow-up script that sends targets from the priorty score lists to be observed with the LT during the the night the list is made.

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
yesterday = now - dt.timedelta(days=1)
yd_str = yesterday.strftime('%Y-%m-%d')

#load in obs_requests.json
if len(glob.glob("../xOUTPUTS/request_records.json")) != 0:
    with open("../xOUTPUTS/request_records.json","r") as fp:
        allreqs = json.load(fp)
else: #if it doesn't exist create a new one
    allreqs = {}


#check if request A for today has already been made
if yd_str in allreqs.keys(): #check if the date exists in record
    if "Request-2" in allreqs[yd_str].keys(): #check if previous request made
        request_made = True
    else:
        request_made = False
else:
    request_made = False

if request_made:
    print("Request A has already been made to LT today.")

else:
    ## Set up black list ##

    # load in the black list
    blist = csv2list("blacklist.csv")

    # add observations that have already been requested for this night to the black list
    if (yd_str not in allreqs.keys()):
        print("No request made yet for this night as date is not listed.")

    elif allreqs[yd_str]["Request-1"]["status"] == "Connection to LT failed.":
        print("No request made yet for this night as LT connection failed")

    elif allreqs[yd_str]["Request-1"]["status"] == "No requests made.":
        print("No request made yet for this night as previous priority list was empty")

    else:
        #load in previous targets requested for this night
        prev_tars = allreqs[yd_str]["Request-1"]["targets"]
        for tar in prev_tars: #append each name to black list
            blist.append(tar["name"])


    ## Set up start and end times of observations ##

    # open file containing the times sunset/rise and twilight times for the night ahead
    with open('../xOUTPUTS/solar_times.json') as json_file:
        sdict = json.load(json_file)

    #empty dict to add times to
    req_times = {}

    # start date and time (ASAP)
    req_times["start_date"] = now.strftime("%Y-%m-%d")
    req_times["start_time"] = now.strftime("%H:%M:%S")

    # end date and time at sunset before next night starts
    req_times["end_date"] = sdict["nightstart_date"]
    req_times["end_time"] = sdict["sunset"]


    ## try to make requests using the most recent PEPPER fast list ##
    pep_fast = glob.glob("../xOUTPUTS/TransientList_F*.csv")[0]
    req_morn = request(pep_fast,blist,req_times)

    #write out new request record
    if yd_str in allreqs.keys(): #check if the date exists in record
        allreqs[yd_str]["Request-2"] = req_morn
    else: #if doesn't have to make new date entry
        reqA = {}
        reqA["Request-2"] = req_morn
        allreqs[yd_str] = reqA
    with open("../xOUTPUTS/request_records.json","w") as fp:
        json.dump(allreqs, fp, indent=4)
