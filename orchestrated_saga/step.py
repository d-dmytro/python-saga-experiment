from typing import Callable
from orchestrated_saga.command import Command


class StepDef:
    pass


# Step that is handled locally (in app that runs saga).
class LocalStepDef(StepDef):
    def __init__(self, callback: Callable, compensation_callback: Callable):
        self.callback = callback
        self.compensation_callback = compensation_callback


# Step that requires a saga participant (another app)
# to complete a command.
class ParticipantStepDef(StepDef):
    def __init__(
        self,
        command_callback: Callable[[], Command],
        compensation_callback: Callable[[], Command],
    ):
        self.callback = command_callback
        self.compensation_callback = compensation_callback
