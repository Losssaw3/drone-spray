import time
import threading
import random
import os
import json

from uuid import uuid4
from time import sleep
from confluent_kafka import Consumer, OFFSET_BEGINNING
from .producer import proceed_to_deliver
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.serialization import load_pem_private_key, load_pem_public_key
from cryptography.hazmat.backends import default_backend

PRIVATE_KEY_PATH = "/shared/private_key.pem"
PUBLIC_KEY_PATH = "/shared/public_key.pem"

MODULE_NAME = os.getenv("MODULE_NAME")
consumers = ["limiter", "mission-control", "task-orchestrator"]
def turn_on():
    """
    Sends a command to turn on the drone.
    """
    proceed_to_deliver(uuid4().__str__(), {
            "deliver_to": "drone-status-control",
            "operation": "turn_on",
        })

def load_private_key(password: bytes = None):
    """
    Loads the private key from a PEM file.
    
    Args:
        password (bytes, optional): Password for the private key.
    
    Returns:
        Private key object.
    """
    with open(PRIVATE_KEY_PATH, "rb") as key_file:
        return load_pem_private_key(
            key_file.read(),
            password=password,
            backend=default_backend()
        )

def load_public_key():
    """
    Loads the public key from a PEM file.
    
    Returns:
        Public key object.
    """
    with open(PUBLIC_KEY_PATH, "rb") as key_file:
        return load_pem_public_key(
            key_file.read(),
            backend=default_backend()
        )

def sign_json(data: dict, private_key) -> str:
    """
    Signs JSON data and returns the signature in base64.
    
    Args:
        data (dict): JSON data to sign.
        private_key: Private key object.
    
    Returns:
        str: Base64-encoded signature.
    """
    # Конвертируем словарь в стабильный JSON-формат (с сортировкой ключей)
    json_str = json.dumps(data, sort_keys=True, ensure_ascii=False)
    
    # Подписываем текст (предварительно конвертировав в bytes)
    signature = private_key.sign(
        json_str.encode('utf-8'),
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.MAX_LENGTH
        ),
        hashes.SHA256()
    )
    
    # Возвращаем подпись в base64 для удобной передачи
    import base64
    return base64.b64encode(signature).decode('ascii')

def start_mission(details):
    """
    Sends the mission details to all consumers.
    
    Args:
        details (dict): Mission details.
    """
    global consumers
    mission = details.get("mission")
    for consumer in consumers:
        proceed_to_deliver(uuid4().__str__(), {
                "deliver_to": consumer,
                "operation": "set_mission",
                "mission": mission
            })

def sign_and_send(details):
    """
    Signs the status and sends it to the communication module.
    
    Args:
        details (dict): Status details.
    """
    status = details.get("status")
    signature = sign_json(status, load_private_key())
    details["signature"] = signature
    details["check"] = status
    print("signing message")
    proceed_to_deliver(uuid4().__str__(),details)

def verify(details):
    """
    Verifies the signature of a message.
    
    Args:
        details (dict): Message details containing signature and check data.
    
    Returns:
        bool: True if the signature is valid, False otherwise.
    """
    """ Проверяет подпись сообщения. """
    if "signature" in details and "check" in details:
        print("verifying signature")
        import base64

        signature_b64 = details.get("signature")
        check = details.get("check")

        signature = base64.b64decode(signature_b64)
        public_key = load_public_key()

        try:
            public_key.verify(
                signature,
                json.dumps(check, sort_keys=True, ensure_ascii=False).encode('utf-8'),
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            print("Signature is valid.")
            return True
        except Exception as e:
            print(f"Signature verification failed: {e}")
            return False
    return True


def handle_event(id, details_str):
    """
    Handles incoming events and processes operations like turning on the drone or starting a mission.
    
    Args:
        id (str): Event ID.
        details_str (str): JSON string containing event details.
    """
    details = json.loads(details_str)
    source: str = details.get("source")
    deliver_to = None
    operation = None

    if source == "communication":
        if verify(details):
            deliver_to: str = details.get("deliver_to")
            operation: str = details.get("operation")
            if operation == "turn_on":
                    turn_on()
            if operation == "start_mission":
                start_mission(details)
            if operation == "confirm_photo":
                details["deliver_to"] = "mission-control"
                proceed_to_deliver(uuid4().__str__(),details)
        else:
            print("Mission was rejected due invalid signature!")

    elif source == "message-sending": # status , photo
        deliver_to: str = details.get("deliver_to")
        operation: str = details.get("operation")
        details["deliver_to"] = "communication"
        sign_and_send(details)

    print(f"[info] handling event {id}, {source}->{deliver_to}: {operation}")


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