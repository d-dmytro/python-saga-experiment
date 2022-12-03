from typing import Callable
from orchestrated_saga.command import Command
from orchestrated_saga.step import LocalStepDef, ParticipantStepDef


class StepBuilder:
    def __init__(self) -> None:
        self.commandCallback: Callable = None
        self.actionCallback: Callable = None
        self.compensationCallback: Callable = None

    def withCommand(self, command: Command):
        self.commandCallback = command
        return self

    def withAction(self, actionCallback: Callable):
        self.actionCallback = actionCallback
        return self

    def withCompensation(self, func: Callable):
        self.compensationCallback = func
        return self

    def build(self):
        if self.actionCallback:
            return LocalStepDef(self.actionCallback, self.compensationCallback)

        return ParticipantStepDef(self.commandCallback, self.compensationCallback)
