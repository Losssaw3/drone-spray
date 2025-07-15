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

APP_STATUS_URL = "http://mobile:8000/init_status"
CENTER_STATUS_URL = "http://center:8000/init_status"
CENTER_VALIDATE_PHOTO = "http://center:8000/validate"
MODULE_NAME: str = os.getenv("MODULE_NAME")
INIT_PATH: str = "/shared/init"



def send_status(details):
    """
    Sends the drone's status to the app and center modules.
    
    Args:
        details (dict): Status details.
    """
    try:
        responce_app = requests.post(APP_STATUS_URL, json=details)
        
        responce_center = requests.post(CENTER_STATUS_URL, json=details)
    except Exception as e:
        return {"status": "error", "message": str(e)}

def send_photo(details):
    """
    Sends a photo to the center module for validation.
    
    Args:
        details (dict): Photo details.
    """
    try:
        responce_center = requests.post(CENTER_VALIDATE_PHOTO , json=details)
    except Exception as e:
        return {"status": "error", "message": str(e)}

def handle_event(id, details_str):
    """
    Handles incoming events and processes operations like sending status or photos.
    
    Args:
        id (str): Event ID.
        details_str (str): JSON string containing event details.
    """
    details = json.loads(details_str)
    source: str = details.get("source")
    deliver_to: str = details.get("deliver_to")
    operation: str = details.get("operation")
    print(f"[info] handling event {id}, "
          f"{source}->{deliver_to}: {operation}")

    if operation == "photo":
        send_photo(details)

    if operation == "status":
        send_status(details)

def consumer_job(args, config):
    """
    Listens for incoming Kafka messages and processes them.
    
    Args:
        args: Command-line arguments.
        config (dict): Kafka consumer configuration.
    """
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
    """
    Starts the consumer job in a separate thread.
    
    Args:
        args: Command-line arguments.
        config (dict): Kafka consumer configuration.
    """
    print(f'{MODULE_NAME}_consumer started')
    threading.Thread(target=lambda: consumer_job(args, config)).start()