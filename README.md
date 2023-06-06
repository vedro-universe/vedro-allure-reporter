# Vedro Allure Reporter

[![Codecov](https://img.shields.io/codecov/c/github/vedro-universe/vedro-allure-reporter/master.svg?style=flat-square)](https://codecov.io/gh/vedro-universe/vedro-allure-reporter)
[![PyPI](https://img.shields.io/pypi/v/vedro-allure-reporter.svg?style=flat-square)](https://pypi.python.org/pypi/vedro-allure-reporter/)
[![PyPI - Downloads](https://img.shields.io/pypi/dm/vedro-allure-reporter?style=flat-square)](https://pypi.python.org/pypi/vedro-allure-reporter/)
[![Python Version](https://img.shields.io/pypi/pyversions/vedro-allure-reporter.svg?style=flat-square)](https://pypi.python.org/pypi/vedro-allure-reporter/)

[Allure](https://docs.qameta.io/allure/) reporter for [Vedro](https://vedro.io/) testing framework.

## Installation

<details open>
<summary>Quick</summary>
<p>

For a quick installation, you can use a plugin manager as follows:

```shell
$ vedro plugin install vedro-allure-reporter
```

</p>
</details>

<details>
<summary>Manual</summary>
<p>

To install manually, follow these steps:

1. Install the package using pip:

```shell
$ pip3 install vedro-allure-reporter
```

2. Next, activate the plugin in your `vedro.cfg.py` configuration file:

```python
# ./vedro.cfg.py
import vedro
import vedro_allure_reporter

class Config(vedro.Config):

    class Plugins(vedro.Config.Plugins):

        class AllureReporter(vedro_allure_reporter.AllureReporter):
            enabled = True
```

</p>
</details>

## Usage

To run tests with the Allure reporter, use the following command:

```shell
$ vedro run -r rich allure
```

This command executes your tests and saves the report data in the `./allure_reports` directory.

To generate a report from the saved data, use the [Allure command-line tool](https://docs.qameta.io/allure/#_installing_a_commandline) as follows:

```shell
$ allure serve ./allure_reports
```

This command will serve up the report ([demo](https://allure-framework.github.io/allure-demo/5/)).

---

Explore more at https://vedro.io/en/docs/integrations/allure-reporter
