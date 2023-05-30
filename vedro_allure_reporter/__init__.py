from allure_commons.model2 import Label as AllureLabel

from ._allure_labels import Epic, Feature, Story, allure_labels
from ._allure_reporter import AllureReporter, AllureReporterPlugin

__version__ = "1.7.0"
__all__ = ("AllureReporter", "AllureReporterPlugin", "AllureLabel",
           "Epic", "Story", "Feature", "allure_labels")
