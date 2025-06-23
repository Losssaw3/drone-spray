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


MODULE_NAME = os.getenv("MODULE_NAME")

standard_speed = 1.0
forward_route = []
spray_route = []
backward_route = []

def calculate_azimuth(x1, y1, x2, y2):

    dx = x2 - x1
    dy = y2 - y1

    angle_rad = math.atan2(dx, dy)  # dx и dy местами — т.к. считаем от севера
    angle_deg = math.degrees(angle_rad)
    
    azimuth = (angle_deg + 360) % 360  # Приводим к диапазону [0, 360)
    return azimuth

def calculate_route(route):
    """ Рассчитывает маршрут для движения дрона. """
    if not route:
        return []

    calculated_route = []
    for i in range(len(route) - 1):
        x1, y1 = route[i][0], route[i][1]
        x2, y2 = route[i + 1][0], route[i + 1][1]
        azimuth = calculate_azimuth(x1, y1, x2, y2)
        distance = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
        time_to_travel = distance / standard_speed
        calculated_route.append({
            "start": [x1, y1],
            "end":[x2, y2],
            "azimuth": azimuth,
            "time": time_to_travel
        })
    
    return calculated_route

def start_calculation():
    global forward_route, spray_route, backward_route
    forward_route = calculate_route(forward_route)
    spray_route = calculate_route(spray_route)
    backward_route = calculate_route(backward_route)
    proceed_to_deliver(uuid4().__str__(), {
        "deliver_to": "limiter",
        "operation": "set_routes",
        "mission": {
            "forward_route": forward_route,
            "spray": spray_route,
            "backward_route": backward_route
        }
    })
    print(f"[info] Mission set with forward route: {forward_route}, "
          f"spray route: {spray_route}, "
          f"backward route: {backward_route}")

def set_mission(mission):
    global forward_route,spray_route,backward_route
    forward_route = mission.get("forward_route")
    spray_route = mission.get("spray")
    backward_route = mission.get("backward_route")
    start_calculation()


def handle_event(id, details_str):
    """ Обработчик входящих в модуль задач. """
    details = json.loads(details_str)

    source: str = details.get("source")
    deliver_to: str = details.get("deliver_to")
    operation: str = details.get("operation")
    if operation == "set_mission":
        mission = details.get("mission")
        set_mission(mission)


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