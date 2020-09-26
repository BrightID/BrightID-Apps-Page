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


def read_googl_sheet():
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


def uchart_gen(currentValue):
    client = pymongo.MongoClient('mongodb://localhost:27017/')
    db = client['sponsored_users']
    uchart = {'title': 'Sponsored Users', 'timestamps': [0], 'values': [0]}
    for p in db.uchart.find().sort('_id'):
        uchart['timestamps'].append(
            p['_id'].generation_time.timestamp() * 1000)
        uchart['values'].append(p['value'])
    now = int(time.time() * 1000)
    # first point
    if not uchart['timestamps']:
        uchart['timestamps'].append(0)
        uchart['values'].append(0)
    # update weekly
    if (now - uchart['timestamps'][-1]) > 604800000:
        db.uchart.insert_one({'value': currentValue})
        uchart['timestamps'].append(now)
        uchart['values'].append(currentValue)
    client.close()
    return uchart


def main():
    print('Updating the application page data')

    result = read_googl_sheet()
    cs = requests.get(config.apps_url).json()['data']['apps']
    sponsereds = sum([c['assignedSponsorships'] -
                      c['unusedSponsorships'] for c in cs])
    apps = {c['name']: c for c in cs}
    for app in result['Applications']:
        app['Assigned Sponsorships'] = '_'
        app['Unused Sponsorships'] = '_'
        if not app.get('Application'):
            continue
        context_name = app.get('Application')
        if not apps.get(context_name):
            print('Cannot find "{}" in the node apps'.format(context_name))
            continue
        context = apps.get(context_name)
        app['Assigned Sponsorships'] = context.get('assignedSponsorships')
        app['Unused Sponsorships'] = context.get('unusedSponsorships')
        app['Used Sponsorships'] = context.get('assignedSponsorships') - context.get('unusedSponsorships')
        app['order'] = app['Assigned Sponsorships'] * (app['Used Sponsorships'] + 1)

    # sort applications by used sponsorships
    result['Applications'].sort(key=lambda i: i['order'], reverse=True)

    # sponsored users chart data
    result['Charts'] = [uchart_gen(sponsereds)]

    # applications chart data
    achart = {'title': 'Applications', 'timestamps': [0], 'values': [0]}

    achart['timestamps'].extend(sorted([time.mktime(datetime.datetime.strptime(
        r['Joined'], "%m/%d/%Y").timetuple()) for r in result['Applications']]))
    achart['values'].extend(
        [i + 1 for i, t in enumerate(achart['timestamps'])])
    result['Charts'].append(achart)

    # nodes chart data
    nchart = {'title': 'Nodes', 'timestamps': [0], 'values': [0]}

    nchart['timestamps'].extend(sorted([time.mktime(datetime.datetime.strptime(
        r['Joined'], "%m/%d/%Y").timetuple()) for r in result['Nodes']]))
    nchart['values'].extend(
        [i + 1 for i, t in enumerate(nchart['timestamps'])])
    result['Charts'].append(nchart)
    with open(config.data_file_addr, 'w') as f:
        f.write('result = {}'.format(json.dumps(result, indent=2)))


if __name__ == '__main__':
    main()
