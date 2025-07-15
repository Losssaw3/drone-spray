from flask import Flask, request, jsonify
import requests
import random

app = Flask(__name__)

DRONE_TURN_ON_URL = "http://communication:8000/turn_on"
DRONE_START_URL = "http://communication:8000/start"
ready_flag = False
turn_on_flag = False
flight_status = False

@app.route('/turn_on')
def turn_on():
    """
    Turns on the drone if it is not already turned on.
    
    Returns:
        Response: JSON response indicating the status.
    """
    global turn_on_flag
    if not turn_on_flag:
        payload = {"state": "on"}
        response = requests.get(DRONE_TURN_ON_URL, json=payload)
        turn_on_flag = True
        return jsonify({"status": "drone initializing..."}) , 200
    else:
        return jsonify({"error": "drone already turned "}) , 409

@app.route('/init_status', methods=['POST'])
def init_status():
    """
    Updates the initialization status of the drone.
    
    Returns:
        Response: JSON response indicating the status.
    """
    global ready_flag
    data = request.get_json()
    print (f'{data.get("status")}')
    ready_flag = True
    return jsonify({"status": "ok"}), 200

@app.route('/start', methods=['GET'])
def start():
    """
    Starts the drone if it is ready and not already started.
    
    Returns:
        Response: JSON response indicating the status.
    """
    global flight_status
    if ready_flag and not flight_status:    
        payload = {"state": "start"}
        response = requests.get(DRONE_START_URL , json=payload)
        if response.status_code == 200:
            flight_status = True
            return jsonify({"status": "start successfully requested"}) , 200
    else:
        return jsonify({"error": "drone turned off! or its repeated attempt to start drone"}) , 409

def start_web():
    """
    Starts the Flask web server.
    """
    app.run(host='0.0.0.0', port=8000, threaded=True)
