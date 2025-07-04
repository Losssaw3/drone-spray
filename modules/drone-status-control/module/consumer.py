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
current_height = 0
current_coordinates = [0.0 , 0.0]
battery_level = 0

def initialize():
    global current_coordinates, battery_level, current_height
    with open(INIT_PATH, 'w') as file:
            file.write('1')
    print("Drone turned on , checking module health...")
    current_coordinates = [float(randint(0, 100)), float(randint(0, 100))]
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
    global current_coordinates, battery_level, current_height
    while True:
        status = {"coords": current_coordinates,"height": current_height,"battery": battery_level}
        try:
            with open(INIT_PATH, 'r') as file:
                content = file.read().strip()
            if content == '1' and current_coordinates:
                proceed_to_deliver(uuid4().__str__(), {
                "deliver_to": "message-sending",
                "operation": "status",
                "status": status
            })
            elif content == '0':
                pass
        except FileNotFoundError:
            print(f"Файл не найден: {INIT_PATH}")
        except Exception as e:
            print(f"Произошла ошибка при чтении файла: {e}")
        sleep(10)

def handle_event(id, details_str):
    global current_coordinates, battery_level, current_height
    """ Обработчик входящих в модуль задач. """
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
    threading.Thread(target=send_status).start()