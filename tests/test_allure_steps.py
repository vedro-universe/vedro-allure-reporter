import threading
import time
from unittest.mock import Mock, patch

import pytest
from baby_steps import given, then, when

from vedro_allure_reporter._allure_steps import (
    AllureStepContext,
    _step_context,
    add_step_parameter,
    allure_step,
    clear_current_steps,
    get_current_step_uuid,
    get_current_steps,
    get_step_depth,
)


def test_step_context_initial_state():
    """Test that new context has no current step."""
    with given:
        context = AllureStepContext()

    with when:
        current_step = context.get_current_step()

    with then:
        assert current_step is None


def test_step_context_set_and_get():
    """Test setting and getting current step."""
    with given:
        context = AllureStepContext()
        step_uuid = "test-step-uuid"

    with when:
        context.set_current_step(step_uuid)
        current_step = context.get_current_step()

    with then:
        assert current_step == step_uuid


def test_step_context_clear():
    """Test clearing current step."""
    with given:
        context = AllureStepContext()
        context.set_current_step("test-step-uuid")

    with when:
        context.clear_current_step()
        current_step = context.get_current_step()

    with then:
        assert current_step is None


def test_decorator_execution():
    """Test that decorated function executes with step context."""
    with given:
        clear_current_steps()

        @allure_step("Test step")
        def test_function():
            return "result"

    with when:
        result = test_function()

    with then:
        assert result == "result"
        # Check that a step was recorded
        recorded_steps = get_current_steps()
        assert len(recorded_steps) == 1
        assert recorded_steps[0].name == "Test step"
        assert recorded_steps[0].status == "passed"


def test_decorator_preserves_metadata():
    """Test that decorator preserves original function metadata."""
    with given:
        def original_function():
            """Original docstring."""
            pass

    with when:
        decorated = allure_step("Test step")(original_function)

    with then:
        assert decorated.__name__ == "original_function"
        assert decorated.__doc__ == "Original docstring."


def test_decorator_handles_exceptions():
    """Test that decorator properly handles exceptions."""
    with given:
        clear_current_steps()

        @allure_step("Failing step")
        def failing_function():
            raise ValueError("Test error")

    with when:
        with pytest.raises(ValueError, match="Test error"):
            failing_function()

    with then:
        # Check that step was recorded with failed status
        recorded_steps = get_current_steps()
        assert len(recorded_steps) == 1
        assert recorded_steps[0].name == "Failing step"
        assert recorded_steps[0].status == "failed"


def test_context_manager_basic():
    """Test basic context manager usage."""
    with given:
        clear_current_steps()

    with when:
        with allure_step("Test context step") as step_uuid:
            result_uuid = step_uuid

    with then:
        assert result_uuid is not None
        # Check that step was recorded
        recorded_steps = get_current_steps()
        assert len(recorded_steps) == 1
        assert recorded_steps[0].name == "Test context step"
        assert recorded_steps[0].status == "passed"


def test_context_manager_handles_exceptions():
    """Test that context manager properly handles exceptions."""
    with given:
        clear_current_steps()

    with when:
        with pytest.raises(RuntimeError, match="Test context error"):
            with allure_step("Failing context step"):
                raise RuntimeError("Test context error")

    with then:
        # Check that step was recorded with failed status
        recorded_steps = get_current_steps()
        assert len(recorded_steps) == 1
        assert recorded_steps[0].name == "Failing context step"
        assert recorded_steps[0].status == "failed"


def test_nested_steps():
    """Test nested step execution."""
    with given:
        clear_current_steps()

    with when:
        with allure_step("Parent step"):
            with allure_step("Child step"):
                pass

    with then:
        # Should have recorded both parent and child steps
        recorded_steps = get_current_steps()
        assert len(recorded_steps) == 1  # Only parent is recorded at top level

        parent_step = recorded_steps[0]
        assert parent_step.name == "Parent step"
        assert parent_step.status == "passed"

        # Child step should be nested within parent
        assert hasattr(parent_step, 'steps') and parent_step.steps is not None
        assert len(parent_step.steps) == 1

        child_step = parent_step.steps[0]
        assert child_step.name == "Child step"
        assert child_step.status == "passed"


