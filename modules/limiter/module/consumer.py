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

forward_flag = False
spray_flag = False
backward_flag = False

deviation = 4
speed = 3
current_height = 0.0
current_coords = [0.0 , 0.0]
current_target = []

forward_route_valid = []
spray_route_valid = []
backward_route_valid = []

forward_route = []
spray_route = []
backward_route = []
current_index = 0

def set_mission(details):
    """
    Sets the mission details including forward, spray, and backward routes.
    
    Args:
        details (dict): Mission details containing routes.
    """
    global forward_route_valid,spray_route_valid,backward_route_valid
    forward_route_valid = details.get("mission").get("forward_route")
    spray_route_valid = details.get("mission").get("spray")
    backward_route_valid = details.get("mission").get("backward_route")

def check_route(details):
    """
    Validates the provided routes against the stored valid routes.
    
    Args:
        details (dict): Mission details containing routes.
    
    Returns:
        bool: True if the routes are valid, False otherwise.
    """
    global forward_route_valid,spray_route_valid,backward_route_valid
    valid_flag = True
    forward_route = details.get("mission").get("forward_route")
    spray_route = details.get("mission").get("spray")
    backward_route = details.get("mission").get("backward_route")
    for i in range(len(forward_route_valid) - 1):
        if  forward_route_valid[i] != forward_route[i].get("start") or forward_route[-1].get("end") != forward_route_valid[-1]:
            valid_flag = False
    for i in range(len(spray_route_valid) - 1):
        if  spray_route_valid[i] != spray_route[i].get("start") or spray_route[-1].get("end") != spray_route_valid[-1]:
            valid_flag = False
    for i in range(len(backward_route_valid) - 1):
        if  backward_route_valid[i] != backward_route[i].get("start") or backward_route[-1].get("end") != backward_route_valid[-1]:
            valid_flag = False
    return valid_flag

def set_routes(details):
    """
    Sets the routes for the drone's movement and initiates the forward route.
    
    Args:
        details (dict): Mission details containing routes.
    """
    global forward_route, spray_route, backward_route, forward_flag , current_target
    if check_route(details):
        forward_route = details.get("mission").get("forward_route")
        spray_route = details.get("mission").get("spray")
        backward_route = details.get("mission").get("backward_route")
        
        azimuth = forward_route[current_index].get("azimuth")
        target = forward_route[current_index].get("end")
        proceed_to_deliver(uuid4().__str__(), {
                    "deliver_to": "servo",
                    "operation": "move",
                    "azimuth": azimuth,
                    "end": target
                })
        current_target = target
        forward_flag = True
        with open(FLIGHT_STATUS_PATH, 'w') as file:
            file.write("1")
    else:
        proceed_to_deliver(uuid4().__str__(), {
                    "deliver_to": "message-sending",
                    "operation": "status",
                    "status": "request new mission"
                })
        print("Mission was replaced can't start flight!")

def calculate_distance(x1, y1, x2, y2):
    """
    Calculates the distance between two points.
    
    Args:
        x1 (float): x-coordinate of the first point.
        y1 (float): y-coordinate of the first point.
        x2 (float): x-coordinate of the second point.
        y2 (float): y-coordinate of the second point.
    
    Returns:
        float: Distance between the two points.
    """
    return math.sqrt((x2 - x1)**2 + (y2 - y1)**2)

def float_equal_alt(x1: float, y1: float, x2: float, y2: float, epsilon: float = 5) -> bool:
    """
    Checks if two points are approximately equal within a given epsilon.
    
    Args:
        x1 (float): x-coordinate of the first point.
        y1 (float): y-coordinate of the first point.
        x2 (float): x-coordinate of the second point.
        y2 (float): y-coordinate of the second point.
        epsilon (float): Tolerance for equality.
    
    Returns:
        bool: True if the points are approximately equal, False otherwise.
    """
    return (abs(x1 - x2) <= epsilon and abs(y1 - y2) <= epsilon)

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

    angle_rad = math.atan2(dx, dy)
    angle_deg = math.degrees(angle_rad)
    
    azimuth = (angle_deg + 360) % 360
    return azimuth

def control_servos():
    """
    Monitors the drone's movement and adjusts its azimuth and speed if deviation is detected.
    """
    global current_coords , current_target , deviation , speed
    while True:
        if current_coords and current_target:
            _current_target = current_target
            prev_distance = calculate_distance(current_coords[0] , current_coords[1] , _current_target[0] , _current_target[1])
            sleep(3)
            new_distance = calculate_distance(current_coords[0] , current_coords[1] , _current_target[0] , _current_target[1])
            if new_distance > prev_distance and _current_target == current_target:
                print("Deviation detected")
                azimuth = calculate_azimuth(current_coords[0] , current_coords[1] , _current_target[0] , _current_target[1])
                proceed_to_deliver(uuid4().__str__(), {
                    "deliver_to": "servo",
                    "operation": "move",
                    "azimuth": azimuth,
                    "speed": speed,
                    "end": _current_target
                })

