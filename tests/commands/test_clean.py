# Copyright 2021-2022 Canonical Ltd.
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

from unittest import mock

import pytest

from charmcraft.commands.clean import CleanCommand
from charmcraft.config import Base, BasesConfiguration


@pytest.fixture(autouse=True)
def mock_provider(mock_instance, fake_provider):
    mock_provider = mock.Mock(wraps=fake_provider)
    with mock.patch("charmcraft.commands.clean.get_provider", return_value=mock_provider):
        yield mock_provider


@pytest.fixture(autouse=True)
def mock_is_base_available():
    with mock.patch(
        "charmcraft.providers._provider.Provider.is_base_available",
        return_value=(True, None),
    ) as mock_is_base_available:
        yield mock_is_base_available


def test_clean(config, emitter, mock_provider, tmp_path):
    """Test clean with a complex list of bases."""
    metadata_yaml = tmp_path / "metadata.yaml"
    metadata_yaml.write_text("name: foo")

    bases_config = [
        BasesConfiguration(
            **{
                "build-on": [
                    Base(name="x1name", channel="x1channel", architectures=["x1arch"]),
                ],
                "run-on": [
                    Base(name="x2name", channel="x2channel", architectures=["x2arch"]),
                ],
            }
        ),
    ]

    config.set(bases=bases_config)
    cmd = CleanCommand(config)
    cmd.run([])

    assert mock_provider.mock_calls == [
        mock.call.is_base_available(
            Base(name="x1name", channel="x1channel", architectures=["x1arch"])
        ),
        mock.call.clean_project_environments(
            charm_name="foo", project_path=mock.ANY, bases_index=0, build_on_index=0
        ),
    ]
    emitter.assert_message("Cleaning project 'foo'.")
    emitter.assert_message("Cleaned project 'foo'.")


def test_clean_complex(config, emitter, mock_provider, tmp_path):
    """Test clean with a complex list of bases."""
    metadata_yaml = tmp_path / "metadata.yaml"
    metadata_yaml.write_text("name: foo")

    bases_config = [
        BasesConfiguration(
            **{
                "build-on": [
                    Base(name="x1name", channel="x1channel", architectures=["x1arch"]),
                ],
                "run-on": [
                    Base(name="x2name", channel="x2channel", architectures=["x2arch"]),
                ],
            }
        ),
        BasesConfiguration(
            **{
                "build-on": [
                    Base(name="x3name", channel="x3channel", architectures=["x3arch"]),
                    Base(name="x3name", channel="x3channel", architectures=["x3arch"]),
                ],
                "run-on": [
                    Base(name="x4name", channel="x4channel", architectures=["x4arch"]),
                ],
            }
        ),
        BasesConfiguration(
            **{
                "build-on": [
                    Base(name="x5name", channel="x5channel", architectures=["x5arch"]),
                ],
                "run-on": [
                    Base(name="x6name", channel="x6channel", architectures=["x6arch"]),
                    Base(
                        name="x7name",
                        channel="x7channel",
                        architectures=["x7arch1", "x7arch2"],
                    ),
                ],
            }
        ),
    ]

    config.set(bases=bases_config)

    cmd = CleanCommand(config)
    cmd.run([])

    assert mock_provider.mock_calls == [
        mock.call.is_base_available(
            Base(name="x1name", channel="x1channel", architectures=["x1arch"])
        ),
        mock.call.is_base_available(
            Base(name="x3name", channel="x3channel", architectures=["x3arch"])
        ),
        mock.call.is_base_available(
            Base(name="x5name", channel="x5channel", architectures=["x5arch"])
        ),
        mock.call.clean_project_environments(
            charm_name="foo", project_path=mock.ANY, bases_index=0, build_on_index=0
        ),
        mock.call.clean_project_environments(
            charm_name="foo", project_path=mock.ANY, bases_index=1, build_on_index=0
        ),
        mock.call.clean_project_environments(
            charm_name="foo", project_path=mock.ANY, bases_index=2, build_on_index=0
        ),
    ]
    emitter.assert_message("Cleaning project 'foo'.")
    emitter.assert_message("Cleaned project 'foo'.")
