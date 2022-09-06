from flask import Flask, request, jsonify
from marshmallow import Schema, fields, ValidationError
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import datetime
import ed25519
import pickle
import base64
import json
import os
import re
import config

app = Flask(__name__)


def get_message(req_data):
    signed_req_data = {k: req_data[k] for k in req_data if k not in ['sig']}
    return json.dumps(signed_req_data, sort_keys=True, separators=(',', ':')).encode('ascii')


def verify_app_sig(msg, public_key, sig):
    public_key = ed25519.VerifyingKey(base64.b64decode(public_key))
    try:
        public_key.verify(base64.b64decode(sig), msg, encoding='hex')
    except:
        return False
    return True


class AppSchema(Schema):
    key = fields.Str(required=True)
    name = fields.Str(required=True)
    idsAsHex = fields.Boolean(required=True)
    soulbound = fields.Boolean(required=True)
    soulboundMessage = fields.Str(metadata={'allow_blank': True})
    usingBlindSig = fields.Boolean(required=True)
    verifications = fields.List(
        fields.String(), metadata={'allow_blank': True})
    verificationExpirationLength = fields.Integer()
    nodeUrl = fields.URL()
    verification = fields.Str(metadata={'allow_blank': True})
    description = fields.Str(required=True)
    context = fields.Str(metadata={'allow_blank': True})
    testimonial = fields.Str(metadata={'allow_blank': True})
    links = fields.List(fields.String(), required=True)
    images = fields.List(fields.String(), required=True)
    sponsorPublicKey = fields.Str(required=True)
    poaNetwork = fields.Boolean(load_default=False)
    localFilter = fields.Boolean(load_default=False)
    contractAddress = fields.Str(metadata={'allow_blank': True})
    rpcEndpoint = fields.URL(schemes={'http', 'https', 'ws', 'wss'})
    callbackUrl = fields.URL()
    sig = fields.Str(required=True)


def check_conflicts(req_data):
    if not re.match('(?!^\\d+$)^\\w+$', req_data['key']):
        raise ValueError(f'invalid key ({req_data["key"]}).')

    if req_data['soulbound'] and req_data['usingBlindSig']:
        raise ValueError('soulbound apps cannot use blind signatures.')

    if not req_data['usingBlindSig'] and not req_data['context']:
        raise ValueError('"context" cannot be empty for v5 apps.')

    if not req_data['usingBlindSig'] and not req_data['verification']:
        raise ValueError('"verification" cannot be empty for v5 apps.')

    if req_data['soulboundMessage'] and not req_data['soulbound']:
        raise ValueError(
            'cannot set "soulboundMessage" for not soulbound apps.')

    if req_data['usingBlindSig'] and not req_data['verifications']:
        raise ValueError('verifications cannot be empty for v6 apps.')


def get_service():
    creds = None
    if os.path.exists('token.pickle'):
        with open(config.TOKEN_FILE_ADDR, 'rb') as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                config.CREDENTIALS_FILE, config.SCOPES)
            creds = flow.run_local_server(port=0)
        with open(config.TOKEN_FILE_ADDR, 'wb') as token:
            pickle.dump(creds, token)
    service = build(config.API_NAME, config.API_VERSION, credentials=creds)
    return service


def read_apps_sheet():
    service = get_service()
    sheet = service.spreadsheets().values().get(
        spreadsheetId=config.SPREADSHEET_ID,
        range='Applications'
    ).execute()
    rows = sheet.get('values', [])

    attrs = [f'{c[:1].lower()}{c[1:]}'.replace(' ', '') if c not in ['POA Network',
                                                                     'RPC Endpoint'] else f'{c[:3].lower()}{c[3:]}'.replace(' ', '') for c in rows[0]]
    rows = [dict(zip(attrs, row)) for row in rows[1:]]
    registered_apps = {}
    for row in rows:
        for k in row:
            if k in ['Images', 'Links', 'Verifications']:
                row[k] = list(filter(None, row[k].split('\n')))
            elif k in ['Testing', 'Local Filter', 'Using Blind Sig', 'Ids As Hex', 'Soulbound', 'POA Network']:
                row[k] = row[k] == 'TRUE'
        registered_apps[row['key']] = row
    return attrs, registered_apps


