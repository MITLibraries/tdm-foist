# -*- coding: utf-8 -*-
from __future__ import absolute_import
from io import BytesIO
import os
import re
import shutil
import tempfile

import pytest
import requests_mock


@pytest.yield_fixture(scope="session", autouse=True)
def tmp_dir():
    cur_dir = os.path.dirname(os.path.realpath(__file__))
    tmp = tempfile.mkdtemp(dir=cur_dir)
    tempfile.tempdir = tmp
    yield
    if os.path.isdir(tmp):
        shutil.rmtree(tmp)


@pytest.fixture
def xml():
    cur_dir = os.path.dirname(os.path.realpath(__file__))
    return os.path.join(cur_dir, 'fixtures/thesis/thesis.xml')


@pytest.fixture
def xml_missing_fields():
    cur_dir = os.path.dirname(os.path.realpath(__file__))
    return os.path.join(cur_dir, 'fixtures/thesis_missing_fields.xml')


@pytest.fixture
def pdf():
    cur_dir = os.path.dirname(os.path.realpath(__file__))
    return os.path.join(cur_dir, 'fixtures/thesis/thesis.pdf')


@pytest.fixture
def sparql():
    cur_dir = os.path.dirname(os.path.realpath(__file__))
    return os.path.join(cur_dir, 'fixtures/thesis/thesis.pdf.ru')


@pytest.fixture
def turtle():
    cur_dir = os.path.dirname(os.path.realpath(__file__))
    return os.path.join(cur_dir, 'fixtures/thesis/thesis.ttl')


@pytest.fixture
def text_errors():
    cur_dir = os.path.dirname(os.path.realpath(__file__))
    return os.path.join(cur_dir, 'fixtures/text_errors.tab')


@pytest.fixture
def theses_dir():
    cur_dir = os.path.dirname(os.path.realpath(__file__))
    return os.path.join(cur_dir, 'fixtures')


@pytest.yield_fixture
def fedora():
    with requests_mock.Mocker() as m:
        matcher = re.compile('/rest/tx:123456789/theses/thesis-')
        m.patch('/rest/initialize', status_code=204)
        m.put('/rest/initialize', status_code=201)
        m.delete('/rest/initialize', status_code=204)
        m.delete('/rest/initialize/fcr:tombstone', status_code=204)
        m.post('/rest/fcr:tx', status_code=201,
               headers={'Location': 'mock://example.com/rest/tx:123456789'})
        m.post('/rest/tx:123456789/fcr:tx/fcr:commit',
               status_code=204)
        m.post('/rest/tx:123456789/fcr:tx/fcr:rollback',
               status_code=204)
        m.put('/rest/tx:123456789/theses/thesis',
              status_code=201)
        m.put('/rest/tx:123456789/theses/thesis/',
              status_code=201)
        m.put('/rest/tx:123456789/theses/thesis/thesis.pdf/',
              status_code=201)
        m.patch('/rest/tx:123456789/theses/thesis/thesis.pdf/fcr:metadata',
                status_code=204)
        m.put('/rest/tx:123456789/theses/thesis/thesis.txt/',
              status_code=201)
        m.patch('/rest/tx:123456789/theses/thesis/thesis.txt/fcr:metadata',
                status_code=204)
        m.patch('/rest/tx:123456789/theses',
                status_code=204)
        m.patch('/rest/tx:123456789/theses/',
                status_code=204)
        m.patch('/rest/tx:123456789/theses/thesis/',
                status_code=204)
        m.patch('/rest/tx:123456789/theses/thesis',
                status_code=204)
        m.put('/rest/theses', status_code=201)
        m.patch('/rest/theses/', status_code=204)
        m.patch('/rest/theses/thesis', status_code=204)
        m.head('/rest/theses/thesis', status_code=200)
        m.head('/rest/theses/uningested_thesis', status_code=404)
        m.put(matcher, status_code=409)
        m.patch(matcher, status_code=204)
        yield m


