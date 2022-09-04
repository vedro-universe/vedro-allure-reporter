import os
import string
from argparse import Namespace
from contextlib import contextmanager
from pathlib import Path
from random import choice
from typing import Any, Dict, List, Optional, Union
from unittest.mock import Mock, patch
from uuid import UUID, uuid4

import pytest
from allure_commons.logger import AllureMemoryLogger
from allure_commons.model2 import ATTACHMENT_PATTERN, Attachment
from vedro import Config, Scenario
from vedro.core import (
    ArgumentParser,
    Dispatcher,
    FileArtifact,
    MemoryArtifact,
    ScenarioResult,
    StepResult,
    VirtualScenario,
)
from vedro.events import ArgParseEvent, ConfigLoadedEvent
from vedro.plugins.director import Director, DirectorPlugin

from vedro_allure_reporter import AllureLabel, AllureReporterPlugin

__all__ = ("plugin_manager_", "logger_", "logger_factory_", "dispatcher", "director",
           "make_parsed_args", "logger", "patch_uuid", "make_test_case", "make_scenario_result",
           "choose_reporter", "create_attachment",)


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
def director(dispatcher: Dispatcher) -> DirectorPlugin:
    director = DirectorPlugin(Director)
    director.subscribe(dispatcher)
    return director


@pytest.fixture()
def logger() -> AllureMemoryLogger:
    return AllureMemoryLogger()


def make_parsed_args(*, allure_report_dir: str, allure_attach_scope: bool = False) -> Namespace:
    return Namespace(allure_report_dir=allure_report_dir,
                     allure_attach_scope=allure_attach_scope)


@contextmanager
def patch_uuid(uuid: Optional[str] = None):
    if uuid is None:
        uuid = str(uuid4())
    with patch("allure_commons.utils.uuid4", Mock(return_value=uuid)):
        yield uuid


def make_vscenario(*,
                   path: Optional[Path] = None,
                   subject: Optional[str] = None,
                   tags: Optional[List[str]] = None,
                   labels: Optional[List[AllureLabel]] = None) -> VirtualScenario:
    namespace = {}
    if path is not None:
        namespace["__file__"] = str(path)
    if subject is not None:
        namespace["subject"] = subject
    if tags is not None:
        namespace["tags"] = tags
    if labels is not None:
        namespace['__vedro__allure_labels__'] = labels
    scenario = type("Scenario", (Scenario,), namespace)
    return VirtualScenario(scenario, [])


def make_scenario_result(path: Optional[Path] = None,
                         subject: Optional[str] = None,
                         tags: Optional[List[str]] = None,
                         labels: Optional[List[AllureLabel]] = None) -> ScenarioResult:
    if path is None:
        path = make_path("namespace")
    if subject is None:
        subject = make_random_name()
    vscenario = make_vscenario(path=path, subject=subject, tags=tags, labels=labels)
    return ScenarioResult(vscenario)


def make_test_case(uuid: str, scenario_result: ScenarioResult,
                   steps: Optional[List[StepResult]] = None,
                   labels: Optional[List[AllureLabel]] = None,
                   attachments: Optional[List[Attachment]] = None) -> Dict[str, Any]:
    test_case = {
        "uuid": uuid,
        "name": scenario_result.scenario.subject,
        "status": scenario_result.status.value.lower(),
        "start": int(scenario_result.started_at * 1000),
        "stop": int(scenario_result.ended_at * 1000),
        "historyId": scenario_result.scenario.unique_id,
        "testCaseId": scenario_result.scenario.unique_id,
        "labels": [
            {"name": "framework", "value": "vedro"},
            {"name": "package", "value": "scenarios.namespace"},
            {"name": "suite", "value": "scenarios"},
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
    if labels:
        for label in labels:
            test_case["labels"].append({
                "name": label.name,
                "value": label.value
            })
    if attachments:
        test_case["attachments"] = []
        for attachment in attachments:
            test_case["attachments"].append({
                "name": attachment.name,
                "source": attachment.source,
                "type": attachment.type,
            })
    return test_case


async def choose_reporter(dispatcher: Dispatcher,
                          director: DirectorPlugin, reporter: AllureReporterPlugin) -> None:
    await dispatcher.fire(ConfigLoadedEvent(Path(), Config))
    await dispatcher.fire(ArgParseEvent(ArgumentParser()))


def create_attachment(artifact: Union[MemoryArtifact, FileArtifact],
                      attachment_uuid: UUID) -> Attachment:
    file_name = ATTACHMENT_PATTERN.format(prefix=attachment_uuid, ext="txt")
    return Attachment(name=artifact.name, source=file_name, type=artifact.mime_type)


def make_random_name(length: int = 10) -> str:
    return ''.join(choice(string.ascii_lowercase) for _ in range(length))


def make_path(path: str = "", name: str = "scenario.py") -> Path:
    return Path(os.getcwd()) / "scenarios" / path / name
