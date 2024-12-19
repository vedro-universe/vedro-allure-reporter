from typing import Any, Callable
from unittest.mock import Mock, call

import pytest
from baby_steps import given, then, when
from vedro.core import AggregatedResult, Dispatcher, ScenarioResult
from vedro.events import ArgParsedEvent, ScenarioReportedEvent
from vedro.plugins.director import DirectorPlugin

from vedro_allure_reporter import AllureReporter, AllureReporterPlugin

from ._utils import (
    choose_reporter,
    director,
    dispatcher,
    logger_,
    logger_factory_,
    make_parsed_args,
    make_scenario_result,
    plugin_manager_,
)

__all__ = ("dispatcher", "director", "plugin_manager_", "logger_", "logger_factory_",)


@pytest.fixture()
def reporter(dispatcher: Dispatcher,
             plugin_manager_: Any, logger_factory_: Any) -> AllureReporterPlugin:
    reporter = AllureReporterPlugin(AllureReporter,
                                    plugin_manager=plugin_manager_,
                                    logger_factory=logger_factory_)
    reporter.subscribe(dispatcher)
    return reporter


async def test_arg_parsed_event(*, dispatcher: Dispatcher,
                                director: DirectorPlugin,
                                reporter: AllureReporterPlugin,
                                plugin_manager_: Mock,
                                logger_factory_: Mock,
                                logger_: Mock):
    with given:
        await choose_reporter(dispatcher, director, reporter)

        report_dir = "allure_reports"
        args = make_parsed_args(allure_report_dir=report_dir)
        event = ArgParsedEvent(args)

    with when:
        await dispatcher.fire(event)

    with then:
        assert logger_factory_.mock_calls == [
            call(report_dir, clean=True)
        ]
        assert plugin_manager_.mock_calls == [
            call.register(reporter),
            call.register(logger_),
        ]


@pytest.mark.parametrize("make_result", [
    lambda: make_scenario_result().mark_passed(),
    lambda: make_scenario_result().mark_failed(),
    lambda: make_scenario_result().mark_skipped(),
])
async def test_scenario_reported(make_result: Callable[[], ScenarioResult], *,
                                 dispatcher: Dispatcher,
                                 director: DirectorPlugin,
                                 reporter: AllureReporterPlugin,
                                 plugin_manager_: Mock,
                                 logger_: Mock):
    with given:
        await choose_reporter(dispatcher, director, reporter)

        scenario_result = make_result()
        aggregated_result = AggregatedResult.from_existing(scenario_result, [scenario_result])
        event = ScenarioReportedEvent(aggregated_result)

    with when:
        await dispatcher.fire(event)

    with then:
        assert plugin_manager_.hook.report_result.assert_called() is None
        assert len(plugin_manager_.mock_calls) == 1
        assert logger_.mock_calls == []


async def test_scenario_reported_unknown_status(*, dispatcher: Dispatcher,
                                                director: DirectorPlugin,
                                                reporter: AllureReporterPlugin,
                                                plugin_manager_: Mock,
                                                logger_: Mock):
    with given:
        await choose_reporter(dispatcher, director, reporter)

        scenario_result = make_scenario_result()
        aggregated_result = AggregatedResult.from_existing(scenario_result, [scenario_result])
        event = ScenarioReportedEvent(aggregated_result)

    with when:
        await dispatcher.fire(event)

    with then:
        assert plugin_manager_.hook.report_result.assert_called() is None
        assert len(plugin_manager_.mock_calls) == 1
        assert logger_.mock_calls == []
