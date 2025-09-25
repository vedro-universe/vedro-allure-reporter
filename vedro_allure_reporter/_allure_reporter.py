import json
import os
from hashlib import blake2b
from pathlib import Path
from time import time
from traceback import format_exception
from types import TracebackType
from typing import Any, Dict, List, Tuple, Type, Union

import allure_commons.utils as utils
import vedro
from allure_commons import plugin_manager
from allure_commons._core import MetaPluginManager
from allure_commons.logger import AllureFileLogger
from allure_commons.model2 import Attachment as AllureAttachment
from allure_commons.model2 import Label, Status, StatusDetails, TestResult, TestStepResult
from allure_commons.types import LabelType
from niltype import Nil
from vedro.core import (
    Artifact,
    Dispatcher,
    ExcInfo,
    FileArtifact,
    MemoryArtifact,
    PluginConfig,
    ScenarioResult,
    StepResult,
    StepStatus,
    VirtualScenario,
)
from vedro.events import ArgParsedEvent, ArgParseEvent, ScenarioReportedEvent, StartupEvent
from vedro.plugins.director import DirectorInitEvent, Reporter

from ._allure_attachments import (
    create_attachment,
    create_file_attachment,
    create_memory_attachment,
)
from .allure_rerunner import AllureRerunner, AllureRerunnerPlugin

__all__ = ("AllureReporter", "AllureReporterPlugin",)


