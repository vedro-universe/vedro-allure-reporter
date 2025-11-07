from typing import Generator

import pytest
from allure_commons import plugin_manager as allure_plugin_manager
from allure_commons.model2 import Status
from allure_commons.reporter import AllureReporter as AllureCommonsReporter
from baby_steps import given, then, when

from vedro_allure_reporter._allure_steps import AllureStepHooks


@pytest.fixture()
def allure_reporter() -> AllureCommonsReporter:
    """Real AllureCommonsReporter instance for integration tests."""
    return AllureCommonsReporter()


@pytest.fixture()
def step_hooks(allure_reporter: AllureCommonsReporter) -> Generator[AllureStepHooks, None, None]:
    """Create AllureStepHooks instance with real reporter."""
    hooks = AllureStepHooks(allure_reporter)
    # Register hooks with allure plugin manager
    allure_plugin_manager.register(hooks)
    yield hooks
    # Unregister after test
    allure_plugin_manager.unregister(hooks)


def test_hooks_registered_with_plugin_manager(step_hooks: AllureStepHooks):
    """Test that hooks are properly registered with allure plugin_manager."""
    with given:
        # step_hooks fixture already registers the hooks
        pass

    with then:
        # Check that our hooks instance is in the plugin manager
        plugins = allure_plugin_manager.get_plugins()
        assert step_hooks in plugins


def test_start_and_stop_step_integration(step_hooks: AllureStepHooks,
                                         allure_reporter: AllureCommonsReporter):
    """Test complete start-stop step cycle with real reporter."""
    with given:
        # Schedule a test first (required by AllureCommonsReporter)
        test_uuid = "test-uuid-123"
        from allure_commons.model2 import TestResult
        test_result = TestResult(uuid=test_uuid, name="Test")
        allure_reporter.schedule_test(test_uuid, test_result)

        step_uuid = "step-uuid-456"
        step_title = "Integration test step"
        params = {"key": "value"}

    with when:
        # Start step
        step_hooks.start_step(step_uuid, step_title, params)

        # Stop step
        step_hooks.stop_step(step_uuid, None, None, None)

    with then:
        # Get the test result
        result = allure_reporter.get_test(test_uuid)
        assert result is not None

        # Check that step was added
        assert len(result.steps) == 1
        assert result.steps[0].name == step_title
        assert result.steps[0].status == Status.PASSED


def test_nested_steps_integration(
        step_hooks: AllureStepHooks,
        allure_reporter: AllureCommonsReporter):
    """Test nested steps work correctly."""
    with given:
        # Schedule a test
        test_uuid = "test-uuid-nested"
        from allure_commons.model2 import TestResult
        test_result = TestResult(uuid=test_uuid, name="Nested Test")
        allure_reporter.schedule_test(test_uuid, test_result)

        parent_step_uuid = "parent-step"
        child_step_uuid = "child-step"

    with when:
        # Start parent step
        step_hooks.start_step(parent_step_uuid, "Parent step", {})

        # Start child step
        step_hooks.start_step(child_step_uuid, "Child step", {})

        # Stop child step
        step_hooks.stop_step(child_step_uuid, None, None, None)

        # Stop parent step
        step_hooks.stop_step(parent_step_uuid, None, None, None)

    with then:
        result = allure_reporter.get_test(test_uuid)
        assert len(result.steps) == 1  # Only parent step at root level

        parent_step = result.steps[0]
        assert parent_step.name == "Parent step"

        # Check child step is nested
        assert len(parent_step.steps) == 1
        assert parent_step.steps[0].name == "Child step"


def test_step_with_exception_integration(step_hooks: AllureStepHooks,
                                         allure_reporter: AllureCommonsReporter):
    """Test step that fails with exception."""
    with given:
        # Schedule a test
        test_uuid = "test-uuid-exception"
        from allure_commons.model2 import TestResult
        test_result = TestResult(uuid=test_uuid, name="Exception Test")
        allure_reporter.schedule_test(test_uuid, test_result)

        step_uuid = "step-with-error"
        exc_type = AssertionError
        exc_val = AssertionError("Test failed")
        exc_tb = None

    with when:
        step_hooks.start_step(step_uuid, "Failing step", {})
        step_hooks.stop_step(step_uuid, exc_type, exc_val, exc_tb)

    with then:
        result = allure_reporter.get_test(test_uuid)
        step = result.steps[0]

        # Check status is FAILED
        assert step.status == Status.FAILED

        # Check statusDetails exists
        assert step.statusDetails is not None
        assert step.statusDetails.message is not None