def test_step_context_restoration():
    """Test that step context is properly restored after nested steps."""
    with given:
        # Clear any existing context
        clear_current_steps()

    with when:
        with allure_step("Outer step"):
            outer_step_uuid = get_current_step_uuid()
            with allure_step("Inner step"):
                inner_step_uuid = get_current_step_uuid()
            restored_step_uuid = get_current_step_uuid()
        final_step_uuid = get_current_step_uuid()

    with then:
        assert outer_step_uuid is not None
        assert inner_step_uuid is not None
        assert inner_step_uuid != outer_step_uuid
        assert restored_step_uuid == outer_step_uuid  # Context restored after inner step
        assert final_step_uuid is None  # No context after all steps


def test_thread_local_isolation():
    """Test that step context is isolated between threads."""
    with given:
        results = {}

        def thread_function(thread_id: str):
            _step_context.set_current_step(f"step-{thread_id}")
            time.sleep(0.1)  # Allow other threads to run
            results[thread_id] = _step_context.get_current_step()

    with when:
        threads = []
        for i in range(3):
            thread = threading.Thread(target=thread_function, args=[str(i)])
            threads.append(thread)

        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

    with then:
        assert results["0"] == "step-0"
        assert results["1"] == "step-1"
        assert results["2"] == "step-2"


def test_step_depth_tracking():
    """Test that step depth is tracked correctly for nested contexts."""
    with given:
        clear_current_steps()

    with when:
        assert get_step_depth() == 0, "Initial depth should be 0"

        with allure_step("Level 1"):
            depth_1 = get_step_depth()

            with allure_step("Level 2"):
                depth_2 = get_step_depth()

                with allure_step("Level 3"):
                    depth_3 = get_step_depth()

                depth_2_restored = get_step_depth()

            depth_1_restored = get_step_depth()

        final_depth = get_step_depth()

    with then:
        assert depth_1 == 1, "Depth should be 1 in first level"
        assert depth_2 == 2, "Depth should be 2 in second level"
        assert depth_3 == 3, "Depth should be 3 in third level"
        assert depth_2_restored == 2, "Depth should return to 2 after level 3"
        assert depth_1_restored == 1, "Depth should return to 1 after level 2"
        assert final_depth == 0, "Depth should return to 0 after all contexts"


def test_current_step_uuid_tracking():
    """Test that current step UUID is tracked correctly."""
    with given:
        clear_current_steps()
        assert get_current_step_uuid() is None, "No current step initially"

    with when:
        with allure_step("Test step") as step_uuid:
            current_uuid = get_current_step_uuid()

            with allure_step("Nested step") as nested_uuid:
                nested_current_uuid = get_current_step_uuid()

            restored_uuid = get_current_step_uuid()

        final_uuid = get_current_step_uuid()

    with then:
        assert current_uuid == step_uuid, "Current step UUID should match context UUID"
        assert nested_current_uuid == nested_uuid, "Should track nested step UUID"
        assert restored_uuid == step_uuid, "Should return to parent UUID"
        assert final_uuid is None, "Should clear UUID after context"


def test_parameter_substitution_in_decorator():
    """Test parameter substitution in allure_step decorator."""
    with given:
        @allure_step("Process {count} items with method {method}")
        def test_function(count, method="default"):
            return f"Processed {count} items using {method}"

    with when:
        with patch('vedro_allure_reporter._allure_steps.AllureStep') as mock_step_class:
            # Create a mock instance that can be used as context manager
            mock_step_instance = Mock()
            mock_step_instance.__enter__ = Mock(return_value="test-uuid")
            mock_step_instance.__exit__ = Mock(return_value=None)
            mock_step_class.return_value = mock_step_instance

            result = test_function(5, method="batch")

    with then:
        # Check that AllureStep was created with formatted title and parameters
        expected_params = [
            {'name': 'count', 'value': '5'},
            {'name': 'method', 'value': 'batch'}
        ]
        mock_step_class.assert_called_once_with(
            "Process 5 items with method batch", parameters=expected_params)
        assert result == "Processed 5 items using batch"


