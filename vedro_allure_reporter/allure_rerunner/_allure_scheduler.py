from typing import List

from vedro.core import AggregatedResult, MonotonicScenarioScheduler, ScenarioResult

__all__ = ("AllureRerunnerScenarioScheduler",)


class AllureRerunnerScenarioScheduler(MonotonicScenarioScheduler):
    """
    Implements a scenario scheduler adhering to Allure reporting logic.

    This scheduler extends the MonotonicScenarioScheduler to aggregate scenario results
    according to Allure rules. Specifically, it determines the final scenario outcome as:
      - Passed, if at least one rerun of the scenario passed.
      - Failed, if every rerun of the scenario failed.
    """

    def aggregate_results(self, scenario_results: List[ScenarioResult]) -> AggregatedResult:
        """
        Aggregate scenario results into a single outcome following Allure logic.

        This method takes multiple scenario results (original run plus any reruns)
        and consolidates them into one final result. According to Allure logic:
          - If at least one scenario run passed, the final result is passed.
          - If all scenario runs failed, the final result is failed.

        :param scenario_results: A non-empty list of scenario results,
                                 including original and rerun attempts.
        :return: An AggregatedResult instance reflecting the Allure-compliant final outcome.
        """
        assert len(scenario_results) > 0

        passed, failed = [], []
        for scenario_result in scenario_results:
            if scenario_result.is_passed():
                passed.append(scenario_result)
            elif scenario_result.is_failed():
                failed.append(scenario_result)

        # Determine the final result:
        # If no passed and no failed, fallback to last scenario_result (edge case)
        # If at least one passed scenario, final is passed; otherwise, failed.
        if len(passed) == 0 and len(failed) == 0:
            result = scenario_results[-1]
        else:
            result = passed[-1] if len(passed) > 0 else failed[-1]

        return AggregatedResult.from_existing(result, scenario_results)
