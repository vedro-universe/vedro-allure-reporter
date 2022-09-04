from typing import Any, Callable, Type, TypeVar

from allure_commons.model2 import Label as AllureLabel
from allure_commons.types import LabelType
from vedro import Scenario

__all__ = ("Epic", "Feature", "Story", "NamedLabel", "allure_labels")


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


T = TypeVar("T", bound=Type[Scenario])


def allure_labels(*labels: AllureLabel) -> Callable[[T], T]:
    assert len(labels) > 0

    def wrapped(scenario: T) -> T:
        setattr(scenario, "__vedro__allure_labels__", labels)
        return scenario
    return wrapped
