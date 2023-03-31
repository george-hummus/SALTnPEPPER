"""
Script to send email from gmail account with HTML message and attachments. Based on code from: https://mailtrap.io/blog/python-send-email-gmail/

Author: George Hume
2023
"""

import smtplib
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
import os
import numpy as np
import datetime as dt
import csv
import json
import sys
import glob
sys.path.append('..')
from SnP_funcs import loadDB, csv2list, array2html

#list of emails addresses to send the email to as CSV file
correspondents = csv2list("correspondents.csv")

#yesterday's date
yesterday = (dt.datetime.utcnow() - dt.timedelta(days=1))
date = yesterday.strftime('%Y-%m-%d')

#if connection did not fail on both or either of the requests then...
if len(glob.glob("../RITA/fail.txt")) == 0:
    #load in CSV containing all PEPPER observations
    obspath = "../xOUTPUTS/observations.csv"
    dummy, headers, DB = loadDB(obspath)

    #check if yesterday's date is in database
    if date in DB.T[0]:
        #extract rows from the database corresponding just to yesterday's date
        DBmsk = DB.T[0] == date #make mask to removes dates other than one we want
        DByd = DB[DBmsk] #apply mask
        DByd = np.delete(DByd, 0, 1) #delete date column

        htmlpath = f"../xOUTPUTS/observations_{yesterday.strftime('%Y%m%d')}.html"
        array2html(headers[1:],DByd,htmlpath)
        #make the html table to attach to email if there were request

        #add html observations table to end of email
        with open(htmlpath,"r") as file:
            table = file.read()

    else:
        #message indicating no requests were made
        table = f"<p><font color=#FF0000><em> No transients were requested for observation with MOPTOP on the night starting {date} as none met the requirements of PEPPER Fast. Therefore, attachments were not created. </em></font> </p>"

else:
    #if connection failed on both nights then show the requests that were made for the past night

    #load the request record
    with open("../xOUTPUTS/request_records.json","r") as r:
        allreqs = json.load(r)

    if date in allreqs.keys():
        #open requests for past night and convert the dict to a string to
        #add to email (with html line breaks)
        reqs = "<pre>"+json.dumps(allreqs[date],indent=4).replace("\n","<br>")+"</pre>"
    else:
        #if can't open then no requests were made
        reqs = "No requests made on the previous night."


    table = f"<p><font color=#FF0000><em> No transients were requested for observation with MOPTOP on the night starting {date} as the connection to the LT failed. Therefore, the attachments were not created. </em></font> <br><br> Here is what should have been requested:<br> {reqs} </p>"



#body of email
#reads in text to put in body of the email
with open('obs_email.html', 'r') as file:
    words = file.read()
fulltxt = words + "<br><hr> <b> Observations Requests and Statuses </b> <br><br>" + table

### SET UP EMAIL ###
message = MIMEMultipart()
message['Subject'] = f"Observation Statuses of Requests for Night Starting {date}"
message['From'] = "SALT&PEPPER Pipeline"
message['To'] = "PEPPER Survey Collaborators"
html_part = MIMEText(fulltxt,'html')
message.attach(html_part)


### attach csv file and spliced log (if latter was made) ###
slog_glob = glob.glob("../xOUTPUTS/*spliced.log")

if len(slog_glob) != 0:
    slog = slog_glob[0] #path to the spliced log
    attachments = [obspath, slog]
    for file in attachments:
        with open(file, "rb") as attachment:
        # Add the attachment to the message
            part = MIMEBase("application", "octet-stream")
            part.set_payload((attachment).read())
        encoders.encode_base64(part)
        part.add_header("Content-Disposition",f"attachment; filename= {os.path.basename(file)}")
        message.attach(part)
else:
    print("Spliced log not made.")


### SEND EMAIL ###
try:
    #email credentials
    with open('email_creds.json') as json_file:
        creds = json.load(json_file)
    #set up email
    smtpObj = smtplib.SMTP_SSL('smtp.gmail.com', 465)
    smtpObj.login(creds["email"],creds["password"])

    smtpObj.sendmail(creds["email"], correspondents, message.as_string())
    print("email sent")

except Exception as e:
    print(e)
    print("email failed")
