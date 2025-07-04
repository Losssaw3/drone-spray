import time
import threading
import random
import os
import json
import math

from uuid import uuid4
from time import sleep
from confluent_kafka import Consumer, OFFSET_BEGINNING

current_azimuth = 0
current_speed = 3.0

FLIGHT_STATUS_PATH = "/shared/flight_status"
COORDS = "/shared/coords"
MODULE_NAME = os.getenv("MODULE_NAME")

def calculate_new_position(x, y, azimuth, speed):
    """
    Вычисляет новые координаты после движения по азимуту
    
    Параметры:
        x, y - текущие координаты (в метрах)
        azimuth - азимут в градусах (0-360°, где 0° - север)
        speed - скорость (метры в секунду
    """
    
    azimuth_rad = math.radians(azimuth)
    dx = speed * math.sin(azimuth_rad)
    dy = speed * math.cos(azimuth_rad)
    new_x = x + dx
    new_y = y + dy
    print(f"nex_x = {new_x} , new_y = {new_y} , old_x = {x} , old_y = {y}")
    return [new_x, new_y]

def report_move():
    global current_azimuth
    while True:
        with open(FLIGHT_STATUS_PATH, 'r') as file:
            content = file.read().strip()
        
        if content == "1":
            with open(COORDS, 'r') as file:
                data = file.read().strip()
            values = [float(x.strip()) for x in data.split(',')]
            x, y, z = values[0], values[1], values[2]
            new_x, new_y = calculate_new_position(x, y, current_azimuth, current_speed)

            values[0] = new_x
            values[1] = new_y

            new_data = ', '.join([str(v) for v in values])
            with open(COORDS, 'w') as file:
                file.write(new_data)
            
            sleep(0.5)
        else:
            sleep(0.5)

def move(details):
    global current_azimuth, current_speed
    current_azimuth = details.get("azimuth")
    print(f"moving on course {current_azimuth} with speed {current_speed}")

def handle_event(id, details_str):
    """ Обработчик входящих в модуль задач. """
    details = json.loads(details_str)

    source: str = details.get("source")
    deliver_to: str = details.get("deliver_to")
    operation: str = details.get("operation")
    if operation == "move":
        move(details)
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
    threading.Thread(target=report_move).start()