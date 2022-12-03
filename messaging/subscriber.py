from typing import Callable
from threading import Event, Thread
from pika.adapters.blocking_connection import BlockingConnection
from pika.connection import ConnectionParameters
from pika.exceptions import AMQPConnectionError


def run_subscription(
    queue_name: str, callback: Callable[[bytes], None], ev_stopping: Event
):
    while True:
        try:
            connection = BlockingConnection(
                ConnectionParameters(
                    host="localhost", heartbeat=10, blocked_connection_timeout=10
                )
            )
            channel = connection.channel()

            for method_frame, properties, body in channel.consume(
                queue=queue_name, inactivity_timeout=1
            ):
                if ev_stopping.is_set():
                    break

                if method_frame == None:
                    continue

                try:
                    callback(body, method_frame.routing_key)
                    channel.basic_ack(method_frame.delivery_tag)
                except Exception as e:
                    print(
                        "failed to process a message with delivery tag %d"
                        % (method_frame.delivery_tag)
                    )
                    print("exception:", e)
                    # @TODO: remove this line
                    channel.basic_ack(method_frame.delivery_tag)
                    continue

            if channel.is_open:
                channel.close()
            if connection.is_open:
                connection.close()

            break
        except AMQPConnectionError:
            print("disconnected from RabbitMQ, trying to reconnect...")
            continue


def create_subscription_thread(
    queue_name: str,
    callback: Callable[[bytes], None],
    ev_stopping: Event,
):
    thread = Thread(target=run_subscription, args=[queue_name, callback, ev_stopping])
    thread.start()
    return thread
