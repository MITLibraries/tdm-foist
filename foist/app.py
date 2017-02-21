# -*- coding: utf-8 -*-
from __future__ import absolute_import
from contextlib import contextmanager
import csv
import logging
import os

import rdflib
import requests

from foist.namespaces import BIBO, DCTERMS, DCTYPE, LOCAL, MODS, MSL, PCDM, RDF

log = logging.getLogger(__name__)

base_mets_search = './mets:dmdSec/*/*/*/mods:'
mets_namespace = {'mets': 'http://www.loc.gov/METS/',
                  'mods': 'http://www.loc.gov/mods/v3'}


class Thesis(object):
    '''A thesis object representing a single thesis intellectual entity with
    all its associated metadata.
    '''
    def __init__(self, name, mets, text_errors=None, collection=None):
        self.name = name
        self.mets = mets
        self.errors = text_errors
        self.collection = collection

    @property
    def abstract(self):
        try:
            result = ''.join([e.text.lstrip('(cont.)') for
                             e in self.mets.findall('.//mods:abstract',
                                                    mets_namespace)])
        except AttributeError:
            pass
        return result or None

    @property
    def advisor(self):
        result = [e.text for e in
                  self.mets.findall(('.//mods:name/*[mods:roleTerm='
                                     '"advisor"]/../mods:namePart'),
                                    mets_namespace)]
        return result or None

    @property
    def alt_title(self):
        result = [e.text for e in
                  self.mets.findall(('.//mods:titleInfo[@type="alternative"]/'
                                     'mods:title'), mets_namespace)]
        return result or None

    @property
    def author(self):
        result = [e.text for e in
                  self.mets.findall(('.//mods:name/*[mods:roleTerm="author"]/'
                                     '../mods:namePart'), mets_namespace)]
        return result or None

    @property
    def copyright_date(self):
        try:
            result = self.mets.find('.//mods:originInfo/mods:copyrightDate',
                                    mets_namespace).text
        except AttributeError:
            result = None
        return result

    @property
    def dc_type(self):
        return DCTYPE.Text

    @property
    def degree_statement(self):
        result = [e.text for e in
                  self.mets.findall('.//mods:note', mets_namespace) if
                  e.text.startswith('Thesis')]
        return result[0] if result else None

    @property
    def department(self):
        try:
            result = [self.mets.find('.//mods:subject/mods:topic',
                                     mets_namespace).text]
        except AttributeError:
            result = []
        if self.collection:
            result.append(self.collection)
        return result or None

    @property
    def encoded_text(self):
        return self._get_error_value('Encoded text new file') if self.errors else None

    @property
    def handle(self):
        try:
            result = self.mets.find('.//mods:identifier[@type="uri"]',
                                    mets_namespace).text
        except AttributeError:
            result = None
        return result

    @property
    def issue_date(self):
        try:
            result = self.mets.find('.//mods:originInfo/mods:dateIssued',
                                    mets_namespace).text
        except AttributeError:
            result = None
        return result

    @property
    def ligatures(self):
        return self._get_error_value('Ligatures new') if self.errors else None

    @property
    def no_full_text(self):
        return self._get_full_text_error() if self.errors else None

    @property
    def notes(self):
        result = [e.text for e in
                  self.mets.findall('.//mods:note', mets_namespace) if not
                  e.text.startswith('Thesis')]
        return result or None

    @property
    def publisher(self):
        return 'Massachusetts Institute of Technology'

    @property
    def rdf_type(self):
        return [BIBO.Thesis, PCDM.Object]

    @property
    def rights_statement(self):
        return ('MIT theses are protected by copyright. They may be viewed, '
                'downloaded, or printed from this source but further '
                'reproduction or distribution in any format is prohibited '
                'without written permission.')

    @property
    def title(self):
        try:
            result = self.mets.find('.//mods:titleInfo/mods:title',
                                    mets_namespace).text
        except AttributeError:
            result = None
        return result

    def get_metadata(self, serialization='turtle'):
        m = rdflib.Graph()
        s = rdflib.URIRef('')

        def _add_metadata_field(p, obj, obj_type='string'):
            if obj is None:
                o = rdflib.Literal('None')
                m.add((s, p, o))
            elif obj is True:
                o = rdflib.Literal('True')
                m.add((s, p, o))
            elif type(obj) == str:
                o = _create_rdf_obj(obj, obj_type)
                m.add((s, p, o))
            elif type(obj) == list:
                for i in obj:
                    o = _create_rdf_obj(i, obj_type)
                    m.add((s, p, o))

        def _create_rdf_obj(obj, obj_type):
            if obj_type == 'string':
                o = rdflib.Literal(obj)
                return o
            elif obj_type == 'uri':
                o = rdflib.URIRef(obj)
                return o

        # Bind prefixes to metadata graph
        m.bind('bibo', BIBO)
        m.bind('dcterms', DCTERMS)
        m.bind('dctype', DCTYPE)
        m.bind('local', LOCAL)
        m.bind('mods', MODS)
        m.bind('msl', MSL)
        m.bind('pcdm', PCDM)
        m.bind('rdf', RDF)

        # Add all metadata properties
        _add_metadata_field(DCTERMS.abstract, self.abstract)
        _add_metadata_field(MSL.reviewedBy, self.advisor)
        if self.alt_title:
            _add_metadata_field(DCTERMS.title, self.alt_title)
        _add_metadata_field(DCTERMS.creator, self.author)
        _add_metadata_field(DCTERMS.dateCopyrighted, self.copyright_date)
        _add_metadata_field(DCTERMS.type, self.dc_type, obj_type='uri')
        _add_metadata_field(MSL.degreeGrantedForCompletion,
                            self.degree_statement)
        _add_metadata_field(MSL.associatedDepartment, self.department)
        _add_metadata_field(LOCAL.encoded_text, self.encoded_text)
        _add_metadata_field(BIBO.handle, self.handle, obj_type='uri')
        _add_metadata_field(DCTERMS.dateIssued, self.issue_date)
        _add_metadata_field(LOCAL.ligature_errors, self.ligatures)
        _add_metadata_field(LOCAL.no_full_text, self.no_full_text)
        _add_metadata_field(MODS.note, self.notes)
        _add_metadata_field(DCTERMS.publisher, self.publisher)
        _add_metadata_field(RDF.type, self.rdf_type, obj_type='uri')
        _add_metadata_field(DCTERMS.rights, self.rights_statement)
        _add_metadata_field(DCTERMS.title, self.title)

        if serialization == 'turtle':
            return m.serialize(format='turtle')

    def create_file_sparql_update(self, file_ext):
        lang = self.mets.find('.//mods:language/mods:languageTerm',
                              mets_namespace).text
        query = ('PREFIX dcterms: <http://purl.org/dc/terms/> PREFIX pcdm: '
                 '<http://pcdm.org/models#> PREFIX ebucore: '
                 '<http://www.ebu.ch/metadata/ontologies/ebucore/ebucore#> '
                 'INSERT { <> a pcdm:File ; dcterms:language "' + lang + '"')
        if file_ext == '.pdf':
            pages = self.mets.find('.//mods:physicalDescription/mods:extent',
                                   mets_namespace).text
            query += ' ; dcterms:extent "' + pages + '"'
        elif file_ext == '.txt':
            query += ' ; ebucore:hasEncodingFormat "utf-8"'
        query += ' . } WHERE { }'
        return query

    def _get_error_value(self, error):
        if self.errors[error] == '1':
            return True

    def _get_full_text_error(self):
        s = self.errors
        if (s['PDFBox err'] == '1' or (s['No text old file'] == '1' and
                                       s['No text new file'] == '1')):
            return True


