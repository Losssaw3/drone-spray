import os
import json
import threading

from confluent_kafka import Consumer, OFFSET_BEGINNING

from .polices import check_operation
from .producer import proceed_to_deliver


MODULE_NAME = os.getenv('MODULE_NAME')


def handle_event(id, details_str):
    """
    Processes incoming events and checks policies before delivering.
    
    Args:
        id (str): Event ID.
        details_str (str): JSON string containing event details.
    """
    details = json.loads(details_str)

    print(f"[info] handling event {id}, " \
          f"{details['source']}->{details['deliver_to']}: " \
          f"{details['operation']}")

    if check_operation(id, details):
        return proceed_to_deliver(id, details)

    print(f"[error] !!!! policies check failed, delivery unauthorized !!! " \
          f"id: {id}, {details['source']}->{details['deliver_to']}: " \
          f"{details['operation']}")
    print(f"[error] suspicious event details: {details}")
    

    


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
                id = msg.key().decode('utf-8')
                details_str = msg.value().decode('utf-8')
                handle_event(id, details_str)

                # except Exception as e:
                #     print(f"[error] Malformed event received from " \
                #           f"topic {topic}: {msg.value()}, {e}")
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
    print(f'{MODULE_NAME}_consumer started')
    threading.Thread(target=lambda: consumer_job(args, config)).start()