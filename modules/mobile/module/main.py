from flask import Flask, request, jsonify
import requests
import random

app = Flask(__name__)

DRONE_TURN_ON_URL = "http://communication:8000/turn_on"
DRONE_START_URL = "http://communication:8000/start"
ready_flag = False

@app.route('/turn_on')
def turn_on():
    payload = {"state": "on"}
    response = requests.get(DRONE_TURN_ON_URL, json=payload)
    return jsonify({"status": "drone initializing..."}) , 200

@app.route('/init_status')
def init_status():
    global ready_flag
    data = request.get_json()
    print (f'{data.get("status")}')
    ready_flag = True

@app.route('/start', methods=['GET'])
def start():
    if ready_flag:    
        payload = {"state": "start"}
        response = requests.get(DRONE_START_URL , json=payload)
        if response.status_code == 200:
            return jsonify({"status": "start successfully requested"}) , 200
    else:
        print("drone turned off, cant start!")

def start_web():
    app.run(host='0.0.0.0', port=8000, threaded=True)
    