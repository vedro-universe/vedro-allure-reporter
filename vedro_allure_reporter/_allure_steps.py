"""
Allure Steps Integration for Vedro Testing Framework

This module provides decorators and context managers for creating hierarchical steps
in Allure reports when using the Vedro testing framework.
"""

import functools
import inspect
import json
import threading
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, TypeVar, Union

from allure_commons.model2 import TestStepResult
from allure_commons.utils import now, uuid4

from ._allure_attachments import (
    add_attachment_to_step,
    create_file_attachment,
    create_screenshot_attachment,
    create_text_attachment,
)

__all__ = [
    'allure_step',
    'AllureStepContext',
    'get_current_steps',
    'get_steps_by_vedro_step',
    'set_current_vedro_step',
    'clear_current_vedro_step',
    'clear_current_steps',
    'get_step_depth',
    'get_current_step_uuid',
    'add_step_parameter',
    'attach_text',
    'attach_json',
    'attach_file',
    'attach_screenshot',
    'add_link',
    'create_step_parameter'
]

F = TypeVar('F', bound=Callable[..., Any])


class AllureStepContext:
    """Thread-local context for managing Allure steps with hierarchical support."""

    def __init__(self) -> None:
        self._local = threading.local()

    def get_current_step(self) -> Optional[str]:
        """Get the current step UUID for this thread."""
        return getattr(self._local, 'current_step', None)

    def set_current_step(self, step_uuid: str) -> None:
        """Set the current step UUID for this thread."""
        self._local.current_step = step_uuid

    def clear_current_step(self) -> None:
        """Clear the current step UUID for this thread."""
        if hasattr(self._local, 'current_step'):
            delattr(self._local, 'current_step')

    def push_step(self, step_uuid: str, step_obj: TestStepResult) -> None:
        """Push a step UUID and object onto the step stack."""
        if not hasattr(self._local, 'step_stack'):
            self._local.step_stack = []
            self._local.step_objects = []
        self._local.step_stack.append(step_uuid)
        self._local.step_objects.append(step_obj)
        self.set_current_step(step_uuid)

    def pop_step(self) -> Optional[TestStepResult]:
        """Pop a step from the step stack and return the step object."""
        if not hasattr(self._local, 'step_stack') or not self._local.step_stack:
            self.clear_current_step()
            return None

        self._local.step_stack.pop()
        popped_step = self._local.step_objects.pop()

        # Set current step to the parent step (if any)
        if self._local.step_stack:
            self.set_current_step(self._local.step_stack[-1])
        else:
            self.clear_current_step()

        return popped_step

    def get_step_depth(self) -> int:
        """Get the current nesting depth of steps."""
        return len(getattr(self._local, 'step_stack', []))

    def get_current_step_object(self) -> Optional[TestStepResult]:
        """Get the current step object."""
        step_objects = getattr(self._local, 'step_objects', [])
        return step_objects[-1] if step_objects else None

    def get_recorded_steps(self) -> List[TestStepResult]:
        """Get all recorded steps for this thread."""
        return getattr(self._local, 'recorded_steps', [])

    def get_steps_by_vedro_step(self) -> Dict[str, List[TestStepResult]]:
        """Get recorded steps grouped by Vedro step name."""
        return getattr(self._local, 'steps_by_vedro_step', {})

    def get_current_vedro_step(self) -> Optional[str]:
        """Get current vedro step name."""
        return getattr(self._local, 'current_vedro_step', None)

    def add_attachment_to_current_step(self, attachment: Any) -> None:
        """Add an attachment to the currently active step."""
        current_step_obj = self.get_current_step_object()
        if current_step_obj:
            if (not hasattr(current_step_obj, 'attachments') or
                    current_step_obj.attachments is None):
                current_step_obj.attachments = []
            current_step_obj.attachments.append(attachment)

    def add_recorded_step(self, step: TestStepResult) -> None:
        """Add a step to the recorded steps for this thread."""
        if not hasattr(self._local, 'recorded_steps'):
            self._local.recorded_steps = []
        if not hasattr(self._local, 'steps_by_vedro_step'):
            self._local.steps_by_vedro_step = {}

        self._local.recorded_steps.append(step)

        # Also group by current Vedro step
        vedro_step = self.get_current_vedro_step()
        if vedro_step:
            if vedro_step not in self._local.steps_by_vedro_step:
                self._local.steps_by_vedro_step[vedro_step] = []
            self._local.steps_by_vedro_step[vedro_step].append(step)

    def clear_recorded_steps(self) -> None:
        """Clear all recorded steps for this thread."""
        if hasattr(self._local, 'recorded_steps'):
            self._local.recorded_steps = []
        if hasattr(self._local, 'steps_by_vedro_step'):
            self._local.steps_by_vedro_step = {}
        if hasattr(self._local, 'step_stack'):
            self._local.step_stack = []
        if hasattr(self._local, 'step_objects'):
            self._local.step_objects = []
        if hasattr(self._local, 'current_vedro_step'):
            delattr(self._local, 'current_vedro_step')
        self.clear_current_step()


