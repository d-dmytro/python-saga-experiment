import json
from threading import Event, Thread
from pika.adapters.blocking_connection import BlockingConnection
from pika.connection import ConnectionParameters

class Publisher(Thread):
    def __init__(self, ev_stopping: Event) -> None:
        Thread.__init__(self, daemon=True)
        self.ev_stopping = ev_stopping
        self.connection = BlockingConnection(ConnectionParameters(host="localhost", heartbeat=10, blocked_connection_timeout=10))
        self.channel = self.connection.channel()

    def run(self):
        while True:
            self.connection.process_data_events(time_limit=1)

            if (self.ev_stopping.is_set()):
                break

        if self.connection.is_open:
            self.connection.close()

    def _publish(self, key: str, payload: dict):
        self.channel.basic_publish(
            exchange="mini-booking",
            body=json.dumps(payload),
            routing_key=key,
        )

    def publish(self, key: str, payload: dict):
        self.connection.add_callback_threadsafe(lambda: self._publish(key, payload))
