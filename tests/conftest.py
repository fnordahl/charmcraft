# Copyright 2020-2022 Canonical Ltd.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# For further info, check https://github.com/canonical/charmcraft

import contextlib
import datetime
import json
import imp
import pathlib
import tempfile
import types
from unittest.mock import Mock

import pytest
import responses as responses_module
from craft_parts import callbacks
from craft_providers import Executor

from charmcraft import config as config_module, instrum
from charmcraft import deprecations, parts
from charmcraft.bases import get_host_as_base
from charmcraft.config import Base, BasesConfiguration
from charmcraft.providers import Provider


@pytest.fixture(autouse=True, scope="session")
def tmpdir_under_tmpdir(tmpdir_factory):
    tempfile.tempdir = str(tmpdir_factory.getbasetemp())


@pytest.fixture(autouse=True, scope="session")
def setup_parts():
    parts.setup_parts()


@pytest.fixture
def config(tmp_path):
    """Provide a config class with an extra set method for the test to change it."""

    class TestConfig(config_module.Config, frozen=False):
        """The Config, but with a method to set test values."""

        def set(self, prime=None, **kwargs):
            # prime is special, so we don't need to write all this structure in all tests
            if prime is not None:
                if self.parts is None:
                    self.parts = {}
                self.parts["charm"] = {"plugin": "charm", "prime": prime}

            # the rest is direct
            for k, v in kwargs.items():
                object.__setattr__(self, k, v)

    project = config_module.Project(
        dirpath=tmp_path,
        started_at=datetime.datetime.utcnow(),
        config_provided=True,
    )

    base = BasesConfiguration(**{"build-on": [get_host_as_base()], "run-on": [get_host_as_base()]})
    return TestConfig(type="charm", bases=[base], project=project)


@pytest.fixture
def bundle_config(tmp_path):
    """Provide a config class with an extra set method for the test to change it."""

    class TestConfig(config_module.Config, frozen=False):
        """The Config, but with a method to set test values."""

        def set(self, prime=None, **kwargs):
            # prime is special, so we don't need to write all this structure in all tests
            if prime is not None:
                if self.parts is None:
                    self.parts = {}
                self.parts["bundle"] = {"plugin": "bundle", "prime": prime}

            # the rest is direct
            for k, v in kwargs.items():
                object.__setattr__(self, k, v)

    project = config_module.Project(
        dirpath=tmp_path,
        started_at=datetime.datetime.utcnow(),
        config_provided=True,
    )

    return TestConfig(type="bundle", project=project)


@pytest.fixture(autouse=True)
def intertests_cleanups():
    """Run some cleanups between tests.

    Before each test:

    - reload the instrumentator module to start clean.

    After each test:

    - clear the already-notified structure for each test (this is needed as that
      structure is a module-level one (by design), so otherwise it will be dirty
      between tests).

    - unregister all Craft Parts plugins callbacks
    """
    imp.reload(instrum)
    yield
    deprecations._ALREADY_NOTIFIED.clear()
    callbacks.unregister_all()


@pytest.fixture
def responses():
    """Simple helper to use responses module as a fixture, for easier integration in tests."""
    with responses_module.RequestsMock() as rsps:
        yield rsps


@pytest.fixture
def mock_instance():
    """Provide a mock instance (Executor)."""
    yield Mock(spec=Executor)


@pytest.fixture(autouse=True)
def fake_provider(mock_instance, monkeypatch):
    """Provide a minimal/fake provider."""

    class FakeProvider(Provider):
        def clean_project_environments(
            self,
            *,
            charm_name: str,
            project_path: pathlib.Path,
            bases_index: int,
            build_on_index: int,
        ) -> None:
            pass

        @classmethod
        def ensure_provider_is_available(cls) -> None:
            pass

        def environment(
            self,
            *,
            instance_name: str,
        ) -> Executor:
            return mock_instance

        @contextlib.contextmanager
        def launched_environment(
            self,
            *,
            charm_name: str,
            project_path: pathlib.Path,
            base: Base,
            bases_index: int,
            build_on_index: int,
        ):
            yield mock_instance

        @classmethod
        def is_provider_available(cls) -> bool:
            """Check if provider is installed and available for use.

            :returns: True if installed.
            """
            return True

    return FakeProvider()


@pytest.fixture
def create_config(tmp_path):
    """Helper to create a config file in disk.

    If content is not given, create a minimum valid file.
    """

    def create_config(text=None):
        if text is None:
            text = """
                type: charm
                bases:
                  - build-on:
                    - name: test-build-name
                      channel: test-build-channel
                    run-on:
                    - name: test-build-name
                      channel: test-build-channel
            """
        test_file = tmp_path / "charmcraft.yaml"
        test_file.write_text(text)
        return tmp_path

    return create_config


@pytest.fixture
def emitter(emitter):
    """Monkeypatch craft-cli's emitter fixture to easily test the JSON encoded output."""

    def assert_json_output(self, expected_content):
        """Get last output, which should be a message, and validate its content."""
        last_output = self.interactions[-1]
        output_type, raw_output = last_output.args
        assert output_type == "message", "Last command output is not 'message'"
        try:
            output_content = json.loads(raw_output)
        except json.decoder.JSONDecodeError:
            pytest.fail("Last command output is not valid JSON.")
        assert output_content == expected_content

    emitter.assert_json_output = types.MethodType(assert_json_output, emitter)
    return emitter
