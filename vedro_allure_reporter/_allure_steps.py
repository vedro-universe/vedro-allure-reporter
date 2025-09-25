"""
Allure Steps Integration for Vedro Testing Framework

This module provides decorators and context managers for creating hierarchical steps
in Allure reports when using the Vedro testing framework.
"""

import functools
import inspect
import json
import sys
import threading
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

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


class AllureStepContext:
    """Thread-local context for managing Allure steps with hierarchical support."""

    def __init__(self) -> None:
        self._local = threading.local()

    def _ensure_initialized(self) -> None:
        """Ensure thread-local storage is initialized."""
        if not hasattr(self._local, 'initialized'):
            self._local.step_stack = []
            self._local.step_objects = []
            self._local.recorded_steps = []
            self._local.steps_by_vedro_step = {}
            self._local.current_step = None
            # Don't override current_vedro_step if it's already set
            if not hasattr(self._local, 'current_vedro_step'):
                self._local.current_vedro_step = None
            self._local.initialized = True

    def get_current_step(self) -> Optional[str]:
        """Get the current step UUID for this thread."""
        self._ensure_initialized()
        return getattr(self._local, 'current_step', None)

    def set_current_step(self, step_uuid: str) -> None:
        """Set the current step UUID for this thread."""
        self._ensure_initialized()
        self._local.current_step = step_uuid

    def clear_current_step(self) -> None:
        """Clear the current step UUID for this thread."""
        self._ensure_initialized()
        self._local.current_step = None

    def push_step(self, step_uuid: str, step_obj: TestStepResult) -> None:
        """Push a step UUID and object onto the step stack."""
        self._ensure_initialized()
        self._local.step_stack.append(step_uuid)
        self._local.step_objects.append(step_obj)
        self._local.current_step = step_uuid

    def pop_step(self) -> Optional[TestStepResult]:
        """Pop a step from the step stack and return the step object."""
        self._ensure_initialized()
        if not self._local.step_stack:
            self._local.current_step = None
            return None

        self._local.step_stack.pop()
        popped_step: Optional[TestStepResult] = self._local.step_objects.pop()

        # Set current step to the parent step (if any)
        self._local.current_step = self._local.step_stack[-1] if self._local.step_stack else None

        return popped_step

    def get_step_depth(self) -> int:
        """Get the current nesting depth of steps."""
        self._ensure_initialized()
        return len(self._local.step_stack)

    def get_current_step_object(self) -> Optional[TestStepResult]:
        """Get the current step object."""
        self._ensure_initialized()
        step_objects = getattr(self._local, 'step_objects', [])
        return step_objects[-1] if step_objects else None

    def get_recorded_steps(self) -> List[TestStepResult]:
        """Get all recorded steps for this thread."""
        self._ensure_initialized()
        return getattr(self._local, 'recorded_steps', [])

    def get_steps_by_vedro_step(self) -> Dict[str, List[TestStepResult]]:
        """Get recorded steps grouped by Vedro step name."""
        self._ensure_initialized()
        return getattr(self._local, 'steps_by_vedro_step', {})

    def get_current_vedro_step(self) -> Optional[str]:
        """Get current vedro step name."""
        self._ensure_initialized()
        return getattr(self._local, 'current_vedro_step', None)

    def add_recorded_step(self, step: TestStepResult) -> None:
        """Add a step to the recorded steps for this thread."""
        self._ensure_initialized()

        self._local.recorded_steps.append(step)

        # Also group by current Vedro step
        if self._local.current_vedro_step:
            vedro_steps = self._local.steps_by_vedro_step
            if self._local.current_vedro_step not in vedro_steps:
                vedro_steps[self._local.current_vedro_step] = []
            vedro_steps[self._local.current_vedro_step].append(step)

    def clear_recorded_steps(self) -> None:
        """Clear all recorded steps for this thread."""
        self._ensure_initialized()
        self._local.recorded_steps.clear()
        self._local.steps_by_vedro_step.clear()
        self._local.step_stack.clear()
        self._local.step_objects.clear()
        self._local.current_vedro_step = None
        self._local.current_step = None


# Global thread-local step context
_step_context = AllureStepContext()


def set_current_vedro_step(step_name: str) -> None:
    """
    Set the current Vedro step name for proper step grouping.

    This should be called by AllureReporter when a Vedro step starts executing.

    Args:
        step_name: Name of the Vedro step that is starting
    """
    _step_context._ensure_initialized()
    _step_context._local.current_vedro_step = step_name


def clear_current_vedro_step() -> None:
    """
    Clear the current Vedro step name.

    This should be called by AllureReporter when a Vedro step finishes executing.
    """
    _step_context._ensure_initialized()
    _step_context._local.current_vedro_step = None


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

    attachment = create_file_attachment(file_path, name or file_path.name)
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
        param["excluded"] = True  # type: ignore[assignment]

    return param