@pytest.yield_fixture
def fedora_errors():
    with requests_mock.Mocker() as m:
        m.post('/rest/fcr:tx', status_code=201,
               headers={'Location': 'mock://example.com/rest/tx:error'})
        m.post('/rest/tx:error/fcr:tx/fcr:commit', status_code=410)
        m.post('/rest/tx:error/fcr:tx/fcr:rollback', status_code=410)
        m.put('/rest/tx:error/theses/thesis', status_code=412)
        m.put('/rest/tx:error/theses/thesis/thesis.pdf', status_code=412)
        m.patch('/rest/tx:error/theses/thesis/thesis.pdf/fcr:metadata',
                status_code=412)
        m.patch('/rest/tx:error/theses', status_code=412)
        m.patch('/rest/theses/thesis', status_code=412)
        m.head('/rest/theses/no_auth', status_code=401)
        yield m


@pytest.yield_fixture
def pipeline():
    with requests_mock.Mocker() as m:
        cur_dir = os.path.dirname(os.path.realpath(__file__))
        pdf_file = os.path.join(cur_dir, 'fixtures/thesis/thesis.pdf')
        record_list = os.path.join(cur_dir, 'fixtures/record_list.xml')
        mets_record = os.path.join(cur_dir, 'fixtures/mets_record.xml')
        with open(record_list, 'rb') as rl, \
                open(pdf_file, 'rb') as pdf, \
                open(mets_record, 'rb') as xml:
            m.get('/oai/request?verb=ListIdentifiers&metadataPrefix=mets'
                  '&from=2017-01-01&until=2017-02-01',
                  status_code=200, content=rl.read())
            m.get(('/oai/request?verb=GetRecord&identifier=oai:'
                   'dspace.mit.edu:1721.1/12345&metadataPrefix=mets'),
                  status_code=200,
                  text=('<?xml version="1.0" encoding="UTF-8"?><OAI-PMH '
                        'xmlns="http://www.openarchives.org/OAI/2.0/" '
                        'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"'
                        ' xsi:schemaLocation="http://www.openarchives.org/'
                        'OAI/2.0/ http://www.openarchives.org/OAI/2.0/'
                        'OAI-PMH.xsd"></OAI-PMH>'))
            m.get(('/oai/request?verb=GetRecord&identifier=oai:'
                   'dspace.mit.edu:1721.1/108390&metadataPrefix=mets'),
                  status_code=200, content=xml.read())
            m.get('/bitstream/handle/test/pdf', status_code=200,
                  content=pdf.read())
            m.get('/bitstream/handle/test/bad_pdf', status_code=404)
            m.get('/bitstream/1721.1/107085/1/971247903-MIT.pdf',
                  status_code=200, content=pdf.read())
            m.head('/rest/theses/1721.1-108390', status_code=404)
            m.post('/rest/fcr:tx', status_code=201,
                   headers={'Location':
                            'mock://example.com/rest/tx:123456789'})
            m.post('/rest/tx:123456789/fcr:tx/fcr:commit', status_code=204)
            m.put('/rest/tx:123456789/theses/1721.1-108390/', status_code=201)
            m.put('/rest/tx:123456789/theses/1721.1-108390/1721.1-108390.pdf/',
                  status_code=201)
            m.patch(('/rest/tx:123456789/theses/1721.1-108390/1721.1-108390'
                     '.pdf/fcr:metadata'), status_code=204)
            m.patch('/rest/tx:123456789/theses/1721.1-108390/',
                    status_code=204)
        yield m


@pytest.yield_fixture
def record_list():
    cur_dir = os.path.dirname(os.path.realpath(__file__))
    xml_file = os.path.join(cur_dir, 'fixtures/record_list.xml')
    with open(xml_file, 'r') as f:
        yield f.read()


@pytest.yield_fixture
def mets_xml():
    cur_dir = os.path.dirname(os.path.realpath(__file__))
    return os.path.join(cur_dir, 'fixtures/mets_record.xml')


@pytest.yield_fixture
def test_pdf():
    cur_dir = os.path.dirname(os.path.realpath(__file__))
    return os.path.join(cur_dir, 'fixtures/test_pdf.pdf')
