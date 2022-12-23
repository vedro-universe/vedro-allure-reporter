import json
import os
from hashlib import blake2b
from mimetypes import guess_extension
from pathlib import Path
from time import time
from typing import Any, Dict, List, Tuple, Type, Union

import allure_commons.utils as utils
from allure_commons import plugin_manager
from allure_commons._core import MetaPluginManager
from allure_commons.logger import AllureFileLogger
from allure_commons.model2 import ATTACHMENT_PATTERN
from allure_commons.model2 import Attachment as AllureAttachment
from allure_commons.model2 import Label, Status, StatusDetails, TestResult, TestStepResult
from allure_commons.types import LabelType
from allure_commons.utils import format_exception, format_traceback
from vedro.core import (
    Artifact,
    Dispatcher,
    FileArtifact,
    MemoryArtifact,
    PluginConfig,
    ScenarioResult,
    StepResult,
    StepStatus,
    VirtualScenario,
)
from vedro.events import ArgParsedEvent, ArgParseEvent, ScenarioReportedEvent
from vedro.plugins.director import DirectorInitEvent, Reporter

__all__ = ("AllureReporter", "AllureReporterPlugin",)


class AllureReporterPlugin(Reporter):
    def __init__(self, config: Type["AllureReporter"], *,
                 plugin_manager: MetaPluginManager = plugin_manager,
                 logger_factory: Any = AllureFileLogger) -> None:
        super().__init__(config)
        self._plugin_manager = plugin_manager
        self._logger_factory = logger_factory
        self._logger: Union[AllureFileLogger, None] = None
        self._test_result: Union[TestResult, None] = None
        self._project_name = config.project_name
        self._report_dir = config.report_dir
        self._attach_scope = config.attach_scope
        self._attach_artifacts = config.attach_artifacts
        self._config_labels = config.labels

    def subscribe(self, dispatcher: Dispatcher) -> None:
        super().subscribe(dispatcher)
        dispatcher.listen(DirectorInitEvent, lambda e: e.director.register("allure", self))

    def on_chosen(self) -> None:
        assert isinstance(self._dispatcher, Dispatcher)
        self._dispatcher.listen(ArgParseEvent, self.on_arg_parse) \
                        .listen(ArgParsedEvent, self.on_arg_parsed) \
                        .listen(ScenarioReportedEvent, self.on_scenario_reported)

    def on_arg_parse(self, event: ArgParseEvent) -> None:
        group = event.arg_parser.add_argument_group("Allure Reporter")

        group.add_argument("--allure-report-dir",
                           default=self._report_dir,
                           type=Path,
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

    def on_scenario_reported(self, event: ScenarioReportedEvent) -> None:
        aggregated_result = event.aggregated_result
        if aggregated_result.is_passed():
            self._report_result(aggregated_result, Status.PASSED)
        elif aggregated_result.is_failed():
            self._report_result(aggregated_result, Status.FAILED)
        elif aggregated_result.is_skipped():
            self._report_result(aggregated_result, Status.SKIPPED)

    def _to_seconds(self, elapsed: float) -> int:
        return int(elapsed * 1000)

    def _create_labels(self, scenario: VirtualScenario) -> List[Label]:
        path = os.path.dirname(os.path.relpath(scenario.path))
        package = path.replace("/", ".")

        labels = [
            Label(LabelType.FRAMEWORK, "vedro"),
            Label("package", package),
            Label(LabelType.SUITE, "scenarios"),
        ]
        if self._project_name:
            labels.append(Label("project_name", self._project_name))
        if self._config_labels:
            for label in self._config_labels:
                labels.append(label)

        scenario_tags = self._get_scenario_tags(scenario)
        for tag in scenario_tags:
            labels.append(Label(LabelType.TAG, tag))

        scenario_labels = self._get_scenario_labels(scenario)
        for label in scenario_labels:
            labels.append(Label(label.name, label.value))

        return labels

    def _get_scenario_tags(self, scenario: VirtualScenario) -> Tuple[str, ...]:
        return getattr(scenario._orig_scenario, "tags", ())

    def _get_scenario_labels(self, scenario: VirtualScenario) -> Tuple[Label, ...]:
        template = getattr(scenario._orig_scenario, "__vedro__template__", None)
        return getattr(template or scenario._orig_scenario, "__vedro__allure_labels__", ())

    def _create_attachment(self, name: str, mime_type: str, ext: str) -> AllureAttachment:
        file_name = ATTACHMENT_PATTERN.format(prefix=utils.uuid4(), ext=ext)
        return AllureAttachment(name=name, source=file_name, type=mime_type)

    def _add_memory_attachment(self, artifact: MemoryArtifact) -> AllureAttachment:
        guessed = guess_extension(artifact.mime_type)
        ext = guessed.lstrip(".") if guessed else "unknown"
        attachment = self._create_attachment(artifact.name, artifact.mime_type, ext)

        self._plugin_manager.hook.report_attached_data(body=artifact.data,
                                                       file_name=attachment.source)

        return attachment

    def _add_file_attachment(self, artifact: FileArtifact) -> AllureAttachment:
        suffix = artifact.path.suffix
        ext = suffix.lstrip(".") if suffix else "unknown"
        attachment = self._create_attachment(artifact.name, artifact.mime_type, ext)

        self._plugin_manager.hook.report_attached_file(source=artifact.path,
                                                       file_name=attachment.source)

        return attachment

    def _add_attachments(self, result: Union[TestResult, TestStepResult],
                         artifacts: List[Artifact]) -> None:
        for artifact in artifacts:
            if isinstance(artifact, MemoryArtifact):
                attachment = self._add_memory_attachment(artifact)
            elif isinstance(artifact, FileArtifact):
                attachment = self._add_file_attachment(artifact)
            else:
                raise ValueError(f"Unknown artifact type {type(artifact)}")
            result.attachments.append(attachment)

    def _format_scope(self, scope: Dict[Any, Any], indent: int = 4) -> str:
        res = ""
        for key, val in scope.items():
            try:
                val_repr = json.dumps(val, ensure_ascii=False, indent=4)
            except:  # noqa: E722
                val_repr = repr(val)
            res += f"{indent * ' '}{key}:\n{val_repr}\n\n"
        return res

    def _get_scenario_unique_id(self, scenario: VirtualScenario) -> str:
        unique_id = f"{self._project_name}_{scenario.unique_id}"
        return blake2b(unique_id.encode(), digest_size=32).hexdigest()

    def _report_result(self, scenario_result: ScenarioResult, status: Status) -> None:
        test_result = TestResult()
        test_result.uuid = utils.uuid4()
        test_result.name = scenario_result.scenario.subject
        test_result.historyId = self._get_scenario_unique_id(scenario_result.scenario)
        test_result.testCaseId = self._get_scenario_unique_id(scenario_result.scenario)
        test_result.status = status
        test_result.start = self._to_seconds(scenario_result.started_at or time())
        test_result.stop = self._to_seconds(scenario_result.ended_at or time())

        test_result.labels.extend(self._create_labels(scenario_result.scenario))

        if self._attach_artifacts:
            self._add_attachments(test_result, scenario_result.artifacts)

        if self._attach_scope and (status != Status.SKIPPED):
            body = self._format_scope(scenario_result.scope or {})
            artifact = MemoryArtifact("Scope", "text/plain", body.encode())
            attachment = self._add_memory_attachment(artifact)
            test_result.attachments.append(attachment)

        for step_result in scenario_result.step_results:
            test_step_result = self._create_test_step_result(step_result)
            if step_result.exc_info:
                message = format_exception(step_result.exc_info.type, step_result.exc_info.value)
                trace = format_traceback(step_result.exc_info.traceback)
                test_result.statusDetails = StatusDetails(message=message, trace=trace)
            if self._attach_artifacts:
                self._add_attachments(test_step_result, step_result.artifacts)
            test_result.steps.append(test_step_result)

        self._plugin_manager.hook.report_result(result=test_result)

    def _create_test_step_result(self, step_result: StepResult) -> TestStepResult:
        test_step_result = TestStepResult()
        test_step_result.uuid = utils.uuid4()
        test_step_result.name = step_result.step_name.replace("_", " ")
        test_step_result.start = self._to_seconds(step_result.started_at or time())
        test_step_result.stop = self._to_seconds(step_result.ended_at or time())
        if step_result.status == StepStatus.PASSED:
            test_step_result.status = Status.PASSED
        elif step_result.status == StepStatus.FAILED:
            test_step_result.status = Status.FAILED
        return test_step_result


class AllureReporter(PluginConfig):
    plugin = AllureReporterPlugin

    # Set project name (adds label "project_name" and prefix for testCaseId)
    project_name: str = ""

    # Set directory for Allure reports
    report_dir: Path = Path("./allure_reports")

    # Attach scope to Allure report
    attach_scope: bool = False

    # Attach tags to Allure report
    attach_tags: bool = True

    # Attach artifacts to Allure report
    attach_artifacts: bool = True

    # Add custom labels to each scenario
    labels: List[Label] = []
