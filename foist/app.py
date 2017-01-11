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
    def __init__(self, name, mets, text_errors):
        self.name = name
        self.mets = mets

        try:
            self.errors = text_errors[self.name]
        except KeyError:
            self.errors = None

    @property
    def abstract(self):
        return self._get_field('abstract', field_type='split',
                               text_to_strip='(cont.)')

    @property
    def advisor(self):
        return self._get_field(('name/*[mods:roleTerm="advisor"]/../'
                                'mods:namePart'), field_type='multi')

    @property
    def alt_title(self):
        return self._get_field('titleInfo[@type="alternative"]/mods:title',
                               field_type='multi')

    @property
    def author(self):
        return self._get_field(('name/*[mods:roleTerm="author"]/../'
                                'mods:namePart'), field_type='multi')

    @property
    def copyright_date(self):
        return self._get_field('originInfo/mods:copyrightDate')

    @property
    def dc_type(self):
        return DCTYPE.Text

    @property
    def degree_statement(self):
        return self._get_field('note', field_type='degree')

    @property
    def department(self):
        return self._get_field('subject/mods:topic', field_type='multi')

    @property
    def handle(self):
        return self._get_field('identifier[@type="uri"]')

    @property
    def issue_date(self):
        return self._get_field('originInfo/mods:dateIssued')

    @property
    def ligatures(self):
        if self.errors:
            return self._get_error_value('Ligatures')
        else:
            return None

    @property
    def line_ends(self):
        if self.errors:
            return self._get_error_value('Line ends')
        else:
            return None

    @property
    def no_full_text(self):
        if self.errors:
            return self._get_full_text_error()
        else:
            return None

    @property
    def notes(self):
        return self._get_field('note', field_type='notes')

    @property
    def publisher(self):
        return 'Massachusetts Institute of Technology'

    @property
    def rdf_type(self):
        return [BIBO.Thesis, PCDM.Object]

    @property
    def rights_statement(self):
        return ('M.I.T. theses are protected by copyright. They may be viewed '
                'from this source for any purpose, but reproduction or '
                'distribution in any format is prohibited without written '
                'permission. See provided URL for inquiries about permission.')

    @property
    def title(self):
        return self._get_field('titleInfo/mods:title')

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
        _add_metadata_field(DCTERMS.title, self.alt_title)
        _add_metadata_field(DCTERMS.creator, self.author)
        _add_metadata_field(DCTERMS.dateCopyrighted, self.copyright_date)
        _add_metadata_field(DCTERMS.type, self.dc_type)
        _add_metadata_field(MSL.degreeGrantedForCompletion,
                            self.degree_statement)
        _add_metadata_field(MSL.associatedDepartment, self.department)
        _add_metadata_field(BIBO.handle, self.handle, obj_type='uri')
        _add_metadata_field(DCTERMS.dateIssued, self.issue_date)
        _add_metadata_field(LOCAL.ligature_errors, self.ligatures)
        _add_metadata_field(LOCAL.line_ends, self.line_ends)
        _add_metadata_field(LOCAL.no_full_text, self.no_full_text)
        _add_metadata_field(MODS.note, self.notes)
        _add_metadata_field(DCTERMS.publisher, self.publisher)
        _add_metadata_field(RDF.type, self.rdf_type)
        _add_metadata_field(DCTERMS.rights, self.rights_statement)
        _add_metadata_field(DCTERMS.title, self.title)

        if serialization == 'turtle':
            return m.serialize(format='turtle')

    def create_file_sparql_update(self, file_ext):
        lang = self._get_field('language/mods:languageTerm')
        query = ('PREFIX dcterms: <http://purl.org/dc/terms/> PREFIX pcdm: '
                 '<http://pcdm.org/models#> INSERT { <> a pcdm:File ; '
                 'dcterms:language "' + lang + '"')
        if file_ext == '.pdf':
            pages = self._get_field('physicalDescription/mods:extent')
            query += ' ; dcterms:extent "' + pages + '"'
        query += ' . } WHERE { }'
        return query

    def _get_field(self, search_string, field_type='single',
                   text_to_strip=None):
        result = []
        if field_type == 'degree':
            for f in self.mets.findall(base_mets_search + search_string,
                                       mets_namespace):
                if f.text.startswith('Thesis'):
                    result = f.text
        elif field_type == 'multi':
            for f in self.mets.findall(base_mets_search + search_string,
                                       mets_namespace):
                result.append(f.text)
        elif field_type == 'notes':
            for f in self.mets.findall(base_mets_search + search_string,
                                       mets_namespace):
                if not f.text.startswith('Thesis'):
                    result.append(f.text)
        elif field_type == 'single':
            try:
                result = self.mets.find(base_mets_search + search_string,
                                        mets_namespace).text
            except AttributeError as e:
                result = None
        elif field_type == 'split':
            for f in self.mets.findall(base_mets_search + search_string,
                                       mets_namespace):
                if not result:
                    result = f.text
                else:
                    t = f.text.lstrip(text_to_strip)
                    result += t
        if not result:
            result = None
        return result

    def _get_error_value(self, error):
        result = None
        if self.errors[error] == '1':
            result = True
        return result

    def _get_full_text_error(self):
        result = None
        s = self.errors
        if (s['PDFBox err'] == '1' or
            (s['No new text'] == '1' and s['No old text'] == '1') or
                s['Encoded'] == '1' or s['Hex strings'] == '1'):
            result = True
        return result


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
    print(uri)
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