def test_self_attribute_substitution():
    """Test substitution of self attributes in method decorators."""
    with given:
        class TestClass:
            def __init__(self):
                self.username = "test_user"
                self.role = "admin"

            @allure_step("Login user {username} with role {role}")
            def login_method(self):
                return f"Logged in {self.username} as {self.role}"

        test_obj = TestClass()

    with when:
        with patch('vedro_allure_reporter._allure_steps.AllureStep') as mock_step_class:
            # Create a mock instance that can be used as context manager
            mock_step_instance = Mock()
            mock_step_instance.__enter__ = Mock(return_value="test-uuid")
            mock_step_instance.__exit__ = Mock(return_value=None)
            mock_step_class.return_value = mock_step_instance

            result = test_obj.login_method()

    with then:
        # Check that AllureStep was created with self attributes substituted and empty parameters
        mock_step_class.assert_called_once_with(
            "Login user test_user with role admin", parameters=[])
        assert result == "Logged in test_user as admin"


@patch('vedro_allure_reporter._allure_steps.TestStepResult')
def test_enhanced_context_with_parameters(mock_test_step_result):
    """Test allure_step with parameters."""
    with given:
        clear_current_steps()
        test_params = [{"name": "batch_size", "value": "100"}]

    with when:
        with allure_step("Test step with params", parameters=test_params):
            # Verify that TestStepResult was created with correct parameters
            pass

    with then:
        # Verify that TestStepResult constructor was called
        mock_test_step_result.assert_called()
        # Check that parameters were set
        call_args = mock_test_step_result.call_args
        assert call_args[1]['name'] == "Test step with params"


def test_add_step_parameter():
    """Test adding parameters to current step."""
    with given:
        clear_current_steps()

    with when:
        with allure_step("Test step"):
            # This function should work within an active context
            add_step_parameter("test_param", "test_value")

    with then:
        # In a real scenario, this would add parameter to the step
        # For unit test, we just verify it doesn't crash
        pass


def test_exception_handling_in_nested_context():
    """Test that exceptions are properly handled in nested contexts."""
    with given:
        clear_current_steps()

    with when:
        try:
            with allure_step("Outer step"):
                assert get_step_depth() == 1

                with allure_step("Inner step that fails"):
                    assert get_step_depth() == 2
                    raise ValueError("Test exception")

        except ValueError:
            # Exception should bubble up
            pass

    with then:
        # Verify depth is reset after exception
        assert get_step_depth() == 0, "Step depth should be reset after exception"
        assert get_current_step_uuid() is None, "Current step should be cleared after exception"


