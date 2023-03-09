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
import datetime as dt
import csv
import json
import sys
import glob
sys.path.append('..')
from PAFUP_funcs import loadDB, csv2list

#list of emails addresses to send the email to as CSV file
correspondents = csv2list("correspondents.csv")

#if connection did not fail
if len(glob.glob("../RITA/fail.txt")) == 0:
    #get date and entries from the csv observations file
    obspath = glob.glob("../xOUTPUTS/observations_*.csv")[0]
    info, dummy, DB = loadDB(obspath)
    date = info[-10:] #date for night of observations
    try:
        htmlpath = csv2html(obspath) #make the html table to attach to email if there were request

        #add html observations table to end of email
        with open(htmlpath,"r") as file:
            table = file.read()

    except:
        #message indicating no requests were made
        table = f"<p><font color=#FF0000><em> No transients were requested for observation with MOPTOP on the night starting {date} as none met the requirements of PEPPER Fast. </em></font> </p>"

else:
    date = dt.datetime.utcnow().strftime('%Y-%m-%d')
    table = f"<p><font color=#FF0000><em> No transients were requested for observation with MOPTOP on the night starting {date} as the connection to the LT failed. Therefore, attachments were not created. </em></font> </p>"

#body of email
#reads in text to put in body of the email
with open('obs_email.html', 'r') as file:
    words = file.read()
fulltxt = words + "<br><hr> <b> Observations Requests and Statuses </b> <br><br>" + table

### SET UP EMAIL ###
message = MIMEMultipart()
message['Subject'] = f"Observation Statuses of Transients for Night Starting {date}"
message['From'] = "PEPPER Automated Follow-Up Observations <noreply>"
message['To'] = "PEPPER Survey Collaborators"
html_part = MIMEText(fulltxt,'html')
message.attach(html_part)

#if connection did not fail then file would be created
if len(glob.glob("../RITA/fail.txt")) == 0:
    ### attach csv file and spliced log ###
    slog = glob.glob("../xOUTPUTS/*spliced.log")[0] #path to the spliced log
    attachments = [obspath, slog]
    for file in attachments:
        with open(file, "rb") as attachment:
        # Add the attachment to the message
            part = MIMEBase("application", "octet-stream")
            part.set_payload((attachment).read())
        encoders.encode_base64(part)
        part.add_header("Content-Disposition",f"attachment; filename= {os.path.basename(file)}")
        message.attach(part)


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

except:
    print("email failed")
