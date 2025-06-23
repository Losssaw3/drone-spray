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

substance = 500
work_flag = False


def start_spraying():
    proceed_to_deliver(uuid4().__str__(), {
            "deliver_to": "sprayer",
            "operation": "turn_on",
        })
    
def stop_spraying():
    proceed_to_deliver(uuid4().__str__(), {
            "deliver_to": "sprayer",
            "operation": "turn_off",
        })


def handle_event(id, details_str):
    global work_flag
    """ Обработчик входящих в модуль задач. """
    details = json.loads(details_str)

    source: str = details.get("source")
    deliver_to: str = details.get("deliver_to")
    operation: str = details.get("operation")
    if operation == "turn_on":
        work_flag = True
        start_spraying()
    
    if operation == "turn_off":
        work_flag = False
        stop_spraying()


    print(f"[info] handling event {id}, "
          f"{source}->{deliver_to}: {operation}")
    

def consumer_job(args, config):
    consumer = Consumer(config)
    global work_flag
    global substance
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
            if work_flag:
                substance = substance - 0.5
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