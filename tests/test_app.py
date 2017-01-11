# -*- coding: utf-8 -*-
from __future__ import absolute_import
import os
import tempfile

import pytest
from rdflib import Graph, Literal, Namespace, URIRef
import requests
import xml.etree.ElementTree as ET

from foist.app import (add_file_metadata, add_thesis_item_file,
                       create_pcdm_relationships, create_thesis_item_container,
                       parse_text_encoding_errors, Thesis, transaction)
from foist.namespaces import BIBO, DCTERMS, DCTYPE, LOCAL, MODS, MSL, PCDM, RDF


def test_thesis(tmpdir, xml, text_errors):
    '''Thesis object should initialize with a name, mets, errors.
    '''
    l = tempfile.mkdtemp()
    mets = ET.parse(xml).getroot()
    errors = parse_text_encoding_errors(text_errors)
    t = Thesis('thesis', mets, errors)

    assert t.name == 'thesis'
    assert t.mets == mets
    assert t.errors == errors['thesis']


def test_thesis_with_all_metadata_fields_parses_correctly(tmpdir, xml,
                                                          text_errors):
    '''Thesis object should create properties for all metadata fields.
    '''
    l = tempfile.mkdtemp()
    mets = ET.parse(xml).getroot()
    errors = parse_text_encoding_errors(text_errors)
    t = Thesis('thesis', mets, errors)

    assert t.abstract == 'Sample abstract.'
    assert t.advisor == ['Advisor One.', 'Advisor Two.']
    assert t.alt_title == ['Alternative Title.']
    assert t.author == ['Author One.', 'Author Two.']
    assert t.copyright_date == '2006'
    assert t.dc_type == DCTYPE.Text
    assert t.degree_statement == ('Thesis (S.M.)--Massachusetts Institute '
                                  'of Technology, Computation for Design and '
                                  'Optimization Program, 2006.')
    assert t.department == ['Department One.', 'Department Two.']
    assert t.handle == 'http://hdl.handle.net/1721.1/39208'
    assert t.issue_date == '2006'
    assert t.ligatures is None
    assert t.line_ends is True
    assert t.no_full_text is True
    assert t.notes == ['Includes bibliographical references (p. 1-2).',
                       'by Lei Zhang.']
    assert t.publisher == 'Massachusetts Institute of Technology'
    assert t.rdf_type == [BIBO.Thesis, PCDM.Object]
    assert t.rights_statement == ('M.I.T. theses are protected by copyright. '
                                  'They may be viewed from this source for '
                                  'any purpose, but reproduction or '
                                  'distribution in any format is prohibited '
                                  'without written permission. See provided '
                                  'URL for inquiries about permission.')
    assert t.title == 'Sample Title.'


def test_thesis_get_metadata_returns_turtle(tmpdir, xml, text_errors):
    l = tempfile.mkdtemp()
    mets = ET.parse(xml).getroot()
    errors = parse_text_encoding_errors(text_errors)
    t = Thesis('thesis', mets, errors)
    m = t.get_metadata()

    # Check all prefix bindings
    assert b'@prefix bibo: <http://purl.org/ontology/bibo/> .' in m
    assert b'@prefix dcterms: <http://purl.org/dc/terms/> .' in m
    assert b'@prefix dctype: <http://purl.org/dc/dcmitype/> .' in m
    assert b'@prefix local: <http://example.com/> .' in m
    assert b'@prefix mods: <http://www.loc.gov/standards/mods/modsrdf/v1/#> .'\
        in m
    assert b'@prefix msl: <http://purl.org/montana-state/library/> .' in m
    assert b'@prefix pcdm: <http://pcdm.org/models#> .' in m
    assert b'@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .' in m
    assert b'@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .' in m
    assert b'@prefix xml: <http://www.w3.org/XML/1998/namespace> .' in m
    assert b'@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .' in m

    # Check a few metadata statements
    assert b'<>' in m
    assert b'a "http://pcdm.org/models#Object"' in m
    assert b'dcterms:title "Alternative Title."' in m
    assert b'local:ligature_errors "None"' in m
    assert b'local:line_ends "True"' in m
    assert b'bibo:handle <http://hdl.handle.net/1721.1/39208>' in m


