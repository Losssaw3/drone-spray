import time
import threading
import random
import os
import json

from uuid import uuid4
from time import sleep
from .producer import proceed_to_deliver
from confluent_kafka import Consumer, OFFSET_BEGINNING

current_coords_gps = [0.0 , 0.0]
current_coords_ins = [0.0 , 0.0]
coords = [0.0 , 0.0]
MODULE_NAME = os.getenv("MODULE_NAME")
INIT_PATH: str = "/shared/init"
FLIGHT_STATUS_PATH: str = "/shared/flight_status"

def set_ins_coords(details):
    global current_coords_ins
    current_coords_ins = details.get("coords")

def set_gps_coords(details):
    global current_coords_gps
    current_coords_gps = details.get("coords")

def read_init() -> bool:
    with open(INIT_PATH, "r") as file:
        status = file.read()

    return status == "1"

def read_finish() -> bool:
    with open(FLIGHT_STATUS_PATH, "r") as file:
        status = file.read()

    return status == "2"

def complex():
    global coords , current_coords_gps , current_coords_ins
    while True:
        if read_init():
            coords[0] = (current_coords_gps[0] + current_coords_ins[0]) / 2
            coords[1] = (current_coords_gps[1] + current_coords_ins[1]) / 2
            proceed_to_deliver(uuid4().__str__(), {
                        "deliver_to": "limiter",
                        "operation": "current_coords",
                        "coords": coords
                    })
            proceed_to_deliver(uuid4().__str__(), {
                        "deliver_to": "drone-status-control",
                        "operation": "current_coords",
                        "coords": coords
                    })
        if read_finish():
            break
        sleep(2)

def handle_event(id, details_str):
    global work_flag
    """ Обработчик входящих в модуль задач. """
    details = json.loads(details_str)

    source: str = details.get("source")
    deliver_to: str = details.get("deliver_to")
    operation: str = details.get("operation")
    if operation == "current_coords_gps":
        set_gps_coords(details)
    
    if operation == "current_coords_ins":
        set_ins_coords(details)


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
    threading.Thread(target=complex).start()