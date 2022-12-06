import unittest

from orchestrated_saga.saga import Saga, SagaAttributes
from orchestrated_saga.step import LocalStepDef, ParticipantStepDef, StepDef


def mock_participant_step_def():
    return ParticipantStepDef(lambda: None, lambda: None)


def mock_local_step_def():
    return LocalStepDef(lambda: None, lambda: None)


def mock_saga(saga_step_defs: list[StepDef], saga_attributes: SagaAttributes = {}):
    class MockedSaga(Saga):
        name = "MockedSaga"
        step_defs = saga_step_defs

    attributes = {"data": {}, "current_step": 0, "status": "pending"}
    attributes.update(saga_attributes)

    return MockedSaga(attributes)


class TestSaga(unittest.TestCase):
    def test_pending_to_processing(self):
        saga = mock_saga([mock_participant_step_def()])
        saga.tick()
        self.assertEqual(saga.get_status(), "processing")

    def test_pending_to_done(self):
        saga = mock_saga([mock_local_step_def()])
        saga.tick()
        self.assertEqual(saga.get_status(), "done")

    def test_pending_next_step(self):
        saga = mock_saga([mock_local_step_def(), mock_local_step_def()])
        saga.tick()
        self.assertEqual(saga.get_status(), "pending")
        self.assertEqual(saga.get_current_step(), 1)

    def test_processing_to_pending(self):
        saga = mock_saga(
            [mock_local_step_def(), mock_local_step_def()],
            {"status": "processing"},
        )
        saga.tick()
        self.assertEqual(saga.get_status(), "pending")
        self.assertEqual(saga.get_current_step(), 1)

    def test_processing_to_done(self):
        saga = mock_saga(
            [mock_local_step_def()],
            {"status": "processing"},
        )
        saga.tick()
        self.assertEqual(saga.get_status(), "done")

    def test_processing_to_pending_on_command_response(self):
        saga = mock_saga(
            [mock_local_step_def(), mock_local_step_def()],
            {"status": "processing"},
        )
        saga.tick_command_response(True)
        self.assertEqual(saga.get_status(), "pending")
        self.assertEqual(saga.get_current_step(), 1)

    def test_processing_to_done_on_command_response(self):
        saga = mock_saga(
            [mock_local_step_def()],
            {"status": "processing"},
        )
        saga.tick_command_response(True)
        self.assertEqual(saga.get_status(), "done")

    def test_processing_to_failed_on_command_response(self):
        saga = mock_saga(
            [],
            {"status": "processing"},
        )
        saga.tick_command_response(False)
        self.assertEqual(saga.get_status(), "failed")

    def test_processing_to_compensation_on_command_response(self):
        saga = mock_saga(
            [],
            {"status": "processing", "current_step": 1},
        )
        saga.tick_command_response(False)
        self.assertEqual(saga.get_status(), "compensation")

    def test_compensation_to_failed(self):
        saga = mock_saga(
            [mock_local_step_def()],
            {"status": "compensation"},
        )
        saga.tick()
        self.assertEqual(saga.get_status(), "failed")

    def test_compensation_to_decrement_step(self):
        saga = mock_saga(
            [mock_local_step_def(), mock_local_step_def()],
            {"status": "compensation", "current_step": 1},
        )
        saga.tick()
        self.assertEqual(saga.get_current_step(), 0)

    def test_compensation_to_failed(self):
        saga = mock_saga(
            [mock_participant_step_def()],
            {"status": "compensation"},
        )
        saga.tick()
        self.assertEqual(saga.get_status(), "failed")

    def test_compensation_to_compensating(self):
        saga = mock_saga(
            [mock_local_step_def(), mock_participant_step_def()],
            {"status": "compensation", "current_step": 1},
        )
        saga.tick()
        self.assertEqual(saga.get_status(), "compensating")

    def test_compensating_to_done_on_command_response(self):
        saga = mock_saga(
            [mock_participant_step_def()],
            {"status": "compensating"},
        )
        saga.tick_command_response(True)
        self.assertEqual(saga.get_status(), "done")

    def test_compensating_to_compensation_on_command_response(self):
        saga = mock_saga(
            [mock_local_step_def(), mock_participant_step_def()],
            {"status": "compensating", "current_step": 1},
        )
        saga.tick_command_response(True)
        self.assertEqual(saga.get_status(), "compensation")
        self.assertEqual(saga.get_current_step(), 0)

    def test_compensating_to_failed_on_failed_command_response(self):
        saga = mock_saga(
            [mock_participant_step_def()],
            {"status": "compensating"},
        )
        saga.tick_command_response(False)
        self.assertEqual(saga.get_status(), "failed")

    def test_compensating_to_compensation_on_failed_command_response(self):
        saga = mock_saga(
            [mock_local_step_def(), mock_participant_step_def()],
            {"status": "compensating", "current_step": 1},
        )
        saga.tick_command_response(False)
        self.assertEqual(saga.get_status(), "compensation")
        self.assertEqual(saga.get_current_step(), 0)


if __name__ == "__main__":
    unittest.main()