class AllureReporterPlugin(Reporter):
    """
    Integrates Allure reporting.

    This plugin generates Allure-compatible test reports. It handles attaching artifacts
    and scope data, configuring Allure settings, and filtering scenarios based on labels.
    """

    def __init__(self, config: Type["AllureReporter"], *,
                 plugin_manager: MetaPluginManager = plugin_manager,
                 logger_factory: Any = AllureFileLogger) -> None:
        """
        Initialize the AllureReporterPlugin instance with configuration settings.

        :param config: Configuration class for Allure reporting.
        :param plugin_manager: Plugin manager for managing Allure plugins.
        :param logger_factory: Factory method for creating the AllureFileLogger instance.
        """
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
        self._clean_report_dir = config.clean_report_dir
        self._report_rescheduled_scenarios = config.report_rescheduled_scenarios
        self._allure_labels: Union[str, None] = None
        self._allure_rerunner = AllureRerunnerPlugin(AllureRerunner)

    async def on_startup(self, event: StartupEvent) -> None:
        """
        Handle the startup event and filter scenarios based on Allure labels.

        :param event: The startup event from Vedro's lifecycle.
        """
        if self._allure_labels is None:
            return

        labels = set()
        for label_str in self._allure_labels:
            name, value = label_str.split("=")
            label = (name.lower(), value)
            labels.add(label)

        async for scenario in event.scheduler:
            scenario_labels = set([(label.name.lower(), label.value)
                                   for label in self._get_scenario_labels(scenario)])
            if not labels.issubset(scenario_labels):
                event.scheduler.ignore(scenario)

    def subscribe(self, dispatcher: Dispatcher) -> None:
        """
        Subscribe to relevant Vedro events and register the reporter with the dispatcher.

        :param dispatcher: The dispatcher used to listen to Vedro events.
        """
        super().subscribe(dispatcher)
        dispatcher.listen(DirectorInitEvent, lambda e: e.director.register("allure", self))
        dispatcher.listen(ArgParseEvent, self.on_subscribe_arg_parse)
        dispatcher.listen(ArgParsedEvent, self.on_subscribe_arg_parsed)
        dispatcher.listen(StartupEvent, self.on_startup)

        self._allure_rerunner.subscribe(dispatcher)

    def on_chosen(self) -> None:
        """
        Handle the reporter being chosen and set up event listeners for ArgParse
        and ScenarioReported events.
        """
        assert isinstance(self._dispatcher, Dispatcher)
        self._dispatcher.listen(ArgParseEvent, self.on_chosen_arg_parse) \
                        .listen(ArgParsedEvent, self.on_chosen_arg_parsed) \
                        .listen(ScenarioReportedEvent, self.on_scenario_reported)

    def on_chosen_arg_parse(self, event: ArgParseEvent) -> None:
        """
        Add Allure-specific command-line arguments when the reporter is chosen.

        :param event: The ArgParse event containing the argument parser.
        """
        group = event.arg_parser.add_argument_group("Allure Reporter")

        group.add_argument("--allure-report-dir",
                           default=self._report_dir,
                           type=Path,
                           help="Set directory for Allure reports")
        group.add_argument("--allure-attach-scope",
                           action='store_true',
                           default=self._attach_scope,
                           help="Attach scope to Allure report")

    def on_subscribe_arg_parse(self, event: ArgParseEvent) -> None:
        """
        Add Allure-specific command-line arguments when the reporter is subscribed.

        :param event: The ArgParse event containing the argument parser.
        """
        group = event.arg_parser.add_argument_group("Allure Reporter")
        group.add_argument("--allure-labels",
                           default=None,
                           nargs="+",
                           help="Run tests with specific Allure labels")

    def on_chosen_arg_parsed(self, event: ArgParsedEvent) -> None:
        """
        Parse command-line arguments and configure the Allure reporter.

        :param event: The ArgParsed event containing parsed arguments.
        """
        self._report_dir = event.args.allure_report_dir
        self._attach_scope = event.args.allure_attach_scope
        self._allure_labels = event.args.allure_labels

        self._plugin_manager.register(self)
        self._logger = self._logger_factory(self._report_dir, clean=self._clean_report_dir)
        self._plugin_manager.register(self._logger)

        if getattr(event.args, "reruns", None):
            print(
                "⚠️ AllureReporterPlugin: "
                "Use '--allure-reruns' instead of '--reruns' for proper Allure-compliant rerun "
                "reporting, ensuring that the final scenario status aligns with Allure logic"
            )

    def on_subscribe_arg_parsed(self, event: ArgParsedEvent) -> None:
        """
        Parse Allure-specific command-line arguments for subscribed reporters.

        :param event: The ArgParsed event containing parsed arguments.
        """
        self._allure_labels = event.args.allure_labels

    def on_scenario_reported(self, event: ScenarioReportedEvent) -> None:
        """
        Report the scenario results to Allure, including status and attachments.

        :param event: The ScenarioReported event containing scenario results.
        """
        aggregated_result = event.aggregated_result
        if self._report_rescheduled_scenarios:
            for scenario_result in aggregated_result.scenario_results:
                self._report_result(scenario_result,
                                    self._get_scenario_result_status(scenario_result))
        else:
            self._report_result(aggregated_result,
                                self._get_scenario_result_status(aggregated_result))

    def _get_scenario_result_status(self, scenario_result: ScenarioResult) -> str:
        """
        Retrieve the Allure status of a scenario result based on its status.

        :param scenario_result: The ScenarioResult object containing scenario data.
        :return: The Allure status of the scenario (PASSED, FAILED, SKIPPED).
        """
        if scenario_result.is_passed():
            return Status.PASSED
        elif scenario_result.is_failed():
            return Status.FAILED
        elif scenario_result.is_skipped():
            return Status.SKIPPED
        else:
            return Status.UNKNOWN

    def _to_seconds(self, elapsed: float) -> int:
        """
        Convert elapsed time from seconds to milliseconds.

        :param elapsed: The time duration in seconds.
        :return: The time duration in milliseconds.
        """
        return int(elapsed * 1000)

    def _create_labels(self, scenario: VirtualScenario) -> List[Label]:
        """
        Create labels for the given scenario to be included in the Allure report.

        :param scenario: The VirtualScenario instance containing scenario details.
        :return: A list of Label objects for the scenario.
        """
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
        """
        Retrieve the tags associated with the given scenario.

        :param scenario: The VirtualScenario instance containing scenario details.
        :return: A tuple of tags associated with the scenario.
        """
        return getattr(scenario._orig_scenario, "tags", ())

    def _get_scenario_labels(self, scenario: VirtualScenario) -> Tuple[Label, ...]:
        """
        Retrieve the Allure labels associated with the given scenario.

        :param scenario: The VirtualScenario instance containing scenario details.
        :return: A tuple of Label objects for the scenario.
        """
        template = getattr(scenario._orig_scenario, "__vedro__template__", None)

        labels = getattr(template, "__vedro__allure_labels__", ())
        labels += getattr(scenario._orig_scenario, "__vedro__allure_labels__", ())

        return labels

    def _create_attachment(self, name: str, mime_type: str, ext: str) -> AllureAttachment:
        """
        Create an Allure attachment with the given name, MIME type, and extension.

        :param name: The name of the attachment.
        :param mime_type: The MIME type of the attachment.
        :param ext: The file extension of the attachment.
        :return: An AllureAttachment object.
        """
        return create_attachment(name, mime_type, ext)

    def _add_memory_attachment(self, artifact: MemoryArtifact) -> AllureAttachment:
        """
        Add an in-memory artifact as an Allure attachment.

        :param artifact: The MemoryArtifact to be attached.
        :return: The created AllureAttachment object.
        """
        return create_memory_attachment(artifact.data, artifact.name, artifact.mime_type)

    def _add_file_attachment(self, artifact: FileArtifact) -> AllureAttachment:
        """
        Add a file artifact as an Allure attachment.

        :param artifact: The FileArtifact to be attached.
        :return: The created AllureAttachment object.
        """
        return create_file_attachment(artifact.path, artifact.name, artifact.mime_type)

    def _add_attachments(self, result: Union[TestResult, TestStepResult],
                         artifacts: List[Artifact]) -> None:
        """
        Add artifacts as attachments to a test result or step result.

        :param result: The test result or step result to which attachments are added.
        :param artifacts: The list of artifacts to be attached.
        :raises ValueError: If an unknown artifact type is encountered.
        """
        for artifact in artifacts:
            if isinstance(artifact, MemoryArtifact):
                attachment = self._add_memory_attachment(artifact)
            elif isinstance(artifact, FileArtifact):
                attachment = self._add_file_attachment(artifact)
            else:
                raise ValueError(f"Unknown artifact type {type(artifact)}")
            result.attachments.append(attachment)

    def _format_scope(self, scope: Dict[Any, Any], indent: int = 4) -> str:
        """
        Format the scope dictionary into a human-readable string with indentation.

        :param scope: The scope dictionary to format.
        :param indent: The number of spaces to use for indentation (default: 4).
        :return: A formatted string representation of the scope.
        """
        res = ""
        for key, val in scope.items():
            try:
                val_repr = json.dumps(val, ensure_ascii=False, indent=4)
            except:  # noqa: E722
                val_repr = repr(val)
            res += f"{indent * ' '}{key}:\n{val_repr}\n\n"
        return res

    def _get_scenario_unique_id(self, scenario: VirtualScenario) -> str:
        """
        Generate a unique ID for the scenario using a hash.

        :param scenario: The VirtualScenario instance containing scenario details.
        :return: A hashed unique ID for the scenario.
        """
        unique_id = f"{self._project_name}_{scenario.unique_id}"
        return blake2b(unique_id.encode(), digest_size=32).hexdigest()

    def _report_result(self, scenario_result: ScenarioResult, status: str) -> None:
        """
        Report a scenario result to Allure, including steps, labels, and attachments.

        :param scenario_result: The ScenarioResult object containing scenario data.
        :param status: The status of the scenario (PASSED, FAILED, SKIPPED).
        """
        test_result = TestResult()
        test_result.uuid = utils.uuid4()  # type: ignore[no-untyped-call]
        test_result.name = scenario_result.scenario.subject
        test_result.fullName = scenario_result.scenario.unique_id
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
                test_result.statusDetails = self._create_status_details(step_result.exc_info)
            if self._attach_artifacts:
                self._add_attachments(test_step_result, step_result.artifacts)
            test_result.steps.append(test_step_result)

        # Add allure_step steps if any were recorded during scenario execution
        try:
            from ._allure_steps import (
                clear_current_steps,
                get_current_steps,
                get_steps_by_vedro_step,
            )
            recorded_steps = get_current_steps()
            steps_by_vedro = get_steps_by_vedro_step()

            # Try to assign custom steps to corresponding Vedro steps by grouping
            self._assign_custom_steps_to_vedro_steps(
                test_result.steps, recorded_steps, steps_by_vedro)

            clear_current_steps()  # Clean up for next scenario
        except ImportError:
            # allure_steps module not available, skip integration
            pass

        self._plugin_manager.hook.report_result(result=test_result)

    def _assign_custom_steps_to_vedro_steps(
            self, vedro_steps: List[TestStepResult],
            custom_steps: List[TestStepResult],
            steps_by_vedro: Dict[str, List[TestStepResult]]) -> None:
        """
        Assign custom allure_step steps to corresponding Vedro steps.

        This method uses proper grouping based on execution context to assign
        custom steps to their corresponding Vedro steps.

        :param vedro_steps: List of Vedro TestStepResult objects
        :param custom_steps: List of custom TestStepResult objects from
                             allure_step
        :param steps_by_vedro: Dictionary mapping Vedro step names to custom
                               steps
        """
        if not custom_steps or not vedro_steps:
            return

        # If we have proper grouping information, use it
        if steps_by_vedro:
            for vedro_step in vedro_steps:
                vedro_step_name = vedro_step.name
                if vedro_step_name in steps_by_vedro:
                    if (not hasattr(vedro_step, 'steps') or
                            vedro_step.steps is None):
                        vedro_step.steps = []
                    vedro_step.steps.extend(steps_by_vedro[vedro_step_name])
        else:
            # If no proper grouping is available, just add all custom steps
            # to the first Vedro step as a fallback
            if vedro_steps and custom_steps:
                first_vedro_step = vedro_steps[0]
                if (not hasattr(first_vedro_step, 'steps') or
                        first_vedro_step.steps is None):
                    first_vedro_step.steps = []
                first_vedro_step.steps.extend(custom_steps)

    def _create_status_details(self, exc_info: ExcInfo) -> StatusDetails:
        """
        Create a StatusDetails object from exception information.

        This method formats the exception details, including the traceback, into a
        StatusDetails object. It provides a human-readable message and the full
        traceback as a string.

        :param exc_info: The exception information containing type, value, and traceback.
        :return: A StatusDetails object with the formatted exception message and trace.
        """
        traceback = self._filter_traceback(exc_info.traceback)
        message = self.___format_exception_message(exc_info.value) or str(exc_info.type.__name__)

        trace = "".join(format_exception(exc_info.type, exc_info.value, traceback))
        return StatusDetails(message=message, trace=trace)

    def ___format_exception_message(self, exc_value: BaseException) -> str:
        """
        Format an exception message for `AssertionError` or other exception types.

        This method customizes the formatting of `AssertionError` messages by
        including additional details, such as left and right operands and the
        operator if they are available. For non-`AssertionError` exceptions, it
        returns the string representation of the exception.

        :param exc_value: The exception value to format.
        :return: A string containing the formatted exception message.
        """
        if not isinstance(exc_value, AssertionError):
            return str(exc_value)

        left = getattr(exc_value, "__vedro_assert_left__", Nil)
        if left is Nil:
            return str(exc_value)

        right = getattr(exc_value, "__vedro_assert_right__", Nil)
        operator = getattr(exc_value, "__vedro_assert_operator__", Nil)
        if (right is Nil) or (operator is Nil):
            return f"{exc_value.__class__.__name__}: assert {left!r}"
        else:
            return f"{exc_value.__class__.__name__}: assert {left!r} {operator} {right!r}"

    def _filter_traceback(self, traceback: TracebackType) -> TracebackType:
        """
        Filter a traceback to include only relevant frames.

        This method attempts to filter out irrelevant frames from a traceback,
        focusing on frames from specific modules (e.g., `vedro`). If the
        `TracebackFilter` utility is unavailable, it returns the unmodified traceback.

        :param traceback: The original traceback to filter.
        :return: The filtered traceback, or the original traceback if filtering fails.
        """
        try:
            from vedro.plugins.director.rich.utils import TracebackFilter
        except ImportError:
            # backward compatibility
            return traceback
        else:
            return TracebackFilter(modules=[vedro]).filter_tb(traceback)

    def _create_test_step_result(self, step_result: StepResult) -> TestStepResult:
        """
        Create a TestStepResult for a given step, including status and timing.

        :param step_result: The StepResult object containing step data.
        :return: The TestStepResult object for the step.
        """
        test_step_result = TestStepResult()
        if hasattr(test_step_result, 'uuid'):
            test_step_result.uuid = utils.uuid4()  # type: ignore[no-untyped-call]
        test_step_result.name = step_result.step_name.replace("_", " ")
        test_step_result.start = self._to_seconds(step_result.started_at or time())
        test_step_result.stop = self._to_seconds(step_result.ended_at or time())
        if step_result.status == StepStatus.PASSED:
            test_step_result.status = Status.PASSED
        elif step_result.status == StepStatus.FAILED:
            test_step_result.status = Status.FAILED
        return test_step_result


class AllureReporter(PluginConfig):
    """
    Configuration for the AllureReporterPlugin.

    Defines the settings for Allure reporting, such as project name, report directory,
    and options for attaching scope, tags, and artifacts.
    """

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

    # Clean the report directory before generating new reports
    clean_report_dir: bool = True

    # Add custom labels to each scenario
    labels: List[Label] = []

    # If True, includes all individual scenario runs in the Allure report when scenarios
    # are rescheduled (e.g., due to reruns or repeats). Each additional run will be
    # represented, providing visibility into the scenario's intermediate attempts.
    # If False, only the aggregated final result is reported.
    report_rescheduled_scenarios: bool = False
