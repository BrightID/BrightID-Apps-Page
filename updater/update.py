from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import requests
import datetime
import os.path
import pymongo
import pickle
import config
import json
import time


def num_linked_users(context):
    url = config.verifications_url.format(context)
    res = requests.get(url).json()
    if res['error']:
        print(f"Error in getting {context} verifications: ", res)
        return '_'
    return res['data']['count']


def read_google_sheet():
    creds = None
    if os.path.exists('token.pickle'):
        with open(config.token_file_addr, 'rb') as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                config.credentials_file, config.scopes)
            creds = flow.run_local_server(port=0)
        with open(config.token_file_addr, 'wb') as token:
            pickle.dump(creds, token)
    service = build('sheets', 'v4', credentials=creds)
    sheet = service.spreadsheets()
    results = {}
    for sheet_name in ['Applications', 'Nodes']:
        r = sheet.values().get(spreadsheetId=config.spreadsheet_id,
                               range=sheet_name).execute()
        rows = r.get('values', [])
        results[sheet_name] = [dict(zip(rows[0], row)) for row in rows[1:]]
        for d in results[sheet_name]:
            for key in d:
                if key in ['Images', 'Links']:
                    d[key] = d[key].split('\n')
    return results


def uchart_gen(currentValue, timestamps):
    client = pymongo.MongoClient('mongodb://localhost:27017/')
    db = client['sponsored_users']
    points = list(db.uchart.find().sort('_id', -1))
    now = int(time.time())
    # update db
    if (now - points[0]['_id'].generation_time.timestamp()) > config.sponsoreds_snapshot_period:
        db.uchart.insert_one({'value': currentValue})
    else:
        db.uchart.replace_one({"_id": points[0]['_id']}, {'value': currentValue})
    # generate chart data
    uchart = {'title': 'Sponsored Users',
              'timestamps': timestamps, 'values': [0] * 6}
    for p in db.uchart.find().sort('_id', -1):
        for i, t in enumerate(timestamps):
            if p['_id'].generation_time.timestamp() <= t and uchart['values'][i] == 0:
                uchart['values'][i] = p['value']
    points = list(db.uchart.find().sort('_id', -1))
    client.close()
    return uchart


def main():
    print('Updating the application page data.', time.ctime())
    cs = requests.get(config.apps_url).json()['data']['apps']
    sponsereds = sum([c['assignedSponsorships'] -
                      c['unusedSponsorships'] for c in cs])
    node_apps = {c['id']: c for c in cs}

    result = read_google_sheet()
    for app in result['Applications']:
        app['Assigned Sponsorships'] = '_'
        app['Unused Sponsorships'] = '_'
        app['users'] = '_'
        app['order'] = 0
        if not app.get('Application'):
            continue
        app_name = app.get('Application')
        if not node_apps.get(app_name):
            print('Cannot find "{}" in the node data'.format(app_name))
            continue
        node_app = node_apps.get(app_name)
        app['Assigned Sponsorships'] = node_app.get('assignedSponsorships')
        app['Unused Sponsorships'] = node_app.get('unusedSponsorships')
        app['Used Sponsorships'] = node_app.get(
            'assignedSponsorships') - node_app.get('unusedSponsorships')
        app['order'] = app['Assigned Sponsorships'] * \
            (app['Used Sponsorships'] + 1)
        app['users'] = num_linked_users(app.get('Context'))

    # sort applications by used sponsorships
    result['Applications'].sort(key=lambda i: i['order'], reverse=True)

    timestamps = []
    for i in range(6):
        now = time.time()
        pw = now - i * config.chart_step
        timestamps.insert(0, pw)

    # sponsored users chart data
    result['Charts'] = [uchart_gen(sponsereds, timestamps)]

    # applications chart data
    achart = {'title': 'Applications',
              'timestamps': timestamps, 'values': [0] * 6}
    for app in result['Applications']:
        joined_timestamp = time.mktime(datetime.datetime.strptime(
            app['Joined'], "%m/%d/%Y").timetuple())
        for i, t in enumerate(timestamps):
            if joined_timestamp <= t:
                achart['values'][i] += 1
    result['Charts'].append(achart)

    # nodes chart data
    nchart = {'title': 'Nodes', 'timestamps': timestamps, 'values': [0] * 6}
    for node in result['Nodes']:
        joined_timestamp = time.mktime(datetime.datetime.strptime(
            node['Joined'], "%m/%d/%Y").timetuple())
        for i, t in enumerate(timestamps):
            if joined_timestamp <= t:
                nchart['values'][i] += 1
    result['Charts'].append(nchart)
    with open(config.data_file_addr, 'w') as f:
        f.write(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
