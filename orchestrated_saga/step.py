from typing import Callable
from orchestrated_saga.command import Command


class StepDef:
    pass


class LocalStepDef(StepDef):
    def __init__(self, callback: Callable, compensation_callback: Callable):
        self.callback = callback
        self.compensation_callback = compensation_callback


class ParticipantStepDef(StepDef):
    def __init__(
        self,
        command_callback: Callable[[], Command],
        compensation_callback: Callable[[], Command],
    ):
        self.callback = command_callback
        self.compensation_callback = compensation_callback
