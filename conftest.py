import os

# NotifyNL: upstream (alphagov) tests that don't hold for NL are listed in superseded_tests_nl.toml instead of being
# skipped inline, so upstream test files stay identical to alphagov's. This plugin reads that manifest: tests with an NL
# twin or counterpart are left out of the run, tests without one still show as skipped. See notifynl-utils'
# notifications_utils/testing_nl/superseded_tests.py for the options
# (--nl-verify, --nl-show-superseded, --nl-run-superseded).
pytest_plugins = ["notifications_utils.testing_nl.superseded_tests"]


def pytest_configure(config):
    # NotifyNL: .env sets AWS_ENDPOINT_URL so the local app can reach the devcontainer's ministack. pytest-dotenv loads
    # .env, and botocore honours that env var even inside moto's mock_aws(), so without this the "mocked" S3 calls hit
    # the real ministack container instead. Cleared here rather than at import time because it has to run after
    # pytest-dotenv/pytest-env have set it. Same fix as notifynl-api's tests/conftest.py.
    os.environ.pop("AWS_ENDPOINT_URL", None)