def parse_text_encoding_errors(tsv_file):
    '''Parse text encoding error log file and return a dict of items with
    errors.
    '''
    with open(tsv_file) as tsv_file:
        text_encoding_errors = {}
        read = csv.DictReader(tsv_file, delimiter='\t')
        for row in read:
            text_encoding_errors[row['Subdir']] = row
        return text_encoding_errors


@contextmanager
def transaction(fedora_uri):
    '''Starts a Fedora transaction, yields a location header, commits and
    closes the transaction.
    '''
    uri = fedora_uri + 'fcr:tx'
    r = requests.post(uri)
    location = r.headers['Location']
    try:
        yield location
    except Exception as e:
        uri = location + '/fcr:tx/fcr:rollback'
        r = requests.post(uri)
        log.debug(e)
        log.warning('Transaction %s rolled back and closed' % location)
    else:
        uri = location + '/fcr:tx/fcr:commit'
        try:
            r = requests.post(uri)
            r.raise_for_status()
        except requests.exceptions.HTTPError as e:
            raise e


def create_thesis_item_container(location, item, turtle_path):
    '''Create basic PCDM container for a thesis item.
    '''
    uri = location + item
    headers = {'Content-Type': 'text/turtle; charset=utf-8'}
    with open(turtle_path, 'rb') as data:
        try:
            r = requests.put(uri, headers=headers, data=data)
            r.raise_for_status()
            return r.status_code
        except requests.exceptions.HTTPError as e:
            raise e


def add_thesis_item_file(location, item, ext, mimetype, file_path):
    '''Add a file to a thesis item container.
    '''
    uri = location + item + ext
    headers = {'Content-Type': mimetype}
    with open(file_path, 'rb') as data:
        try:
            r = requests.put(uri, headers=headers, data=data)
            r.raise_for_status()
            return r.status_code
        except requests.exceptions.HTTPError as e:
            raise e


def add_file_metadata(location, item, ext, file_path, sparql_path):
    '''Update the metadata for a given file.
    '''
    uri = location + 'fcr:metadata'
    headers = {'Content-Type': 'application/sparql-update'}
    with open(sparql_path, 'rb') as data:
        try:
            r = requests.patch(uri, headers=headers, data=data)
            r.raise_for_status()
            return r.status_code
        except requests.exceptions.HTTPError as e:
            raise e


def create_pcdm_relationships(uri, query):
    '''Create PCDM relationship statement between a thesis item and its parent
    container (hasMember).
    '''
    headers = {'Content-Type': 'application/sparql-update'}
    try:
        r = requests.patch(uri, headers=headers, data=query)
        r.raise_for_status()
        return r.status_code
    except requests.exceptions.HTTPError as e:
        raise e
