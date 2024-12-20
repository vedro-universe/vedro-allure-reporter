# Changelog

## v1.0

### v1.11 (2024-12-20)

- Add support for reporting rescheduled scenarios [#14](https://github.com/vedro-universe/vedro-allure-reporter/pull/14)
- Introduce `AllureRerunner` for handling rerun scenarios [#14](https://github.com/vedro-universe/vedro-allure-reporter/pull/14)
- Add warnings for incorrect rerun flag usage [#14](https://github.com/vedro-universe/vedro-allure-reporter/pull/14)

## v1.10 (2024-11-01)

- Add `fullName` attribute to test cases for better identification ([f8472f5](https://github.com/vedro-universe/vedro-allure-reporter/commit/f8472f5d96ce45f48e7d3a73cd78cb881a3a31c0))
- Ensure error message is not empty by using exception type name as fallback ([c77d47a](https://github.com/vedro-universe/vedro-allure-reporter/commit/c77d47a74d1c2379431cceb36c681878a0bee846))
- Refactor exception handling for improved traceback extraction and formatting ([21d2678](https://github.com/vedro-universe/vedro-allure-reporter/commit/21d2678383a23ad097ed5a4091080027b6d37214))

### v1.9 (2024-10-21)

- Add configuration for cleaning report directory ([05bda39](https://github.com/vedro-universe/vedro-allure-reporter/commit/05bda39d330163a33a3dfe5b453b0e6efba54b5e))

### v1.8 (2023-06-24)

- Add `--allure-labels` arg [#9](https://github.com/vedro-universe/vedro-allure-reporter/pull/9)

### v1.7.1 (2023-06-06)

- Update requirements and README [#11](https://github.com/vedro-universe/vedro-allure-reporter/pull/11)

### v1.7.0 (2023-05-23)

- Support labels for parametrized scenarios [#10](https://github.com/vedro-universe/vedro-allure-reporter/pull/10)

### v1.6.0 (2022-09-04)

- Add `project_name` config param [#8](https://github.com/vedro-universe/vedro-allure-reporter/pull/8)
- Fix `testCaseId` generation [#8](https://github.com/vedro-universe/vedro-allure-reporter/pull/8)

### v1.5.0 (2022-07-25)

- Fix postponed step attachment [#6](https://github.com/vedro-universe/vedro-allure-reporter/pull/6)

### v1.4.0 (2022-07-01)

- Add scenario allure labels [#5](https://github.com/vedro-universe/vedro-allure-reporter/pull/5)

### v1.3.0 (2022-06-05)

- Add attachments [#4](https://github.com/vedro-universe/vedro-allure-reporter/pull/4)
- Param `--allure-report-dir` is now optional

### v1.2.0 (2022-05-25)

- Fix: send only skipped by user

### v1.1.0 (2022-04-30)

- Add tag attach feature [#3](https://github.com/vedro-universe/vedro-allure-reporter/pull/3)

### v1.0.0 (2022-04-27)

- Add plugin configuration [#2](https://github.com/vedro-universe/vedro-allure-reporter/pull/2)
- Add custom label attach feature [#2](https://github.com/vedro-universe/vedro-allure-reporter/pull/2)
