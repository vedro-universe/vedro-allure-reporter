from pathlib import Path

import pytest
from allure_commons.logger import AllureMemoryLogger
from baby_steps import given, then, when
from vedro.core import Dispatcher, FileArtifact, MemoryArtifact
from vedro.events import (
    ArgParsedEvent,
    ScenarioFailedEvent,
    ScenarioPassedEvent,
    ScenarioRunEvent,
    ScenarioSkippedEvent,
)
from vedro.plugins.director import DirectorPlugin
from vedro.plugins.director.rich.test_utils import make_step_result

import vedro_allure_reporter
from vedro_allure_reporter import AllureLabel, AllureReporterPlugin

from ._utils import (
    choose_reporter,
    create_attachment,
    director,
    dispatcher,
    logger,
    make_parsed_args,
    make_scenario_result,
    make_test_case,
    patch_uuid,
)

__all__ = ("dispatcher", "director", "logger",)


@pytest.fixture()
def reporter(dispatcher: Dispatcher, logger: AllureMemoryLogger) -> AllureReporterPlugin:
    reporter = AllureReporterPlugin(vedro_allure_reporter.AllureReporter,
                                    logger_factory=lambda *args, **kwargs: logger)
    reporter.subscribe(dispatcher)
    return reporter


async def fire_arg_parsed_event(dispatcher: Dispatcher,
                                report_dir: str = "allure_reports") -> None:
    args = make_parsed_args(allure_report_dir=report_dir)
    event = ArgParsedEvent(args)
    await dispatcher.fire(event)


@pytest.mark.asyncio
async def test_scenario_skipped_event(*, dispatcher: Dispatcher,
                                      director: DirectorPlugin,
                                      reporter: AllureReporterPlugin,
                                      logger: AllureMemoryLogger):
    with given:
        await choose_reporter(dispatcher, director, reporter)
        await fire_arg_parsed_event(dispatcher)

        scenario_result = make_scenario_result()
        scenario_result = scenario_result.mark_skipped().set_started_at(1.0).set_ended_at(3.0)
        event = ScenarioSkippedEvent(scenario_result)

    with when, patch_uuid():
        await dispatcher.fire(event)

    with then:
        assert logger.test_cases == [
            # make_test_case(uuid, scenario_result)
        ]
        assert logger.test_containers == []
        assert logger.attachments == {}


@pytest.mark.asyncio
async def test_scenario_passed_event(*, dispatcher: Dispatcher,
                                     director: DirectorPlugin,
                                     reporter: AllureReporterPlugin,
                                     logger: AllureMemoryLogger):
    with given:
        await choose_reporter(dispatcher, director, reporter)
        await fire_arg_parsed_event(dispatcher)

        scenario_result = make_scenario_result()
        with patch_uuid() as uuid:
            await dispatcher.fire(ScenarioRunEvent(scenario_result))

        scenario_result = scenario_result.mark_passed().set_started_at(1.0).set_ended_at(3.0)
        event = ScenarioPassedEvent(scenario_result)

    with when:
        await dispatcher.fire(event)

    with then:
        assert logger.test_cases == [
            make_test_case(uuid, scenario_result)
        ]
        assert logger.test_containers == []
        assert logger.attachments == {}


@pytest.mark.asyncio
async def test_scenario_failed_event(*, dispatcher: Dispatcher,
                                     director: DirectorPlugin,
                                     reporter: AllureReporterPlugin,
                                     logger: AllureMemoryLogger):
    with given:
        await choose_reporter(dispatcher, director, reporter)
        await fire_arg_parsed_event(dispatcher)

        scenario_result = make_scenario_result()
        with patch_uuid() as uuid:
            await dispatcher.fire(ScenarioRunEvent(scenario_result))

        scenario_result = scenario_result.mark_failed().set_started_at(1.0).set_ended_at(3.0)
        event = ScenarioFailedEvent(scenario_result)

    with when:
        await dispatcher.fire(event)

    with then:
        assert logger.test_cases == [
            make_test_case(uuid, scenario_result)
        ]
        assert logger.test_containers == []
        assert logger.attachments == {}


@pytest.mark.asyncio
async def test_scenario_passed_with_steps_event(*, dispatcher: Dispatcher,
                                                director: DirectorPlugin,
                                                reporter: AllureReporterPlugin,
                                                logger: AllureMemoryLogger):
    with given:
        await choose_reporter(dispatcher, director, reporter)
        await fire_arg_parsed_event(dispatcher)

        scenario_result = make_scenario_result()
        with patch_uuid() as uuid:
            await dispatcher.fire(ScenarioRunEvent(scenario_result))

        t = 1.0
        step_result_passed = (make_step_result().mark_passed()
                                                .set_started_at(t + 1)
                                                .set_ended_at(t + 2))
        scenario_result.add_step_result(step_result_passed)

        scenario_result = scenario_result.mark_passed().set_started_at(t).set_ended_at(t + 3)
        event = ScenarioPassedEvent(scenario_result)

    with when:
        await dispatcher.fire(event)

    with then:
        assert logger.test_cases == [
            make_test_case(uuid, scenario_result, [
                step_result_passed,
            ])
        ]
        assert logger.test_containers == []
        assert logger.attachments == {}


