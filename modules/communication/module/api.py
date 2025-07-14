import os
import time
import json
import threading
import multiprocessing
import requests

from uuid import uuid4
from flask import Flask, request, jsonify, abort
from .producer import proceed_to_deliver

HOST: str = "0.0.0.0"
PORT: int = int(os.getenv("MODULE_PORT"))
MODULE_NAME: str = os.getenv("MODULE_NAME")
REQUEST_ROUTE_FROM_CENTER_URL = "http://center:8000/start"


_requests_queue: multiprocessing.Queue = None
_response_queue: multiprocessing.Queue = None

app = Flask(__name__)

@app.route('/turn_on')
def turn_on():
    proceed_to_deliver(uuid4().__str__(), {
            "deliver_to": "encryption",
            "operation": "turn_on",
        })
    return jsonify({"status": "ok"}) , 200

@app.route('/start_mission', methods = ['POST'])
def start_mission():
    payload = request.get_json()
    proceed_to_deliver(uuid4().__str__(), {
        "deliver_to": "encryption",
        "operation": "start_mission",
        "mission": payload.get("mission"),
        "signature": payload.get("signature"),
        "check": payload.get("check")
    })
    return jsonify({"status": "ok"}) , 200


@app.route('/confirm_photo' , methods = ['GET'])
def confirm_photo():
    payload = request.get_json()
    proceed_to_deliver(uuid4().__str__(), {
            "deliver_to": "encryption",
            "operation": "confirm_photo",
            "check": payload.get("check"),
            "signature": payload.get("signature"),
        })
    return jsonify({"status": "confirmation received"}) , 200


@app.route('/start')
def start():
    try:
        data = request.get_json()
        if data.get("state") == "start":
            response = requests.get(REQUEST_ROUTE_FROM_CENTER_URL , json=data)
            return jsonify({"status": "preparing to start"}) , 200
    except Exception as e:
        return {"status": "error", "message": str(e)}


def start_web(requests_queue, response_queue):
    global _requests_queue
    global _response_queue

    _requests_queue = requests_queue
    _response_queue = response_queue

    threading.Thread(target=lambda: app.run(
        host=HOST, port=PORT, debug=True, use_reloader=False
    )).start()