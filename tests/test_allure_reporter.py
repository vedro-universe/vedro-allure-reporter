from vedro.plugins.director import Reporter

from vedro_allure_reporter import AllureReporter


def test_allure_reporter():
    reporter = AllureReporter()
    assert isinstance(reporter, Reporter)
