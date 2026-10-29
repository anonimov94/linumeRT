"""Operator configuration must survive generator previews and backups (062).

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Codex
"""

import pytest

from linumert.machine.config_files import backup_configuration, configuration_diff


def test_backups_preserve_operator_files_and_never_overwrite(tmp_path):
    config = tmp_path / "machine"
    config.mkdir()
    (config / "machine.ini").write_text("old\n", encoding="utf-8")
    (config / "tool.tbl").write_bytes(b"T12 P12 Z1.25\n")
    first = backup_configuration(config)
    (config / "machine.ini").write_text("new\n", encoding="utf-8")
    second = backup_configuration(config)
    assert first != second
    assert (first / "machine.ini").read_text() == "old\n"
    assert (second / "machine.ini").read_text() == "new\n"
    assert (first / "tool.tbl").read_bytes() == (config / "tool.tbl").read_bytes()


def test_preview_does_not_change_source_or_create_new_destination(tmp_path):
    config = tmp_path / "new"
    assert backup_configuration(config) is None
    diff = configuration_diff(config, {"machine.ini": "[EMC]\n"})
    assert "+[EMC]" in diff and "after/machine.ini" in diff
    assert not config.exists()
    config.mkdir()
    (config / "machine.ini").write_text("old\n", encoding="utf-8")
    diff = configuration_diff(config, {"machine.ini": "new\n"})
    assert "-old" in diff and "+new" in diff
    assert (config / "machine.ini").read_text() == "old\n"


@pytest.mark.parametrize("name", ["../other.ini", "/other.ini", "C:/other.ini", "a\\b.ini", ""])
def test_preview_refuses_escaping_paths(tmp_path, name):
    with pytest.raises(ValueError):
        configuration_diff(tmp_path / "config", {name: "data"})


def test_backup_failure_is_not_reported_as_success(tmp_path, monkeypatch):
    config = tmp_path / "config"
    config.mkdir()

    def fail(*args, **kwargs):
        raise OSError("disk full")

    monkeypatch.setattr("linumert.machine.config_files.shutil.copytree", fail)
    with pytest.raises(OSError, match="disk full"):
        backup_configuration(config)
    assert config.is_dir()
