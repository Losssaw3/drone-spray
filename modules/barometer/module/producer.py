import os
import json
import threading
import multiprocessing

from uuid import uuid4
from time import sleep
from random import randint
from confluent_kafka import Producer


_requests_queue: multiprocessing.Queue = None
INIT_PATH: str = "/shared/flight_status"
MODULE_NAME: str = os.getenv("MODULE_NAME")
COORDS: str = "/shared/coords"
standart_height = 10.0

def read_init() -> bool:
    with open(INIT_PATH, "r") as file:
        status = file.read()

    return status == "1"

def read_finish() -> bool:
    with open(INIT_PATH, "r") as file:
        status = file.read()

    return status == "2"

def imitate_height():
    while True:
        height = standart_height + randint(-2 , 2)
        if read_init():
            with open(COORDS, 'r') as file:
                data = file.read().strip()
            values = [x.strip() for x in data.split(',')]
            values[2] = str(height)
            new_data = ', '.join(values)
            with open(COORDS, 'w') as file:
                file.write(new_data)
            proceed_to_deliver(uuid4().__str__(), {
                "deliver_to": "limiter",
                "operation": "current_height",
                "height": height
            })
            proceed_to_deliver(uuid4().__str__(), {
                "deliver_to": "drone-status-control",
                "operation": "current_height",
                "height": height
            })
        if read_finish():
            with open(COORDS, 'r') as file:
                data = file.read().strip()
            values = [x.strip() for x in data.split(',')]
            values[2] = 0
            new_data = ', '.join(values)
            with open(COORDS, 'w') as file:
                file.write(new_data)
            proceed_to_deliver(uuid4().__str__(), {
                "deliver_to": "limiter",
                "operation": "current_height",
                "height": 0
            })
            proceed_to_deliver(uuid4().__str__(), {
                "deliver_to": "drone-status-control",
                "operation": "current_height",
                "height": 0
            })
            break     
        sleep(randint(7, 10))



def proceed_to_deliver(id, details):
    details["id"] = id
    details["source"] = MODULE_NAME
    _requests_queue.put(details)


def producer_job(_, config, requests_queue: multiprocessing.Queue):
    producer = Producer(config)

    threading.Thread(target=imitate_height).start()

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