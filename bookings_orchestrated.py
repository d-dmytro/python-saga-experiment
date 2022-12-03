import argparse
import json
import signal
from threading import Event
from colorama import init as init_colorama
from pika.adapters.blocking_connection import BlockingConnection
from pika.connection import ConnectionParameters
from initialize_messaging import initialize_messaging
from messaging import Publisher, create_subscription_thread
from orchestrated_saga.command import Command
from orchestrated_saga.command_response import CommandResponse
from utils import colored, generate_id


class Booking:
    def __init__(self, id: str, order_id: str, status: str, color: str) -> None:
        self.id = id
        self.order_id = order_id
        self.status = status
        self.color = color


def print_booking(booking: Booking):
    print(
        "Booking",
        booking.id,
        "for order",
        colored(str(booking.order_id), booking.color),
        "-",
        booking.status,
    )


def handle_create_booking_command(
    command: Command,
    should_fail: bool,
    publisher: Publisher,
    bookings: dict[str, Booking],
):
    response = CommandResponse(command.name, command.saga_id, False)
    booking: Booking | None = None

    if not should_fail:
        booking = Booking(
            generate_id(), command.payload["id"], "completed", command.payload["color"]
        )
        bookings[booking.id] = booking
        response.ok = True

    publisher.publish(
        "create_order_saga.command_response",
        {"saga_id": response.saga_id, "name": response.name, "ok": response.ok},
    )

    if booking:
        print_booking(booking)
        return

    print(
        "Booking for order",
        colored(command.payload["id"], command.payload["color"]),
        "failed",
    )


def create_create_order_saga_handler(
    publisher: Publisher, bookings: dict[str, Booking], ev_should_fail: Event
):
    def create_order_saga_handler(body: bytes, _key: str):
        should_fail = ev_should_fail.is_set()
        command_body = json.loads(body)
        command = Command(
            command_body["name"], command_body["saga_id"], command_body["payload"]
        )

        if command.name == "create_booking":
            handle_create_booking_command(
                command,
                should_fail,
                publisher,
                bookings,
            )

    return create_order_saga_handler


def main():
    init_colorama(autoreset=True)

    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument("-f", "--fail", action="store_true", help="fail command")
    args = arg_parser.parse_args()
    fail: bool = args.fail

    ev_should_fail = Event()

    if fail:
        ev_should_fail.set()
        print(colored("[x] Fail command enabled", "RED"))

    connection = BlockingConnection(ConnectionParameters(host="localhost"))
    channel = connection.channel()
    initialize_messaging(channel)
    channel.close()
    connection.close()

    bookings: dict[str, Booking] = {}
    ev_stopping = Event()

    publisher = Publisher(ev_stopping)
    publisher.start()

    create_order_saga_handler = create_create_order_saga_handler(
        publisher, bookings, ev_should_fail
    )

    create_order_saga_handler_thread = create_subscription_thread(
        queue_name="bookings_create_order_saga_commands",
        callback=create_order_saga_handler,
        ev_stopping=ev_stopping,
    )

    def exit_signal_handler(signum, frame):
        print("Exiting...")
        ev_stopping.set()

    signal.signal(signal.SIGINT, exit_signal_handler)

    create_order_saga_handler_thread.join()
    publisher.join()


main()
