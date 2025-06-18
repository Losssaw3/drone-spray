import os
import time
import json
import threading
import multiprocessing

from uuid import uuid4
from flask import Flask, request, jsonify, abort
from .producer import proceed_to_deliver

HOST: str = "0.0.0.0"
PORT: int = int(os.getenv("MODULE_PORT"))
MODULE_NAME: str = os.getenv("MODULE_NAME")
MAX_WAIT_TIME: int = 10
APP_LOG_URL = "http://ckob:8000/log-boat-data"
CENTER_LOG_URL = "http://orvd:8000/log-boat-pos"


# Очереди задач и ответов
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

def start_web(requests_queue, response_queue):
    global _requests_queue
    global _response_queue

    _requests_queue = requests_queue
    _response_queue = response_queue

    threading.Thread(target=lambda: app.run(
        host=HOST, port=PORT, debug=True, use_reloader=False
    )).start()