import pytest
from allure_commons.logger import AllureMemoryLogger
from allure_commons.model2 import Status
from baby_steps import given, then, when
from vedro.core import Dispatcher
from vedro.events import ScenarioReportedEvent
from vedro.plugins.director import DirectorPlugin

import vedro_allure_reporter
from vedro_allure_reporter import AllureReporter, AllureReporterPlugin

from ._utils import (
    choose_reporter,
    director,
    dispatcher,
    fire_arg_parsed_event,
    logger,
    logger_,
    logger_factory_,
    make_aggregated_result,
    make_scenario_result,
    patch_uuid,
    plugin_manager_,
)

__all__ = ("dispatcher", "director", "plugin_manager_", "logger_", "logger_factory_", "logger")


@pytest.fixture()
def reporter(dispatcher: Dispatcher, logger: AllureMemoryLogger) -> AllureReporterPlugin:
    reporter = AllureReporterPlugin(vedro_allure_reporter.AllureReporter,
                                    logger_factory=lambda *args, **kwargs: logger)
    reporter.subscribe(dispatcher)
    return reporter


async def test_report_skipped_scenario_default(*, dispatcher: Dispatcher,
                                               director: DirectorPlugin,
                                               reporter: AllureReporterPlugin,
                                               logger: AllureMemoryLogger):
    with given:
        await choose_reporter(dispatcher, director, reporter)
        await fire_arg_parsed_event(dispatcher)

        scenario_result = make_scenario_result(subject="Skipped scenario")
        scenario_result.mark_skipped().set_started_at(1.0).set_ended_at(1.0)

        aggregated_result = make_aggregated_result(scenario_result)
        event = ScenarioReportedEvent(aggregated_result)

    with when:
        with patch_uuid() as test_uuid:
            await dispatcher.fire(event)

    with then:
        assert len(logger.test_cases) == 1
        test_case = logger.test_cases[0]
        assert test_case["uuid"] == test_uuid
        assert test_case["name"] == "Skipped scenario"
        assert test_case["status"] == Status.SKIPPED
        assert "steps" not in test_case or len(test_case.get("steps", [])) == 0


async def test_report_skipped_scenario_disabled(*, dispatcher: Dispatcher,
                                                director: DirectorPlugin,
                                                logger: AllureMemoryLogger):
    with given:
        # Create reporter with report_skipped_scenarios=False
        class AllureReporterNoSkipped(AllureReporter):
            report_skipped_scenarios = False

        reporter = AllureReporterPlugin(AllureReporterNoSkipped,
                                        logger_factory=lambda *args, **kwargs: logger)
        reporter.subscribe(dispatcher)

        await choose_reporter(dispatcher, director, reporter)
        await fire_arg_parsed_event(dispatcher)

        scenario_result = make_scenario_result(subject="Skipped scenario")
        scenario_result.mark_skipped().set_started_at(1.0).set_ended_at(1.0)

        aggregated_result = make_aggregated_result(scenario_result)
        event = ScenarioReportedEvent(aggregated_result)

    with when:
        await dispatcher.fire(event)

    with then:
        assert len(logger.test_cases) == 0


async def test_report_skipped_scenario_with_labels(*, dispatcher: Dispatcher,
                                                   director: DirectorPlugin,
                                                   reporter: AllureReporterPlugin,
                                                   logger: AllureMemoryLogger):
    with given:
        from vedro_allure_reporter import AllureLabel

        await choose_reporter(dispatcher, director, reporter)
        await fire_arg_parsed_event(dispatcher)

        labels = (AllureLabel("feature", "TEST_FEATURE"), AllureLabel("story", "TEST_STORY"))
        scenario_result = make_scenario_result(subject="Skipped with labels", labels=labels)
        scenario_result.mark_skipped().set_started_at(1.0).set_ended_at(1.0)

        aggregated_result = make_aggregated_result(scenario_result)
        event = ScenarioReportedEvent(aggregated_result)

    with when:
        with patch_uuid():
            await dispatcher.fire(event)

    with then:
        assert len(logger.test_cases) == 1
        test_case = logger.test_cases[0]

        assert test_case["status"] == Status.SKIPPED

        # Check that labels are present
        label_dict = {label["name"]: label["value"] for label in test_case["labels"]}
        assert label_dict["feature"] == "TEST_FEATURE"
        assert label_dict["story"] == "TEST_STORY"