# Global thread-local step context
_step_context = AllureStepContext()


def set_current_vedro_step(step_name: str) -> None:
    """
    Set the current Vedro step name for proper step grouping.

    This should be called by AllureReporter when a Vedro step starts executing.

    Args:
        step_name: Name of the Vedro step that is starting
    """
    _step_context._local.current_vedro_step = step_name


def clear_current_vedro_step() -> None:
    """
    Clear the current Vedro step name.

    This should be called by AllureReporter when a Vedro step finishes executing.
    """
    if hasattr(_step_context._local, 'current_vedro_step'):
        delattr(_step_context._local, 'current_vedro_step')


def get_current_steps() -> List[TestStepResult]:
    """
    Get all recorded steps for the current thread.

    This function can be called by AllureReporterPlugin to get steps
    that were recorded during scenario execution.

    Returns:
        List of TestStepResult objects recorded in current thread
    """
    return _step_context.get_recorded_steps()


def get_steps_by_vedro_step() -> Dict[str, List[TestStepResult]]:
    """
    Get recorded steps grouped by Vedro step name.

    Returns:
        Dictionary mapping Vedro step names to lists of custom steps
    """
    return _step_context.get_steps_by_vedro_step()


def clear_current_steps() -> None:
    """
    Clear all recorded steps for the current thread.

    This should be called at the start of each scenario to ensure
    steps don't leak between scenarios.
    """
    _step_context.clear_recorded_steps()
    _step_context.clear_current_step()


def get_step_depth() -> int:
    """
    Get the current nesting depth of steps.

    Returns:
        Current step nesting depth (0 = no active steps, 1 = one level, etc.)
    """
    return _step_context.get_step_depth()


def get_current_step_uuid() -> Optional[str]:
    """
    Get the UUID of the currently active step.

    Returns:
        UUID of current step, or None if no step is active
    """
    return _step_context.get_current_step()


def add_step_parameter(name: str, value: Any) -> None:
    """
    Add a parameter to the currently active step.

    Args:
        name: Parameter name
        value: Parameter value (will be converted to string)

    Note:
        This function only works when called within an active allure_step
    """
    current_step_obj = _step_context.get_current_step_object()
    if current_step_obj:
        if not hasattr(current_step_obj, 'parameters') or current_step_obj.parameters is None:
            current_step_obj.parameters = []
        current_step_obj.parameters.append({"name": name, "value": str(value)})


def attach_text(text: str, name: str = "Text Attachment",
                attachment_type: str = "text/plain") -> None:
    """
    Attach text content to the current step.

    Args:
        text: Text content to attach
        name: Name of the attachment (default: "Text Attachment")
        attachment_type: MIME type (default: "text/plain")
    """
    current_step_obj = _step_context.get_current_step_object()
    if current_step_obj:
        attachment = create_text_attachment(text, name, attachment_type)
        add_attachment_to_step(current_step_obj, attachment)


def attach_json(data: Any, name: str = "JSON Data") -> None:
    """
    Attach JSON data to the current step.

    Args:
        data: Any JSON-serializable data
        name: Name of the attachment (default: "JSON Data")
    """
    try:
        json_text = json.dumps(data, indent=2, ensure_ascii=False)
        attach_text(json_text, name=name,
                    attachment_type="application/json")
    except (TypeError, ValueError):
        # Fallback to string representation
        attach_text(str(data), name=f"{name} (fallback)",
                    attachment_type="text/plain")


def attach_file(file_path: Union[str, Path], name: Optional[str] = None) -> None:
    """
    Attach a file to the current step.

    Args:
        file_path: Path to the file to attach
        name: Name of the attachment (defaults to filename)
    """
    current_step_obj = _step_context.get_current_step_object()
    if not current_step_obj:
        return

    file_path = Path(file_path)
    if not file_path.exists():
        add_step_parameter("file_error", f"File not found: {file_path}")
        return

    attachment = create_file_attachment(file_path, name)
    add_attachment_to_step(current_step_obj, attachment)


def attach_screenshot(screenshot_data: bytes, name: str = "Screenshot") -> None:
    """
    Attach screenshot data to the current step.

    Args:
        screenshot_data: Raw screenshot data (PNG/JPEG bytes)
        name: Name of the attachment (default: "Screenshot")
    """
    current_step_obj = _step_context.get_current_step_object()
    if current_step_obj:
        attachment = create_screenshot_attachment(screenshot_data, name)
        add_attachment_to_step(current_step_obj, attachment)


