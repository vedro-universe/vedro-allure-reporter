import asyncio
from typing import Any, Callable, Coroutine, Type, Union

from vedro.core import ConfigType, Dispatcher, Plugin, PluginConfig, ScenarioScheduler
from vedro.events import (
    ArgParsedEvent,
    ArgParseEvent,
    CleanupEvent,
    ConfigLoadedEvent,
    ScenarioFailedEvent,
    ScenarioPassedEvent,
    ScenarioRunEvent,
    ScenarioSkippedEvent,
    StartupEvent,
)

from ._allure_scheduler import AllureRerunnerScenarioScheduler

__all__ = ("AllureRerunner", "AllureRerunnerPlugin",)

SleepType = Callable[[float], Coroutine[Any, Any, None]]


class AllureRerunnerPlugin(Plugin):
    """
    A plugin to rerun failed scenarios according to Allure logic.

    This plugin allows scenarios that fail to be rerun a specified number of times.
    According to Allure logic, if any rerun passes, the scenario is reported as passed.
    Otherwise, it remains failed. The plugin also supports introducing a delay
    before each rerun if desired.
    """

    def __init__(self, config: Type["AllureRerunner"], *,
                 sleep: SleepType = asyncio.sleep) -> None:
        """
        Initialize the AllureRerunnerPlugin.

        :param config: The plugin configuration class (AllureRerunner).
        :param sleep: An async sleep function (default: asyncio.sleep).
        """
        super().__init__(config)
        self._sleep = sleep
        self._reruns: int = 0
        self._reruns_delay: float = 0.0
        self._global_config: Union[ConfigType, None] = None
        self._scheduler: Union[ScenarioScheduler, None] = None
        self._rerun_scenario_id: Union[str, None] = None
        self._reran: int = 0
        self._times: int = 0

    def subscribe(self, dispatcher: Dispatcher) -> None:
        """
        Subscribe to events for handling configuration, scenario execution,
        scenario end results, and cleanup.

        :param dispatcher: The event dispatcher.
        """
        dispatcher.listen(ConfigLoadedEvent, self.on_config_loaded) \
                  .listen(ArgParseEvent, self.on_arg_parse) \
                  .listen(ArgParsedEvent, self.on_arg_parsed) \
                  .listen(StartupEvent, self.on_startup) \
                  .listen(ScenarioRunEvent, self.on_scenario_execute) \
                  .listen(ScenarioSkippedEvent, self.on_scenario_execute) \
                  .listen(ScenarioPassedEvent, self.on_scenario_end) \
                  .listen(ScenarioFailedEvent, self.on_scenario_end) \
                  .listen(CleanupEvent, self.on_cleanup)

    def on_config_loaded(self, event: ConfigLoadedEvent) -> None:
        """
        Handle the configuration loaded event.

        Stores the global configuration reference for later use in registering
        the scenario scheduler.

        :param event: The ConfigLoadedEvent containing the loaded configuration.
        """
        self._global_config = event.config

    def on_arg_parse(self, event: ArgParseEvent) -> None:
        """
        Handle the argument parsing event.

        Adds command-line arguments for controlling reruns and rerun delay.

        :param event: The ArgParseEvent containing the argument parser.
        """
        group = event.arg_parser.add_argument_group("Allure Rerunner")
        help_message = (
            "Number of times to rerun failed scenarios (default: 0). "
            "If at least one rerun passes, the scenario is reported as passed, otherwise failed"
        )
        group.add_argument("--allure-reruns", type=int, default=self._reruns, help=help_message)
        group.add_argument("--allure-reruns-delay", type=float, default=self._reruns_delay,
                           help="Delay in seconds between reruns (default: 0.0s)")

    def on_arg_parsed(self, event: ArgParsedEvent) -> None:
        """
        Handle the event triggered after arguments are parsed.

        Validates the provided values for reruns and delay, and if rerunning is enabled,
        registers the AllureRerunnerScenarioScheduler.

        :param event: The ArgParsedEvent with parsed arguments.
        :raises ValueError: If invalid rerun configurations are provided.
        """
        self._reruns = event.args.allure_reruns
        self._reruns_delay = event.args.allure_reruns_delay

        if self._reruns < 0:
            raise ValueError("--allure-reruns must be >= 0")

        if self._reruns_delay < 0.0:
            raise ValueError("--allure-reruns-delay must be >= 0.0")

        if (self._reruns_delay > 0.0) and (self._reruns < 1):
            raise ValueError("--allure-reruns-delay must be used with --allure-reruns > 0")

        if self._is_rerunning_enabled():
            assert self._global_config is not None  # for type checking
            self._global_config.Registry.ScenarioScheduler.register(
                AllureRerunnerScenarioScheduler,
                self
            )

    def on_startup(self, event: StartupEvent) -> None:
        """
        Handle the startup event.

        Stores the scenario scheduler for scheduling reruns later.

        :param event: The StartupEvent containing the current scheduler.
        """
        self._scheduler = event.scheduler

    async def on_scenario_execute(self,
                                  event: Union[ScenarioRunEvent, ScenarioSkippedEvent]) -> None:
        """
        Handle the scenario execution event (both run and skipped).

        If the scenario is being rerun and a delay is configured, waits for the specified
        delay time before executing the scenario again.

        :param event: Either ScenarioRunEvent or ScenarioSkippedEvent.
        """
        if not self._is_rerunning_enabled():
            return

        scenario = event.scenario_result.scenario
        if (self._rerun_scenario_id == scenario.unique_id) and (self._reruns_delay > 0.0):
            await self._sleep(self._reruns_delay)

    async def on_scenario_end(self,
                              event: Union[ScenarioPassedEvent, ScenarioFailedEvent]) -> None:
        """
        Handle the scenario end event (either passed or failed).

        If the scenario fails and reruns are enabled, schedule the specified number of reruns.
        Each rerun attempt will potentially change the final outcome if it passes.

        :param event: Either ScenarioPassedEvent or ScenarioFailedEvent.
        """
        if not self._is_rerunning_enabled():
            return
        assert isinstance(self._scheduler, ScenarioScheduler)  # for type checking

        scenario = event.scenario_result.scenario
        if scenario.unique_id != self._rerun_scenario_id:
            self._rerun_scenario_id = scenario.unique_id

            if event.scenario_result.is_failed():
                self._reran += 1
                for _ in range(self._reruns):
                    self._scheduler.schedule(scenario)
                    self._times += 1

    def on_cleanup(self, event: CleanupEvent) -> None:
        """
        Handle the cleanup event.

        Adds a summary message to the report indicating how many scenarios were rerun
        and how many times, as well as if a delay was applied.

        :param event: The CleanupEvent containing the report.
        """
        if not self._is_rerunning_enabled():
            return
        message = self._get_summary_message()
        event.report.add_summary(message)

    def _is_rerunning_enabled(self) -> bool:
        """
        Check if rerunning is enabled.

        :return: True if reruns are greater than zero, False otherwise.
        """
        return self._reruns > 0

    def _get_summary_message(self) -> str:
        """
        Construct a summary message for the final report.

        :return: A string summarizing how many scenarios were rerun and how many times,
                 including any configured delay.
        """
        ss = "" if self._reran == 1 else "s"
        ts = "" if self._times == 1 else "s"
        message = f"rerun {self._reran} scenario{ss}, {self._times} time{ts}"
        if self._reruns_delay:
            message += f", with delay {self._reruns_delay!r}s"
        return message


class AllureRerunner(PluginConfig):
    """
    Plugin configuration for the Allure Rerunner plugin.

    This configuration is used to enable rerunning failed scenarios according to Allure logic.
    If any rerun passes, the scenario is reported as passed; otherwise, it remains failed.
    """

    plugin = AllureRerunnerPlugin
    description = ("Reruns failed scenarios according to Allure logic: "
                   "if at least one rerun passes, the scenario is reported as passed")
