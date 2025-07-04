import time
import threading
import random
import os
import json

from uuid import uuid4
from time import sleep
from confluent_kafka import Consumer, OFFSET_BEGINNING
from .producer import proceed_to_deliver

spray_point = []
current_point = []
work_flag = False
permission = False
MODULE_NAME = os.getenv("MODULE_NAME")

def float_equal_alt(x1: float, y1: float, x2: float, y2: float, epsilon: float = 1) -> bool:
    return (abs(x1 - x2) <= epsilon and abs(y1 - y2) <= epsilon)

def check():
    global work_flag , current_point , spray_point
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

    elif float_equal_alt(current_point[0] , current_point[1] , spray_point[0], spray_point[1]) and permission:
            proceed_to_deliver(uuid4().__str__(), {
                "deliver_to": "sprayer-control",
                "operation": "turn_on",
            })
            
    elif float_equal_alt(current_point[0] , current_point[1] , spray_point[0], spray_point[1]) and work_flag:
        work_flag = False
        proceed_to_deliver(uuid4().__str__(), {
            "deliver_to": "sprayer-control",
            "operation": "turn_off",
        })
    else:
        pass

def handle_event(id, details_str):
    global spray_point
    global permission
    global current_point
    """ Обработчик входящих в модуль задач. """
    details = json.loads(details_str)
    source: str = details.get("source")
    deliver_to: str = details.get("deliver_to")
    operation: str = details.get("operation")
    if operation == "set_mission":
        mission = details.get("mission")
        spray_point = mission.get("spray")[0]

    if operation == "current_coords" and spray_point:
        point = details.get("current_coords")
        current_point = point
        check(point)
    if operation == "photo":
        photo = details.get("photo")
        proceed_to_deliver(uuid4().__str__(), {
                "deliver_to": "message-sending",
                "operation": "photo",
                "photo": photo
            })
    if operation == "confirm_photo":
        permission = True
        check(current_point)
        proceed_to_deliver(uuid4().__str__(), {
                "deliver_to": "limiter",
                "operation": "resume",
            })

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