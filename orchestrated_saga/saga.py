from typing import TypedDict
from orchestrated_saga.step import LocalStepDef, ParticipantStepDef, StepDef


class SagaState:
    def __init__(self, saga: "Saga"):
        self.saga = saga

    def set_state(self, state: type["SagaState"]):
        self.saga.state = state(self.saga)

    def set_status(self, status: str):
        if self.saga.get_status() != status:
            self.saga.set_status(status)
            self.set_state(states[status])


class Pending(SagaState):
    def tick(self):
        if self.saga.is_participant_step():
            self.set_status("processing")
        elif self.saga.is_last_step():
            self.set_status("done")
        elif self.saga.is_local_step():
            self.saga.increment_step()

    def tick_command_response(self, ok: bool):
        pass


class Processing(SagaState):
    def tick(self):
        if self.saga.is_last_step():
            self.set_status("done")
        else:
            self.saga.increment_step()
            self.set_status("pending")

    def tick_command_response(self, ok: bool):
        if ok:
            if self.saga.is_last_step():
                self.set_status("done")
            else:
                self.saga.increment_step()
                self.set_status("pending")
        else:
            if self.saga.is_first_step():
                self.set_status("failed")
            else:
                self.saga.decrement_step()
                self.set_status("compensation")


class Compensation(SagaState):
    def tick(self):
        if self.saga.is_local_step():
            if self.saga.is_first_step():
                self.set_status("failed")
            else:
                self.saga.decrement_step()
        elif self.saga.is_first_step():
            self.set_status("failed")
        else:
            self.set_status("compensating")

    def tick_command_response(self, ok: bool):
        pass


class Compensating(SagaState):
    def tick(self):
        pass

    def tick_command_response(self, ok: bool):
        if ok:
            if self.saga.is_first_step():
                self.set_status("done")
            else:
                self.saga.decrement_step()
                self.set_status("compensation")
        elif self.saga.is_first_step():
            self.set_status("failed")
        else:
            self.saga.decrement_step()
            self.set_status("compensation")


class Failed(SagaState):
    def tick(self):
        pass

    def tick_command_response(self, ok: bool):
        pass


class Done(SagaState):
    def tick(self):
        pass

    def tick_command_response(self, ok: bool):
        pass


states: dict[str, SagaState] = {
    "pending": Pending,
    "processing": Processing,
    "compensation": Compensation,
    "compensating": Compensating,
    "failed": Failed,
    "done": Done,
}


class SagaAttributes(TypedDict):
    id: str
    data: dict
    current_step: int
    status: str


class Saga:
    command_key: str
    step_defs: list[StepDef]

    def __init__(self, attributes: SagaAttributes):
        self.attributes = attributes
        self.state = states[self.get_status()](self)

    def get_current_step_def(self):
        return self.step_defs[self.get_current_step()]

    def is_local_step(self):
        return isinstance(self.get_current_step_def(), LocalStepDef)

    def is_participant_step(self):
        return isinstance(self.get_current_step_def(), ParticipantStepDef)

    def increment_step(self):
        self.set_current_step(self.get_current_step() + 1)

    def decrement_step(self):
        self.set_current_step(self.get_current_step() - 1)

    def is_last_step(self):
        return self.get_current_step() == len(self.step_defs) - 1

    def is_first_step(self):
        return self.get_current_step() == 0

    def tick(self):
        self.state.tick()

    def tick_command_response(self, ok: bool):
        self.state.tick_command_response(ok)

    def get_id(self):
        try:
            return self.attributes["id"]
        except:
            return ""

    def set_id(self, val: str):
        self.attributes["id"] = val

    def get_data(self):
        return self.attributes["data"]

    def set_data(self, val: dict):
        self.attributes["data"] = val

    def get_current_step(self):
        return self.attributes["current_step"]

    def set_current_step(self, val: int):
        self.attributes["current_step"] = val

    def get_status(self):
        return self.attributes["status"]

    def set_status(self, val: str):
        self.attributes["status"] = val
