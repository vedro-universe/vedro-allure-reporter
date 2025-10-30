from typing import Any, Dict, Optional

from allure_commons._hooks import hookimpl
from allure_commons.model2 import Parameter, Status, StatusDetails, TestStepResult
from allure_commons.reporter import AllureReporter as AllureCommonsReporter
from allure_commons.utils import format_exception, format_traceback, now, uuid4

__all__ = ("AllureStepHooks",)


class AllureStepHooks:
    """
    Explicit hooks for allure.step() decorator support.

    This class implements the allure_commons hook interface to provide
    support for @allure.step decorators and allure.attach() functions.
    It must be registered with allure_commons plugin_manager to work.
    """

    def __init__(self, reporter: AllureCommonsReporter) -> None:
        """
        Initialize AllureStepHooks with an AllureCommonsReporter instance.

        :param reporter: The AllureCommonsReporter instance used to manage steps and attachments.
        """
        self._reporter = reporter

    @hookimpl
    def start_step(self, uuid: str, title: str, params: Dict[str, Any]) -> None:
        """
        Hook implementation for starting a step in @allure.step decorator.

        Called when entering a context decorated with @allure.step.

        :param uuid: Unique identifier for the step.
        :param title: Title/name of the step.
        :param params: Parameters passed to the step function.
        """
        parameters = [Parameter(name=name, value=value)
                      for name, value in params.items()]
        step = TestStepResult(
            name=title,
            start=now(),  # type: ignore[no-untyped-call]
            parameters=parameters
        )
        self._reporter.start_step(None, uuid, step)  # type: ignore

    @hookimpl
    def stop_step(self, uuid: str, exc_type: Optional[type],
                  exc_val: Optional[BaseException], exc_tb: Any) -> None:
        """
        Hook implementation for stopping a step in @allure.step decorator.

        Called when exiting a context decorated with @allure.step.

        :param uuid: Unique identifier for the step.
        :param exc_type: Type of exception if one occurred, None otherwise.
        :param exc_val: Exception instance if one occurred, None otherwise.
        :param exc_tb: Exception traceback if one occurred, None otherwise.
        """
        # Determine status based on exception
        if exc_val:
            if isinstance(exc_val, AssertionError):
                status = Status.FAILED
            else:
                status = Status.BROKEN
        else:
            status = Status.PASSED

        # Create status details if there's an exception
        status_details = None
        if exc_type and exc_val:
            message = format_exception(exc_type, exc_val)  # type: ignore
            trace = format_traceback(exc_tb)  # type: ignore
            if message or trace:
                status_details = StatusDetails(message=message, trace=trace)

        self._reporter.stop_step(  # type: ignore
            uuid,
            stop=now(),  # type: ignore
            status=status,
            statusDetails=status_details
        )

    @hookimpl
    def attach_data(self, body: bytes, name: str,
                    attachment_type: str, extension: str) -> None:
        """
        Hook implementation for allure.attach() to attach data.

        :param body: The attachment data as bytes.
        :param name: Name of the attachment.
        :param attachment_type: MIME type of the attachment.
        :param extension: File extension for the attachment.
        """
        self._reporter.attach_data(  # type: ignore
            uuid4(),  # type: ignore
            body,
            name=name,
            attachment_type=attachment_type,
            extension=extension
        )

    @hookimpl
    def attach_file(self, source: str, name: str,
                    attachment_type: str, extension: str) -> None:
        """
        Hook implementation for allure.attach.file() to attach files.

        :param source: Path to the file to attach.
        :param name: Name of the attachment.
        :param attachment_type: MIME type of the attachment.
        :param extension: File extension for the attachment.
        """
        self._reporter.attach_file(  # type: ignore
            uuid4(),  # type: ignore
            source,
            name=name,
            attachment_type=attachment_type,
            extension=extension
        )
