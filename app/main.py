from __future__ import print_function
import groupy
import numpy as np
import time
import pandas as pd
from dateutil.relativedelta import relativedelta
from datetime import date
from groupy.client import Client
import requests
from flask import Flask, request
import json
from googleapiclient.discovery import build
from httplib2 import Http
import gspread
from oauth2client.service_account import ServiceAccountCredentials

with open('config.json') as f:
    config = json.load(f)

# Initialize
token = config.get('groupme').get('token')
url = 'https://api.groupme.com/v3/groups/?token='+token
groupme_client = Client.from_token(token)

# get groups
groups = groupme_client.groups.list()

# Get council group
g = groupme_client.groups.get(config.get('groupme').get('group_id'))
botid = config.get('groupme').get('bot_id')

# Retrieve message history
msgs = [m for m in g.messages.list_all()]
msgs_text = [(x.name, x.text, x.created_at) for x in msgs if x.text is not None]
df_msgs = pd.DataFrame(msgs_text, columns= ['user', 'txt', 'timestamp'])
df_msgs['send_date'] = pd.to_datetime(df_msgs.timestamp).apply(lambda x: x.date)

shared_url = config.get('google').get('shared_url')

# use creds to create a client to interact with the Google Drive API


def icu(text, bot_id=botid):
    ''' let ICU send a message to the chat'''
    groupme_client.bots.post(text = text, bot_id = bot_id)

def get_old_conversation(years = 1, months = 0, days = 0):
    ''' retrieve the anniversary conversation in tabular format'''
    query_date = date.today() - relativedelta(years = years, months = months, days = days)
    output = df_msgs[df_msgs.send_date == query_date]
    if len(output) > 0:
        return(output.sort_values('timestamp').loc[:, ['user', 'txt', 'timestamp']])

def update_table(sheet, output):    
    
    nrows, ncols = output.shape
    cell_list = sheet.range('A1:C' + str(nrows+1))
    sheet.clear()

    cell_values = [] 
    cell_values.append('sender')
    cell_values.append('msg')
    cell_values.append('timestamp')
    for i in range(nrows):
        for j in range(ncols):
            cell_values.append(str(output.values[i,j]))

    for idx, cell in enumerate(cell_list):
        cell.value = cell_values[idx]
    sheet.update_cells(cell_list)


# the all-important app variable:
app = Flask(__name__)

@app.route("/", methods = ['POST'])
def hello():
    data = request.json
    current_message = data['text']
    if data['name'] != 'EYE SEE YOU':
        if current_message.startswith("@rewind"):
            yrs = current_message.split('-')[-1]
            yrs_num = int(yrs)
            if yrs.isdigit(): 
                if yrs_num < 8 and yrs_num >0:
                    output = get_old_conversation(years = yrs_num)

                    scope = ['https://spreadsheets.google.com/feeds','https://www.googleapis.com/auth/drive']
                    creds = ServiceAccountCredentials.from_json_keyfile_name(config.get('google').get('key_path'), scope)
                    client = gspread.authorize(creds)

                    # Find a workbook by name and open the first sheet
                    # Make sure you use the right name here.
                    sheet = client.open("icuoutput").sheet1
                    update_table(sheet,output)
                    icu(shared_url)
                    time.sleep(2)
    return('OK')

if __name__ == "__main__":
    app.run(host='0.0.0.0', debug=True, port=8888)