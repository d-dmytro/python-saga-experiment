import json
from typing import Tuple
from orchestrated_saga.saga import Saga


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

    def create(self, saga: Saga):
        with self.connection.cursor() as curs:
            curs.execute(
                """
                INSERT INTO sagas (id, name, data, current_step, status)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE
                SET
                    name = excluded.name,
                    data = excluded.data,
                    current_step = excluded.current_step,
                    status = excluded.status
                """,
                (
                    saga.id,
                    saga.name,
                    json.dumps(saga.data),
                    saga.current_step,
                    saga.status,
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
                    json.dumps(saga.data),
                    saga.current_step,
                    saga.status,
                    saga.id,
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
                record[0],
                json.loads(record[2]),
                record[3],
                record[4],
            )
