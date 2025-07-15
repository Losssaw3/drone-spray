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

standard_speed = 3.0
forward_route = []
spray_route = []
backward_route = []
flag = False

def calculate_azimuth(x1, y1, x2, y2):
    """
    Calculates the azimuth angle between two points.
    
    Args:
        x1 (float): x-coordinate of the first point.
        y1 (float): y-coordinate of the first point.
        x2 (float): x-coordinate of the second point.
        y2 (float): y-coordinate of the second point.
    
    Returns:
        float: Azimuth angle in degrees.
    """

    dx = x2 - x1
    dy = y2 - y1

    angle_rad = math.atan2(dx, dy)  # dx и dy местами — т.к. считаем от севера
    angle_deg = math.degrees(angle_rad)
    
    azimuth = (angle_deg + 360) % 360  # Приводим к диапазону [0, 360)
    return azimuth

def calculate_route(route):
    """
    Calculates the route for the drone's movement.
    
    Args:
        route (list): List of coordinates representing the route.
    
    Returns:
        list: Calculated route with azimuth, time, and speed details.
    """

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
            "time": time_to_travel,
            "speed": standard_speed
        })
    
    return calculated_route

def start_calculation():
    """
    Starts the calculation of forward, spray, and backward routes.
    """

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

def set_fake_mission():
    """
    Sets a fake mission with predefined routes and initiates route calculation.
    """

    global forward_route,spray_route,backward_route , flag
    forward_route = [[80.0, 80.0], [221, 43], [170, 159], [161, 158], [207, 206]]
    spray_route = [[104,98], [207, 221], [222, 221], [222, 206]]
    backward_route = [[207, 206], [161, 158], [170, 159], [191, 143], [80.0, 80.0]]
    flag = True
    start_calculation()

def set_mission(details):
    """
    Sets the mission details and initiates route calculation.
    
    Args:
        details (dict): Mission details containing routes.
    """

    global forward_route,spray_route,backward_route
    forward_route = details.get("mission").get("forward_route")
    spray_route = details.get("mission").get("spray")
    backward_route = details.get("mission").get("backward_route")
    start_calculation()

def handle_event(id, details_str):
    """
    Processes incoming events and executes operations such as setting missions.
    
    Args:
        id (str): Event ID.
        details_str (str): JSON string containing event details.
    """

    details = json.loads(details_str)

    source: str = details.get("source")
    deliver_to: str = details.get("deliver_to")
    operation: str = details.get("operation")
    if operation == "set_mission" and not flag:
        set_fake_mission()
    else:
        set_mission(details)


    print(f"[info] handling event {id}, "
          f"{source}->{deliver_to}: {operation}")
    

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
    """
    Starts the consumer job in a separate thread.
    
    Args:
        args: Command-line arguments.
        config (dict): Kafka consumer configuration.
    """

    print(f"{MODULE_NAME}_consumer started")
    threading.Thread(target=lambda: consumer_job(args, config)).start()