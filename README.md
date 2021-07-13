# Vedro Allure Reporter

[![PyPI](https://img.shields.io/pypi/v/vedro-allure-reporter.svg?style=flat-square)](https://pypi.python.org/pypi/vedro-allure-reporter/)
[![PyPI - Downloads](https://img.shields.io/pypi/dm/vedro-allure-reporter?style=flat-square)](https://pypi.python.org/pypi/vedro-allure-reporter/)
[![Python Version](https://img.shields.io/pypi/pyversions/vedro-allure-reporter.svg?style=flat-square)](https://pypi.python.org/pypi/vedro-allure-reporter/)

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

```shell
$ python3 bootstrap.py -r allure --allure-report-dir "./reports"
```
