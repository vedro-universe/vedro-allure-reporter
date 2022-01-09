import json
import os
from typing import Any, Dict, Union, cast

import allure_commons.utils as utils
from allure_commons import plugin_manager
from allure_commons._core import MetaPluginManager
from allure_commons.logger import AllureFileLogger
from allure_commons.model2 import (
    ATTACHMENT_PATTERN,
    Attachment,
    Label,
    Status,
    StatusDetails,
    TestResult,
    TestStepResult,
)
from allure_commons.types import AttachmentType, LabelType
from allure_commons.utils import format_exception, format_traceback
from vedro.core import Dispatcher, ScenarioResult, StepResult
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
        self._report_dir = None
        self._attach_scope = False

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
        group = event.arg_parser.add_argument_group("Allure Reporter")

        group.add_argument("--allure-report-dir",
                           required=True,
                           help="Set directory for Allure reports")
        group.add_argument("--allure-attach-scope",
                           action='store_true',
                           default=self._attach_scope,
                           help="Attach scope to Allure report")

    def on_arg_parsed(self, event: ArgParsedEvent) -> None:
        self._report_dir = event.args.allure_report_dir
        self._attach_scope = event.args.allure_attach_scope

        self._plugin_manager.register(self)
        self._logger = self._logger_factory(self._report_dir, clean=True)
        self._plugin_manager.register(self._logger)

    def _to_seconds(self, elapsed: float) -> int:
        return int(elapsed * 1000)

    def _start_scenario(self, scenario_result: ScenarioResult) -> TestResult:
        test_result = TestResult()
        test_result.uuid = utils.uuid4()
        test_result.name = scenario_result.scenario.subject
        test_result.historyId = scenario_result.scenario.unique_id
        test_result.testCaseId = scenario_result.scenario.unique_id

        path = os.path.dirname(os.path.relpath(scenario_result.scenario.path))
        package = path.replace("/", ".")
        test_result.labels.extend([
            Label(name="package", value=package),
            Label(name=LabelType.SUITE, value="scenarios"),
        ])

        return test_result

    def _create_attachment(self, name: str, type_: AttachmentType) -> Attachment:
        file_name = ATTACHMENT_PATTERN.format(prefix=utils.uuid4(), ext=type_.extension)
        return Attachment(name=name, source=file_name, type=type_.mime_type)

    def _format_scope(self, scope: Dict[Any, Any], indent: int = 4) -> str:
        res = ""
        for key, val in scope.items():
            try:
                val_repr = json.dumps(val, ensure_ascii=False, indent=4)
            except:  # noqa: E722
                val_repr = repr(val)
            res += f"{indent * ' '}{key}:\n{val_repr}\n\n"
        return res

    def _stop_scenario(self, test_result: TestResult,
                       scenario_result: ScenarioResult, status: Status) -> None:
        test_result.status = status
        test_result.start = self._to_seconds(scenario_result.started_at or utils.now())
        test_result.stop = self._to_seconds(scenario_result.ended_at or utils.now())

        if self._attach_scope:
            body = self._format_scope(scenario_result.scope or {})
            attachment = self._create_attachment("Scope", AttachmentType.TEXT)
            test_result.attachments.append(attachment)

            self._plugin_manager.hook.report_attached_data(body=body, file_name=attachment.source)

        self._plugin_manager.hook.report_result(result=test_result)

    def _start_step(self, test_result: TestResult, step_result: StepResult) -> TestStepResult:
        test_step_result = TestStepResult()
        test_step_result.uuid = utils.uuid4()
        test_step_result.name = step_result.step_name.replace("_", " ")
        test_result.steps.append(test_step_result)
        return test_step_result

    def _stop_step(self, test_step_result: TestStepResult,
                   step_result: StepResult, status: Status) -> None:
        test_step_result.status = status
        test_step_result.start = self._to_seconds(step_result.started_at or utils.now())
        test_step_result.stop = self._to_seconds(step_result.ended_at or utils.now())

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
