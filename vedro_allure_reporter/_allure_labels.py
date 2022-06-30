from typing import Any, Type

from allure_commons.model2 import Label as AllureLabel
from allure_commons.types import LabelType
from vedro._scenario import Scenario


class NamedLabel(AllureLabel):  # type: ignore
    name: Any = ...

    def __init__(self, value: str) -> None:
        self._value = value

    @property
    def value(self) -> str:
        return self._value


class Epic(NamedLabel):
    name = LabelType.EPIC


class Feature(NamedLabel):
    name = LabelType.FEATURE


class Story(NamedLabel):
    name = LabelType.STORY


def allure_labels(*labels: AllureLabel) -> Any:
    assert len(labels) > 0

    def wrapped(scenario: Type[Scenario]) -> Type[Scenario]:
        setattr(scenario, "__vedro__allure_labels__", labels)
        return scenario
    return wrapped