def _format_step_title(title: str, func_args: Tuple[Any, ...],
                       func_kwargs: Dict[str, Any], func_self: Any = None) -> str:
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


def _extract_function_parameters(
        func: Callable[..., Any], args: Tuple[Any, ...], kwargs: Dict[str, Any]
) -> Tuple[Any, Dict[str, Any], List[Dict[str, str]]]:
    """
    Extract and format function parameters for Allure reporting.

    Returns:
        Tuple of (func_self, formatted_title_kwargs, function_parameters)
    """
    # Extract self if this is a method call
    func_self = args[0] if args and hasattr(args[0], '__dict__') else None

    try:
        sig = inspect.signature(func)
        bound_args = sig.bind(*args, **kwargs)
        bound_args.apply_defaults()

        # Remove 'self' from arguments for cleaner parameter mapping
        clean_args = dict(bound_args.arguments)
        if 'self' in clean_args:
            del clean_args['self']

        # Convert function parameters to Allure parameters format
        function_parameters = [
            {"name": param_name, "value": str(param_value)}
            for param_name, param_value in clean_args.items()
        ]

        return func_self, clean_args, function_parameters

    except Exception:
        # Fallback to basic parameter extraction
        function_parameters = [
            {"name": param_name, "value": str(param_value)}
            for param_name, param_value in kwargs.items()
        ]
        return func_self, kwargs, function_parameters


def _create_contextmanager_parameters(
        func: Callable[..., Any], args: Tuple[Any, ...], kwargs: Dict[str, Any]
) -> Tuple[Dict[str, Any], List[Dict[str, str]]]:
    """
    Create parameter mapping for context manager functions.

    Returns:
        Tuple of (format_kwargs, function_parameters)
    """
    format_kwargs = kwargs.copy()

    # Try to get parameter names from original function
    try:
        original_func = func.__wrapped__ if hasattr(func, '__wrapped__') else func
        sig = inspect.signature(original_func)
        param_names = list(sig.parameters.keys())

        # Map positional arguments to parameter names
        for i, arg in enumerate(args):
            if i < len(param_names):
                format_kwargs[param_names[i]] = arg
    except Exception:
        # Fallback: use generic arg names
        for i, arg in enumerate(args):
            format_kwargs[f'arg{i}'] = arg

    # Create function parameters for Allure
    function_parameters = [
        {"name": param_name, "value": str(param_value)}
        for param_name, param_value in format_kwargs.items()
    ]

    return format_kwargs, function_parameters


class _AllureStepContextManagerWrapper:
    """
    Reusable context manager wrapper for Allure steps.

    Moved outside of __call__ method to avoid recreation on every function call.
    """

    def __init__(self, cm: Any, title: str, parameters: Optional[List[Dict[str, str]]]) -> None:
        self.cm = cm
        self.title = title
        self.parameters = parameters
        self.allure_step: Optional["AllureStep"] = None

    def __enter__(self) -> Any:
        # Start the Allure step first
        self.allure_step = AllureStep(self.title, self.parameters)
        self.allure_step.__enter__()

        # Then enter the wrapped context manager
        try:
            result = self.cm.__enter__()
            return result
        except Exception:
            # If cm.__enter__ fails, we need to clean up the AllureStep
            if self.allure_step:
                self.allure_step.__exit__(*sys.exc_info())
            raise

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> Any:
        # First exit the wrapped context manager
        try:
            cm_result = self.cm.__exit__(exc_type, exc_val, exc_tb)
        except Exception:
            # If cm.__exit__ raises an exception, we still need to exit AllureStep
            if self.allure_step:
                self.allure_step.__exit__(*sys.exc_info())
            raise

        # Then exit the Allure step
        if self.allure_step:
            self.allure_step.__exit__(exc_type, exc_val, exc_tb)

        # Return the original context manager's exit result
        return cm_result


