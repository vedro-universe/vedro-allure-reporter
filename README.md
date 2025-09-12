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

### Allure Steps

Create detailed step-by-step documentation for your tests using the `allure_step` functionality:

#### Basic Step Usage

```python
from vedro_allure_reporter import allure_step

# Using decorator
@allure_step("Login with username {username}")
def login(username: str, password: str):
    # Your login logic here
    pass

# Using context manager
def test_user_workflow():
    with allure_step("Navigate to dashboard"):
        # Navigation logic
        pass
    
    with allure_step("Verify user data"):
        # Verification logic  
        pass
```

#### Attachments

Add rich context to your test steps with attachments:

```python
from vedro_allure_reporter import attach_text, attach_json, attach_file

with allure_step("API Response Validation"):
    response_data = {"status": "success", "user_id": 123}
    attach_json(response_data, name="API Response")
    attach_text("Validation completed successfully", name="Validation Log")
```

#### Nested Steps

Create hierarchical step structures for complex workflows:

```python
def complex_user_registration():
    with allure_step("User Registration Flow"):
        with allure_step("Input Validation"):
            with allure_step("Email Format Check"):
                # Email validation logic
                pass
            with allure_step("Password Strength Check"):
                # Password validation logic
                pass
        
        with allure_step("Account Creation"):
            # Account creation logic
            pass
```

---

Explore more at https://vedro.io/docs/integrations/allure-reporter
