import json
import signal
from threading import Event
from colorama import init as init_colorama
from pika.adapters.blocking_connection import BlockingConnection
from pika.connection import ConnectionParameters
import psycopg2
from initialize_messaging import initialize_messaging
from messaging import Publisher
from messaging.subscriber import create_subscription_thread
from orchestrated_saga.command import Command
from orchestrated_saga.command_response import CommandResponse
from orchestrated_saga.saga import Saga
from orchestrated_saga.saga_dao import SagaDao
from orchestrated_saga.saga_manager import SagaManager
from orchestrated_saga.step_builder import StepBuilder
from utils import generate_id, get_random_color, colored, ShutdownException


class Order:
    def __init__(self, id: str, status: str, color: str):
        self.id = id
        self.status = status
        self.color = color


orders: dict[str, Order] = {}


def print_order(order: Order):
    print("Order", colored(str(order.id), order.color), "-", order.status)


def create_command_response_handler(saga_manager: SagaManager):
    def command_response_handler(body: bytes, _key: str):
        response_body = json.loads(body)
        response = CommandResponse(
            response_body["name"], response_body["saga_id"], response_body["ok"]
        )
        saga_manager.handle_saga_command_response(response)

    return command_response_handler


class CreatePaymentCommand(Command):
    def __init__(self, saga_id: str, data: dict):
        super().__init__("create_payment", saga_id, data)


class CancelPaymentCommand(Command):
    def __init__(self, saga_id: str, data: dict):
        super().__init__("cancel_payment", saga_id, data)


class CreateBookingCommand(Command):
    def __init__(self, saga_id: str, data: dict):
        super().__init__("create_booking", saga_id, data)


def create_order(saga: Saga):
    order = Order(saga.get_data()["id"], "pending", saga.get_data()["color"])
    orders[order.id] = order
    print_order(order)


def cancel_order(saga: Saga):
    order = orders[saga.get_data()["id"]]
    order.status = "canceled"
    print_order(order)


def complete_order(saga: Saga):
    order = orders[saga.get_data()["id"]]
    order.status = "completed"
    print_order(order)


def create_payment(saga: Saga):
    return CreatePaymentCommand(saga.get_id(), saga.get_data())


def cancel_payment(saga: Saga):
    return CancelPaymentCommand(saga.get_id(), saga.get_data())


def create_booking(saga: Saga):
    return CreateBookingCommand(saga.get_id(), saga.get_data())


class CreateOrderSaga(Saga):
    command_key = "orders"
    step_defs = [
        StepBuilder().withAction(create_order).withCompensation(cancel_order).build(),
        StepBuilder()
        .withCommand(create_payment)
        .withCompensation(cancel_payment)
        .build(),
        StepBuilder().withCommand(create_booking).build(),
        StepBuilder().withAction(complete_order).build(),
    ]
    name = "CreateOrderSaga"


def main():
    init_colorama(autoreset=True)

    connection = BlockingConnection(ConnectionParameters(host="localhost"))
    channel = connection.channel()
    initialize_messaging(channel)
    channel.close()
    connection.close()

    ev_stopping = Event()

    publisher = Publisher(ev_stopping)
    publisher.start()

    connection = psycopg2.connect(
        "host=localhost port=5432 dbname=saga user=postgres password=postgres"
    )
    saga_dao = SagaDao(
        connection,
        {
            "CreateOrderSaga": CreateOrderSaga,
        },
    )
    saga_manager = SagaManager(saga_dao, publisher)

    command_response_handler = create_command_response_handler(saga_manager)

    command_response_thread = create_subscription_thread(
        queue_name="create_order_saga_command_responses",
        callback=command_response_handler,
        ev_stopping=ev_stopping,
    )

    def quit():
        print("Exiting...")
        ev_stopping.set()

    def exit_signal_handler(signum, frame):
        quit()
        raise ShutdownException()

    signal.signal(signal.SIGINT, exit_signal_handler)

    try:
        while True:
            command = input()

            if command not in {"", "create", "exit"}:
                print('Enter "create" or "exit" or just hit ENTER')
                continue

            if command == "exit":
                quit()
                break

            saga_manager.start_saga(
                CreateOrderSaga, {"id": generate_id(), "color": get_random_color()}
            )
    except ShutdownException:
        pass

    publisher.join()
    command_response_thread.join()


main()
