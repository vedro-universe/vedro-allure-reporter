from allure_commons.model2 import Label as AllureLabel

from ._allure_labels import Epic, Feature, Story, allure_labels
from ._allure_reporter import AllureReporter, AllureReporterPlugin
from ._allure_steps import (
    add_link,
    add_step_parameter,
    allure_step,
    attach_file,
    attach_json,
    attach_screenshot,
    attach_text,
    create_step_parameter,
)

__version__ = "1.11.1"
__all__ = ("AllureReporter", "AllureReporterPlugin", "allure_step", "add_step_parameter",
           "create_step_parameter", "attach_text", "attach_json", "attach_file",
           "attach_screenshot", "add_link", "AllureLabel", "Epic", "Story", "Feature",
           "allure_labels")
