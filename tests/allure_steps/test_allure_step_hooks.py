from unittest.mock import Mock

import pytest
from allure_commons.model2 import Status, StatusDetails, TestStepResult
from allure_commons.reporter import AllureReporter as AllureCommonsReporter
from baby_steps import given, then, when

from vedro_allure_reporter._allure_steps import AllureStepHooks


@pytest.fixture()
def allure_reporter() -> Mock:
    """Mock AllureCommonsReporter for testing."""
    return Mock(spec=AllureCommonsReporter)


@pytest.fixture()
def step_hooks(allure_reporter: Mock) -> AllureStepHooks:
    """Create AllureStepHooks instance with mocked reporter."""
    return AllureStepHooks(allure_reporter)


def test_init(allure_reporter: Mock):
    """Test AllureStepHooks initialization."""
    with when:
        hooks = AllureStepHooks(allure_reporter)

    with then:
        assert hooks._reporter is allure_reporter


def test_start_step_without_params(step_hooks: AllureStepHooks, allure_reporter: Mock):
    """Test starting a step without parameters."""
    with given:
        step_uuid = "test-uuid-123"
        step_title = "Test step title"
        params = {}

    with when:
        step_hooks.start_step(step_uuid, step_title, params)

    with then:
        assert allure_reporter.start_step.called
        call_args = allure_reporter.start_step.call_args

        # Check positional arguments
        assert call_args[0][0] is None  # parent_uuid
        assert call_args[0][1] == step_uuid

        # Check TestStepResult
        step_result = call_args[0][2]
        assert isinstance(step_result, TestStepResult)
        assert step_result.name == step_title
        assert step_result.parameters == []
        assert step_result.start is not None


def test_start_step_with_params(step_hooks: AllureStepHooks, allure_reporter: Mock):
    """Test starting a step with parameters."""
    with given:
        step_uuid = "test-uuid-456"
        step_title = "Create user: {username}"
        params = {"username": "testuser", "age": 25}

    with when:
        step_hooks.start_step(step_uuid, step_title, params)

    with then:
        assert allure_reporter.start_step.called
        call_args = allure_reporter.start_step.call_args

        # Check TestStepResult
        step_result = call_args[0][2]
        assert isinstance(step_result, TestStepResult)
        assert step_result.name == step_title
        assert len(step_result.parameters) == 2

        # Check parameters
        param_names = {p.name for p in step_result.parameters}
        assert param_names == {"username", "age"}

        param_dict = {p.name: p.value for p in step_result.parameters}
        assert param_dict["username"] == "testuser"
        assert param_dict["age"] == 25


def test_stop_step_passed(step_hooks: AllureStepHooks, allure_reporter: Mock):
    """Test stopping a step that passed."""
    with given:
        step_uuid = "test-uuid-789"
        exc_type = None
        exc_val = None
        exc_tb = None

    with when:
        step_hooks.stop_step(step_uuid, exc_type, exc_val, exc_tb)

    with then:
        assert allure_reporter.stop_step.called
        call_args = allure_reporter.stop_step.call_args

        # Check UUID (first positional argument)
        assert call_args[0][0] == step_uuid

        # Check kwargs
        kwargs = call_args[1]

        # Check status is PASSED
        assert kwargs["status"] == Status.PASSED

        # Check statusDetails is None for passed steps
        assert kwargs["statusDetails"] is None

        # Check stop time exists
        assert kwargs["stop"] is not None


def test_stop_step_failed_with_assertion_error(
        step_hooks: AllureStepHooks,
        allure_reporter: Mock):
    """Test stopping a step that failed with AssertionError."""
    with given:
        step_uuid = "test-uuid-assertion"
        exc_type = AssertionError
        exc_val = AssertionError("Expected 5 but got 3")
        exc_tb = None  # Simplified for test

    with when:
        step_hooks.stop_step(step_uuid, exc_type, exc_val, exc_tb)

    with then:
        assert allure_reporter.stop_step.called
        call_args = allure_reporter.stop_step.call_args
        kwargs = call_args[1]

        # Check status is FAILED for AssertionError
        assert kwargs["status"] == Status.FAILED

        # Check statusDetails exists
        status_details = kwargs["statusDetails"]
        assert isinstance(status_details, StatusDetails)
        assert status_details.message is not None


def test_stop_step_broken_with_exception(
        step_hooks: AllureStepHooks,
        allure_reporter: Mock):
    """Test stopping a step that failed with non-AssertionError exception."""
    with given:
        step_uuid = "test-uuid-exception"
        exc_type = ValueError
        exc_val = ValueError("Invalid value")
        exc_tb = None

    with when:
        step_hooks.stop_step(step_uuid, exc_type, exc_val, exc_tb)

    with then:
        assert allure_reporter.stop_step.called
        call_args = allure_reporter.stop_step.call_args
        kwargs = call_args[1]

        # Check status is BROKEN for non-AssertionError
        assert kwargs["status"] == Status.BROKEN

        # Check statusDetails exists
        status_details = kwargs["statusDetails"]
        assert isinstance(status_details, StatusDetails)
        assert status_details.message is not None


