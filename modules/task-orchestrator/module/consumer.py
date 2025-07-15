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

forward_route = []
spray_route = []
backward_route = []

def set_mission(mission):
    """
    Sets the mission details including forward, spray, and backward routes.
    Sends the mission details to the movement-calculation module.
    
    Args:
        mission (dict): Mission details containing routes.
    """
    global forward_route,spray_route,backward_route
    forward_route = mission.get("forward_route")
    spray_route = mission.get("spray")
    backward_route = mission.get("backward_route")
    proceed_to_deliver(uuid4().__str__(), {
            "deliver_to": "movement-calculation",
            "operation": "set_mission",
            "mission": mission
        })

def handle_event(id, details_str):
    """
    Handles incoming events and processes operations like setting missions.
    
    Args:
        id (str): Event ID.
        details_str (str): JSON string containing event details.
    """
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
    """
    Starts the consumer job to listen for incoming Kafka messages.
    
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
    Initializes the consumer job in a separate thread.
    
    Args:
        args: Command-line arguments.
        config (dict): Kafka consumer configuration.
    """
    print(f"{MODULE_NAME}_consumer started")
    threading.Thread(target=lambda: consumer_job(args, config)).start()