def start_forward():
    """
    Starts the forward route of the drone's mission.
    """
    global forward_route, spray_route, backward_route, current_index, forward_flag , current_target
    while True:
        with open(FLIGHT_STATUS_PATH, 'r') as file:
            content = file.read().strip()
        
        if content != "1":
           sleep(2)

        if forward_route and float_equal_alt(current_coords[0] , current_coords[1] , forward_route[-1].get("end")[0], forward_route[-1].get("end")[1]):
            forward_flag = False
            print("Окончание маршрута до места распрыскивания")
            break
        
        if content == "1" and forward_route and float_equal_alt(current_coords[0] , current_coords[1] , forward_route[current_index].get("end")[0], forward_route[current_index].get("end")[1]):
            azimuth = calculate_azimuth(
                  current_coords[0] , current_coords[1] ,
                  forward_route[current_index + 1].get("end")[0],
                  forward_route[current_index + 1].get("end")[1]
            )
            target = forward_route[current_index + 1].get("end")
            current_target = target
            speed = forward_route[current_index + 1].get("speed")
            proceed_to_deliver(uuid4().__str__(), {
                "deliver_to": "servo",
                "operation": "move",
                "azimuth": azimuth,
                "speed": speed,
                "end": target
            })
            current_index += 1

def pause_flight():
    """
    Pauses the drone's flight by setting its speed to zero.
    """
    global current_index
    current_index = 0
    proceed_to_deliver(uuid4().__str__(), {
                "deliver_to": "servo",
                "operation": "pause",
                "speed": 0
            })

def start_backward():
    """
    Starts the backward route of the drone's mission.
    """
    global backward_route, current_index , spray_flag, current_target
    while True:
        if backward_route and backward_flag and float_equal_alt(current_coords[0] , current_coords[1] , backward_route[-1].get("end")[0], backward_route[-1].get("end")[1]):
            print("Окончание маршрута")
            with open(FLIGHT_STATUS_PATH, 'w') as file:
                file.write("2")
            break
        
        if backward_route and backward_flag and float_equal_alt(current_coords[0] , current_coords[1] , backward_route[current_index].get("end")[0], backward_route[current_index].get("end")[1]):
            if current_index + 1 < len(backward_route):
                azimuth = calculate_azimuth(
                    current_coords[0], current_coords[1],
                    backward_route[current_index + 1].get("end")[0],
                    backward_route[current_index + 1].get("end")[1]
                )
                target = backward_route[current_index + 1].get("end")
                current_target = target
                speed = backward_route[current_index + 1].get("speed")
                proceed_to_deliver(uuid4().__str__(), {
                    "deliver_to": "servo",
                    "operation": "move",
                    "azimuth": azimuth,
                    "speed": speed,
                    "end": target
                })
                current_index += 1

def start_spraying():
    """
    Starts the spraying operation of the drone's mission.
    """
    global spray_route, current_index , spray_flag , backward_flag, current_target
    while True:
        if spray_route and spray_flag and not forward_flag and float_equal_alt(current_coords[0] , current_coords[1] , spray_route[-1].get("end")[0], spray_route[-1].get("end")[1]):
            spray_flag = False
            current_index = 0
            print("Окончание маршрута распрыскивания")
            azimuth = calculate_azimuth(current_coords[0] , current_coords[1] , backward_route[current_index].get("end")[0], backward_route[current_index].get("end")[1])
            target = backward_route[current_index].get("end")
            current_target = target
            speed = backward_route[current_index].get("speed")
            proceed_to_deliver(uuid4().__str__(), {
                "deliver_to": "servo",
                "operation": "move",
                "azimuth": azimuth,
                "speed": speed,
                "end": target
            })
            sleep(3)
            backward_flag = True
            break
        
        if spray_route and spray_flag and not forward_flag and float_equal_alt(current_coords[0] , current_coords[1] , spray_route[current_index].get("end")[0], spray_route[current_index].get("end")[1])and (current_index < len(spray_route)):
            if current_index + 1 < len(spray_route):
                azimuth = calculate_azimuth(
                    current_coords[0] , current_coords[1] ,
                    spray_route[current_index + 1].get("end")[0],
                    spray_route[current_index + 1].get("end")[1]
                )
                target = spray_route[current_index + 1].get("end")
                current_target = target
                speed = spray_route[current_index + 1].get("speed")
                proceed_to_deliver(uuid4().__str__(), {
                    "deliver_to": "servo",
                    "operation": "move",
                    "azimuth": azimuth,
                    "speed": speed,
                    "end": target
                })
                current_index += 1

def handle_event(id, details_str):
    """
    Processes incoming events and executes operations such as setting routes or pausing the flight.
    
    Args:
        id (str): Event ID.
        details_str (str): JSON string containing event details.
    """
    global current_height , current_coords , spray_flag , current_index , current_target
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

    if operation == "pause" and source == "mission-control":
        pause_flight()

    if operation == "resume" and source == "mission-control":
        spray_flag = True
        azimuth = calculate_azimuth(current_coords[0] , current_coords[1] , spray_route[current_index].get("end")[0], spray_route[current_index].get("end")[1])
        target = spray_route[current_index].get("end")
        current_target = target
        speed = spray_route[current_index].get("speed")
        proceed_to_deliver(uuid4().__str__(), {
                "deliver_to": "servo",
                "operation": "move",
                "azimuth": azimuth,
                "end": target,
                "speed": speed
            })

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
    Starts the consumer job and related threads.
    
    Args:
        args: Command-line arguments.
        config (dict): Kafka consumer configuration.
    """
    print(f"{MODULE_NAME}_consumer started")
    threading.Thread(target=lambda: consumer_job(args, config)).start()
    threading.Thread(target=start_forward).start()
    threading.Thread(target=start_spraying).start()
    threading.Thread(target=start_backward).start()
    threading.Thread(target=control_servos).start()