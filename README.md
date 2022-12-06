# Saga Pattern Example

This is a basic example of implementation of the saga pattern.

Python is not my primary programming language, so don't judge too harsh.

The goal of this project was just to experiment with the saga pattern in async communication between microservices.

## Install

```
pipenv install
```

## Run

First we need to run rabbitmq:

```
docker compose up
```

Then, log in to the database and create the sagas table: `./orchestrated_saga/migrations/1_sagas_table.sql`.

Then, run three applications:

- Orders
- Payments
- Bookings

### To run the choreography saga:

1. Start bookings app: `pipenv run python3 bookings.py`.
2. Start payments app: `pipenv run python3 payments.py`.
3. Start orders app: `pipenv run python3 orders.py` and hit enter to create an order.

You can run bookings and payments with the `-f` (fail) flag to simulate failure and check the compensation flow of the saga.

### To run the orchestrated saga:

1. Start bookings app: `pipenv run python3 bookings_orchestrated.py`.
2. Start payments app: `pipenv run python3 payments_orchestrated.py`.
3. Start orders app: `pipenv run python3 orders_orchestrated.py` and hit enter to create an order.

You can set the `-f` flag for bookings and payments to simulate failure (similar to previous example).

## Test

```
pipenv run python3 -m nose2
```
