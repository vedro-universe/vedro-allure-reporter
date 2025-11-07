from typing import Any
from unittest.mock import Mock, call

import pytest
from baby_steps import given, then, when
from vedro.core import Dispatcher
from vedro.events import ArgParsedEvent
from vedro.plugins.director import DirectorPlugin

from vedro_allure_reporter import AllureReporter, AllureReporterPlugin

from ._utils import (
    choose_reporter,
    director,
    dispatcher,
    logger_,
    logger_factory_,
    make_parsed_args,
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
        # AllureStepHooks is now registered along with the logger
        assert len(plugin_manager_.mock_calls) == 2
        assert plugin_manager_.mock_calls[0] == call.register(reporter._allure_step_hooks)
        assert plugin_manager_.mock_calls[1] == call.register(logger_)
