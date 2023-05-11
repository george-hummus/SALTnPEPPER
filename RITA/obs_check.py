"""
Follow-up script to check that the requested targets were observed by the Liverpool Telescope.

Author: George Hume
2023
"""

### IMPORTS ###
import numpy as np
import datetime as dt
import json
import subprocess
import time
import csv
import sys
sys.path.append('..')
from SnP_funcs import loadDB

#DATES
today = dt.datetime.utcnow()
yesterday = today - dt.timedelta(days=1)

#check if the checks have already been performed
obspath = "../xOUTPUTS/observations.csv"
dummy, dummy2, DB = loadDB(obspath)

if yesterday.strftime('%Y-%m-%d') in DB:
    print("Last night's observation requests have already been checked.")

else:
    #load in observation file
    with open("../xOUTPUTS/request_records.json","r") as fp:
        allobs = json.load(fp)

    try: #try to extract request 1 status from last night
        req1 = allobs[yesterday.strftime('%Y-%m-%d')]["Request-1"]
        req1S = req1["status"]
    except:
        req1S = "Connection to LT failed."
        #if request not present so treat as non-connection to LT

    try: #try to extract request 2 status from last night
        req2 = allobs[yesterday.strftime('%Y-%m-%d')]["Request-2"]
        req2S = req2["status"]
    except:
        req2S = "Connection to LT failed."
        #date not present so treat as non-connection to LT

    ### Add requests info to list if connection was made ###
    requests = []
    if req1S != "Connection to LT failed.":
        #if request 1 didn't fail add requests file to list
        requests.append(req1)
    if req2S != "Connection to LT failed.":
        #if request 2 didn't fail add requests file to list
        requests.append(req2)


    if len(requests) == 0: #i.e., no connection was made on either date
        with open("fail.txt","w") as fail:
            fail.write("We're more popular than Jesus now; I don't know which will go first – rock 'n' roll or Christianity. ")

    else: #i.e., connection was made at least on one date

        ## load in targets names and its uid from requests of today and yesterday ###
        rtargets = [] #empty list to fill with tuples of requested target and their UID
        for rqst in requests:
            if rqst["status"] == "No requests made.":
                #if no requests made for date then continue
                continue
            else:
                uid = rqst["uid"]
                for entry in rqst['targets']:
                    rtargets.append((entry['name'],uid))

        if len(rtargets) != 0:
            #if there were targets requested
            released = False
            while released == False:
                ### Try to download LT log for the previous night using curl ###
                cmd = f'curl -s https://telescope.livjm.ac.uk/data/archive/webfiles/Logs/lt//{yesterday.strftime("%Y%m%d")}.log > ../xOUTPUTS/LT{yesterday.strftime("%Y%m%d")}.log'
                subprocess.call(cmd,shell=True)

                #open log and read all lines to a list
                with open(f"../xOUTPUTS/LT{yesterday.strftime('%Y%m%d')}.log") as L:
                    Log = L.readlines()

                #if the log has not been released yet wait 30mins and try again
                if "<p>The requested URL was not found on this server.</p>\n" in Log:
                    released = False
                    time.sleep(1800)
                else:
                    released = True


            #exp-time requested
            with open('obs_prams.json') as json_file:
                obs_prams = json.load(json_file)
            r_texp = float(obs_prams['exp_time'])

            #load in proposal name from LT credentials
            with open('LT_creds.json') as json_file:
                propID = json.load(json_file)["proposal"]

            observations = [] #blank list which will contain the contents for the csv
            slog = [] #empty list to contain all log rows that contain our targets

            #extract all rows for each target if it is in the log
            for target in rtargets:
                trows = [] #empty list to store all the rows corresponding to this target
                for row in Log:
                    if (target[0] in row) and (target[1] in row):
                        #if target name and UID is this row then its our obs so add to list
                        trows.append(row.split()) #split row string into a list
                        slog.append(row)
                trows = np.array(trows)

                if trows.size == 0:
                    #if target was not observed
                    observed = False
                    pc = 0
                    fname_root = "n/a"
                    propid = propID
                    groupid = target[1]

                else:
                    observed = True

                    #calculate percentage of observations completed
                    total_exp = sum(trows.T[10].astype(float))
                    pc = total_exp/r_texp

                    if pc >= 1:
                        #if the target has been observed for full time requested
                        with open("blacklist.csv","a") as blist:
                            #append name to black list to avoid repeats
                            blist.write(f"{target[0]}\n")

                    #extract proposal and group ids from the first log entry for the target
                    propid = trows.T[2][0]
                    groupid = trows.T[14][0] #group id should be same as the uid

                    #extract the root file name from the first log entry for the target
                    split_fname = trows.T[13][0].split("_") #split using underscores
                    fname_root = f"{split_fname[1]}_{split_fname[2]}_{split_fname[3]}"

                #add target's info to list
                observations.append([yesterday.strftime('%Y-%m-%d'), propid, groupid, target[0][0:2],target[0][2:],observed,fname_root])

            #save observations array to the CSV containing info on all data at top and headers
            with open(f"../xOUTPUTS/observations.csv",'a') as obs:
                csvwriter = csv.writer(obs,delimiter=",")
                csvwriter.writerows(observations)

            #save log spliced to only contain our targets
            #get headers from the log file
            lines = Log[0:4]
            with open(f"../xOUTPUTS/LT{yesterday.strftime('%Y%m%d')}_spliced.log","w") as f:
                for l in lines: #write headers to top
                    f.write(l)
                for r in slog: #write spliced entries afterwards
                    f.write(r+"\n")
