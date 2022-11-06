from pika.channel import Channel
from pika.spec import ExchangeType

def create_default_exchange(channel: Channel):
    channel.exchange_declare(
        exchange="mini-booking",
        exchange_type=ExchangeType.topic
    )

def initialize_queue(queue_name: str, key: str, channel: Channel):
    queue = channel.queue_declare(queue=queue_name, durable=True)
    channel.queue_bind(
        exchange="mini-booking",
        queue=queue.method.queue,
        routing_key=key,
    )
