from allure_commons.model2 import Label as AllureLabel

from ._allure_labels import Epic, Feature, Story, allure_labels
from ._allure_reporter import AllureReporter, AllureReporterPlugin
from ._allure_steps import (
    allure_step, AllureStepContext, 
    get_current_steps, clear_current_steps, get_step_depth,
    get_current_step_uuid, add_step_parameter, attach_text,
    attach_json, attach_file, attach_screenshot, add_link,
    create_step_parameter
)

__version__ = "1.11.1"
__all__ = ("AllureReporter", "AllureReporterPlugin", "AllureLabel",
           "Epic", "Story", "Feature", "allure_labels",
           "allure_step", "AllureStepContext",
           "get_current_steps", "clear_current_steps", "get_step_depth",
           "get_current_step_uuid", "add_step_parameter", "attach_text",
           "attach_json", "attach_file", "attach_screenshot", "add_link",
           "create_step_parameter")
