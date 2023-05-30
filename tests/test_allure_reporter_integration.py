from pathlib import Path
from typing import Callable
from uuid import uuid4

import pytest
from allure_commons.logger import AllureMemoryLogger
from baby_steps import given, then, when
from vedro.core import Dispatcher, FileArtifact, MemoryArtifact, ScenarioResult
from vedro.events import ScenarioReportedEvent
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
