from pathlib import Path
from typing import Callable
from uuid import uuid4

import pytest
from allure_commons.logger import AllureMemoryLogger
from baby_steps import given, then, when
from vedro.core import Dispatcher, FileArtifact, MemoryArtifact
from vedro.core import MonotonicScenarioScheduler as Scheduler
from vedro.core import ScenarioResult
from vedro.events import ScenarioReportedEvent, StartupEvent
from vedro.plugins.director import DirectorPlugin

import vedro_allure_reporter
from vedro_allure_reporter import AllureLabel, AllureReporterPlugin

from ._utils import (
    choose_reporter,
    create_attachment,
    director,
    dispatcher,
    fire_arg_parsed_event,
    logger,
    make_aggregated_result,
    make_scenario_result,
    make_step_result,
    make_test_case,
    make_vscenario,
    patch_uuid,
    patch_uuids,
)

__all__ = ("dispatcher", "director", "logger",)


@pytest.fixture()
def reporter(dispatcher: Dispatcher, logger: AllureMemoryLogger) -> AllureReporterPlugin:
    reporter = AllureReporterPlugin(vedro_allure_reporter.AllureReporter,
                                    logger_factory=lambda *args, **kwargs: logger)
    reporter.subscribe(dispatcher)
    return reporter


@pytest.mark.parametrize("make_result", [
    lambda: make_scenario_result().mark_passed(),
    lambda: make_scenario_result().mark_failed(),
    lambda: make_scenario_result().mark_skipped(),
])
async def test_scenario_reported(make_result: Callable[[], ScenarioResult], *,
                                 dispatcher: Dispatcher,
                                 director: DirectorPlugin,
                                 reporter: AllureReporterPlugin,
                                 logger: AllureMemoryLogger):
    with given:
        await choose_reporter(dispatcher, director, reporter)
        await fire_arg_parsed_event(dispatcher)

        scenario_result = make_result().set_started_at(1.0).set_ended_at(3.0)
        aggregated_result = make_aggregated_result(scenario_result)
        event = ScenarioReportedEvent(aggregated_result)

    with when, patch_uuid() as uuid:
        await dispatcher.fire(event)

    with then:
        assert logger.test_cases == [
            make_test_case(uuid, scenario_result)
        ]
        assert logger.test_containers == []
        assert logger.attachments == {}


async def test_scenario_passed_with_steps_event(*, dispatcher: Dispatcher,
                                                director: DirectorPlugin,
                                                reporter: AllureReporterPlugin,
                                                logger: AllureMemoryLogger):
    with given:
        await choose_reporter(dispatcher, director, reporter)
        await fire_arg_parsed_event(dispatcher)

        t = 1.0
        scenario_result = make_scenario_result()
        step_result_passed = (make_step_result().mark_passed()
                                                .set_started_at(t + 1)
                                                .set_ended_at(t + 2))
        scenario_result.add_step_result(step_result_passed)
        scenario_result = scenario_result.mark_passed().set_started_at(t).set_ended_at(t + 3)

        aggregated_result = make_aggregated_result(scenario_result)
        event = ScenarioReportedEvent(aggregated_result)

    with when, patch_uuid() as uuid:
        await dispatcher.fire(event)

    with then:
        assert logger.test_cases == [
            make_test_case(uuid, scenario_result, [
                step_result_passed,
            ])
        ]
        assert logger.test_containers == []
        assert logger.attachments == {}


