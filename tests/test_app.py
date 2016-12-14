# -*- coding: utf-8 -*-
from __future__ import absolute_import
import os
import tempfile

import pytest
from rdflib import Graph, Literal, Namespace, URIRef
import xml.etree.ElementTree as ET

from foist.app import (add_file_metadata, add_thesis_item_file,
                       commit_transaction, create_pcdm_relationships,
                       create_thesis_item_container,
                       parse_text_encoding_errors, start_transaction,
                       ThesisItem)
from foist.namespaces import DCTERMS, LOCAL


def test_thesis(tmpdir, xml):
    l = tempfile.mkdtemp()
    t = ThesisItem('thesis', l, xml)
    assert t.name == 'thesis'
    assert t.output_location == l
    assert type(t.metadata) == Graph
    assert ('pcdm', Namespace('http://pcdm.org/models#')) in \
        t.metadata.namespaces()
    assert type(t.root) == ET.Element


def test_generate_item_metadata_adds_all_fields(tmpdir, xml):
    l = tempfile.mkdtemp()
    t = ThesisItem('thesis', l, xml)
    t.generate_item_metadata()
    assert len(t.metadata) == 11
    assert DCTERMS.title in t.metadata.predicates()


def test_generate_item_metadata_with_no_abstract_returns_none(tmpdir, xml):
    pass


def test_add_text_errors_adds_all_errors_to_metadata(tmpdir, xml):
    pass


def test_create_item_turtle_statements_creates_a_file(tmpdir, xml):
    l = tempfile.mkdtemp()
    p = os.path.join(l, 'thesis')
    d = os.makedirs(p)
    t = ThesisItem('thesis', l, xml)
    t.create_item_turtle_statements()
    assert os.path.isfile(os.path.join(p, 'thesis.ttl'))


def test_create_file_sparql_update_creates_a_file(tmpdir, xml):
    l = tempfile.mkdtemp()
    p = os.path.join(l, 'thesis')
    d = os.makedirs(p)
    t = ThesisItem('thesis', l, xml)
    t.create_file_sparql_update('.pdf')
    assert os.path.isfile(os.path.join(p, 'thesis.pdf.ru'))


def test_get_field_handles_missing_metadata_field(tmpdir,
                                                  xml_missing_abstract):
    l = tempfile.mkdtemp()
    t = ThesisItem('thesis', l, xml_missing_abstract)
    f = t.get_field('abstract', 'abstract')
    assert f == Literal('None')


def test_parse_text_encoding_errors_creates_dict(text_errors):
    d = parse_text_encoding_errors(text_errors)
    assert type(d) == dict
    assert d['thesis']['Encoded'] == '1'


def test_add_text_errors_adds_all_fields_to_metadata(tmpdir, xml, text_errors):
    e = parse_text_encoding_errors(text_errors)
    l = tempfile.mkdtemp()
    t = ThesisItem('thesis', l, xml)
    t.add_text_errors(e)
    assert len(t.metadata) == 3
    assert LOCAL.ligature_errors in t.metadata.predicates()


def test_start_transaction_posts(fedora):
    t = start_transaction('mock://example.com/rest/')
    assert 'tx:123456789' in t


def test_commit_transacation_posts(fedora):
    t = commit_transaction('mock://example.com/rest/tx:123456789')
    assert t


def test_create_thesis_item_container_is_successful(fedora, turtle):
    loc = start_transaction('mock://example.com/rest/')
    r = create_thesis_item_container(loc + '/theses/', 'thesis', turtle)
    assert r == 'Success'


def test_add_thesis_item_file_is_successful(fedora, pdf):
    loc = start_transaction('mock://example.com/rest/')
    r = add_thesis_item_file(loc + '/theses/', 'thesis', '.pdf',
                             'application/pdf', pdf)
    assert r == 'Success'


def test_add_file_metadata_is_successful(fedora, pdf):
    loc = start_transaction('mock://example.com/rest/')
    r = add_file_metadata(loc + '/theses/', 'thesis', '.pdf', pdf)
    assert r == 'Success'


def test_create_pcdm_relationships_is_successful(fedora):
    loc = start_transaction('mock://example.com/rest/')
    r = create_pcdm_relationships(loc + '/theses/', 'thesis')
    assert r == 'Success'