@pytest.mark.asyncio
async def test_scenario_failed_with_steps_event(*, dispatcher: Dispatcher,
                                                director: DirectorPlugin,
                                                reporter: AllureReporterPlugin,
                                                logger: AllureMemoryLogger):
    with given:
        await choose_reporter(dispatcher, director, reporter)
        await fire_arg_parsed_event(dispatcher)

        scenario_result = make_scenario_result()
        with patch_uuid() as uuid:
            await dispatcher.fire(ScenarioRunEvent(scenario_result))

        t = 1.0
        step_result_passed = (make_step_result().mark_passed()
                              .set_started_at(t + 1)
                              .set_ended_at(t + 2))
        scenario_result.add_step_result(step_result_passed)

        step_result_failed = (make_step_result().mark_failed()
                              .set_started_at(t + 3)
                              .set_ended_at(t + 4))
        scenario_result.add_step_result(step_result_failed)

        scenario_result = scenario_result.mark_failed().set_started_at(t).set_ended_at(t + 5)
        event = ScenarioFailedEvent(scenario_result)

    with when:
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


@pytest.mark.asyncio
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

        scenario_result = make_scenario_result()
        with patch_uuid() as uuid:
            await dispatcher.fire(ScenarioRunEvent(scenario_result))

        scenario_result = scenario_result.mark_passed().set_started_at(0.1).set_ended_at(0.2)
        event = ScenarioPassedEvent(scenario_result)

    with when:
        await dispatcher.fire(event)

    with then:
        assert logger.test_cases == [
            make_test_case(uuid, scenario_result, labels=AllureReporter.labels)
        ]
        assert logger.test_containers == []
        assert logger.attachments == {}


@pytest.mark.asyncio
async def test_scenario_tags(*, dispatcher: Dispatcher, director: DirectorPlugin,
                             reporter: AllureReporterPlugin, logger: AllureMemoryLogger):
    with given:
        await choose_reporter(dispatcher, director, reporter)
        await fire_arg_parsed_event(dispatcher)

        tags = ["API"]
        scenario_result = make_scenario_result(tags=tags)
        with patch_uuid() as uuid:
            await dispatcher.fire(ScenarioRunEvent(scenario_result))

        scenario_result = scenario_result.mark_passed().set_started_at(0.1).set_ended_at(0.2)
        event = ScenarioPassedEvent(scenario_result)

    with when:
        await dispatcher.fire(event)

    with then:
        assert logger.test_cases == [
            make_test_case(uuid, scenario_result, labels=[AllureLabel("tag", "API")])
        ]
        assert logger.test_containers == []
        assert logger.attachments == {}


@pytest.mark.asyncio
async def test_scenario_passed_attachments(*, dispatcher: Dispatcher,
                                           director: DirectorPlugin,
                                           reporter: AllureReporterPlugin,
                                           logger: AllureMemoryLogger):
    with given:
        await choose_reporter(dispatcher, director, reporter)
        await fire_arg_parsed_event(dispatcher)

        scenario_result = make_scenario_result()
        with patch_uuid() as uuid:
            await dispatcher.fire(ScenarioRunEvent(scenario_result))

        scenario_result = scenario_result.mark_passed().set_started_at(1.0).set_ended_at(3.0)
        artifact = MemoryArtifact("log", "text/plain", b"<body>")
        scenario_result.attach(artifact)

        event = ScenarioPassedEvent(scenario_result)

    with when, patch_uuid() as attachment_uuid:
        await dispatcher.fire(event)

    with then:
        assert logger.test_cases == [
            make_test_case(uuid, scenario_result, attachments=[
                create_attachment(artifact, attachment_uuid),
            ])
        ]
        assert logger.test_containers == []
        assert list(logger.attachments.values()) == [artifact.data]


@pytest.mark.asyncio
async def test_scenario_failed_attachments(*, tmp_path: Path, dispatcher: Dispatcher,
                                           director: DirectorPlugin,
                                           reporter: AllureReporterPlugin,
                                           logger: AllureMemoryLogger):
    with given:
        await choose_reporter(dispatcher, director, reporter)
        await fire_arg_parsed_event(dispatcher)

        scenario_result = make_scenario_result()
        with patch_uuid() as uuid:
            await dispatcher.fire(ScenarioRunEvent(scenario_result))

        scenario_result = scenario_result.mark_passed().set_started_at(1.0).set_ended_at(3.0)
        path = tmp_path / "log.txt"
        path.write_bytes(b"<body>")
        artifact = FileArtifact("log", "text/plain", path)
        scenario_result.attach(artifact)

        event = ScenarioPassedEvent(scenario_result)

    with when, patch_uuid() as attachment_uuid:
        await dispatcher.fire(event)

    with then:
        assert logger.test_cases == [
            make_test_case(uuid, scenario_result, attachments=[
                create_attachment(artifact, attachment_uuid),
            ])
        ]
        assert logger.test_containers == []
        assert list(logger.attachments.values()) == []  # not implemented in AllureMemoryLogger


@pytest.mark.asyncio
async def test_scenario_labels(*, dispatcher: Dispatcher, director: DirectorPlugin,
                               reporter: AllureReporterPlugin, logger: AllureMemoryLogger):
    with given:
        await choose_reporter(dispatcher, director, reporter)
        await fire_arg_parsed_event(dispatcher)

        scenario_labels = [AllureLabel('name', 'value')]
        scenario_result = make_scenario_result(labels=scenario_labels)
        with patch_uuid() as uuid:
            await dispatcher.fire(ScenarioRunEvent(scenario_result))

        scenario_result = scenario_result.mark_passed().set_started_at(0.1).set_ended_at(0.2)
        event = ScenarioPassedEvent(scenario_result)

    with when:
        await dispatcher.fire(event)

    with then:
        assert logger.test_cases == [
            make_test_case(uuid, scenario_result, labels=scenario_labels)
        ]
        assert logger.test_containers == []
        assert logger.attachments == {}
