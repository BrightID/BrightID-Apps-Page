from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from dateutil.relativedelta import relativedelta
import requests
import datetime
import os
import pymongo
import pickle
import config
import json
import time


def num_linked_users(context):
    url = config.linked_users_url.format(context)
    res = requests.get(url).json()
    if res.get('error', False):
        print(f'Error in getting linked users of {context}: {res}')
        return '_'
    return res['data']['count']


def read_google_sheets():
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
    for sheet_name in ['Applications', 'Nodes', 'Removed apps']:
        r = sheet.values().get(spreadsheetId=config.spreadsheet_id,
                               range=sheet_name).execute()
        rows = r.get('values', [])
        results[sheet_name] = [dict(zip(rows[0], row)) for row in rows[1:]]
        for d in results[sheet_name]:
            for key in d:
                if key in ['Images', 'Links', 'Verifications']:
                    d[key] = list(filter(None, d[key].split('\n')))
                if key in ['Testing', 'Local Filter', 'Using Blind Sig', 'Ids As Hex']:
                    d[key] = d[key] == 'TRUE'
    return results


def uchart_generator(currentValue, xticks):
    client = pymongo.MongoClient('mongodb://localhost:27017/')
    db = client['sponsored_users']
    points = list(db.uchart.find().sort('_id', -1))
    now = int(time.time())
    # update db
    if (now - points[0]['_id'].generation_time.timestamp()) > config.sponsoreds_snapshot_period:
        db.uchart.insert_one({'value': currentValue})
    else:
        db.uchart.replace_one({"_id": points[0]['_id']}, {
                              'value': currentValue})
    # generate chart data
    uchart = {'title': 'Sponsored Users',
              'timestamps': xticks['labels'], 'values': [0] * len(xticks['labels'])}
    for p in db.uchart.find().sort('_id', -1):
        for i, t in enumerate(xticks['values']):
            if p['_id'].generation_time.timestamp() <= t and uchart['values'][i] == 0:
                uchart['values'][i] = p['value']
    points = list(db.uchart.find().sort('_id', -1))
    client.close()
    return uchart


def achart_generator(apps, xticks):
    achart = {'title': 'Applications', 'timestamps': xticks['labels'], 'values': [
        0] * len(xticks['labels'])}
    for app in apps:
        if app['Testing']:
            continue
        joined_timestamp = time.mktime(datetime.datetime.strptime(
            app['Joined'], "%m/%d/%Y").timetuple())
        for i, t in enumerate(xticks['values']):
            if joined_timestamp <= t:
                achart['values'][i] += 1
    return achart


def nchart_generator(nodes, xticks):
    nchart = {'title': 'Nodes', 'timestamps': xticks['labels'], 'values': [
        0] * len(xticks['labels'])}
    for node in nodes:
        joined_timestamp = time.mktime(datetime.datetime.strptime(
            node['Joined'], "%m/%d/%Y").timetuple())
        for i, t in enumerate(xticks['values']):
            if joined_timestamp <= t:
                nchart['values'][i] += 1
    return nchart


def xticks_generator():
    xticks = {'labels': [], 'values': []}
    today = datetime.date.today()
    xticks['labels'].insert(0, int(time.mktime(today.timetuple())))
    xticks['values'].insert(0, int(time.mktime(today.timetuple())))
    for i in range(1, 12):
        first = today + relativedelta(months=(-1 * i))
        # Jun 1, 2020
        if int(time.mktime(first.timetuple())) > 1590973200:
            xticks['labels'].insert(0, int(time.mktime(first.timetuple())))
            xticks['values'].insert(0, int(time.mktime(first.timetuple())))
    return xticks


def main():
    print('Updating the application page data.', time.ctime())
    node_apps = requests.get(config.apps_url).json()['data']['apps']
    sponsereds = sum([node_app['assignedSponsorships'] -
                      node_app['unusedSponsorships'] for node_app in node_apps])
    node_apps = {node_app['id']: node_app for node_app in node_apps}

    result = read_google_sheets()
    for app in result['Applications']:
        app.update({'Assigned Sponsorships': '_', 'Unused Sponsorships': '_',
                    'Used Sponsorships': '_', 'users': '_', 'order': 0})
        if not app.get('Key'):
            continue

        key = app.get('Key')
        if not node_apps.get(key):
            print('Cannot find "{}" in the node data'.format(key))
            continue

        node_app = node_apps.get(key)
        app['Assigned Sponsorships'] = node_app.get('assignedSponsorships', 0)
        app['Unused Sponsorships'] = node_app.get('unusedSponsorships', 0)
        app['Used Sponsorships'] = app['Assigned Sponsorships'] - \
            app['Unused Sponsorships']
        app['order'] = app['Assigned Sponsorships'] * \
            max(app['Used Sponsorships'], 1)
        app['users'] = num_linked_users(app.get('Context'))

    # sort applications by used sponsorships
    result['Applications'].sort(key=lambda i: i['order'], reverse=True)

    result['Charts'] = []
    xticks = xticks_generator()

    # sponsored users chart data
    uchart = uchart_generator(sponsereds, xticks)
    result['Charts'].append(uchart)

    # applications chart data
    achart = achart_generator(result['Applications'], xticks)
    result['Charts'].append(achart)

    # nodes chart data
    nchart = nchart_generator(result['Nodes'], xticks)
    result['Charts'].append(nchart)

    # removed apps
    result['Removed apps'] = [app['Key'] for app in result['Removed apps']]

    with open(config.data_file_addr, 'w') as f:
        f.write(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()

