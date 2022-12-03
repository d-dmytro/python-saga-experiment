from uuid import uuid4
from messaging.publisher import Publisher
from orchestrated_saga.command_response import CommandResponse
from orchestrated_saga.saga import Saga
from orchestrated_saga.saga_dao import SagaDao
from orchestrated_saga.step import LocalStepDef, ParticipantStepDef


class SagaManager:
    def __init__(self, saga_dao: SagaDao, publisher: Publisher):
        self.saga_dao = saga_dao
        self.publisher = publisher

    def start_saga(self, saga_class: type[Saga], data: dict):
        saga = saga_class(uuid4().hex, data)
        self.run_saga(saga)

    def run_saga(self, saga: Saga):
        step_def = saga.get_current_step_def()
        is_compensation = saga.status == "compensation"

        if isinstance(step_def, LocalStepDef):
            if is_compensation:
                step_def.compensation_callback(saga)
                if saga.is_first_step():
                    saga.status = "done"
                else:
                    saga.current_step -= 1
            else:
                step_def.callback(saga)
                if saga.is_last_step():
                    saga.status = "done"
                else:
                    saga.current_step += 1
                    saga.status = "pending"
        elif isinstance(step_def, ParticipantStepDef):
            if is_compensation:
                command = step_def.compensation_callback(saga)
                saga.status = "compensating"
            else:
                command = step_def.callback(saga)
                saga.status = "processing"

            self.publisher.publish(
                "create_order_saga.command",
                {
                    "saga_id": command.saga_id,
                    "name": command.name,
                    "payload": command.payload,
                },
            )
        else:
            raise Exception("Unexpected step definition")

        saga = self.saga_dao.create(saga)

        if saga.status in ("pending", "compensation"):
            # Current step is done,
            # let's process next step.
            self.run_saga(saga)

    def run_saga_alt(self, saga: Saga):
        step_def = saga.get_current_step_def()
        saga.tick()

    def handle_saga_command_response(self, response: CommandResponse):
        saga = self.saga_dao.get_one_by_id(response.saga_id)

        if saga == None:
            raise Exception(f"saga {response.saga_id} not found")

        if response.ok:
            # saga.tick()
            if saga.status == "compensating":
                if saga.is_first_step():
                    saga.status = "done"
                    self.saga_dao.update(saga)
                else:
                    saga.current_step -= 1
                    saga.status = "compensation"
                    saga = self.saga_dao.update(saga)
                    self.run_saga(saga)
            else:
                if saga.is_last_step():
                    saga.status = "done"
                    self.saga_dao.update(saga)
                else:
                    saga.current_step += 1
                    saga.status = "pending"
                    saga = self.saga_dao.update(saga)
                    self.run_saga(saga)
        else:
            if saga.is_first_step():
                saga.status = "failed"
                self.saga_dao.update(saga)
            else:
                saga.current_step -= 1
                saga.status = "compensation"
                saga = self.saga_dao.update(saga)
                self.run_saga(saga)
