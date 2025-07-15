import time
import threading
import random
import os
import json

from uuid import uuid4
from time import sleep
from confluent_kafka import Consumer, OFFSET_BEGINNING
from .producer import proceed_to_deliver

end_point = []
spray_point = []
current_point = []
spray_status = False
work_flag = False
permission = False
MODULE_NAME = os.getenv("MODULE_NAME")

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

def check():
    """
    Checks the current point against spray and end points to determine actions.
    """
    global work_flag , current_point , spray_point , spray_status
    if float_equal_alt(current_point[0] , current_point[1] , spray_point[0], spray_point[1]) and not work_flag:  
        work_flag = True
        proceed_to_deliver(uuid4().__str__(), {
            "deliver_to": "limiter",
            "operation": "pause",
        })

        proceed_to_deliver(uuid4().__str__(), {
            "deliver_to": "camera",
            "operation": "take_photo",
        })

    if float_equal_alt(current_point[0] , current_point[1] , end_point[0], end_point[1]) and spray_status:
        work_flag = False
        spray_status = False
        proceed_to_deliver(uuid4().__str__(), {
            "deliver_to": "sprayer-control",
            "operation": "turn_off",
        })

def start_spraying():
    """
    Starts the spraying operation.
    """
    global work_flag , current_point , spray_point , spray_status
    spray_status = True
    proceed_to_deliver(uuid4().__str__(), {
                "deliver_to": "sprayer-control",
                "operation": "turn_on",
        })
    proceed_to_deliver(uuid4().__str__(), {
                "deliver_to": "limiter",
                "operation": "resume",
        })
            
    


def handle_event(id, details_str):
    """
    Processes incoming events and executes operations such as setting missions or spraying.
    
    Args:
        id (str): Event ID.
        details_str (str): JSON string containing event details.
    """
    global spray_point, permission , current_point , end_point
    """ Обработчик входящих в модуль задач. """
    details = json.loads(details_str)
    source: str = details.get("source")
    deliver_to: str = details.get("deliver_to")
    operation: str = details.get("operation")
    if operation == "set_mission":
        mission = details.get("mission")
        spray_point = mission.get("spray")[0]
        end_point = mission.get("spray")[-1]

    if operation == "current_coords" and spray_point and end_point:
        point = details.get("coords")
        current_point = point
        print(point)
        check()
    if operation == "photo":
        photo = details.get("photo")
        proceed_to_deliver(uuid4().__str__(), {
                "deliver_to": "message-sending",
                "operation": "photo",
                "photo": photo
            })
    if operation == "confirm_photo":
        permission = True
        print("Даю команду на возобновление движения")
        start_spraying()
        

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