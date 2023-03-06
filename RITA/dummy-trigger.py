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
sys.path.append('..')
from PAFUP_funcs import loadDB

#list of emails addresses to send the email to as CSV file
file=open("../MR_KITE/correspondents.csv")
correspondents = []
csvreader = csv.reader(file)
for row in csvreader:
    	correspondents.append(row[0]) #save all rows into a list
file.close()

date = datetime.now().strftime('%Y-%m-%d') #date to put in the subject

message = MIMEMultipart()
message['Subject'] = f"Observation requests for {date}"
message['From'] = "PEPPER Automated Follow-Up Observations <noreply>"
message['To'] = "PEPPER Survey Collaborators"

#check if there would of been any requests made
dummy, dummy2, fastDB = loadDB("../xOUTPUTS/transient_list-F.csv")
if fastDB.size == 0:
    #no tranisents met threshold so none could be requested

    html_part = "<p><font color=#FF0000><em> No transients met the requirements for PEPPER Fast tonight, so no observations were requested. </em></font> <br><br> <em>PEPPER Automated Follow-Up Observations</em></p>"
    message.attach(MIMEText(html_part,'html'))

else:
    #requests were made so attach the json of the requests and send
    html_part = "<p> Here are the transients that would have been requested for observations with MOPTOP. <br><br> <em>PEPPER Automated Follow-Up Observations</em></p>"
    message.attach(MIMEText(html_part,'html'))


    with open("../xOUTPUTS/requests.json", "rb") as attachment:
    # Add the attachment to the message
        part = MIMEBase("application", "octet-stream")
        part.set_payload((attachment).read())
    encoders.encode_base64(part)
    part.add_header("Content-Disposition",f'attachment; filename= {os.path.basename("requests.json")}')
    message.attach(part)


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