@app.route('/add', methods=['POST'])
def add():
    req_data = request.get_json()
    print('ADD REQUEST: ', req_data)

    for attr in ['sponsorPublicKey', 'sig']:
        if attr not in req_data:
            return jsonify({attr: ['Missing data for required field.']}), 400

    msg = get_message(req_data)
    if not verify_app_sig(msg, req_data['sponsorPublicKey'], req_data['sig']):
        return jsonify('Signature is not valid.'), 400

    schema = AppSchema()
    try:
        req_data = schema.load(req_data, partial=False)
    except ValidationError as err:
        return jsonify(err.messages), 400

    try:
        check_conflicts(req_data)
    except ValueError as err:
        return jsonify(err.args[0]), 400

    attrs, registered_apps = read_apps_sheet()
    if req_data['key'] in registered_apps:
        return jsonify(f'This key ({req_data["key"]}) is already registered.'), 400

    new_row = []
    for attr in attrs:
        if attr in ['testing', 'disabled']:
            cell = True
        elif attr in ['images', 'links', 'verifications']:
            cell = '\n'.join(req_data.get(attr, []))
        elif attr == 'joined':
            date = datetime.datetime.now()
            cell = f'{date.month}/{date.day}/{date.year}'
        else:
            cell = req_data.get(attr, '')
        new_row.append(cell)

    service = get_service()
    request_body = {
        'majorDimension': 'ROWS',
        'values': [new_row]
    }
    service.spreadsheets().values().append(
        spreadsheetId=config.SPREADSHEET_ID,
        valueInputOption='USER_ENTERED',
        range='Applications!A1',
        body=request_body
    ).execute()
    return json.dumps({'success': True}), 200, {'ContentType': 'application/json'}


@app.route('/update', methods=['PUT'])
def update():
    req_data = request.get_json()
    print('UPDATE REQUEST: ', req_data)

    for attr in ['key', 'sig']:
        if attr not in req_data:
            return jsonify({attr: ['Missing data for required field.']}), 400

    for attr in ['context', 'sponsorPublicKey']:
        if attr in req_data:
            return jsonify(f'Cannot update "{attr}".'), 400
    schema = AppSchema()
    try:
        req_data = schema.load(req_data, partial=True)
    except ValidationError as err:
        return jsonify(err.messages), 400

    attrs, registered_apps = read_apps_sheet()
    if req_data['key'] not in registered_apps:
        return jsonify(f'Cannot find "{req_data["key"]}" app.'), 400

    msg = get_message(req_data)
    if not verify_app_sig(msg, registered_apps[req_data['key']]['sponsorPublicKey'], req_data['sig']):
        return jsonify('Signature is not valid.'), 400

    service = get_service()
    updated_row = []
    for attr in attrs:
        val = req_data[attr] if attr in req_data else registered_apps[req_data['key']][attr]
        if attr in ['images', 'links', 'verifications']:
            val = '\n'.join(val)
        updated_row.append(val)

    row_num = list(registered_apps.keys()).index(req_data['key']) + 2

    request_body = {
        'majorDimension': 'ROWS',
        'values': [updated_row]
    }
    service.spreadsheets().values().update(
        spreadsheetId=config.SPREADSHEET_ID,
        valueInputOption='USER_ENTERED',
        range=f'Applications!A{row_num}',
        body=request_body
    ).execute()

    return json.dumps({'success': True}), 200, {'ContentType': 'application/json'}


@app.route('/remove', methods=['DELETE'])
def remove():
    req_data = request.get_json()
    print('REMOVE REQUEST: ', req_data)

    for attr in ['key', 'sig']:
        if attr not in req_data:
            return jsonify({attr: ['Missing data for required field.']}), 400

    for attr in req_data:
        if attr not in ['key', 'sig']:
            return jsonify({attr: ['Unknown field.']}), 400

    attrs, registered_apps = read_apps_sheet()
    if req_data['key'] not in registered_apps:
        return jsonify(f'Cannot find "{req_data["key"]}" app.'), 400

    msg = get_message(req_data)
    if not verify_app_sig(msg, registered_apps[req_data['key']]['sponsorPublicKey'], req_data['sig']):
        return jsonify('Signature is not valid.'), 400

    row_num = list(registered_apps.keys()).index(req_data['key']) + 2

    service = get_service()
    request_body = {
        'requests': [
            {
                'deleteDimension': {
                    'range': {
                        'sheetId': 0,
                        'dimension': 'ROWS',
                        'startIndex': row_num - 1,
                        'endIndex': row_num
                    }
                }
            }
        ]
    }
    service.spreadsheets().batchUpdate(
        spreadsheetId=config.SPREADSHEET_ID,
        body=request_body
    ).execute()

    request_body = {
        'majorDimension': 'ROWS',
        'values': [[req_data['key']]]
    }
    service.spreadsheets().values().append(
        spreadsheetId=config.SPREADSHEET_ID,
        valueInputOption='USER_ENTERED',
        range='Removed apps!A1',
        body=request_body
    ).execute()

    return json.dumps({'success': True}), 200, {'ContentType': 'application/json'}


if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=7070, threaded=True)
