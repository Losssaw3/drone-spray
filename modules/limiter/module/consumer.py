import time
import threading
import random
import os
import json
import math

from uuid import uuid4
from time import sleep
from confluent_kafka import Consumer, OFFSET_BEGINNING
from .producer import proceed_to_deliver

INIT_PATH = "/shared/init"
FLIGHT_STATUS_PATH = "/shared/flight_status"
MODULE_NAME = os.getenv("MODULE_NAME")

current_height = 0.0
current_coords = [0.0 , 0.0]

forward_route_valid = []
spray_route_valid = []
backward_route_valid = []

forward_route = []
spray_route = []
backward_route = []
current_index = 0

def set_mission(details):
    global forward_route_valid,spray_route_valid,backward_route_valid
    forward_route_valid = details.get("mission").get("forward_route")
    spray_route_valid = details.get("mission").get("spray")
    backward_route_valid = details.get("mission").get("backward_route")

#######################################
def set_routes(details):
    """ Устанавливает маршруты для движения дрона. """
    global forward_route, spray_route, backward_route

    forward_route = details.get("mission").get("forward_route")
    spray_route = details.get("mission").get("spray")
    backward_route = details.get("mission").get("backward_route")
    azimuth = forward_route[current_index].get("azimuth")
    time = forward_route[current_index].get("time")
    proceed_to_deliver(uuid4().__str__(), {
                "deliver_to": "servo",
                "operation": "move",
                "azimuth": azimuth,
                "time": time
            })
    file_path = FLIGHT_STATUS_PATH
    with open(file_path, 'w') as file:
        file.write("1")

def float_equal_alt(x1: float, y1: float, x2: float, y2: float, epsilon: float = 1) -> bool:
    return (abs(x1 - x2) <= epsilon and abs(y1 - y2) <= epsilon)

def control_servos():
    global forward_route, spray_route, backward_route, current_index
    while True:
        with open(FLIGHT_STATUS_PATH, 'r') as file:
            content = file.read().strip()
        if content != "1":
           sleep(2) 
        elif content == "1" and float_equal_alt(current_coords[0] , current_coords[1] , forward_route[current_index].get("end")[0], forward_route[current_index].get("end")[1]):
            azimuth = forward_route[current_index + 1].get("azimuth")
            time = forward_route[current_index + 1].get("time")
            speed = forward_route[current_index + 1].get("speed")
            proceed_to_deliver(uuid4().__str__(), {
                "deliver_to": "servo",
                "operation": "move",
                "azimuth": azimuth,
                "time": time,
                "speed": speed
            })
            # current_index += 1
            # if current_index == len(fo)
            # sleep(2)
            # continue


def handle_event(id, details_str):
    """ Обработчик входящих в модуль задач. """
    global current_height , current_coords
    details = json.loads(details_str)
    source: str = details.get("source")
    deliver_to: str = details.get("deliver_to")
    operation: str = details.get("operation")
    if operation == "set_routes":
        set_routes(details)
    if operation == "set_mission":
        set_mission(details)

    if operation == "current_height":
        current_height = details.get("height")

    if operation == "current_coords":
        current_coords = details.get("coords")

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
    threading.Thread(target=control_servos).start()