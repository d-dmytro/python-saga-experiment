import argparse
import json
import signal
from threading import Event
from colorama import init as init_colorama
from pika.adapters.blocking_connection import BlockingConnection
from pika.connection import ConnectionParameters
from initialize_messaging import initialize_messaging
from messaging import Publisher, create_subscription_thread
from utils import colored, generate_id

class Booking:
    def __init__(self, id: str, order_id: str, payment_id: str, status: str, color: str) -> None:
        self.id = id
        self.order_id = order_id
        self.payment_id = payment_id
        self.status = status
        self.color = color

def print_booking(booking: Booking):
    print("Booking", booking.id, "for order", colored(str(booking.order_id), booking.color), "-", booking.status)

def create_payment_created_handler(publisher: Publisher, bookings: dict[str, Booking], ev_should_fail: Event):
    def payment_created_handler(body: bytes):
        # create booking
        payment = json.loads(body)
        booking = Booking(generate_id(), payment["order_id"], payment["id"], "pending", payment["color"])
        bookings[booking.id] = booking

        if (not ev_should_fail.is_set()):
            booking.status = "completed"
            publisher.publish("bookings.booking-created", {
                "id": booking.id,
                "order_id": booking.order_id,
                "payment_id": booking.payment_id,
            })
        else:
            booking.status = "failed"
            publisher.publish("bookings.booking-failed", {
                "id": booking.id,
                "order_id": booking.order_id,
                "payment_id": booking.payment_id,
            })

        print_booking(booking)

    return payment_created_handler

def main():
    init_colorama(autoreset=True)

    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument("-f", "--fail", action="store_true")
    args = arg_parser.parse_args()
    fail: bool = args.fail

    bookings: dict[str, Booking] = {}

    ev_should_fail = Event()

    if (fail):
        ev_should_fail.set()
        print(colored("[x] Fail bookings enabled", "RED"))

    connection = BlockingConnection(ConnectionParameters(host="localhost"))
    channel = connection.channel()
    initialize_messaging(channel)
    channel.close()
    connection.close()

    ev_stopping = Event()

    publisher = Publisher(ev_stopping)
    publisher.start()

    payment_created_handler = create_payment_created_handler(publisher, bookings, ev_should_fail)

    payment_created_thread = create_subscription_thread(
        queue_name="bookings-payment-created",
        callback=payment_created_handler,
        ev_stopping=ev_stopping,
    )

    def exit_signal_handler(signum, frame):
        print("Exiting...")
        ev_stopping.set()

    signal.signal(signal.SIGINT, exit_signal_handler)

    payment_created_thread.join()
    publisher.join()

main()
