from typing import Any, Type

from allure_commons.types import LabelType
from vedro._scenario import Scenario


class Epic:
    name = LabelType.EPIC


class Feature:
    name = LabelType.FEATURE


class Story:
    name = LabelType.STORY


def allure_labels(*labels: Any) -> Any:
    def wrapped(scenario: Type[Scenario]) -> Type[Scenario]:
        setattr(scenario, "labels", labels)
        return scenario
    return wrapped
