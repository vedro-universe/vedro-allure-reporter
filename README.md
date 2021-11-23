# Vedro Allure Reporter

[![Codecov](https://img.shields.io/codecov/c/github/nikitanovosibirsk/vedro-allure-reporter/master.svg?style=flat-square)](https://codecov.io/gh/nikitanovosibirsk/vedro-allure-reporter)
[![PyPI](https://img.shields.io/pypi/v/vedro-allure-reporter.svg?style=flat-square)](https://pypi.python.org/pypi/vedro-allure-reporter/)
[![PyPI - Downloads](https://img.shields.io/pypi/dm/vedro-allure-reporter?style=flat-square)](https://pypi.python.org/pypi/vedro-allure-reporter/)
[![Python Version](https://img.shields.io/pypi/pyversions/vedro-allure-reporter.svg?style=flat-square)](https://pypi.python.org/pypi/vedro-allure-reporter/)

[Allure](https://docs.qameta.io/allure/) reporter for [Vedro](https://github.com/nikitanovosibirsk/vedro) framework

## Installation

```shell
$ pip3 install vedro-allure-reporter
```

```python
# ./bootstrap.py
import vedro
from vedro_allure_reporter import AllureReporter

vedro.run(plugins=[AllureReporter()])
```

## Usage

### Run tests

```shell
$ python3 bootstrap.py -r allure --allure-report-dir ./allure_reports
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

Documentation — https://docs.qameta.io/allure-testops/quickstart/qa-auto/