def test_thesis_handles_missing_metadata_fields(tmpdir, xml_missing_fields,
                                                text_errors):
    l = tempfile.mkdtemp()
    mets = ET.parse(xml_missing_fields).getroot()
    errors = parse_text_encoding_errors(text_errors)
    t = Thesis('thesis-02', mets, errors)

    assert t.advisor is None
    assert t.copyright_date is None
    assert t.degree_statement is None
    assert t.notes is None
    assert t.line_ends is None


def test_thesis_create_file_sparql_update_is_correct(tmpdir, xml, text_errors):
    l = tempfile.mkdtemp()
    mets = ET.parse(xml).getroot()
    errors = parse_text_encoding_errors(text_errors)
    t = Thesis('thesis', mets, errors)

    s = t.create_file_sparql_update('.pdf')
    assert s == ('PREFIX dcterms: <http://purl.org/dc/terms/> PREFIX pcdm: '
                 '<http://pcdm.org/models#> INSERT { <> a pcdm:File ; '
                 'dcterms:language "eng" ; dcterms:extent "109 p." . } WHERE '
                 '{ }')


def test_parse_text_encoding_errors_creates_dict(text_errors):
    d = parse_text_encoding_errors(text_errors)
    assert type(d) == dict
    assert d['thesis']['Encoded'] == '1'


def test_transaction_commits(fedora):
    with transaction('mock://example.com/rest/') as t:
        assert t == 'mock://example.com/rest/tx:123456789'


def test_transaction_with_error_rolls_back_and_closes(fedora):
    with transaction('mock://example.com/rest/') as t:
        raise


def test_transaction_commit_fail_raises_exception(fedora_errors):
    with pytest.raises(requests.exceptions.HTTPError):
        with transaction('mock://example.com/rest/') as t:
            pass


def test_create_thesis_item_container_is_successful(fedora, turtle):
    r = None
    with transaction('mock://example.com/rest/') as t:
        r = create_thesis_item_container(t + '/theses/', 'thesis', turtle)
    assert r == 201


def test_create_thesis_item_failure_raises_error(fedora_errors, turtle):
    with pytest.raises(requests.exceptions.HTTPError):
        create_thesis_item_container(('mock://example.com/rest/tx:error/'
                                     'theses/'), 'thesis', turtle)


def test_add_thesis_item_file_is_successful(fedora, pdf):
    r = None
    with transaction('mock://example.com/rest/') as t:
        r = add_thesis_item_file(t + '/theses/thesis/', 'thesis', '.pdf',
                                 'application/pdf', pdf)
    assert r == 201


def test_add_thesis_item_file_failure_raises_error(fedora_errors, pdf):
    with pytest.raises(requests.exceptions.HTTPError):
        add_thesis_item_file('mock://example.com/rest/tx:error/theses/thesis/',
                             'thesis', '.pdf', 'application/pdf', pdf)


def test_add_file_metadata_is_successful(fedora, pdf, sparql):
    r = None
    with transaction('mock://example.com/rest/') as t:
        r = add_file_metadata(t + '/theses/thesis/thesis.pdf/', 'thesis',
                              '.pdf', pdf, sparql)
    assert r == 204


def test_add_file_metadata_failure_raises_error(fedora_errors, pdf, sparql):
    with pytest.raises(requests.exceptions.HTTPError):
        add_file_metadata(('mock://example.com/rest/tx:error/theses/thesis/'
                          'thesis.pdf/'), 'thesis', '.pdf', pdf, sparql)


def test_create_pcdm_relationships_is_successful(fedora):
    r = None
    with transaction('mock://example.com/rest/') as t:
        uri = t + '/theses'
        query = ('PREFIX pcdm: <http://pcdm.org/models#> INSERT { <> '
                 'pcdm:hasMember <' + uri + '/thesis> . } WHERE { }')
        r = create_pcdm_relationships(uri, query)
    assert r == 204


def test_create_pcdm_relationships_failure_raises_error(fedora_errors):
    with pytest.raises(requests.exceptions.HTTPError):
        uri = 'mock://example.com/rest/tx:error/theses'
        query = ('PREFIX pcdm: <http://pcdm.org/models#> INSERT { <> '
                 'pcdm:hasMember <' + uri + '/thesis> . } WHERE { }')
        create_pcdm_relationships(uri, query)
