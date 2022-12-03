from orchestrated_saga.step import LocalStepDef, ParticipantStepDef, StepDef


class SagaState:
    def __init__(self, saga: "Saga"):
        self.saga = saga

    def set_state(self, state: type["SagaState"]):
        self.saga.state = state(self.saga)

    def set_status(self, status: str):
        if self.saga.status != status:
            self.saga.status = status
            self.set_state(states[status])


class Pending(SagaState):
    def tick(self):
        if self.saga.is_last_step():
            self.set_status("done")
        elif self.saga.is_participant_step():
            self.set_status("processing")
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
                self.set_status("done")
            else:
                self.saga.decrement_step()
        elif self.saga.is_last_step():
            self.set_status("done")
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


class Saga:
    command_key: str
    step_defs: list[StepDef]

    def __init__(self, id: str, data: dict, current_step=0, status="pending"):
        self.id = id
        self.data = data
        self.current_step = current_step
        self.status = status
        self.state = states[self.status](self)

    def get_current_step_def(self):
        return self.step_defs[self.current_step]

    def is_local_step(self):
        return isinstance(self.get_current_step_def(), LocalStepDef)

    def is_participant_step(self):
        return isinstance(self.get_current_step_def(), ParticipantStepDef)

    def increment_step(self):
        self.current_step += 1

    def decrement_step(self):
        self.current_step -= 1

    def is_last_step(self):
        return self.current_step == len(self.step_defs) - 1

    def is_first_step(self):
        return self.current_step == 0

    def tick(self):
        self.state.tick()

    def tick_command_response(self, ok: bool):
        self.state.tick_command_response(ok)