async def test_scenario_failed_with_steps_event(*, dispatcher: Dispatcher,
                                                director: DirectorPlugin,
                                                reporter: AllureReporterPlugin,
                                                logger: AllureMemoryLogger):
    with given:
        await choose_reporter(dispatcher, director, reporter)
        await fire_arg_parsed_event(dispatcher)

        t = 1.0
        scenario_result = make_scenario_result()
        step_result_passed = (make_step_result().mark_passed()
                              .set_started_at(t + 1)
                              .set_ended_at(t + 2))
        scenario_result.add_step_result(step_result_passed)

        step_result_failed = (make_step_result().mark_failed()
                              .set_started_at(t + 3)
                              .set_ended_at(t + 4))
        scenario_result.add_step_result(step_result_failed)
        scenario_result = scenario_result.mark_failed().set_started_at(t).set_ended_at(t + 5)

        aggregated_result = make_aggregated_result(scenario_result)
        event = ScenarioReportedEvent(aggregated_result)

    with when, patch_uuid() as uuid:
        await dispatcher.fire(event)

    with then:
        assert logger.test_cases == [
            make_test_case(uuid, scenario_result, [
                step_result_passed,
                step_result_failed,
            ])
        ]
        assert logger.test_containers == []
        assert logger.attachments == {}


async def test_scenario_config_labels(*, dispatcher: Dispatcher, director: DirectorPlugin,
                                      logger: AllureMemoryLogger):
    with given:
        class AllureReporter(vedro_allure_reporter.AllureReporter):
            labels = [AllureLabel("name", "value")]

        reporter = AllureReporterPlugin(AllureReporter,
                                        logger_factory=lambda *args, **kwargs: logger)
        reporter.subscribe(dispatcher)
        await choose_reporter(dispatcher, director, reporter)
        await fire_arg_parsed_event(dispatcher)

        scenario_result = make_scenario_result().mark_passed() \
                                                .set_started_at(0.1).set_ended_at(0.2)
        aggregated_result = make_aggregated_result(scenario_result)
        event = ScenarioReportedEvent(aggregated_result)

    with when, patch_uuid() as uuid:
        await dispatcher.fire(event)

    with then:
        assert logger.test_cases == [
            make_test_case(uuid, scenario_result, labels=AllureReporter.labels)
        ]
        assert logger.test_containers == []
        assert logger.attachments == {}


async def test_scenario_tags(*, dispatcher: Dispatcher, director: DirectorPlugin,
                             reporter: AllureReporterPlugin, logger: AllureMemoryLogger):
    with given:
        await choose_reporter(dispatcher, director, reporter)
        await fire_arg_parsed_event(dispatcher)

        tags = ["API"]
        scenario_result = make_scenario_result(tags=tags).mark_passed() \
                                                         .set_started_at(0.1).set_ended_at(0.2)
        aggregated_result = make_aggregated_result(scenario_result)
        event = ScenarioReportedEvent(aggregated_result)

    with when, patch_uuid() as uuid:
        await dispatcher.fire(event)

    with then:
        assert logger.test_cases == [
            make_test_case(uuid, scenario_result, labels=[AllureLabel("tag", "API")])
        ]
        assert logger.test_containers == []
        assert logger.attachments == {}


async def test_scenario_no_labels_config_labels_to_tags(*, dispatcher: Dispatcher,
                                                        director: DirectorPlugin,
                                                        logger: AllureMemoryLogger):
    with given:
        class AllureReporter(vedro_allure_reporter.AllureReporter):
            labels = [AllureLabel("name_1", "value_1"), AllureLabel("name_2", "value_2")]

        reporter = AllureReporterPlugin(AllureReporter,
                                        logger_factory=lambda *args, **kwargs: logger)
        reporter.subscribe(dispatcher)
        await choose_reporter(dispatcher, director, reporter)
        await fire_arg_parsed_event(dispatcher, labels_to_tags=["name_2"])

        tags = ["API"]
        scenario_result = make_scenario_result(tags=tags).mark_passed() \
                                                         .set_started_at(0.1) \
                                                         .set_ended_at(0.2)
        aggregated_result = make_aggregated_result(scenario_result)
        event = ScenarioReportedEvent(aggregated_result)

    with when, patch_uuid() as uuid:
        await dispatcher.fire(event)

    with then:
        assert logger.test_cases == [
            make_test_case(uuid, scenario_result,
                           labels=AllureReporter.labels + [AllureLabel("tag", "API")])
        ]
        assert logger.test_containers == []
        assert logger.attachments == {}
        assert scenario_result.scenario._orig_scenario.tags == ("API", )


