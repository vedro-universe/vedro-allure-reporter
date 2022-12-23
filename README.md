# Vedro Allure Reporter

[![Codecov](https://img.shields.io/codecov/c/github/nikitanovosibirsk/vedro-allure-reporter/master.svg?style=flat-square)](https://codecov.io/gh/nikitanovosibirsk/vedro-allure-reporter)
[![PyPI](https://img.shields.io/pypi/v/vedro-allure-reporter.svg?style=flat-square)](https://pypi.python.org/pypi/vedro-allure-reporter/)
[![PyPI - Downloads](https://img.shields.io/pypi/dm/vedro-allure-reporter?style=flat-square)](https://pypi.python.org/pypi/vedro-allure-reporter/)
[![Python Version](https://img.shields.io/pypi/pyversions/vedro-allure-reporter.svg?style=flat-square)](https://pypi.python.org/pypi/vedro-allure-reporter/)

[Allure](https://docs.qameta.io/allure/) reporter for [Vedro](https://vedro.io/) framework

## Installation

### 1. Install package

```shell
$ pip3 install vedro-allure-reporter
```

### 2. Enable plugin

```python
# ./vedro.cfg.py
import vedro
import vedro_allure_reporter as allure_reporter

class Config(vedro.Config):

    class Plugins(vedro.Config.Plugins):

        class AllureReporter(allure_reporter.AllureReporter):
            enabled = True
```

## Usage

### Run tests

```shell
$ vedro run -r allure --allure-report-dir ./allure_reports
```

### Generate report via [Allure command-line tool](https://docs.qameta.io/allure/#_installing_a_commandline)

```shell
$ allure serve ./allure_reports
```

### Upload report to [Allure TestOps](https://docs.qameta.io/allure-testops/)

```shell
$ export ALLURE_ENDPOINT=<endpoint>
$ export ALLURE_PROJECT_ID=<project_id>
$ export ALLURE_TOKEN=<token>

$ export LAUNCH_ID=`allurectl launch create --launch-name test --no-header --format ID | tail -n1`
$ allurectl upload ./allure_reports --launch-id $LAUNCH_ID
$ allurectl launch close $LAUNCH_ID
```

Docs — https://docs.qameta.io/allure-testops/quickstart/qa-auto/

## Documentation

### Custom Global Labels

Global labels will be added to each scenario

```python
# ./vedro.cfg.py
import vedro
import vedro_allure_reporter as allure_reporter
from vedro_allure_reporter import AllureLabel

class Config(vedro.Config):

    class Plugins(vedro.Config.Plugins):

        class AllureReporter(allure_reporter.AllureReporter):
            enabled = True

            labels = [
                AllureLabel("custom", "value")
            ]
```

### Custom Scenario Labels

Scenario labels will be added to specific scenario

```python
# ./scenarios/sign_up_user.py
import vedro
from vedro_allure_reporter import allure_labels, Story, AllureLabel

@allure_labels(Story("Sign Up"), AllureLabel("custom", "value"))
class Scenario(vedro.Scenario):
    subject = "sign up user via email"

```
