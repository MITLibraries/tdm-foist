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


def test_initialize_fedora(runner, fedora):
    result = runner.invoke(main, ['initialize_fedora', 'theses', '-f',
                           'mock://example.com/rest/'])
    assert result.exit_code == 0


def test_ingest_new_theses(runner, pipeline):
    result = runner.invoke(main, ['ingest_new_theses',
                                  'mock://example.com/oai/request?',
                                  'oai%3Adspace.mit.edu%3A1721.1%2F', '-sd',
                                  '2017-01-01', '-ed', '2017-02-01', '-f',
                                  'mock://example.com/rest/'])
    assert result.exit_code == 0


def test_process_metadata(runner, theses_dir, tmpdir):
    l = tempfile.mkdtemp()
    p = os.path.join(l, 'thesis')
    q = os.path.join(l, 'thesis-02')
    r = os.path.join(l, 'thesis-03')
    s = os.path.join(l, 'thesis-04')
    t = os.path.join(l, 'thesis-05')
    u = os.path.join(l, 'thesis-06')
    os.makedirs(p)
    os.makedirs(q)
    os.makedirs(r)
    os.makedirs(s)
    os.makedirs(t)
    os.makedirs(u)
    result = runner.invoke(main, ['process_metadata',
                           theses_dir, 'Test Collection', '-o', l])
    assert result.exit_code == 0


def test_upload_theses(runner, theses_dir, fedora):
    result = runner.invoke(main, ['batch_upload_theses', theses_dir, '-f',
                           'mock://example.com/rest/'])
    assert result.exit_code == 0


def test_update_metadata(runner, theses_dir, fedora):
    result = runner.invoke(main, ['update_metadata_for_collection', theses_dir,
                           ('PREFIX local: <http://example.com/> INSERT { <> '
                            'local:isFun "True" . } WHERE { }'), '-f',
                           'mock://example.com/rest/'])
    assert result.exit_code == 0