async def test_scenario_labels_config_labels_to_tags(*, dispatcher: Dispatcher,
                                                     director: DirectorPlugin,
                                                     reporter: AllureReporterPlugin,
                                                     logger: AllureMemoryLogger):
    with given:
        await choose_reporter(dispatcher, director, reporter)
        await fire_arg_parsed_event(dispatcher, labels_to_tags=["name_2"])

        tags = ["API"]
        labels = (AllureLabel("name_1", "value_1"), AllureLabel("name_2", "value_2"))
        scenario_result = make_scenario_result(
            tags=tags, labels=labels
        ).mark_passed().set_started_at(0.1).set_ended_at(0.2)
        aggregated_result = make_aggregated_result(scenario_result)
        event = ScenarioReportedEvent(aggregated_result)

    with when, patch_uuid() as uuid:
        await dispatcher.fire(event)

    with then:
        assert logger.test_cases == [
            make_test_case(uuid, scenario_result, labels=(AllureLabel("tag", "API"), *labels))
        ]
        assert logger.test_containers == []
        assert logger.attachments == {}
        assert scenario_result.scenario._orig_scenario.tags == ("API", "name_2:value_2")


async def test_scenario_passed_attachments(*, dispatcher: Dispatcher,
                                           director: DirectorPlugin,
                                           reporter: AllureReporterPlugin,
                                           logger: AllureMemoryLogger):
    with given:
        await choose_reporter(dispatcher, director, reporter)
        await fire_arg_parsed_event(dispatcher)

        scenario_result = make_scenario_result().mark_passed() \
                                                .set_started_at(1.0).set_ended_at(3.0)
        artifact = MemoryArtifact("log", "text/plain", b"<body>")
        scenario_result.attach(artifact)

        aggregated_result = make_aggregated_result(scenario_result)
        event = ScenarioReportedEvent(aggregated_result)

        uuid, attachment_uuid = str(uuid4()), str(uuid4())

    with when, patch_uuids(uuid, attachment_uuid):
        await dispatcher.fire(event)

    with then:
        assert logger.test_cases == [
            make_test_case(uuid, scenario_result, attachments=[
                create_attachment(artifact, attachment_uuid),
            ])
        ]
        assert logger.test_containers == []
        assert list(logger.attachments.values()) == [artifact.data]


async def test_scenario_failed_attachments(*, tmp_path: Path, dispatcher: Dispatcher,
                                           director: DirectorPlugin,
                                           reporter: AllureReporterPlugin,
                                           logger: AllureMemoryLogger):
    with given:
        await choose_reporter(dispatcher, director, reporter)
        await fire_arg_parsed_event(dispatcher)

        scenario_result = make_scenario_result().mark_passed() \
                                                .set_started_at(1.0).set_ended_at(3.0)
        path = tmp_path / "log.txt"
        path.write_bytes(b"<body>")
        artifact = FileArtifact("log", "text/plain", path)
        scenario_result.attach(artifact)

        aggregated_result = make_aggregated_result(scenario_result)
        event = ScenarioReportedEvent(aggregated_result)

        uuid, attachment_uuid = str(uuid4()), str(uuid4())

    with when, patch_uuids(uuid, attachment_uuid):
        await dispatcher.fire(event)

    with then:
        assert logger.test_cases == [
            make_test_case(uuid, scenario_result, attachments=[
                create_attachment(artifact, attachment_uuid),
            ])
        ]
        assert logger.test_containers == []
        assert list(logger.attachments.values()) == [artifact.path]


async def test_scenario_labels(*, dispatcher: Dispatcher, director: DirectorPlugin,
                               reporter: AllureReporterPlugin, logger: AllureMemoryLogger):
    with given:
        await choose_reporter(dispatcher, director, reporter)
        await fire_arg_parsed_event(dispatcher)

        scenario_labels = (AllureLabel('name', 'value'),)
        scenario_result = make_scenario_result(labels=scenario_labels).mark_passed() \
                                                                      .set_started_at(0.1) \
                                                                      .set_ended_at(0.2)

        aggregated_result = make_aggregated_result(scenario_result)
        event = ScenarioReportedEvent(aggregated_result)

    with when, patch_uuid() as uuid:
        await dispatcher.fire(event)

    with then:
        assert logger.test_cases == [
            make_test_case(uuid, scenario_result, labels=scenario_labels)
        ]
        assert logger.test_containers == []
        assert logger.attachments == {}


