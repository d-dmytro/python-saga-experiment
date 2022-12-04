import json
from uuid import uuid4
from typing import Tuple
from orchestrated_saga.saga import Saga, SagaAttributes


class SagaDao:
    def __init__(
        self,
        connection: any,
        saga_classes: dict[str, type[Saga]],
    ):
        self.connection = connection
        self.saga_classes = saga_classes

    def get_saga_class(self, saga_name: str):
        if saga_name not in self.saga_classes:
            return Saga
        return self.saga_classes[saga_name]

    def save(self, saga: Saga):
        if not saga.get_id():
            return self.create(saga)
        return self.update(saga)

    def create(self, saga: Saga):
        saga.set_id(uuid4().hex)
        with self.connection.cursor() as curs:
            curs.execute(
                """
                INSERT INTO sagas (id, name, data, current_step, status)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    saga.get_id(),
                    saga.name,
                    json.dumps(saga.get_data()),
                    saga.get_current_step(),
                    saga.get_status(),
                ),
            )
        self.connection.commit()
        return saga

    def update(self, saga: Saga):
        with self.connection.cursor() as curs:
            curs.execute(
                """
                UPDATE sagas
                SET name = %s, data = %s, current_step = %s, status = %s
                WHERE id = %s
                """,
                (
                    saga.name,
                    json.dumps(saga.get_data()),
                    saga.get_current_step(),
                    saga.get_status(),
                    saga.get_id(),
                ),
            )
        self.connection.commit()
        return saga

    def get_one_by_id(self, id: str):
        with self.connection.cursor() as curs:
            curs.execute(
                """
                SELECT id, name, data, current_step, status
                FROM sagas
                WHERE id = %s
                """,
                (id,),
            )
            record: Tuple = curs.fetchone()

            if record == None:
                return None

            return self.get_saga_class(record[1])(
                SagaAttributes(
                    id=record[0],
                    data=json.loads(record[2]),
                    current_step=record[3],
                    status=record[4],
                )
            )
