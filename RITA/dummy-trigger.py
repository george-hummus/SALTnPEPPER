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
from PAFUP_funcs import loadDB, csv2list

#list of emails addresses to send the email to as CSV file
correspondents = csv2list("../MR_KITE/correspondents.csv")

date = datetime.now().strftime('%Y-%m-%d') #date to put in the subject

message = MIMEMultipart()
message['Subject'] = f"Observation requests for {date}"
message['From'] = "PEPPER Automated Follow-Up Observations <noreply>"
message['To'] = "PEPPER Survey Collaborators"

#check if there would of been any requests made by loking at json
with open(glob.glob("../xOUTPUTS/requests*.json")[0], "r") as attachment:
    # Add the attachment to the message
    jfile = attachment.read()

if len(jfile) == 0:
    #no tranisents met threshold so none could be requested

    html_part = "<p><font color=#FF0000><em> No transients met the requirements for PEPPER Fast tonight, so no observations were requested. </em></font> <br><br> <em>PEPPER Automated Follow-Up Observations</em> </p>"

else:
    #requests were made so attach the json of the requests and send
    html_part = "<p> Below are the dictonaries that would have formed the observation requests. It detials the targets requested, the intrument set-up, and any constraints. <br><br> <em>PEPPER Automated Follow-Up Observations</em></p>"


message.attach(MIMEText(html_part,'html'))

#add json as plain text to email
message.attach(MIMEText(jfile))


### SEND EMAIL ###
try:
    #email credentials
    with open('../MR_KITE/email_creds.json') as json_file:
        creds = json.load(json_file)
    #set up email
    smtpObj = smtplib.SMTP_SSL('smtp.gmail.com', 465)
    smtpObj.login(creds["email"],creds["password"])

    smtpObj.sendmail(creds["email"], correspondents, message.as_string())
    print("email sent")

except:
    print("email failed")