def add_link(url: str, name: Optional[str] = None) -> None:
    """
    Add a link to the current step.

    Args:
        url: URL to link to
        name: Display name for the link (defaults to URL)
    """
    current_step_obj = _step_context.get_current_step_object()
    if current_step_obj:
        # Create HTML link attachment
        display_name = name or url
        link_html = f'<a href="{url}" target="_blank">{display_name}</a>'

        attach_text(link_html, name=f"Link: {display_name}", attachment_type="text/html")


def create_step_parameter(name: str, value: Any, mode: str = "default") -> Dict[str, Any]:
    """
    Create a properly formatted step parameter.

    Args:
        name: Parameter name
        value: Parameter value
        mode: Display mode ("default", "masked", "hidden")

    Returns:
        Dictionary representing the parameter
    """
    param = {
        "name": name,
        "value": str(value)
    }

    if mode == "masked":
        param["value"] = "***"
    elif mode == "hidden":
        param["excluded"] = True

    return param


def _format_step_title(title: str, func_args: tuple, func_kwargs: dict, func_self=None) -> str:
    """
    Format step title with function arguments and self attributes.

    Replaces placeholders like {arg_name} with actual argument values.
    Also supports {self.attr_name} for accessing self attributes.

    Args:
        title: Step title template with placeholders
        func_args: Positional arguments from the decorated function
        func_kwargs: Keyword arguments from the decorated function
        func_self: The 'self' object if the function is a method

    Returns:
        Formatted step title with substituted values
    """
    try:
        # Create a mapping for format substitution
        format_kwargs = func_kwargs.copy()

        # Add positional arguments with generic names
        for i, arg in enumerate(func_args):
            format_kwargs[f'arg{i}'] = arg

        # If we have self, add its attributes for substitution
        if func_self is not None:
            for attr_name in dir(func_self):
                if not attr_name.startswith('_'):  # Skip private attributes
                    try:
                        attr_value = getattr(func_self, attr_name)
                        # Only include simple types that can be converted to string
                        if isinstance(attr_value, (str, int, float, bool)):
                            format_kwargs[attr_name] = attr_value
                    except (AttributeError, TypeError):
                        continue

        # Try to substitute placeholders
        return title.format(**format_kwargs)
    except (KeyError, ValueError):
        # If formatting fails, return original title
        return title


