import os
import string
import uuid
from argparse import ArgumentParser, Namespace
from contextlib import contextmanager
from hashlib import blake2b
from pathlib import Path
from random import choice
from typing import Any, Dict, List, Optional, Tuple, Union
from unittest.mock import Mock, patch
from uuid import uuid4

import pytest
from allure_commons.logger import AllureMemoryLogger
from allure_commons.model2 import ATTACHMENT_PATTERN, Attachment
from vedro import Config, Scenario
from vedro.core import (
    AggregatedResult,
    Dispatcher,
    FileArtifact,
    MemoryArtifact,
    ScenarioResult,
    StepResult,
    VirtualScenario,
    VirtualStep,
)
from vedro.events import ArgParsedEvent, ArgParseEvent, ConfigLoadedEvent
from vedro.plugins.director import Director, DirectorPlugin

from vedro_allure_reporter import AllureLabel, AllureReporterPlugin


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


def make_parsed_args(*,
                     allure_report_dir: str,
                     allure_attach_scope: bool = False,
                     allure_labels: Optional[list] = None) -> Namespace:

    return Namespace(allure_report_dir=allure_report_dir,
                     allure_attach_scope=allure_attach_scope,
                     allure_labels=allure_labels,
                     allure_reruns=0,
                     allure_reruns_delay=0.0)


@contextmanager
def patch_uuid(uuid: Optional[str] = None):
    if uuid is None:
        uuid = str(uuid4())
    with patch("allure_commons.utils.uuid4", Mock(return_value=uuid)):
        yield uuid


@contextmanager
def patch_uuids(*uuids: str):
    with patch("allure_commons.utils.uuid4", Mock(side_effect=uuids)):
        yield uuids


def make_vscenario(*,
                   path: Optional[Path] = None,
                   subject: Optional[str] = None,
                   tags: Optional[List[str]] = None,
                   labels: Optional[Tuple[AllureLabel]] = None) -> VirtualScenario:
    namespace = {}
    if path is not None:
        namespace["__file__"] = str(path)
    else:
        namespace["__file__"] = Path(os.getcwd() + f'/{uuid.uuid4()}')
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
                         labels: Optional[Tuple[AllureLabel]] = None) -> ScenarioResult:
    if path is None:
        path = make_path("namespace")
    if subject is None:
        subject = make_random_name()
    vscenario = make_vscenario(path=path, subject=subject, tags=tags, labels=labels)
    return ScenarioResult(vscenario)


def make_aggregated_result(scenario_result: Optional[ScenarioResult] = None) -> AggregatedResult:
    if scenario_result is None:
        scenario_result = make_scenario_result()
    return AggregatedResult.from_existing(scenario_result, [scenario_result])


def get_scenario_unique_id(scenario: VirtualScenario, project_name: str = "") -> str:
    unique_id = f"{project_name}_{scenario.unique_id}"
    return blake2b(unique_id.encode(), digest_size=32).hexdigest()


def make_test_case(uuid: str, scenario_result: ScenarioResult,
                   steps: Optional[List[StepResult]] = None,
                   labels: Optional[Tuple[AllureLabel]] = None,
                   attachments: Optional[List[Attachment]] = None) -> Dict[str, Any]:
    test_case = {
        "uuid": uuid,
        "name": scenario_result.scenario.subject,
        "fullName": scenario_result.scenario.unique_id,
        "status": scenario_result.status.value.lower(),
        "start": int(scenario_result.started_at * 1000),
        "stop": int(scenario_result.ended_at * 1000),
        "historyId": get_scenario_unique_id(scenario_result.scenario),
        "testCaseId": get_scenario_unique_id(scenario_result.scenario),
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
    # Make reporter chosen by calling on_chosen directly
    reporter.on_chosen()


def create_attachment(artifact: Union[MemoryArtifact, FileArtifact],
                      attachment_uuid: str) -> Attachment:
    file_name = ATTACHMENT_PATTERN.format(prefix=attachment_uuid, ext="txt")
    return Attachment(name=artifact.name, source=file_name, type=artifact.mime_type)


def make_random_name(length: int = 10) -> str:
    return ''.join(choice(string.ascii_lowercase) for _ in range(length))


def make_path(path: str = "", name: str = "scenario.py") -> Path:
    return Path(os.getcwd()) / "scenarios" / path / name


def make_vstep(*, name: Optional[str] = None) -> VirtualStep:
    def method(self: Any) -> None:
        pass
    if name:
        method.__name__ = name
    return VirtualStep(method)


def make_step_result(vstep: Optional[VirtualStep] = None) -> StepResult:
    if vstep is None:
        vstep = make_vstep(name=make_random_name())
    step_result = StepResult(vstep)
    return step_result


async def fire_arg_parsed_event(dispatcher: Dispatcher,
                                report_dir: str = "allure_reports",
                                labels: Optional[list] = None) -> None:
    args = make_parsed_args(allure_report_dir=report_dir, allure_labels=labels)
    event = ArgParsedEvent(args)
    await dispatcher.fire(event)
