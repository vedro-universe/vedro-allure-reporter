import pytest
from allure_commons.logger import AllureMemoryLogger
from baby_steps import given, then, when
from vedro.core import Dispatcher, StepResult
from vedro.events import (
    ArgParsedEvent,
    ScenarioFailedEvent,
    ScenarioPassedEvent,
    ScenarioRunEvent,
    ScenarioSkippedEvent,
    StepFailedEvent,
    StepPassedEvent,
    StepRunEvent,
)
from vedro.plugins.director.rich.test_utils import make_scenario_result, make_step_result

from vedro_allure_reporter import AllureReporter

from ._utils import dispatcher, logger, make_parsed_args, make_test_case, patch_uuid

__all__ = ("dispatcher", "logger",)


@pytest.fixture()
def reporter(logger) -> AllureReporter:
    return AllureReporter(logger_factory=lambda *args, **kwargs: logger)


async def fire_arg_parsed_event(dispatcher: Dispatcher,
                                report_dir: str = "allure_reports") -> None:
    args = make_parsed_args(allure_report_dir=report_dir)
    event = ArgParsedEvent(args)
    await dispatcher.fire(event)


async def fire_step_passed_event(dispatcher: Dispatcher, step_result: StepResult) -> None:
    await dispatcher.fire(StepRunEvent(step_result))
    await dispatcher.fire(StepPassedEvent(step_result))


async def fire_step_failed_event(dispatcher: Dispatcher, step_result: StepResult) -> None:
    await dispatcher.fire(StepRunEvent(step_result))
    await dispatcher.fire(StepFailedEvent(step_result))


@pytest.mark.asyncio
async def test_scenario_skipped_event(*, dispatcher: Dispatcher, reporter: AllureReporter,
                                      logger: AllureMemoryLogger):
    with given:
        reporter.subscribe(dispatcher)
        await fire_arg_parsed_event(dispatcher)

        scenario_result = make_scenario_result()
        scenario_result = scenario_result.mark_skipped().set_started_at(1.0).set_ended_at(3.0)
        event = ScenarioSkippedEvent(scenario_result)

    with when, patch_uuid() as uuid:
        await dispatcher.fire(event)

    with then:
        assert logger.test_cases == [
            make_test_case(uuid, scenario_result)
        ]
        assert logger.test_containers == []
        assert logger.attachments == {}


@pytest.mark.asyncio
async def test_scenario_passed_event(*, dispatcher: Dispatcher, reporter: AllureReporter,
                                     logger: AllureMemoryLogger):
    with given:
        reporter.subscribe(dispatcher)
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
async def test_scenario_failed_event(*, dispatcher: Dispatcher, reporter: AllureReporter,
                                     logger: AllureMemoryLogger):
    with given:
        reporter.subscribe(dispatcher)
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
                                                reporter: AllureReporter,
                                                logger: AllureMemoryLogger):
    with given:
        reporter.subscribe(dispatcher)
        await fire_arg_parsed_event(dispatcher)

        scenario_result = make_scenario_result()
        with patch_uuid() as uuid:
            await dispatcher.fire(ScenarioRunEvent(scenario_result))

        t = 1.0
        step_result_passed = make_step_result().mark_passed()
        await fire_step_passed_event(dispatcher,
                                     step_result_passed.set_started_at(t + 1).set_ended_at(t + 2))

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
                                                reporter: AllureReporter,
                                                logger: AllureMemoryLogger):
    with given:
        reporter.subscribe(dispatcher)
        await fire_arg_parsed_event(dispatcher)

        scenario_result = make_scenario_result()
        with patch_uuid() as uuid:
            await dispatcher.fire(ScenarioRunEvent(scenario_result))

        t = 1.0
        step_result_passed = make_step_result().mark_passed()
        await fire_step_passed_event(dispatcher,
                                     step_result_passed.set_started_at(t + 1).set_ended_at(t + 2))

        step_result_failed = make_step_result().mark_failed()
        await fire_step_failed_event(dispatcher,
                                     step_result_failed.set_started_at(t + 3).set_ended_at(t + 4))

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
