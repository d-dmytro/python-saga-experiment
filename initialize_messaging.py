from pika.channel import Channel
from messaging import create_default_exchange, initialize_queue


def initialize_messaging(channel: Channel):
    create_default_exchange(channel)

    initialize_queue("orders-payment-failed", "bookings.payment-failed", channel)
    initialize_queue("orders-booking-created", "bookings.booking-created", channel)
    initialize_queue("orders-booking-failed", "bookings.booking-failed", channel)

    initialize_queue("payments-booking-failed", "bookings.booking-failed", channel)
    initialize_queue("payments-order-created", "bookings.order-created", channel)

    initialize_queue("bookings-payment-created", "bookings.payment-created", channel)

    initialize_queue(
        "payments_create_order_saga_commands", "create_order_saga.command", channel
    )
    initialize_queue(
        "bookings_create_order_saga_commands", "create_order_saga.command", channel
    )
    initialize_queue(
        "create_order_saga_command_responses",
        "create_order_saga.command_response",
        channel,
    )
