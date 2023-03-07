"""
Follow-up script that sends targets from the priorty score lists to be observed with the LT.

Author: George Hume
2023
"""

### IMPORTS ###

import ltrtml
import numpy as np
import datetime as dt
import json
import csv
import sys
sys.path.append('..')
from PAFUP_funcs import loadDB, LTcoords, csv2list


### Set up targets ###

# load in the PEPPER Fast priority list CSV file
info, headers, flist = loadDB("../xOUTPUTS/transient_list-F.csv")

# load in the black list
blist = csv2list("black_list.csv")

#remove any entries from the list which are in the black list
bad_idx = [] #empty list to add bad indices to
for idx, entry in enumerate(flist):
    if (entry[1]+entry[2]) in blist: #check if transient name is in black_list
        bad_idx.append(idx) #if it is append to bad indices list
flist = np.delete(flist,bad_idx,0) #deletes bad rows

if flist.shape[0] == 0: #check if there are targets in the list
    print("No sutible targets to request observations of.")
    with open("../xOUTPUTS/requests.json","w") as fp: # make json blank
        fp.write("")

else: #if there are targets then can submit observations to the LT

    ### Extract targets to request observations of ###
    #only extract targets with a priorty scores less than 0.5 and if min > 0.5 then the first target
    pmin = np.min(flist.T[-2].astype(float))
    if pmin < 0.5:
        bad_idx = [] #empty list to add bad indices to
        for idx, entry in enumerate(flist):
            if float(entry[-2]) > 0.5: #check the pscore the target
                bad_idx.append(idx) #if greater than 0.5 append to bad indices list
        top = np.delete(flist,bad_idx,0) #deletes bad rows
    else:
        top = np.array([flist[0]])

    #create list of dicts containing the transients names and RA and Dec in correct format for ltrtml
    names = top.T[1]+top.T[2]
    RA = top.T[3].astype(float)
    DEC = top.T[4].astype(float)

    ra, dec = LTcoords(RA,DEC)

    #make list of target dicts
    targets = []
    for i in range(len(ra)):
        targets.append( {"name":names[i],"RA":ra[i],"DEC":dec[i]} )


    ### Set up constraints ###
    # we want to request the observations as soon as we get the list so constraints in time will be from when released to start of morning twilight on the next day (over 24hrs away if release at 01:10 local time)

    # start date and time
    now = dt.datetime.utcnow()
    sdate = now.strftime("%Y-%m-%d")
    stime = now.strftime("%H:%M:%S")

    # end date and time
    # open file containing the times sunset/rise and twilight times for the night ahead
    with open('../xOUTPUTS/solar_times.json') as json_file:
        sdict = json.load(json_file)
    edate = sdict["nightend_date"]
    etime = sdict["darkend"] #end on morning twilight of the next day

    # make the constraints dict
    constraints = {
        'air_mass': '1.74',           # 1.7 airmass corresponds to 35deg alt
        'sky_bright': '1.0',          # We dont need a max as are targets shouldn't be near the moon
        'seeing': '1.2',              # Maximum allowable FWHM seeing in arcsec (ask J)
        'photometric': 'yes',         # Photometric conditions, ['yes', 'no'] (ask J - probs yes)
        'start_date': sdate,          # Start Date should be today
        'start_time': stime,          # Start Time should be when darktime starts
        'end_date': edate,            # End Date should be next day
        'end_time': etime,            # End Time when
    }


    ### Set up observations ###
    # we want to observe with MOPTOP in the R-band for 880s with slow rot speed for all targets

    # make a list of observation dicts for each target
    obs = []

    for target in targets:
        observation = {
            'instrument': 'Moptop',
            'target': target,
            'filters': {'R': {'exp_time': '880',    # Exposure time is 880 seconds
                              'rot_speed': 'slow'}}}  # Rotor speed is slow
        obs.append(observation)


    ### Set up the credentials ###
    # need to load the settings in from separate json - these are secrete so don't publish

    with open('LT_creds.json') as json_file:
        settings = json.load(json_file)


    ### Save requests we wanr to make to LT as a JSON file ###
    requests = {"observations": obs, "constraints": constraints}
    with open(f"../xOUTPUTS/requests.json","w") as fp: # write
        json.dump(requests, fp, indent=4)


    ### Set up connection to the LT ###
    try:
        obs_object = ltrtml.LTObs(settings)


        ### Send Observation request and save group ids ###
        uid, error = obs_object.submit_group(obs, constraints) #real

        #make dictonary with uids as keys and target info
        obs_dict = {}
        for i, target in enumerate(targets):
            obs_dict[str(uid[i])] = target

        #save any errors to the dict also
        obs_dict["errors"] = error

        #append dict to JSON of previous observations
        try: #try to open obs json if it exisits
            with open("../xOUTPUTS/observations.json","r") as fp: #read and write
                allobs = json.load(json_file)
        except: #if it doesn't exisit create a new one
            allobs = {}

        #add observations the dict (with date as key) and save as a JSON
        allobs[sdate] = obs_dict
        with open("../xOUTPUTS/observations.json","w") as fp: # write
            json.dump(allobs, fp, indent=4)

    except:
        print("could not access the LT - please check credentials")
