"""
Script to make the attachments for the email alert.These include:
- the visibility plots of the highest priorty transients on la Palma on the coming night
- the HTML table of the PEPPER Fast List

Author: George Hume
2023
"""

### IMPORTS ###
import datetime as dt
from skyfield.api import N, E, wgs84, load, utc, Star
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import json
import pandas as pd
import sys
sys.path.append('..')
from PAFUP_funcs import loadDB


### HTML TABLE ###

dummy, headers, fastDB = loadDB("../xOUTPUTS/transient_list-F.csv")

try: #may not be possible if databse is empty
    df = pd.DataFrame(fastDB, columns = headers)
    df['fink_url'] = '<a href=' + df['fink_url'] + '><div>' + df['fink_url'] +'</div></a>' #makes fink url clickable
    df['name'] = '<a href=' + "https://www.wis-tns.org/object/" + df['name'] + '><div>' + df['name'] +'</div></a>' #click tns name to take to website
    html = df.to_html(escape=False, justify = "left",index = False)
    with open("../xOUTPUTS/transient_list-F.html", "w") as file:
        file.write(html)
except:
    print("HTML table failed")


### VISIBILITY PLOTS ###

# DATES #
today = dt.datetime.combine(dt.datetime.now(), dt.datetime.min.time()) + dt.timedelta(days=0.5)
today =today.replace(tzinfo=utc)
tomorrow = today + dt.timedelta(days=1) #next day at midday
tomorrow = tomorrow.replace(tzinfo=utc)

#location of Liverpool Telescope
lat = 28.6468866 #latitude in degs
long = -17.7742491 #longitude in degs
elv = 2326.0 #elevation in metres

### Set-up sky-field observing ##
location = wgs84.latlon(lat * N, long * E, elevation_m = elv) #location of observatory
ts = load.timescale() #loads in timescale
eph = load('de421.bsp')  #loads in ephemerides
#sets up sun, earth (needed for calculating dark time and our location respectivly) and moon (for illumination, etc.)
earth, sun, moon = eph['earth'], eph['sun'], eph['moon']
Epos = earth + location #sets up observing position (i.e., the postion of the follow-up telescope)

#makes time objects from today and tomorrow
t0 = ts.from_datetime(today)
t1 = ts.from_datetime(tomorrow)

### Load in the sunrise/set and twilight times ###
with open('../xOUTPUTS/solar_times.json') as json_file:
    sdict = json.load(json_file)
#save them as time objects in skyfield
sunset = ts.utc(
int(sdict["nightstart_date"][0:4]), int(sdict["nightstart_date"][5:7]), int(sdict["nightstart_date"][8:]),
int(sdict["sunset"][0:2]), int(sdict["sunset"][3:5]), int(sdict["sunset"][6:])
)
darkstart = ts.utc(
int(sdict["nightstart_date"][0:4]), int(sdict["nightstart_date"][5:7]), int(sdict["nightstart_date"][8:]),
int(sdict["darkstart"][0:2]), int(sdict["darkstart"][3:5]), int(sdict["darkstart"][6:])
)
darkend = ts.utc(
int(sdict["nightend_date"][0:4]), int(sdict["nightend_date"][5:7]), int(sdict["nightend_date"][8:]),
int(sdict["darkend"][0:2]), int(sdict["darkend"][3:5]), int(sdict["darkend"][6:])
)
sunrise = ts.utc(
int(sdict["nightend_date"][0:4]), int(sdict["nightend_date"][5:7]), int(sdict["nightend_date"][8:]),
int(sdict["sunrise"][0:2]), int(sdict["sunrise"][3:5]), int(sdict["sunrise"][6:])
)

#set up figure
fig, ax = plt.subplots(1,2,figsize=(20,10))

lists = ["transient_list-F.csv", "transient_list-S.csv"]

for j, fname in enumerate(lists):
    ## format the plots ##
    ax[j].plot((sunset.utc_datetime(),sunrise.utc_datetime()),(0,0),color="grey",alpha=0.5,zorder=0) #horizon
    ax[j].plot((sunset.utc_datetime(),sunrise.utc_datetime()),(35,35),color="grey",alpha=0.5,zorder=0) #lower alt limit

    ax[j].vlines(darkstart.utc_datetime(), 0,90,color="grey",alpha=0.5,zorder=0)
    ax[j].vlines(darkend.utc_datetime(), 0,90,color="grey",alpha=0.5,zorder=0)
    ax[j].vlines(today + dt.timedelta(days=0.5), 0,90,color="grey",alpha=0.5,zorder=0)

    #annotations
    ax[j].annotate("End of Twilight", (darkstart.utc_datetime(),88),ha='center')
    ax[j].annotate("Start of Twilight", (darkend.utc_datetime(),88),ha='center')
    ax[j].annotate("Midnight", (today + dt.timedelta(days=0.5),88),ha='center')
    ax[j].annotate("Horizon", (sunset.utc_datetime(),1),(10,0),textcoords="offset pixels")
    ax[j].annotate("Airmass Lower Limit", (sunset.utc_datetime(),36),(10,0),textcoords="offset pixels")

    #backgrounds
    ax[j].axhspan(35, 0, facecolor='grey', alpha=0.2)
    ax[j].axhspan(0, -90, facecolor='grey', alpha=0.4)

    #formatting the plot
    xfmt = mdates.DateFormatter(' %H:%M')
    ax[j].xaxis.set_major_formatter(xfmt)
    ax[j].set_xlabel("UTC Time")
    ax[j].set_ylabel("Altitude (degrees)")
    ax[j].set_xlim((sunset.utc_datetime(),sunrise.utc_datetime()))
    ax[j].set_ylim(0,90)
    ax[j].set_title(f"Visibility of highest priority transients from {fname} during dark time on La Palma ({today.strftime('%Y-%m-%d')})")

    ax[j].grid(linestyle = ':')


    #ingest the Pscore File
    dummy, dummy, plist = loadDB(f"../xOUTPUTS/{fname}")

    nrows = plist.shape[0] #number of rows in original list

    # check the number of rows in the pscore list
    if nrows > 5: #if over 5 pick the top 5
        top = plist[0:5]
    elif nrows != 0: #if less than 5 and greater than 0 then pick all
        top = plist[0:]
    else: #if no rows (blank list) then skip
        continue

    names = top.T[1]+top.T[2] #TNS name of each target
    RA = top.T[3].astype(float)/15 #convert to decimal hours
    dec = top.T[4].astype(float) #declination

    trows = top.shape[0] #number of rows in list of top entries

    talts = []
    for n in range(trows):
        tar =  Star(ra_hours=RA[n],dec_degrees=dec[n])

        Time = sunset

        altitudes = []
        times = []

        while Time.utc_datetime() < sunrise.utc_datetime():
            astro = Epos.at(Time).observe(tar)
            app = astro.apparent()
            #observers star at time from position

            alt, az, distance = app.altaz()

            altitudes.append(alt.degrees)
            times.append(Time.utc_datetime())

            Time += dt.timedelta(hours=0.1)

        talts.append(altitudes)

    for i in range(trows):
        ax[j].plot(times,talts[i],"--",label=names[i])

    ax[j].legend(loc='center left', bbox_to_anchor=(1, 0.5))


#save
plt.tight_layout()
plt.savefig("../xOUTPUTS/top_visplots.jpg",dpi=600)
plt.close()
