from argparse import Namespace
from contextlib import contextmanager
from typing import Any, Dict, List, Optional
from unittest.mock import Mock, patch
from uuid import uuid4

import pytest
from allure_commons.logger import AllureMemoryLogger
from vedro.core import Dispatcher, ScenarioResult, StepResult

__all__ = ("plugin_manager_", "logger_", "logger_factory_", "dispatcher",
           "make_parsed_args", "logger", "patch_uuid", "make_test_case",)


@pytest.fixture()
def plugin_manager_() -> Mock:
    return Mock()


@pytest.fixture()
def logger_() -> Mock:
    return Mock()


@pytest.fixture()
def logger_factory_(logger_) -> Mock:
    return Mock(side_effect=Mock(return_value=logger_))


@pytest.fixture()
def dispatcher() -> Dispatcher:
    return Dispatcher()


@pytest.fixture()
def logger() -> AllureMemoryLogger:
    return AllureMemoryLogger()


def make_parsed_args(*, allure_report_dir: str, allure_attach_scope: bool = False) -> Namespace:
    return Namespace(allure_report_dir=allure_report_dir, allure_attach_scope=allure_attach_scope)


@contextmanager
def patch_uuid(uuid: Optional[str] = None):
    if uuid is None:
        uuid = str(uuid4())
    with patch("allure_commons.utils.uuid4", Mock(return_value=uuid)):
        yield uuid


def make_test_case(uuid: str, scenario_result: ScenarioResult,
                   steps: Optional[List[StepResult]] = None) -> Dict[str, Any]:
    test_case = {
        "uuid": uuid,
        "name": scenario_result.scenario_subject,
        "status": scenario_result.status.value.lower(),
        "start": int(scenario_result.started_at * 1000),
        "stop": int(scenario_result.ended_at * 1000),
        "historyId": scenario_result.scenario.unique_id,
        "testCaseId": scenario_result.scenario.unique_id,
        "labels": [
            {
                "name": "package",
            },
            {
                "name": "suite",
                "value": "scenarios",
            }
        ]
    }
    if steps:
        test_case["steps"] = []
        for step_result in steps:
            test_case["steps"].append({
                "name": step_result.step_name,
                "status": step_result.status.value.lower(),
                "start": int(step_result.started_at * 1000),
                "stop": int(step_result.ended_at * 1000),
            })
    return test_case