def test_attach_data_integration(
        step_hooks: AllureStepHooks,
        allure_reporter: AllureCommonsReporter):
    """Test data attachment works with real reporter."""
    with given:
        # Schedule a test
        test_uuid = "test-uuid-attach"
        from allure_commons.model2 import TestResult
        test_result = TestResult(uuid=test_uuid, name="Attach Test")
        allure_reporter.schedule_test(test_uuid, test_result)

        body = b"Test data"
        name = "test.txt"
        attachment_type = "text/plain"
        extension = "txt"

    with when:
        step_hooks.attach_data(body, name, attachment_type, extension)

    with then:
        result = allure_reporter.get_test(test_uuid)
        # Check attachment was added
        assert len(result.attachments) == 1
        assert result.attachments[0].name == name
        assert result.attachments[0].type == attachment_type


def test_multiple_tests_with_steps(
        step_hooks: AllureStepHooks,
        allure_reporter: AllureCommonsReporter):
    """Test that steps are correctly associated with their test."""
    with given:
        # Schedule one test
        test1_uuid = "test-1"

        from allure_commons.model2 import TestResult
        allure_reporter.schedule_test(test1_uuid, TestResult(uuid=test1_uuid, name="Test 1"))

    with when:
        # Add multiple steps to the test
        step_hooks.start_step("step-1-1", "Test 1 Step 1", {})
        step_hooks.stop_step("step-1-1", None, None, None)

        step_hooks.start_step("step-1-2", "Test 1 Step 2", {})
        step_hooks.stop_step("step-1-2", None, None, None)

    with then:
        result1 = allure_reporter.get_test(test1_uuid)

        # Test should have both steps
        assert len(result1.steps) == 2
        assert result1.steps[0].name == "Test 1 Step 1"
        assert result1.steps[1].name == "Test 1 Step 2"


@pytest.mark.parametrize("params", [
    {},
    {"user": "test"},
    {"user": "test", "id": 123, "active": True},
])
def test_step_parameters_integration(params: dict,
                                     step_hooks: AllureStepHooks,
                                     allure_reporter: AllureCommonsReporter):
    """Test that step parameters are correctly stored."""
    with given:
        test_uuid = "test-params"
        from allure_commons.model2 import TestResult
        allure_reporter.schedule_test(test_uuid, TestResult(uuid=test_uuid, name="Params Test"))

        step_uuid = "step-with-params"

    with when:
        step_hooks.start_step(step_uuid, "Step with params", params)
        step_hooks.stop_step(step_uuid, None, None, None)

    with then:
        result = allure_reporter.get_test(test_uuid)
        step = result.steps[0]

        # Check parameters count
        assert len(step.parameters) == len(params)

        # Check parameter values
        step_param_dict = {p.name: p.value for p in step.parameters}
        assert step_param_dict == params


def test_unregister_hooks():
    """Test that hooks can be unregistered from plugin_manager."""
    with given:
        reporter = AllureCommonsReporter()
        hooks = AllureStepHooks(reporter)
        allure_plugin_manager.register(hooks)

    with when:
        allure_plugin_manager.unregister(hooks)

    with then:
        plugins = allure_plugin_manager.get_plugins()
        assert hooks not in plugins


def test_hooks_called_through_plugin_manager(step_hooks: AllureStepHooks,
                                             allure_reporter: AllureCommonsReporter):
    """Test that hooks are invoked when called through plugin_manager."""
    with given:
        # Schedule a test
        test_uuid = "test-hook-invocation"
        from allure_commons.model2 import TestResult
        allure_reporter.schedule_test(test_uuid, TestResult(uuid=test_uuid, name="Hook Test"))

        step_uuid = "step-invocation"

    with when:
        # Call hooks through plugin_manager (as allure.step decorator does)
        allure_plugin_manager.hook.start_step(
            uuid=step_uuid, title="Hook invoked step", params={})
        allure_plugin_manager.hook.stop_step(
            uuid=step_uuid, exc_type=None, exc_val=None, exc_tb=None)

    with then:
        result = allure_reporter.get_test(test_uuid)
        # Step should be added via our hooks
        assert len(result.steps) == 1
        assert result.steps[0].name == "Hook invoked step"
