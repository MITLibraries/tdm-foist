# -*- coding: utf-8 -*-
from __future__ import absolute_import
import os
import tempfile

from click.testing import CliRunner
import pytest

from foist.cli import main


@pytest.fixture
def runner():
    return CliRunner()


def test_process_metadata(runner, theses_dir, tmpdir):
    l = tempfile.mkdtemp()
    p = os.path.join(l, 'thesis')
    q = os.path.join(l, 'thesis-02')
    os.makedirs(p)
    os.makedirs(q)
    result = runner.invoke(main, ['process_metadata',
                           theses_dir, '-o', l])

    assert result.exit_code == 0


def test_upload_theses(runner, theses_dir, fedora):
    result = runner.invoke(main, ['upload_theses', theses_dir, '-f',
                           'mock://example.com/rest/'])
    assert result.exit_code == 0
