import time
import threading
from random import randint
import os
import json

from uuid import uuid4
from time import sleep
from confluent_kafka import Consumer, OFFSET_BEGINNING
from .producer import proceed_to_deliver


MODULE_NAME = os.getenv("MODULE_NAME")
INIT_PATH: str = "/shared/init"
COORDS_PATH: str = "/shared/coords"
FLIGHT_STATUS_PATH: str = "/shared/flight_status"
current_height = 0
current_coordinates = [0.0 , 0.0]
battery_level = 0

def initialize():
    """
    Initializes the drone by setting its coordinates, height, and battery level.
    Sends the initial status to the message-sending module.
    """
    global current_coordinates, battery_level, current_height
    with open(INIT_PATH, 'w') as file:
            file.write('1')
    print("Drone turned on , checking module health...")
    current_coordinates = [80.0, 80.0]
    with open(COORDS_PATH, 'w') as file:
        file.write(f"{current_coordinates[0]} , {current_coordinates[1]} , {current_height}")
    battery_level = 100
    status = {"coords": current_coordinates,"height": current_height,"battery": battery_level}
    proceed_to_deliver(uuid4().__str__(), {
            "deliver_to": "message-sending",
            "operation": "status",
            "status": status
        })

def send_status():
    """
    Periodically sends the drone's status and coordinates to the message-sending and mission-control modules.
    """
    global current_coordinates, battery_level, current_height
    while True:
        status = {"coords": current_coordinates,"height": current_height,"battery": battery_level}
        try:
            with open(FLIGHT_STATUS_PATH, 'r') as file:
                flight_status = file.read().strip()
            if flight_status == "2":
                proceed_to_deliver(uuid4().__str__(), {
                "deliver_to": "message-sending",
                "operation": "flight-report",
                "status": status,
                "report": "flight ended"
            })
                break

            with open(INIT_PATH, 'r') as file:
                content = file.read().strip()
            if content == '1' and current_coordinates:
                proceed_to_deliver(uuid4().__str__(), {
                "deliver_to": "message-sending",
                "operation": "status",
                "status": status
            })
                proceed_to_deliver(uuid4().__str__(), {
                "deliver_to": "mission-control",
                "operation": "current_coords",
                "coords": current_coordinates
            })
            elif content == '0':
                sleep(1)
        except FileNotFoundError:
            print(f"Файл не найден: {INIT_PATH}")
        except Exception as e:
            print(f"Произошла ошибка при чтении файла: {e}")
        sleep(2)

def handle_event(id, details_str):
    """
    Handles incoming events and processes operations like turning on the drone or updating coordinates.
    
    Args:
        id (str): Event ID.
        details_str (str): JSON string containing event details.
    """
    global current_coordinates, battery_level, current_height
    details = json.loads(details_str)
    source: str = details.get("source")
    deliver_to: str = details.get("deliver_to")
    operation: str = details.get("operation")
    if operation == "turn_on":
        initialize()
    if operation == "current_coords":
        current_coordinates = details.get("coords")
    if operation == "current_height":
        current_height = details.get("height")
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
    Starts the consumer job and status reporting in separate threads.
    
    Args:
        args: Command-line arguments.
        config (dict): Kafka consumer configuration.
    """
    print(f"{MODULE_NAME}_consumer started")
    threading.Thread(target=lambda: consumer_job(args, config)).start()
    threading.Thread(target=send_status).start()