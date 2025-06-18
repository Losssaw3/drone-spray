import time
import threading
import random
import requests
import os
import json

from flask import Flask, request, jsonify
from uuid import uuid4
from time import sleep
from confluent_kafka import Consumer, OFFSET_BEGINNING
from .producer import proceed_to_deliver

app = Flask(__name__)

CKOB_BOAT_DATA_LOG_URL = "http://ckob:8000/log-boat-data"
ORVD_BOAT_POS_LOG_URL = "http://orvd:8000/log-boat-pos"
CKOB_FINISH = "http://ckob:8000/finish"
MODULE_NAME: str = os.getenv("MODULE_NAME")
INIT_PATH: str = "/shared/init"




def send_emergency(code):
    try:
        payload = {"status": "stopped by emergency" , "code": code}
        responce_orvd = requests.post(ORVD_BOAT_POS_LOG_URL, json=payload)
        json_data_orvd = responce_orvd.json()
        
        responce_ckob = requests.post(CKOB_BOAT_DATA_LOG_URL, json=payload)
        json_data_ckob = responce_ckob.json()
    except Exception as e:
        return {"status": "error", "message": str(e)}

def send_telemetry(telemtry):
    try:
        payload = telemtry
        print(payload)
        responce_orvd = requests.post(ORVD_BOAT_POS_LOG_URL, json=payload)
        json_data_orvd = responce_orvd.json()
        
        responce_ckob = requests.post(CKOB_BOAT_DATA_LOG_URL, json=payload)
        json_data_ckob = responce_ckob.json()
    except Exception as e:
        return {"status": "error", "message": str(e)}


def handle_event(id, details_str):
    """ Модуль сбора данных. """
    details = json.loads(details_str)
    source: str = details.get("source")
    deliver_to: str = details.get("deliver_to")
    operation: str = details.get("operation")
    

    print(f"[info] handling event {id}, "
          f"{source}->{deliver_to}: {operation}")

    if operation == "route_complete":
        try:
            responce = requests.get(CKOB_FINISH)
        except Exception as e:
            return {"status": "error", "message": str(e)}

    if operation == "send_telemetry":
        telemetry = details.get("telemetry")
        send_telemetry(telemetry)
        print("[message_processing] send telemetry telemetry")

    if operation == "emergency_stop" and source == "crypto":
        code = details.get("code")
        print("[message processing] boat stopped by emergency")
        send_emergency(code)

def consumer_job(args, config):
    consumer = Consumer(config)

    def reset_offset(verifier_consumer, partitions):
        if not args.reset:
            return

        for p in partitions:
            p.offset = OFFSET_BEGINNING
        verifier_consumer.assign(partitions)

    topic = MODULE_NAME
    consumer.subscribe([topic], on_assign=reset_offset)

    try:
        while True:
            msg = consumer.poll(1.0)
            if msg is None:
                pass
            elif msg.error():
                print(f"[error] {msg.error()}")
            else:
                try:
                    id = msg.key().decode('utf-8')
                    details_str = msg.value().decode('utf-8')
                    handle_event(id, details_str)
                except Exception as e:
                    print(f"[error] Malformed event received from " \
                          f"topic {topic}: {msg.value()}. {e}")
    except KeyboardInterrupt:
        pass

    finally:
        consumer.close()

def start_consumer(args, config):
    print(f'{MODULE_NAME}_consumer started')
    threading.Thread(target=lambda: consumer_job(args, config)).start()