def test_thread_isolation_with_nested_steps():
    """Test that nested steps are isolated between threads."""
    with given:
        results = {}

        def thread_worker(thread_id):
            clear_current_steps()
            results[thread_id] = []

            with allure_step(f"Thread {thread_id} step"):
                results[thread_id].append(get_step_depth())  # Should be 1
                results[thread_id].append(get_current_step_uuid() is not None)

                with allure_step(f"Nested step in thread {thread_id}"):
                    results[thread_id].append(get_step_depth())  # Should be 2

    with when:
        # Create and start threads
        threads = []
        for i in range(3):
            thread = threading.Thread(target=thread_worker, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

    with then:
        # Verify results from each thread
        for thread_id in range(3):
            assert results[thread_id] == [1, True, 2], f"Thread {thread_id} had incorrect results"


def test_attach_text():
    """Test text attachment functionality."""
    with given:
        from vedro_allure_reporter._allure_steps import attach_text
        clear_current_steps()

    with when:
        with allure_step("Test step"):
            attach_text("Test content", name="Test Attachment")

    with then:
        # Verify step was created and has attachments (not parameters)
        recorded_steps = get_current_steps()
        assert len(recorded_steps) == 1

        step = recorded_steps[0]
        assert step.name == "Test step"

        # Check that attachment was added to attachments section
        assert hasattr(step, 'attachments') and step.attachments is not None
        assert len(step.attachments) > 0

        # Find the attachment
        attachment = step.attachments[0]
        assert attachment.name == "Test Attachment"
        assert attachment.type == "text/plain"
        assert attachment.source.endswith("-attachment.txt")


def test_attach_json():
    """Test JSON attachment functionality."""
    with given:
        from vedro_allure_reporter._allure_steps import attach_json
        clear_current_steps()
        test_data = {"key": "value", "number": 42}

    with when:
        with allure_step("Test step"):
            attach_json(test_data, name="Test JSON")

    with then:
        # Verify step was created and has parameters from attachment
        recorded_steps = get_current_steps()
        assert len(recorded_steps) == 1

        step = recorded_steps[0]
        assert step.name == "Test step"

        # Check that attachment was added to attachments section
        assert hasattr(step, 'attachments') and step.attachments is not None
        assert len(step.attachments) > 0

        # Find the JSON attachment
        attachment = step.attachments[0]
        assert attachment.name == "Test JSON"
        assert attachment.type == "application/json"
        assert attachment.source.endswith("-attachment.json")


def test_attach_file_exists(tmp_path):
    """Test file attachment when file exists."""
    with given:
        from vedro_allure_reporter._allure_steps import attach_file
        clear_current_steps()

        # Create a temporary file
        test_file = tmp_path / "test_file.txt"
        test_file.write_text("Test file content")

    with when:
        with allure_step("Test step"):
            attach_file(test_file)

    with then:
        # Verify step was created and has file parameter
        recorded_steps = get_current_steps()
        assert len(recorded_steps) == 1

        step = recorded_steps[0]
        assert step.name == "Test step"

        # Check that file was added to attachments section
        assert hasattr(step, 'attachments') and step.attachments is not None
        assert len(step.attachments) > 0

        # Find the file attachment
        attachment = step.attachments[0]
        assert attachment.name == "test_file.txt"
        assert attachment.type == "text/plain"
        assert attachment.source.endswith("-attachment.txt")


def test_attach_file_not_exists():
    """Test file attachment when file doesn't exist."""
    with given:
        from vedro_allure_reporter._allure_steps import attach_file
        clear_current_steps()

    with when:
        with allure_step("Test step"):
            attach_file("/nonexistent/file.txt")

    with then:
        # Verify step was created and has error parameter
        recorded_steps = get_current_steps()
        assert len(recorded_steps) == 1

        step = recorded_steps[0]
        assert step.name == "Test step"

        # Check that error was added as parameter
        assert hasattr(step, 'parameters') and step.parameters is not None
        assert len(step.parameters) > 0

        # Find error parameter
        error_params = [p for p in step.parameters if 'file_error' in p['name']]
        assert len(error_params) == 1
        assert "File not found" in error_params[0]['value']


def test_create_step_parameter():
    """Test create_step_parameter function."""
    with given:
        from vedro_allure_reporter._allure_steps import create_step_parameter

    with when:
        # Test default parameter
        default_param = create_step_parameter("test_param", "test_value")

        # Test masked parameter
        masked_param = create_step_parameter("secret", "password123", mode="masked")

        # Test hidden parameter
        hidden_param = create_step_parameter("internal", "internal_data", mode="hidden")

    with then:
        assert default_param["name"] == "test_param"
        assert default_param["value"] == "test_value"
        assert "excluded" not in default_param

        assert masked_param["name"] == "secret"
        assert masked_param["value"] == "***"

        assert hidden_param["name"] == "internal"
        assert hidden_param.get("excluded") is True


def test_attach_screenshot():
    """Test screenshot attachment functionality."""
    with given:
        from vedro_allure_reporter._allure_steps import attach_screenshot
        clear_current_steps()
        screenshot_data = b"fake_png_data"

    with when:
        with allure_step("Test step"):
            attach_screenshot(screenshot_data, name="Test Screenshot")

    with then:
        # Verify step was created and has screenshot parameter
        recorded_steps = get_current_steps()
        assert len(recorded_steps) == 1

        step = recorded_steps[0]
        assert step.name == "Test step"

        # Check that screenshot was added to attachments section
        assert hasattr(step, 'attachments') and step.attachments is not None
        assert len(step.attachments) > 0

        # Find the screenshot attachment
        attachment = step.attachments[0]
        assert attachment.name == "Test Screenshot"
        assert attachment.type == "image/png"
        assert attachment.source.endswith("-attachment.png")


def test_add_link():
    """Test add_link functionality."""
    with given:
        from vedro_allure_reporter._allure_steps import add_link
        clear_current_steps()

    with when:
        with allure_step("Test step"):
            add_link("https://example.com", name="Test Link")

    with then:
        # This should not crash and should work within step context
        # In real implementation, this would add link to step parameters
        pass
