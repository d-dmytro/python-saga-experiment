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

class Payment:
    def __init__(self, id: str, order_id: str, status: str, color: str) -> None:
        self.id = id
        self.order_id = order_id
        self.status = status
        self.color = color

def print_payment(payment: Payment):
    print("Payment", payment.id, "for order", colored(str(payment.order_id), payment.color), "-", payment.status)

def create_order_created_handler(publisher: Publisher, payments: dict[str, Payment], ev_should_fail: Event):
    def order_created_handler(body: bytes):
        # create payment
        order = json.loads(body)
        payment = Payment(generate_id(), order["id"], "pending", order["color"])
        payments[payment.id] = payment

        if (not ev_should_fail.is_set()):
            payment.status = "completed"
            publisher.publish("bookings.payment-created", {
                "id": payment.id,
                "order_id": payment.order_id,
                "color": payment.color,
            })
        else:
            payment.status = "failed"
            publisher.publish("bookings.payment-failed", {
                "id": payment.id,
                "order_id": payment.order_id,
                "color": payment.color,
            })
        print_payment(payment)
    return order_created_handler

def create_booking_failed_handler(publisher: Publisher, payments: dict[str, Payment]):
    def booking_failed_handler(body: bytes):
        # cancel payment
        booking = json.loads(body)
        if (not booking["payment_id"] in payments):
            return
        payment = payments[booking["payment_id"]]
        payment.status = "cancelled"
        print_payment(payment)
    return booking_failed_handler

def main():
    init_colorama(autoreset=True)

    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument("-f", "--fail", action="store_true", help="fail payments")
    args = arg_parser.parse_args()
    fail: bool = args.fail

    ev_should_fail = Event()

    if (fail):
        ev_should_fail.set()
        print(colored("[x] Fail payments enabled", "RED"))

    connection = BlockingConnection(ConnectionParameters(host="localhost"))
    channel = connection.channel()
    initialize_messaging(channel)
    channel.close()
    connection.close()

    payments: dict[str, Payment] = {}

    ev_stopping = Event()

    publisher = Publisher(ev_stopping)
    publisher.start()

    order_created_handler = create_order_created_handler(publisher, payments, ev_should_fail)
    booking_failed_handler = create_booking_failed_handler(publisher, payments)

    order_created_thread = create_subscription_thread(
        queue_name="payments-order-created",
        callback=order_created_handler,
        ev_stopping=ev_stopping,
    )

    booking_failed_thread = create_subscription_thread(
        queue_name="payments-booking-failed",
        callback=booking_failed_handler,
        ev_stopping=ev_stopping,
    )

    def exit_signal_handler(signum, frame):
        print("Exiting...")
        ev_stopping.set()

    signal.signal(signal.SIGINT, exit_signal_handler)

    booking_failed_thread.join()
    order_created_thread.join()
    publisher.join()

main()