async def test_no_allure_labels_to_run(*, dispatcher: Dispatcher,
                                       director: DirectorPlugin,
                                       reporter: AllureReporterPlugin,
                                       logger: AllureMemoryLogger):
    with given:
        labels = [
            (AllureLabel('label1', 'value1'),),
            (AllureLabel('label2', 'value2'),)
        ]
        scenarios = [make_vscenario(labels=labels[0]), make_vscenario(labels=labels[1])]
        scheduler = Scheduler(scenarios)

        await fire_arg_parsed_event(dispatcher, labels=[])

        startup_event = StartupEvent(scheduler)

    with when:
        await dispatcher.fire(startup_event)

    with then:
        assert list(scheduler.scheduled) == scenarios


async def test_nonexisting_label_to_run(*, dispatcher: Dispatcher,
                                        director: DirectorPlugin,
                                        reporter: AllureReporterPlugin,
                                        logger: AllureMemoryLogger):
    with given:
        labels = [
            (AllureLabel('label1', 'value1'),),
            (AllureLabel('label2', 'value2'),),
        ]
        scenarios = [make_vscenario(labels=labels[0]), make_vscenario(labels=labels[1])]
        scheduler = Scheduler(scenarios)

        await fire_arg_parsed_event(dispatcher, labels=['label3=value3'])

        startup_event = StartupEvent(scheduler)

    with when:
        await dispatcher.fire(startup_event)

    with then:
        assert list(scheduler.scheduled) == []


async def test_multiple_labels(*, dispatcher: Dispatcher,
                               director: DirectorPlugin,
                               reporter: AllureReporterPlugin,
                               logger: AllureMemoryLogger):
    with given:
        labels = [
            (AllureLabel('label1', 'value1'),),
            (AllureLabel('label2', 'value2'),)
        ]
        scenarios = [make_vscenario(labels=labels[0]), make_vscenario(labels=labels[1])]
        scheduler = Scheduler(scenarios)

        await fire_arg_parsed_event(dispatcher, labels=['label1=value1', 'label2=value2'])

        startup_event = StartupEvent(scheduler)

    with when:
        await dispatcher.fire(startup_event)

    with then:
        assert list(scheduler.scheduled) == []


async def test_multiple_labels_in_one_test(*, dispatcher: Dispatcher,
                                           director: DirectorPlugin,
                                           reporter: AllureReporterPlugin,
                                           logger: AllureMemoryLogger):
    with given:
        labels = [
            (AllureLabel('label1', 'value1'), AllureLabel('label2', 'value2')),
            (AllureLabel('label3', 'value3'),)
        ]
        scenarios = [make_vscenario(labels=labels[0]), make_vscenario(labels=labels[1])]
        scheduler = Scheduler(scenarios)

        await fire_arg_parsed_event(dispatcher, labels=['label1=value1'])

        startup_event = StartupEvent(scheduler)

    with when:
        await dispatcher.fire(startup_event)

    with then:
        assert list(scheduler.scheduled) == [scenarios[0]]


async def test_labels_name_case_insensitive(*, dispatcher: Dispatcher,
                                            director: DirectorPlugin,
                                            reporter: AllureReporterPlugin,
                                            logger: AllureMemoryLogger):
    with given:
        labels = [
            (AllureLabel('lAbEl', 'value'),),
        ]
        scenarios = [make_vscenario(labels=labels[0])]
        scheduler = Scheduler(scenarios)

        await fire_arg_parsed_event(dispatcher, labels=['LaBeL=value'])

        startup_event = StartupEvent(scheduler)

    with when:
        await dispatcher.fire(startup_event)

    with then:
        assert list(scheduler.scheduled) == scenarios
