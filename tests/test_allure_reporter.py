from typing import Any
from unittest.mock import Mock, call

import pytest
from allure_commons.model2 import Label, TestResult
from allure_commons.reporter import AllureReporter as AllureCommonsReporter
from allure_commons.types import LabelType
from baby_steps import given, then, when
from vedro.core import Dispatcher
from vedro.events import ArgParsedEvent
from vedro.plugins.director import DirectorPlugin

from vedro_allure_reporter import AllureLabelHooks, AllureReporter, AllureReporterPlugin

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
        assert len(plugin_manager_.mock_calls) == 3
        assert plugin_manager_.mock_calls[0] == call.register(reporter._label_hooks)
        assert plugin_manager_.mock_calls[1] == call.register(reporter._allure_step_hooks)
        assert plugin_manager_.mock_calls[2] == call.register(logger_)


def test_decorate_as_label():
    with given:
        reporter_mock = Mock(spec=AllureCommonsReporter)
        hooks = AllureLabelHooks(reporter_mock)

        class MyScenario:
            pass

    with when:
        decorator = hooks.decorate_as_label(LabelType.ID, ("12345",))
        result = decorator(MyScenario)

    with then:
        assert result is MyScenario
        labels = getattr(MyScenario, "__vedro__allure_dynamic_labels__", ())
        assert len(labels) == 1
        assert labels[0].name == LabelType.ID
        assert labels[0].value == "12345"


def test_decorate_as_label_multiple():
    with given:
        reporter_mock = Mock(spec=AllureCommonsReporter)
        hooks = AllureLabelHooks(reporter_mock)

        class MyScenario:
            pass

    with when:
        decorator1 = hooks.decorate_as_label(LabelType.ID, ("111",))
        MyScenario = decorator1(MyScenario)
        decorator2 = hooks.decorate_as_label(LabelType.TAG, ("unit",))
        MyScenario = decorator2(MyScenario)

    with then:
        labels = getattr(MyScenario, "__vedro__allure_dynamic_labels__", ())
        assert len(labels) == 2
        assert labels[0].name == LabelType.ID
        assert labels[0].value == "111"
        assert labels[1].name == LabelType.TAG
        assert labels[1].value == "unit"


def test_add_label():
    with given:
        reporter_mock = Mock(spec=AllureCommonsReporter)
        test_result = TestResult(uuid="test-uuid", name="Test")
        reporter_mock.get_test = Mock(return_value=test_result)
        hooks = AllureLabelHooks(reporter_mock)

    with when:
        hooks.add_label(LabelType.ID, ("12345",))

    with then:
        assert len(test_result.labels) == 1
        assert test_result.labels[0].name == LabelType.ID
        assert test_result.labels[0].value == "12345"
        reporter_mock.get_test.assert_called_once_with(None)


def test_add_label_no_current_test():
    with given:
        reporter_mock = Mock(spec=AllureCommonsReporter)
        reporter_mock.get_test = Mock(return_value=None)
        hooks = AllureLabelHooks(reporter_mock)

    with when:
        hooks.add_label(LabelType.ID, ("12345",))

    with then:
        reporter_mock.get_test.assert_called_once_with(None)


def test_add_label_multiple():
    with given:
        reporter_mock = Mock(spec=AllureCommonsReporter)
        test_result = TestResult(uuid="test-uuid", name="Test")
        reporter_mock.get_test = Mock(return_value=test_result)
        hooks = AllureLabelHooks(reporter_mock)

    with when:
        hooks.add_label(LabelType.ID, ("111", "222"))

    with then:
        assert len(test_result.labels) == 2
        assert test_result.labels[0].name == LabelType.ID
        assert test_result.labels[0].value == "111"
        assert test_result.labels[1].name == LabelType.ID
        assert test_result.labels[1].value == "222"
