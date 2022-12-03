from uuid import uuid4
from messaging.publisher import Publisher
from orchestrated_saga.command import Command
from orchestrated_saga.command_response import CommandResponse
from orchestrated_saga.saga import Saga
from orchestrated_saga.saga_dao import SagaDao


class SagaManager:
    def __init__(self, saga_dao: SagaDao, publisher: Publisher):
        self.saga_dao = saga_dao
        self.publisher = publisher

    def start_saga(self, saga_class: type[Saga], data: dict):
        saga = saga_class(uuid4().hex, data)
        self.run_saga(saga)

    def run_saga_step(self, saga: Saga):
        is_compensation = saga.status == "compensation"
        step_def = saga.get_current_step_def()

        if saga.is_local_step():
            if is_compensation:
                step_def.compensation_callback(saga)
            else:
                step_def.callback(saga)

        if saga.is_participant_step():
            command: Command = (
                step_def.compensation_callback(saga)
                if is_compensation
                else step_def.callback(saga)
            )

            self.publisher.publish(
                "create_order_saga.command",
                {
                    "saga_id": command.saga_id,
                    "name": command.name,
                    "payload": command.payload,
                },
            )

    def run_saga(self, saga: Saga):
        self.run_saga_step(saga)
        saga.tick()
        saga = self.saga_dao.create(saga)

        if saga.status in ("pending", "compensation"):
            self.run_saga(saga)

    def handle_saga_command_response(self, response: CommandResponse):
        saga = self.saga_dao.get_one_by_id(response.saga_id)

        if saga == None:
            raise Exception(f"saga {response.saga_id} not found")

        saga.tick_command_response(response.ok)
        saga = self.saga_dao.update(saga)

        if saga.status in ("compensation", "pending"):
            self.run_saga(saga)