class _GeneratorContextManager:
    """
    Reusable context manager for generator objects.
    """

    def __init__(self, gen: Any) -> None:
        self.gen = gen
        self.value: Any = None

    def __enter__(self) -> Any:
        try:
            self.value = next(self.gen)
            return self.value
        except StopIteration:
            return None

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        try:
            next(self.gen)
        except StopIteration:
            pass


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

    def __init__(self, title: str, parameters: Optional[List[Dict[str, Any]]] = None):
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

    def _is_contextmanager_function(self, func: Callable[..., Any]) -> bool:
        """
        Check if function is decorated with @contextlib.contextmanager.
        Works regardless of decorator order. Optimized version.
        """
        # Method 1: Direct check for __wrapped__ (most reliable and fast)
        if hasattr(func, '__wrapped__'):
            return True

        # Method 2: Check for generator function characteristics
        # contextmanager decorator typically works with generator functions
        if inspect.isgeneratorfunction(func):
            return True

        # Method 3: Check wrapped function for generator characteristics
        wrapped_func = getattr(func, '__wrapped__', None)
        if wrapped_func and inspect.isgeneratorfunction(wrapped_func):
            return True

        return False

    def _handle_contextmanager_function(self, func: Callable[..., Any]) -> Callable[..., Any]:
        """Handle context manager function decoration."""
        @functools.wraps(func)
        def context_manager_wrapper(*args: Any, **kwargs: Any) -> Any:
            # Get parameter mapping and function parameters
            format_kwargs, function_parameters = _create_contextmanager_parameters(
                func, args, kwargs)

            # Format title with parameters
            try:
                formatted_title = self.title.format(**format_kwargs)
            except (KeyError, ValueError):
                formatted_title = self.title

            # Get the actual context manager instance by calling the decorated function
            cm_instance = func(*args, **kwargs)

            # Check what type of object we got back
            if hasattr(cm_instance, '__enter__') and hasattr(cm_instance, '__exit__'):
                # For @allure_step -> @contextlib.contextmanager order,
                # cm_instance is already a proper context manager
                return _AllureStepContextManagerWrapper(
                    cm_instance, formatted_title, function_parameters)

            elif hasattr(cm_instance, '__next__') and hasattr(cm_instance, '__iter__'):
                # For @contextlib.contextmanager -> @allure_step order,
                # func() returns a generator, not a context manager
                cm_instance = _GeneratorContextManager(cm_instance)

                # Need to return a generator that contextlib.contextmanager can work with
                def allure_step_generator() -> Any:
                    # Start the Allure step
                    with AllureStep(formatted_title, function_parameters):
                        # Use the original context manager
                        with cm_instance as value:
                            yield value

                return allure_step_generator()
            else:
                # Fall back to regular function decoration
                with AllureStep(self.title, self.parameters):
                    return func(*args, **kwargs)

        return context_manager_wrapper

    def __call__(self, func: Callable[..., Any]) -> Callable[..., Any]:
        """Use as decorator."""
        # Check if this is a context manager function (works with any decorator order)
        if self._is_contextmanager_function(func):
            return self._handle_contextmanager_function(func)
        # Check if this is a generator function (fallback for edge cases)
        elif inspect.isgeneratorfunction(func):
            return self._handle_generator_function(func)

        elif inspect.iscoroutinefunction(func):
            return self._handle_async_function(func)

        else:
            return self._handle_sync_function(func)

    def _handle_generator_function(self, func: Callable[..., Any]) -> Callable[..., Any]:
        """Handle generator function decoration."""
        @functools.wraps(func)
        def generator_wrapper(*args: Any, **kwargs: Any) -> Any:
            # Extract self if this is a method call
            func_self = args[0] if args and hasattr(args[0], '__dict__') else None
            formatted_title = _format_step_title(self.title, args, kwargs, func_self)

            with AllureStep(formatted_title, self.parameters):
                return func(*args, **kwargs)

        return generator_wrapper

    def _handle_async_function(self, func: Callable[..., Any]) -> Callable[..., Any]:
        """Handle async function decoration."""
        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            func_self, clean_args, function_parameters = _extract_function_parameters(
                func, args, kwargs)

            formatted_title = _format_step_title(
                self.title, args[1:] if func_self else args,
                clean_args, func_self)

            with AllureStep(formatted_title, parameters=function_parameters):
                return await func(*args, **kwargs)

        return async_wrapper

    def _handle_sync_function(self, func: Callable[..., Any]) -> Callable[..., Any]:
        """Handle sync function decoration."""
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            func_self, clean_args, function_parameters = _extract_function_parameters(
                func, args, kwargs)

            formatted_title = _format_step_title(
                self.title, args[1:] if func_self else args,
                clean_args, func_self)

            with AllureStep(formatted_title, parameters=function_parameters):
                return func(*args, **kwargs)

        return wrapper

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
        self._step_uuid = str(uuid4())  # type: ignore[no-untyped-call]

        # Create step result
        self._step_result = TestStepResult(name=self.title,
                                           start=now())  # type: ignore[no-untyped-call]
        if hasattr(self._step_result, 'uuid'):
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
        if self._step_uuid and self._step_result is not None:
            # Complete step result with stop time and status
            self._step_result.stop = now()  # type: ignore[no-untyped-call]
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


def allure_step(title: str, parameters: Optional[List[Dict[str, Any]]] = None) -> AllureStep:
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
