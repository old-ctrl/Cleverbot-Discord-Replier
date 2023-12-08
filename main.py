# Kalr 2023 - Cleverbot
# v3

import requests
import json
import websocket
import threading
import time
import datetime
import re
import hashlib

class DiscordCleverbot:
    def __init__(self, token, targets):
        self.token = token
        self.targets = targets
        self.ws = websocket.WebSocket()
        self.connect_to_discord()
        self.cookies = None
        self.sessions = {}

    def connect_to_discord(self):
        self.ws.connect("wss://gateway.discord.gg/?v=10&encoding=json")
        event = self.receive_json_response()
        heartbeat_interval = event['d']['heartbeat_interval'] / 1000
        threading.Thread(target=self.heartbeat, args=(heartbeat_interval,)).start()
        self.send_json_request({
            "op": 2,
            "d": {
                "token": self.token,
                "properties": {
                    "$os": 'windows',
                    '$browser': 'chrome',
                    '$device': 'pc'
                }
            }
        })

    def send_json_request(self, request):
        self.ws.send(json.dumps(request))

    def receive_json_response(self):
        response = self.ws.recv()
        return json.loads(response) if response else None

    def heartbeat(self, interval):
        while True:
            time.sleep(interval)
            self.send_json_request({"op": 1, "d": "null"})

    def send_discord_message(self, channel_id, message):
        url = f"https://discord.com/api/v9/channels/{channel_id}/messages"
        headers = {
            "Authorization": f"{self.token}",
            "Content-Type": "application/json"
        }
        data = {"content": message, "tts": False}
        response = requests.post(url, headers=headers, json=data)
        return response.json()

    def cleverbot(self, stimulus, context=[], session=None):
        if self.cookies is None:
            self.initialize_cookies()
        payload = self.prepare_payload(stimulus, context, session)
        response = requests.post(
            "https://www.cleverbot.com/webservicemin?uc=UseOfficialCleverbotAPI",
            cookies=self.cookies,
            data=payload)
        return self.parse_response(response, stimulus, session)

    def initialize_cookies(self):
        req = requests.get("https://www.cleverbot.com/extras/conversation-social-min.js?{}".format(self.get_date()))
        self.cookies = {'XVIS': re.search(r"\w+(?=;)", req.headers["Set-cookie"]).group()}

    @staticmethod
    def get_date():
        return datetime.datetime.now().strftime("%Y%m%d")

    def prepare_payload(self, stimulus, context, session):
        payload = f"stimulus={requests.utils.requote_uri(stimulus)}&"
        for i, text in enumerate(reversed(context)):
            payload += f"vText{i + 2}={requests.utils.requote_uri(text)}&"
        if session:
            session_context = self.sessions.setdefault(session, [])
            for i, text in enumerate(reversed(session_context)):
                payload += f"vText{i + len(context) + 2}={requests.utils.requote_uri(text)}&"
            self.sessions[session] = context + session_context
        payload += "cb_settings_scripting=no&islearning=1&icognoid=wsf&icognocheck="
        payload += hashlib.md5(payload[7:33].encode()).hexdigest()
        return payload

    def parse_response(self, response, stimulus, session):
        getresponse = re.split(r'\\r', str(response.content))[0]
        response_text = getresponse[2:-1]
        if session:
            self.sessions[session].extend([stimulus, response_text])
        return response_text

    def listen_to_messages(self):
        while True:
            event = self.receive_json_response()
            try:
                if event and event['t'] == 'MESSAGE_CREATE' and event['d']['author']['global_name'] in self.targets:
                    content = event['d']['content']
                    user = event['d']['author']['global_name']
                    print(f"{user}: {content}")
                    response = self.cleverbot(content, session=user)
                    print(response)
                    self.send_discord_message(event['d']['channel_id'], response)
            except Exception as e:
                print(f"Error: {e}")

# Usage
token = "token here" 
targets = ['card'] 
bot = DiscordCleverbot(token, targets)
bot.listen_to_messages()

