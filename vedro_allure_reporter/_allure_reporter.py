import os
from typing import Any, Union, cast

from allure_commons import plugin_manager
from allure_commons._core import MetaPluginManager
from allure_commons.logger import AllureFileLogger
from allure_commons.model2 import Label, Status, StatusDetails, TestResult, TestStepResult
from allure_commons.utils import format_exception, format_traceback, now, uuid4
from vedro._core import Dispatcher, ScenarioResult, StepResult
from vedro.events import (
    ArgParsedEvent,
    ArgParseEvent,
    CleanupEvent,
    ScenarioFailedEvent,
    ScenarioPassedEvent,
    ScenarioRunEvent,
    ScenarioSkippedEvent,
    StepFailedEvent,
    StepPassedEvent,
    StepRunEvent,
)
from vedro.plugins.director import Reporter

__all__ = ("AllureReporter",)


class AllureReporter(Reporter):
    def __init__(self, plugin_manager: MetaPluginManager = plugin_manager,
                 logger_factory: Any = AllureFileLogger) -> None:
        self._plugin_manager = plugin_manager
        self._logger_factory = logger_factory
        self._logger: Union[AllureFileLogger, None] = None
        self._test_result: Union[TestResult, None] = None
        self._test_step_result: Union[TestStepResult, None] = None
        self._report_dir = "reports"

    def subscribe(self, dispatcher: Dispatcher) -> None:
        dispatcher.listen(ArgParseEvent, self.on_arg_parse) \
                  .listen(ArgParsedEvent, self.on_arg_parsed) \
                  .listen(ScenarioRunEvent, self.on_scenario_run) \
                  .listen(ScenarioSkippedEvent, self.on_scenario_skipped) \
                  .listen(ScenarioFailedEvent, self.on_scenario_failed) \
                  .listen(ScenarioPassedEvent, self.on_scenario_passed) \
                  .listen(StepRunEvent, self.on_step_run) \
                  .listen(StepFailedEvent, self.on_step_failed) \
                  .listen(StepPassedEvent, self.on_step_passed) \
                  .listen(CleanupEvent, self.on_cleanup)

    def on_arg_parse(self, event: ArgParseEvent) -> None:
        event.arg_parser.add_argument("--allure-report-dir",
                                      default=self._report_dir,
                                      help="")

    def on_arg_parsed(self, event: ArgParsedEvent) -> None:
        self._report_dir = event.args.allure_report_dir
        self._plugin_manager.register(self)
        self._logger = self._logger_factory(self._report_dir, clean=True)
        self._plugin_manager.register(self._logger)

    def _to_seconds(self, elapsed: float) -> int:
        return int(elapsed * 1000)

    def _start_scenario(self, scenario_result: ScenarioResult) -> TestResult:
        test_result = TestResult()
        test_result.uuid = uuid4()
        test_result.name = scenario_result.scenario_subject
        path = os.path.dirname(os.path.relpath(scenario_result.scenario.path))
        test_result.labels.append(
            Label(name="package", value=path.replace("/", "."))
        )
        return test_result

    def _stop_scenario(self, test_result: TestResult,
                       scenario_result: ScenarioResult, status: Status) -> None:
        test_result.status = status
        test_result.start = self._to_seconds(scenario_result.started_at or now())
        test_result.stop = self._to_seconds(scenario_result.ended_at or now())
        self._plugin_manager.hook.report_result(result=test_result)

    def _start_step(self, test_result: TestResult, step_result: StepResult) -> TestStepResult:
        test_step_result = TestStepResult()
        test_step_result.uuid = uuid4()
        test_step_result.name = step_result.step_name
        test_result.steps.append(test_step_result)
        return test_step_result

    def _stop_step(self, test_step_result: TestStepResult,
                   step_result: StepResult, status: Status) -> None:
        test_step_result.status = status
        test_step_result.start = self._to_seconds(step_result.started_at or now())
        test_step_result.stop = self._to_seconds(step_result.ended_at or now())

    def on_scenario_run(self, event: ScenarioRunEvent) -> None:
        self._test_result = self._start_scenario(event.scenario_result)

    def on_scenario_skipped(self, event: ScenarioRunEvent) -> None:
        self._test_result = self._start_scenario(event.scenario_result)
        self._stop_scenario(self._test_result, event.scenario_result, Status.SKIPPED)

    def on_scenario_failed(self, event: ScenarioFailedEvent) -> None:
        self._stop_scenario(self._test_result, event.scenario_result, Status.FAILED)

    def on_scenario_passed(self, event: ScenarioPassedEvent) -> None:
        self._stop_scenario(self._test_result, event.scenario_result, Status.PASSED)

    def on_step_run(self, event: StepRunEvent) -> None:
        self._test_step_result = self._start_step(self._test_result, event.step_result)

    def on_step_failed(self, event: StepFailedEvent) -> None:
        self._stop_step(self._test_step_result, event.step_result, Status.FAILED)

        exc_info = event.step_result.exc_info
        if exc_info:
            message = format_exception(exc_info.type, exc_info.value)
            trace = format_traceback(exc_info.traceback)
            details = StatusDetails(message=message, trace=trace)
            cast(TestResult, self._test_result).statusDetails = details

    def on_step_passed(self, event: StepPassedEvent) -> None:
        self._stop_step(self._test_step_result, event.step_result, Status.PASSED)

    def on_cleanup(self, event: CleanupEvent) -> None:
        pass
