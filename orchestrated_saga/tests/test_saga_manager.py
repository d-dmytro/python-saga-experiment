from typing import TypedDict
import unittest
from unittest.mock import Mock
from orchestrated_saga.command import Command
from orchestrated_saga.command_response import CommandResponse
from orchestrated_saga.saga import Saga, SagaAttributes
from orchestrated_saga.saga_manager import SagaManager
from orchestrated_saga.step_builder import StepBuilder


def step_one_action(saga: Saga):
    pass


def step_one_compensation(saga: Saga):
    pass


def step_two_command(saga: Saga):
    return Command("create_something", saga.get_id(), {})


def step_two_compensation(saga: Saga):
    return Command("cancel_something", saga.get_id(), {})


class MockedSaga(Saga):
    command_key = "mocked_saga"
    step_defs = [
        StepBuilder()
        .withAction(step_one_action)
        .withCompensation(step_one_compensation)
        .build(),
        StepBuilder()
        .withCommand(step_two_command)
        .withCompensation(step_two_compensation)
        .build(),
    ]
    name = "MockedSaga"


class TestSagaManager(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mocked_saga_dao = Mock()
        cls.mocked_publisher = Mock()

    def setUp(self):
        self.addCleanup(self.resetMocks)

    def resetMocks(self):
        self.mocked_saga_dao.reset_mock()
        self.mocked_publisher.reset_mock()

    def run_saga_test(self, success: bool):
        saga_manager = SagaManager(self.mocked_saga_dao, self.mocked_publisher)
        self.mocked_saga_dao.save.side_effect = lambda saga: saga

        saga_manager.start_saga(MockedSaga, {})

        self.mocked_saga_dao.save.assert_called()
        actual_saga = self.mocked_saga_dao.save.call_args.args[0]
        self.assertEqual(actual_saga.get_current_step(), 1)
        self.assertEqual(actual_saga.get_status(), "processing")

        self.mocked_saga_dao.get_one_by_id.side_effect = lambda _: actual_saga
        command_response = CommandResponse(
            MockedSaga.name, saga_id=actual_saga.get_id(), ok=success
        )
        saga_manager.handle_saga_command_response(command_response)
        actual_saga = self.mocked_saga_dao.save.call_args.args[0]
        self.assertEqual(actual_saga.get_current_step(), 1 if success else 0)
        self.assertEqual(actual_saga.get_status(), "done" if success else "failed")

    def test_success_flow(self):
        self.run_saga_test(True)

    def test_failure_flow(self):
        self.run_saga_test(False)


if __name__ == "__main__":
    unittest.main()
