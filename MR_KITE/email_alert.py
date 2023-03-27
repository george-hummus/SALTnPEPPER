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
from datetime import datetime
import csv
import json
import sys
import glob
sys.path.append('..')
from SnP_funcs import loadDB, csv2list, array2html, visplots

#list of emails addresses to send the email to as CSV file
correspondents = csv2list("correspondents.csv")

plists =[] #blank list to add file paths of pscore lists to

#get dates from slow transient list (assume same as fast one)
slowlist = glob.glob("../xOUTPUTS/TransientList_S*")[0]
info, dummy, slowDB = loadDB(slowlist)

list_date = info[20:30] #date for which priority list was created
tns_date = info[-19:-9] #date of last update of TNS database

# check the size of the databases
fastlist = glob.glob("../xOUTPUTS/TransientList_F*.csv")[0]
dummy, headers, fastDB = loadDB(fastlist)

#add pscore paths to list
plists.append(slowlist)
plists.append(fastlist)

### Make the attachments and return paths ###
htmlpath = f"{fastlist[0:-4]}.html"
array2html(headers,fastDB,htmlpath) #html table of fast list
vispath = visplots(plists) #visiblity plots of highest priority targets in both lists


if fastDB.size == 0:
    #if no transients met the requirements replace table with notice
    with open(htmlpath, "w") as file:
        file.write("<p><font color=#FF0000><em> No transients met the requirements for PEPPER Fast tonight. </em></font></p><br>")

if slowDB.size == 0:
    #if no targets in slow list there will be none is faste either
    with open(htmlpath, "w") as file:
        file.write("<p><font color=#FF0000><em> No transients met the requirements for either PEPPER Fast or Slow tonight. </em></font></p><br>")

date = datetime.now().strftime('%Y-%m-%d') #date to put in the subject

with open('email.html', 'r') as file: #reads in text to put in body of the email
	words = file.read()

## notices to add to top of email if dates are not aligned ##
fault1, fault2 = False, False

if date != list_date: #notice at top of email if transient list is out of date
    fault1 = True
    notice1 = f"Please note: Transient lists have not been updated since {list_date}<br>"
else:
    notice1 = ""

if date != tns_date: #notice at top of email if tns database is out of date
    fault2 = True
    notice2 = f"Please note: TNS database used is out of date (last updated on {tns_date})<br>"
else:
    notice2 = ""

if (fault1 or fault2) == True:
    notice = f"<p><font color=#FF0000><em> {notice1} {notice2} </em></font></p><hr>" #formatting notices
    words = notice+words #adding notices to top of email
else:
    words = words

#add html PEPPER Fast table to end of email
with open(htmlpath,"r") as file:
	table = file.read()
fulltxt = words + "<br><hr> <b> PEPPER Fast List </b> <br><br>" + table

message = MIMEMultipart()
message['Subject'] = f"High Priority Transients for Night Starting {date}"
message['From'] = "SALT&PEPPER Pipeline"
message['To'] = "PEPPER Survey Collaborators"
html_part = MIMEText(fulltxt,'html')
message.attach(html_part)

#attach visiblity plots
with open(vispath, 'rb') as f:
    imagepart = MIMEImage(f.read())
message.attach(imagepart)

for plist in plists:
    with open(plist, "rb") as attachment:
    # Add the attachment to the message
        part = MIMEBase("application", "octet-stream")
        part.set_payload((attachment).read())
    encoders.encode_base64(part)
    part.add_header("Content-Disposition",f"attachment; filename= {os.path.basename(plist)}")
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
