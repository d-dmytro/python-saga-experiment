import json
import signal
from threading import Event
from colorama import init as init_colorama
from pika.adapters.blocking_connection import BlockingConnection
from pika.connection import ConnectionParameters
from initialize_messaging import initialize_messaging
from messaging import Publisher, create_subscription_thread
from utils import generate_id, get_random_color, colored

init_colorama(autoreset=True)

class Order:
    def __init__(self, id: str, status = "pending") -> None:
        self.id = id
        self.status = status
        self.color = get_random_color()

def print_order(order: Order):
    print("Order", colored(str(order.id), order.color), "-", order.status)

orders: dict[str, Order] = {}

def create_booking_created_handler(publisher: Publisher):
    def booking_created_handler(body: bytes):
        # complete order
        booking = json.loads(body)
        if (not booking["order_id"] in orders):
            return
        order = orders[booking["order_id"]]
        order.status = "completed"
        print_order(order)
    return booking_created_handler

def create_booking_failed_handler(publisher: Publisher):
    def booking_failed_handler(body: bytes):
        # fail order
        booking = json.loads(body)
        if (not booking["order_id"] in orders):
            return
        order = orders[booking["order_id"]]
        order.status = "booking_failed"
        print_order(order)
    return booking_failed_handler

def create_payment_failed_handler(publisher: Publisher):
    def payment_failed_handler(body: bytes):
        # fail order
        payment = json.loads(body)
        print(payment)
        if (not payment["order_id"] in orders):
            return
        order = orders[payment["order_id"]]
        order.status = "payment_failed"
        print_order(order)
    return payment_failed_handler

def main():
    connection = BlockingConnection(ConnectionParameters(host="localhost"))
    channel = connection.channel()
    initialize_messaging(channel)
    channel.close()
    connection.close()

    ev_stopping = Event()

    publisher = Publisher(ev_stopping)
    publisher.start()

    booking_created_handler = create_booking_created_handler(publisher)
    booking_failed_handler = create_booking_failed_handler(publisher)
    payment_failed_handler = create_payment_failed_handler(publisher)

    payment_failed_thread = create_subscription_thread(
        queue_name="orders-payment-failed",
        callback=payment_failed_handler,
        ev_stopping=ev_stopping,
    )

    booking_created_thread = create_subscription_thread(
        queue_name="orders-booking-created",
        callback=booking_created_handler,
        ev_stopping=ev_stopping,
    )

    booking_failed_thread = create_subscription_thread(
        queue_name="orders-booking-failed",
        callback=booking_failed_handler,
        ev_stopping=ev_stopping,
    )

    def exit_signal_handler(signum, frame):
        print("Exiting...")
        ev_stopping.set()

    signal.signal(signal.SIGINT, exit_signal_handler)

    # Create an order
    order = Order(generate_id())
    orders[order.id] = order
    publisher.publish("bookings.order-created", {"id": order.id, "color": order.color})
    print_order(order)

    booking_created_thread.join()
    booking_failed_thread.join()
    payment_failed_thread.join()
    publisher.join()

main()
