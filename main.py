# Kalr 2023 - Cleverbot
# v2

import requests
import json
import cleverbotfreeapi
import websocket
import threading
import time
import datetime
import re
import hashlib

token = "" 
targets = [''] # Enter targets display name

headers = {'authorization': token}

def send_json_request(ws, request):
    ws.send(json.dumps(request))

def receive_json_response(ws):
    response = ws.recv()
    if response:
        return json.loads(response)

def send_discord_message(channel_id, message):
    url = f"https://discord.com/api/v9/channels/{channel_id}/messages"
    headers = {
        "Authorization": f"{token}",  # Fixed authorization header
        "Content-Type": "application/json"
    }
    data = {
        "content": message,
        "tts": False
    }
    response = requests.post(url, headers=headers, json=data)
    return response.json()

def heartbeat(interval, ws):
    print('Search activated')
    while True:
        time.sleep(interval)
        heartbeatJSON = {
            "op": 1,
            "d": "null"
        }
        send_json_request(ws, heartbeatJSON)
        print("Looking for messages to be sent.")

ws = websocket.WebSocket()
ws.connect("wss://gateway.discord.gg/?v=10&encoding=json")
event = receive_json_response(ws)

heartbeat_interval = event['d']['heartbeat_interval'] / 1000
threading._start_new_thread(heartbeat, (heartbeat_interval, ws))

payload = {
    "op": 2,
    "d": {
        "token": token,
        "properties": {
            "$os": 'windows',
            '$browser': 'chrome',
            '$device': 'pc'
        }
    }
}
send_json_request(ws, payload)

cookies = None
sessions = dict()

def get_date():
    return datetime.datetime.now().strftime("%Y%m%d")

def cleverbot(stimulus, context=[], session=None):
    global cookies, sessions
    if (cookies is None):
        req = requests.get("https://www.cleverbot.com/extras/conversation-social-min.js?{}".format(get_date()))
        cookies = {
            'XVIS': re.search(
                r"\w+(?=;)",
                req.headers["Set-cookie"]).group()}
    payload = f"stimulus={requests.utils.requote_uri(stimulus)}&"

    _context = context[:]
    reverseContext = list(reversed(_context))

    for i in range(len(_context)):
        payload += f"vText{i + 2}={requests.utils.requote_uri(reverseContext[i])}&"

    if session:
        if session not in sessions.keys():
            sessions[session] = list()

        _session = list(reversed(sessions[session]))
        for i in range(len(sessions[session])):
            payload += f"vText{i + len(_context) + 2}={requests.utils.requote_uri(_session[i])}&"

        sessions[session] = _context + sessions[session]

    payload += "cb_settings_scripting=no&islearning=1&icognoid=wsf&icognocheck="

    payload += hashlib.md5(payload[7:33].encode()).hexdigest()

    req = requests.post(
        "https://www.cleverbot.com/webservicemin?uc=UseOfficialCleverbotAPI",
        cookies=cookies,
        data=payload)
    getresponse = re.split(r'\\r', str(req.content))[0]
    response = getresponse[2:-1]
    if session:
        sessions[session].extend([stimulus, response])
    return response

while True:
    event = receive_json_response(ws)
    try:
        if event['t'] == 'MESSAGE_CREATE' and event['d']['author']['global_name'] in targets:
            content = event['d']['content']
            user = event['d']['author']['global_name']
            message = f"{event['d']['author']['global_name']}: {content}"
            print(message)
            response = cleverbot(content, session=user)
            print(response)
            send_discord_message(event['d']['channel_id'], response)
    except:
        pass