class AllureStep:
    """
    Universal Allure step that can be used both as decorator and context manager.

    This class provides a unified interface for creating Allure steps

    Usage as decorator:
        @allure_step("Login with username '{username}'")
        def login(username: str, password: str):
            # Login logic here
            pass

    Usage as context manager:
        with allure_step("Verify user data"):
            assert user.name == "John Doe"
            assert user.email == "john@example.com"

    Usage with parameters:
        with allure_step("Process batch", parameters=[{"name": "size", "value": "10"}]):
            # Processing logic
            pass
    """

    def __init__(self, title: str, parameters: Optional[List[dict]] = None):
        """
        Initialize the AllureStep.

        Args:
            title: The title of the step to display in Allure reports.
                   Can contain placeholders like {param_name} for parameter substitution.
            parameters: Optional list of parameter dictionaries for context manager usage.
        """
        self.title = title
        self.parameters = parameters
        self._step_uuid: Optional[str] = None
        self._step_result: Optional[TestStepResult] = None

    def __call__(self, func: F) -> F:
        """Use as decorator."""
        if inspect.iscoroutinefunction(func):
            # Handle async functions
            @functools.wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                # Extract self if this is a method call
                func_self = args[0] if args and hasattr(args[0], '__dict__') else None

                # Get function signature for better parameter mapping
                try:
                    sig = inspect.signature(func)
                    bound_args = sig.bind(*args, **kwargs)
                    bound_args.apply_defaults()

                    # Remove 'self' from arguments for cleaner parameter mapping
                    clean_args = dict(bound_args.arguments)
                    if 'self' in clean_args:
                        del clean_args['self']

                    formatted_title = _format_step_title(
                        self.title, args[1:] if func_self else args,
                        clean_args, func_self)

                    # Convert function parameters to Allure parameters format
                    function_parameters = []
                    for param_name, param_value in clean_args.items():
                        function_parameters.append({
                            "name": param_name,
                            "value": str(param_value)
                        })

                except Exception:
                    # Fallback to basic formatting
                    formatted_title = _format_step_title(self.title, args, kwargs, func_self)
                    # Fallback parameters from kwargs
                    function_parameters = []
                    for param_name, param_value in kwargs.items():
                        function_parameters.append({
                            "name": param_name,
                            "value": str(param_value)
                        })

                with AllureStep(formatted_title, parameters=function_parameters):
                    return await func(*args, **kwargs)

            return async_wrapper  # type: ignore

        else:
            # Handle sync functions
            @functools.wraps(func)
            def wrapper(*args: Any, **kwargs: Any) -> Any:
                # Extract self if this is a method call
                func_self = args[0] if args and hasattr(args[0], '__dict__') else None

                # Get function signature for better parameter mapping
                try:
                    sig = inspect.signature(func)
                    bound_args = sig.bind(*args, **kwargs)
                    bound_args.apply_defaults()

                    # Remove 'self' from arguments for cleaner parameter mapping
                    clean_args = dict(bound_args.arguments)
                    if 'self' in clean_args:
                        del clean_args['self']

                    formatted_title = _format_step_title(
                        self.title, args[1:] if func_self else args,
                        clean_args, func_self)

                    # Convert function parameters to Allure parameters format
                    function_parameters = []
                    for param_name, param_value in clean_args.items():
                        function_parameters.append({
                            "name": param_name,
                            "value": str(param_value)
                        })

                except Exception:
                    # Fallback to basic formatting
                    formatted_title = _format_step_title(self.title, args, kwargs, func_self)
                    # Fallback parameters from kwargs
                    function_parameters = []
                    for param_name, param_value in kwargs.items():
                        function_parameters.append({
                            "name": param_name,
                            "value": str(param_value)
                        })

                with AllureStep(formatted_title, parameters=function_parameters):
                    return func(*args, **kwargs)

            return wrapper  # type: ignore

    def _determine_vedro_step_from_callstack(self) -> Optional[str]:
        """
        Try to determine the current Vedro step by analyzing the call stack.

        This looks for Vedro step methods in the call stack (methods starting with
        given_, when_, then_, and_) to determine which step is currently executing.

        Returns:
            Name of the Vedro step if found, None otherwise
        """
        try:
            # Get the current call stack
            stack = inspect.stack()

            # Look through the stack for Vedro step methods
            for frame_info in stack:
                frame = frame_info.frame
                function_name = frame_info.function

                # Check if this looks like a Vedro step method
                if (function_name.startswith(('given_', 'when_', 'then_', 'and_')) and
                        'self' in frame.f_locals):
                    # Convert method name to readable step name
                    step_name = function_name.replace('_', ' ')
                    return step_name

        except Exception:
            # If anything goes wrong with stack inspection, just continue
            pass

        return None

    def __enter__(self) -> str:
        """Context manager entry."""
        self._step_uuid = str(uuid4())

        # Create step result
        self._step_result = TestStepResult(name=self.title, start=now())
        self._step_result.uuid = self._step_uuid
        if self.parameters:
            self._step_result.parameters = self.parameters

        # Try to determine current Vedro step from call stack
        current_vedro_step = self._determine_vedro_step_from_callstack()
        if current_vedro_step:
            _step_context._local.current_vedro_step = current_vedro_step

        # Get parent step for nesting
        parent_step = _step_context.get_current_step_object()

        # Add to step stack
        _step_context.push_step(self._step_uuid, self._step_result)

        # If this is a nested step, add to parent's steps
        if parent_step:
            if not hasattr(parent_step, 'steps') or parent_step.steps is None:
                parent_step.steps = []
            parent_step.steps.append(self._step_result)
        else:
            # This is a top-level step, add to recorded steps for the reporter
            # But don't group by Vedro step if we're in a decorator context
            _step_context.add_recorded_step(self._step_result)

        return self._step_uuid

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit."""
        if self._step_uuid and hasattr(self, '_step_result'):
            # Complete step result with stop time and status
            self._step_result.stop = now()
            if exc_type is not None:
                self._step_result.status = "failed"
                if (not hasattr(self._step_result, 'statusDetails') or
                        self._step_result.statusDetails is None):
                    self._step_result.statusDetails = {}
                self._step_result.statusDetails.update({
                    "message": str(exc_val) if exc_val else str(exc_type.__name__),
                    "trace": (f"{exc_type.__name__}: {exc_val}" if exc_val else
                              str(exc_type.__name__))
                })
            else:
                self._step_result.status = "passed"

            # Remove from step stack
            _step_context.pop_step()


def allure_step(title: str, parameters: Optional[List[dict]] = None) -> AllureStep:
    """
    Create an Allure step that can be used as both decorator and context manager.

    Args:
        title: The title of the step to display in Allure reports.
               Can contain placeholders like {param_name} for parameter substitution.
               Also supports {attr_name} for accessing method's self attributes.
        parameters: Optional list of parameter dictionaries (for context manager usage).

    Returns:
        AllureStep instance that can be used as decorator or context manager
    """
    return AllureStep(title, parameters)
