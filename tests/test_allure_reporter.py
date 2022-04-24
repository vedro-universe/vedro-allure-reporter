from unittest.mock import Mock, call

import pytest
from baby_steps import given, then, when
from vedro.core import Dispatcher
from vedro.events import (
    ArgParsedEvent,
    ScenarioFailedEvent,
    ScenarioPassedEvent,
    ScenarioRunEvent,
    ScenarioSkippedEvent,
)
from vedro.plugins.director import Reporter

from vedro_allure_reporter import AllureReporter, AllureReporterPlugin

from ._utils import (
    dispatcher,
    logger_,
    logger_factory_,
    make_parsed_args,
    make_scenario_result,
    plugin_manager_,
)

__all__ = ("dispatcher", "plugin_manager_", "logger_", "logger_factory_",)


@pytest.fixture()
def reporter(plugin_manager_, logger_factory_) -> AllureReporterPlugin:
    return AllureReporterPlugin(AllureReporter,
                                plugin_manager=plugin_manager_, logger_factory=logger_factory_)


def test_reporter():
    with when:
        reporter = AllureReporterPlugin(AllureReporter)

    with then:
        assert isinstance(reporter, Reporter)


@pytest.mark.asyncio
async def test_arg_parsed_event(*, dispatcher: Dispatcher, reporter: AllureReporterPlugin,
                                plugin_manager_: Mock, logger_factory_: Mock, logger_: Mock):
    with given:
        reporter.subscribe(dispatcher)

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


@pytest.mark.asyncio
async def test_scenario_skip_event(*, dispatcher: Dispatcher, reporter: AllureReporterPlugin,
                                   plugin_manager_: Mock, logger_: Mock):
    with given:
        reporter.subscribe(dispatcher)

        scenario_result = make_scenario_result()
        event = ScenarioSkippedEvent(scenario_result)

    with when:
        await dispatcher.fire(event)

    with then:
        assert plugin_manager_.mock_calls == [
            call.hook.report_result(result=reporter._test_result)
        ]
        assert logger_.mock_calls == []


@pytest.mark.asyncio
async def test_scenario_pass_event(*, dispatcher: Dispatcher, reporter: AllureReporterPlugin,
                                   plugin_manager_: Mock, logger_: Mock):
    with given:
        reporter.subscribe(dispatcher)

        scenario_result = make_scenario_result()
        await dispatcher.fire(ScenarioRunEvent(scenario_result))

        event = ScenarioPassedEvent(scenario_result)

    with when:
        await dispatcher.fire(event)

    with then:
        assert plugin_manager_.mock_calls == [
            call.hook.report_result(result=reporter._test_result)
        ]
        assert logger_.mock_calls == []


@pytest.mark.asyncio
async def test_scenario_failed_event(*, dispatcher: Dispatcher, reporter: AllureReporterPlugin,
                                     plugin_manager_: Mock, logger_: Mock):
    with given:
        reporter.subscribe(dispatcher)

        scenario_result = make_scenario_result()
        await dispatcher.fire(ScenarioRunEvent(scenario_result))

        event = ScenarioFailedEvent(scenario_result)

    with when:
        await dispatcher.fire(event)

    with then:
        assert plugin_manager_.mock_calls == [
            call.hook.report_result(result=reporter._test_result)
        ]
        assert logger_.mock_calls == []
