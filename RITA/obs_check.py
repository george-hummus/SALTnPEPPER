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
import glob

#DATES
today = dt.datetime.utcnow()
yesterday = today - dt.timedelta(days=1)

#load in observation file
with open(f"../xOUTPUTS/observations.json","r") as fp:
    allobs = json.load(fp)

try: #try to extract the obs from today
    td_entry = allobs[today.strftime('%Y-%m-%d')]
except:
    td_entry = "Connection to LT failed."
    #date not present so treat as non-connection to LT

try: #try to extract the obs from yesterday
    yd_entries = allobs[yesterday.strftime('%Y-%m-%d')]
except:
    yd_entries = "Connection to LT failed."
    #date not present so treat as non-connection to LT

### Add requests files to list if connection was made ###
requests = []
if td_entry != "Connection to LT failed.":
    #if today's didn't fail add requests file to list
    requests.append(f"../xOUTPUTS/requests_{today.strftime('%Y%m%d')}.json")
if yd_entries != "Connection to LT failed.":
    #if yesterday's didn't fail add requests file to list
    requests.append(f"../xOUTPUTS/requests_{yesterday.strftime('%Y%m%d')}.json")


if len(requests) == 0: #i.e., no connection was made on either date
    with open("fail.txt") as fail:
        fail.write("")

else: #i.e., connection was made at least on one date

    ### Load in the requests from today and yesterday ###
    rtargets = [] #empty list to fill with the requested targets
    for file in requests:
        try: #try to open the json
            with open(file) as jfile:
                rqst = json.load(jfile)
            for entry in rqst['observations']:
                rtargets.append(entry['target']['name'])
        except: #if can't then it is empty so no requests made
            continue

    if len(rtargets) == 0:
        #if no requests were made there is no need to check
        observations = [["","","","",""]] #write nothing to the csv
        slog = ["No requests made"]
        with open(f"logheaders.txt") as L: #just load in the log headers
            Log = L.readlines()

    else:
        released = False
        while released == False:
            ### Try to download LT log for the previous night using curl ###
            cmd = f'curl https://telescope.livjm.ac.uk/data/archive/webfiles/Logs/lt//{yesterday.strftime("%Y%m%d")}.log > ../xOUTPUTS/LT{yesterday.strftime("%Y%m%d")}.log'
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

        observations = [] #blank list which will contain the contents for the csv
        slog = [] #empty list to contain all log rows that contain our targets

        #extract all rows for each target if it is in the log
        for target in rtargets:
            trows = [] #empty list to store all the rows corresponding to this target
            for row in Log:
                if target in row: #if target names is in the column add row to list
                    trows.append(row.split()) #split row string into a list
                    slog.append(row)
            trows = np.array(trows)

            if trows.size == 0:
                #if target was not observed
                observed = False
                pc = 0
                fnames = []

            else:
                observed = True

                #calculate percentage of observations completed
                total_exp = sum(trows.T[10].astype(float))
                pc = total_exp/r_texp

                #extract the file names into a list
                fnames = list(trows.T[13])

            observations.append([target[0:2],target[2:],observed,pc,fnames])

    #save observations array to a CSV with data at top and headers
    TopRow = f"Requested observations and statuses for the night starting {yesterday.strftime('%Y-%m-%d')}"
    Headers = ["name_prefix","name","observed","fraction_complete","filenames"]
    observations = np.array(observations,dtype=object)
    with open(f"../xOUTPUTS/observations_{yesterday.strftime('%Y%m%d')}.csv","w") as obs:
        csvwriter = csv.writer(obs,delimiter=",")
        csvwriter.writerow([TopRow])
        csvwriter.writerow(Headers)
        csvwriter.writerows(observations)

    #save log spliced to only contain our targets
    #get headers from the log file
    lines = Log[0:4]
    with open(f"../xOUTPUTS/LT{yesterday.strftime('%Y%m%d')}_spliced.log","w") as f:
        for l in lines: #write headers to top
            f.write(l)
        for r in slog: #write spliced entries afterwards
            f.write(r+"\n")
