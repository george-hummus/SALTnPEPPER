"""
Script which automatically downloads new observational data from the LT archive that the SALT&PEPPER pipeline requested.

Author: George Hume
2023
"""

## IMPORTS ##
import numpy as np
import json
import subprocess
import glob
import sys
sys.path.append('..')
from SnP_funcs import loadDB, csv2list


#load in creds for the LT archive
with open("LTarchive_creds.json") as jfile:
    creds = json.load(jfile)

#load in data for all observations
info, headers, obs = loadDB("../xOUTPUTS/observations.csv")


#load in dates and proposal IDs of data that has already been downloaded
pst_dwnlds = csv2list("past_downloads.csv")


#remove all entries from observations that have already been downloaded
if len(pst_dwnlds) != 0: #if there have been previous downloads
    bad_idx = []
    for idx, entry in enumerate(obs):
        #check date and propID has already been listed as downloaded
        if f"{entry[0]} | {entry[1]}" in pst_dwnlds:
            #has been downloaded
            bad_idx.append(idx)
        elif entry[5] == "False":
            #hasn't been downloaded as wasn't observed
            bad_idx.append(idx) #remove entries which haven't been observed
        else:
            #hasn't been downloaded but was observed
            pst_dwnlds.append(f"{entry[0]} | {entry[1]}")
            #add date and propID to pst_dwnlds so multiple downloads don't occur
    new_obs = np.delete(obs,bad_idx,0)
else:  #if there haven't been previous downloads
    new_obs = obs

#open the past downloads file to append new dates and propIDs to
pd_file = open("past_downloads.csv","a")

#download new data
for entry in new_obs:
    if entry.size == 0:
        continue #if nothing in the entry then skip 

    #convert from YYYY-MM-DD to YYYMMDD fmt
    date = "".join(entry[0].split("-"))

    #extract the proposal ID and use it to get the right password
    propID = entry[1] #also the username for LT archive
    psswrd = creds[propID] #pwd for lt archive for this proposal

    #constructing the wget command to download data
    url = f"https://telescope.ljmu.ac.uk/DataProd/RecentData/{propID}/{date}/"
    sign_in = f'--user={propID} --password={psswrd}'
    cmd = f'wget -r -np -k -A *.tgz {sign_in} {url} -nd -e -nv robots=off'
    #this will download all .tgz files created for this night and proposal ID

    #download
    subprocess.call(cmd,shell=True)

    #check that download was a sucess
    if len(glob.glob("*.tgz")) > 0:

        #make dir in data dir for this data
        subprocess.call(f"mkdir ../yDATA/{date}_{propID}",shell=True)

        #move .tgz files to its dir in the data directory
        subprocess.call(f"mv *.tgz ../yDATA/{date}_{propID}",shell=True)

        #add date and propID to the past downloads file
        pd_file.write(f"{entry[0]} | {propID}\n")

    else:
        print(f"Data download of {propID} for night {entry[0]} failed.")

#close the past downloads file
pd_file.close()
