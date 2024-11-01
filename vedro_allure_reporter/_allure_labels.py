from typing import Any, Callable, Type, TypeVar

from allure_commons.model2 import Label as AllureLabel
from allure_commons.types import LabelType
from vedro import Scenario

__all__ = ("Epic", "Feature", "Story", "NamedLabel", "allure_labels")


class NamedLabel(AllureLabel):  # type: ignore
    """
    Represents a custom Allure label with a name and a value.

    This class allows creating Allure labels with a specific value and
    provides a property to access the label's value.
    """

    name: Any = ...

    def __init__(self, value: str) -> None:
        """
        Initialize the NamedLabel with a specified value.

        :param value: The value of the Allure label.
        """
        self._value = value

    @property
    def value(self) -> str:
        """
        Get the value of the Allure label.

        :return: The value of the label as a string.
        """
        return self._value


class Epic(NamedLabel):
    """
    Represents an Allure Epic label.

    This label is used to categorize scenarios under a high-level epic.
    """
    name = LabelType.EPIC


class Feature(NamedLabel):
    """
    Represents an Allure Feature label.

    This label is used to specify the feature associated with a scenario.
    """
    name = LabelType.FEATURE


class Story(NamedLabel):
    """
    Represents an Allure Story label.

    This label is used to associate a scenario with a specific user story.
    """
    name = LabelType.STORY


T = TypeVar("T", bound=Type[Scenario])


def allure_labels(*labels: AllureLabel) -> Callable[[T], T]:
    """
    Decorate a Scenario class to add custom Allure labels.

    This function allows attaching one or more Allure labels to a scenario, making it
    easier to categorize and report in Allure reports.

    :param labels: One or more AllureLabel instances to be added to the scenario.
    :return: A decorator that adds the specified labels to the scenario.
    :raises AssertionError: If no labels are provided.
    """
    assert len(labels) > 0

    def wrapped(scenario: T) -> T:
        """
        Add the specified Allure labels to the given scenario class.

        :param scenario: The Scenario class to which labels will be added.
        :return: The updated Scenario class with attached labels.
        """
        setattr(scenario, "__vedro__allure_labels__", labels)
        return scenario

    return wrapped