def test_attach_data(step_hooks: AllureStepHooks, allure_reporter: Mock):
    """Test attaching data to a step."""
    with given:
        body = b"Test attachment data"
        name = "test_attachment.txt"
        attachment_type = "text/plain"
        extension = "txt"

    with when:
        step_hooks.attach_data(body, name, attachment_type, extension)

    with then:
        assert allure_reporter.attach_data.called
        call_args = allure_reporter.attach_data.call_args

        # Check UUID was generated (first arg)
        assert isinstance(call_args[0][0], str)

        # Check body
        assert call_args[0][1] == body

        # Check kwargs
        assert call_args[1]["name"] == name
        assert call_args[1]["attachment_type"] == attachment_type
        assert call_args[1]["extension"] == extension


def test_attach_file(step_hooks: AllureStepHooks, allure_reporter: Mock):
    """Test attaching a file to a step."""
    with given:
        source = "/path/to/file.log"
        name = "application.log"
        attachment_type = "text/plain"
        extension = "log"

    with when:
        step_hooks.attach_file(source, name, attachment_type, extension)

    with then:
        assert allure_reporter.attach_file.called
        call_args = allure_reporter.attach_file.call_args

        # Check UUID was generated (first arg)
        assert isinstance(call_args[0][0], str)

        # Check source
        assert call_args[0][1] == source

        # Check kwargs
        assert call_args[1]["name"] == name
        assert call_args[1]["attachment_type"] == attachment_type
        assert call_args[1]["extension"] == extension


def test_multiple_steps_sequence(step_hooks: AllureStepHooks, allure_reporter: Mock):
    """Test a sequence of step operations."""
    with given:
        step1_uuid = "step-1"
        step2_uuid = "step-2"

    with when:
        # Start first step
        step_hooks.start_step(step1_uuid, "Step 1", {})

        # Start nested step
        step_hooks.start_step(step2_uuid, "Step 2", {"param": "value"})

        # Stop nested step
        step_hooks.stop_step(step2_uuid, None, None, None)

        # Stop first step
        step_hooks.stop_step(step1_uuid, None, None, None)

    with then:
        # Check start_step was called twice
        assert allure_reporter.start_step.call_count == 2

        # Check stop_step was called twice
        assert allure_reporter.stop_step.call_count == 2

        # Verify order of calls
        calls = allure_reporter.method_calls
        assert calls[0][0] == "start_step"  # step1 start
        assert calls[1][0] == "start_step"  # step2 start
        assert calls[2][0] == "stop_step"   # step2 stop
        assert calls[3][0] == "stop_step"   # step1 stop


def test_attach_data_with_json(step_hooks: AllureStepHooks, allure_reporter: Mock):
    """Test attaching JSON data."""
    with given:
        import json
        data = {"user": "test", "id": 123}
        body = json.dumps(data).encode()
        name = "user_data"
        attachment_type = "application/json"
        extension = "json"

    with when:
        step_hooks.attach_data(body, name, attachment_type, extension)

    with then:
        assert allure_reporter.attach_data.called
        call_args = allure_reporter.attach_data.call_args
        assert call_args[0][1] == body
        assert call_args[1]["attachment_type"] == "application/json"


@pytest.mark.parametrize("exc_class,expected_status", [
    (AssertionError, Status.FAILED),
    (ValueError, Status.BROKEN),
    (TypeError, Status.BROKEN),
    (RuntimeError, Status.BROKEN),
    (KeyError, Status.BROKEN),
])
def test_stop_step_different_exceptions(
        exc_class: type,
        expected_status: Status,
        step_hooks: AllureStepHooks,
        allure_reporter: Mock):
    """Test that different exception types result in correct status."""
    with given:
        step_uuid = "test-uuid"
        exc_type = exc_class
        exc_val = exc_class("Test exception")
        exc_tb = None

    with when:
        step_hooks.stop_step(step_uuid, exc_type, exc_val, exc_tb)

    with then:
        call_args = allure_reporter.stop_step.call_args
        kwargs = call_args[1]
        assert kwargs["status"] == expected_status


def test_step_hooks_are_independent(allure_reporter: Mock):
    """Test that multiple AllureStepHooks instances are independent."""
    with given:
        hooks1 = AllureStepHooks(allure_reporter)
        hooks2 = AllureStepHooks(Mock(spec=AllureCommonsReporter))

    with when:
        hooks1.start_step("uuid1", "Step 1", {})

    with then:
        # Only hooks1's reporter should be called
        assert allure_reporter.start_step.called
        assert not hooks2._reporter.start_step.called
