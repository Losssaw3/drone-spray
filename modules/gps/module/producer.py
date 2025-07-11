import os
import json
import threading
import multiprocessing

from uuid import uuid4
from time import sleep
import random
from confluent_kafka import Producer


_requests_queue: multiprocessing.Queue = None
INIT_PATH: str = "/shared/init"
MODULE_NAME: str = os.getenv("MODULE_NAME")
COORDS: str = "/shared/coords"
FLIGHT_STATUS_PATH: str = "/shared/flight_status"


def read_init() -> bool:
    with open(INIT_PATH, "r") as file:
        status = file.read()

    return status == "1"

def read_finish() -> bool:
    with open(FLIGHT_STATUS_PATH, "r") as file:
        status = file.read()

    return status == "2"

def read_coords():
    while True:
        if read_init():
            with open(COORDS, 'r') as file:
                data = file.read().strip()
            deviation = random.uniform(-0.5, 0.5)
            values = [float(x.strip()) for x in data.split(',')]
            x, y, z = values[0], values[1], values[2]
            current_coords =[x + deviation , y + deviation]
            proceed_to_deliver(uuid4().__str__(), {
                "deliver_to": "complex",
                "operation": "current_coords_gps",
                "coords": current_coords
            })
        if read_finish():
            break   
        sleep(2)


def proceed_to_deliver(id, details):
    details["id"] = id
    details["source"] = MODULE_NAME
    _requests_queue.put(details)


def producer_job(_, config, requests_queue: multiprocessing.Queue):
    producer = Producer(config)

    threading.Thread(target=read_coords).start()

    def delivery_callback(err, msg):
        if err:
            print("[error] Message failed delivery: {}".format(err))

    topic = "monitor"
    while True:
        event_details = requests_queue.get()
        producer.produce(
            topic,
            json.dumps(event_details),
            event_details["id"],
            callback=delivery_callback
        )

        producer.poll(10000)
        producer.flush()


def start_producer(args, config, requests_queue):
    print(f"{MODULE_NAME}_producer started")

    global _requests_queue

    _requests_queue = requests_queue
    threading.Thread(
        target=lambda: producer_job(args, config, requests_queue)
    ).start()