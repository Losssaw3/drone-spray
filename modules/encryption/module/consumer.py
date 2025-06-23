import time
import threading
import random
import os
import json

from uuid import uuid4
from time import sleep
from confluent_kafka import Consumer, OFFSET_BEGINNING
from .producer import proceed_to_deliver


MODULE_NAME = os.getenv("MODULE_NAME")
consumers = ["limiter", "mission-control", "task-orchestrator"]
def turn_on():
    proceed_to_deliver(uuid4().__str__(), {
            "deliver_to": "drone-status-control",
            "operation": "turn_on",
        })

def start_mission(details):
    global consumers
    mission = details.get("mission")
    for consumer in consumers:
        proceed_to_deliver(uuid4().__str__(), {
                "deliver_to": consumer,
                "operation": "set_mission",
                "mission": mission
            })

def sign_and_send(details):
    print("signing message")
    proceed_to_deliver(uuid4().__str__(),details)

def verify():
    return True

def handle_event(id, details_str):
    """ Обработчик входящих в модуль задач. """

    details = json.loads(details_str)
    source: str = details.get("source")
    if source == "communication":
        if verify():
            deliver_to: str = details.get("deliver_to")
            operation: str = details.get("operation")
            if operation == "turn_on":
                turn_on()
            if operation == "start_mission":
                start_mission(details)
            if operation == "confirm_photo":
                details["deliver_to"] = "mission-control"
                proceed_to_deliver(uuid4().__str__(),details)
                
    elif source == "message-sending": # status , photo
        deliver_to: str = details.get("deliver_to")
        operation: str = details.get("operation")
        details["deliver_to"] = "communication"
        sign_and_send(details)
    print(f"[info] handling event {id}, "
          f"{source}->{deliver_to}: {operation}")

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
                    id = msg.key().decode("utf-8")
                    details_str = msg.value().decode("utf-8")
                    handle_event(id, details_str)
                except Exception as e:
                    print(f"[error] Malformed event received from " \
                          f"topic {topic}: {msg.value()}. {e}")
    except KeyboardInterrupt:
        pass

    finally:
        consumer.close()

def start_consumer(args, config):
    print(f"{MODULE_NAME}_consumer started")
    threading.Thread(target=lambda: consumer_job(args, config)).start()