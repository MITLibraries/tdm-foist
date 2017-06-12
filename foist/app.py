# -*- coding: utf-8 -*-
from __future__ import absolute_import
from contextlib import contextmanager
from functools import reduce
import csv
import logging
import re


import rdflib
import requests

from foist.namespaces import BIBO, DCTERMS, DCTYPE, LOCAL, MODS, MSL, PCDM, RDF

log = logging.getLogger(__name__)

mets_namespace = {'mets': 'http://www.loc.gov/METS/',
                  'mods': 'http://www.loc.gov/mods/v3'}

repls = (('E.E', 'Elec.E'), ('Elect.E', 'Elec.E'), ('OceanE', 'Ocean.E'),
         ('M.ArchAS', 'M.Arch.A.S'), ('PhD', 'Ph.D'), ('ScD', 'Sc.D'))

degrees = ['B.Arch.', 'B.C.P.', 'B.S.', 'C.P.H.', 'Chem.E.', 'Civ.E.',
           'E.A.A.', 'Elec.E.', 'Env.E.', 'M.Arch.', 'M.Arch.A.S.', 'M.B.A.',
           'M.C.P.', 'M.Eng.', 'M.Fin.', 'M.S.', 'M.S.V.S.', 'Mat.Eng.',
           'Nav.Arch.', 'Mech.E.', 'Nav.E.', 'Nucl.E.', 'Ocean.E.', 'Ph.D.',
           'S.B.', 'S.M.', 'S.M.M.O.T.', 'Sc.D.']


class Thesis(object):
    '''A thesis object representing a single thesis intellectual entity with
    all its associated metadata.
    '''
    def __init__(self, name, mets, departments, text_errors=None):
        self.name = name
        self.mets = mets
        self.errors = text_errors
        self.departments = departments
        self._no_full_text = self.errors and self._has_full_text_error() or \
            None

    @property
    def abstract(self):
        try:
            result = ''.join([e.text.lstrip('(cont.)') for
                             e in self.mets.findall('.//mods:abstract',
                                                    mets_namespace)])
        except AttributeError:
            result = None
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
    def degree(self):
        result = []
        try:
            degree = re.findall('[A-Z][a-z]{,4}\.? ?[A-Z][a-z]{,3}\.?[A-Z]?\.?'
                                '[A-Z]?\.?[A-Z]?\.?', self.degree_statement)
            for item in degree:
                i = item.replace(' ', '')
                i = i.rstrip('.')
                i = reduce(lambda a, kv: a.replace(*kv), repls, i)
                if not i.endswith('.'):
                    i += '.'
                if i in degrees:
                    result.append(i)
        except TypeError as e:
            result = None
        return result or None

    @property
    def degree_statement(self):
        try:
            result = [e.text for e in
                      self.mets.findall('.//mods:note', mets_namespace) if
                      e.text is not None and
                      (e.text.startswith('Thesis') or
                       e.text.startswith('Massachusetts Institute of '
                                         'Technology'))]
        except AttributeError:
            result = None
        return result[0] if result else None

    @property
    def department(self):
        return self.departments

    @property
    def encoded_text(self):
        return self.errors and self._has_error('Encoded text new file') or None

    @property
    def handle(self):
        try:
            result = self.mets.find('.//mods:identifier[@type="uri"]',
                                    mets_namespace).text
        except AttributeError:
            result = None
        return result

    @property
    def handle_part(self):
        try:
            result = self.handle.split('/')[-1]
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
        return self.errors and self._has_error('Ligatures new') or None

    @property
    def no_full_text(self):
        return self._no_full_text

    @no_full_text.setter
    def no_full_text(self, x):
        self._no_full_text = x

    @property
    def notes(self):
        try:
            result = [e.text for e in
                      self.mets.findall('.//mods:note', mets_namespace)]
        except AttributeError:
            result = None
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

        def _add_metadata_field(p, obj, is_uri=False):
            if isinstance(obj, list):
                for i in obj:
                    o = _create_rdf_obj(i, is_uri)
                    m.add((s, p, o))
            else:
                o = _create_rdf_obj(obj, is_uri)
                m.add((s, p, o))

        def _create_rdf_obj(obj, is_uri):
            if is_uri:
                return rdflib.URIRef(obj)
            return rdflib.Literal(obj)

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
        _add_metadata_field(DCTERMS.type, self.dc_type, is_uri='uri')
        _add_metadata_field(MSL.degreeGrantedForCompletion,
                            self.degree)
        _add_metadata_field(LOCAL.degree_statement, self.degree_statement)
        _add_metadata_field(MSL.associatedDepartment, self.department)
        _add_metadata_field(LOCAL.encoded_text, self.encoded_text)
        _add_metadata_field(BIBO.handle, self.handle, is_uri='uri')
        _add_metadata_field(LOCAL.handle_part, self.handle_part)
        _add_metadata_field(DCTERMS.dateIssued, self.issue_date)
        _add_metadata_field(LOCAL.ligature_errors, self.ligatures)
        _add_metadata_field(LOCAL.no_full_text, self.no_full_text)
        _add_metadata_field(MODS.note, self.notes)
        _add_metadata_field(DCTERMS.publisher, self.publisher)
        _add_metadata_field(RDF.type, self.rdf_type, is_uri='uri')
        _add_metadata_field(DCTERMS.rights, self.rights_statement)
        _add_metadata_field(DCTERMS.title, self.title)

        if serialization == 'turtle':
            return m.serialize(format='turtle')

    def create_file_sparql_update(self, file_ext):
        query = ('PREFIX dcterms: <http://purl.org/dc/terms/> PREFIX pcdm: '
                 '<http://pcdm.org/models#> PREFIX ebucore: '
                 '<http://www.ebu.ch/metadata/ontologies/ebucore/ebucore#> '
                 'INSERT { <> a pcdm:File')
        try:
            lang = self.mets.find('.//mods:language/mods:languageTerm',
                                  mets_namespace).text
            query += ' ; dcterms:language "' + lang + '"'
        except AttributeError:
            pass
        if file_ext == '.pdf':
            try:
                pages = self.mets.find(('.//mods:physicalDescription/mods:'
                                       'extent'), mets_namespace).text
                query += ' ; dcterms:extent "' + pages + '"'
            except AttributeError:
                pass
        elif file_ext == '.txt':
            query += ' ; ebucore:hasEncodingFormat "utf-8"'
        query += ' . } WHERE { }'
        return query

    def _has_error(self, error):
        if self.errors[error] == '1':
            return True

    def _has_full_text_error(self):
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
def transaction(fedora_uri, auth=None):
    '''Starts a Fedora transaction, yields a location header, commits and
    closes the transaction.
    '''
    uri = fedora_uri + 'fcr:tx'
    r = requests.post(uri, auth=auth)
    location = r.headers['Location']
    try:
        yield location
    except Exception as e:
        uri = location + '/fcr:tx/fcr:rollback'
        r = requests.post(uri, auth=auth)
        raise(e)
    else:
        uri = location + '/fcr:tx/fcr:commit'
        r = requests.post(uri, auth=auth)
        r.raise_for_status()


def create_container(uri, turtle, auth=None):
    '''Create basic container for an item.
    '''
    headers = {'Content-Type': 'text/turtle; charset=utf-8'}
    r = requests.put(uri, headers=headers, auth=auth, data=turtle)
    r.raise_for_status()
    return r


def upload_content(uri, content_to_upload, mimetype, auth=None):
    '''Add content in string or bytes format to a given container uri.
    '''
    headers = {'Content-Type': mimetype}
    r = requests.put(uri, headers=headers, auth=auth,
                     data=content_to_upload)
    r.raise_for_status()
    return r.status_code


def upload_file(uri, file_path, mimetype, auth=None):
    '''Add a file to a given container uri.
    '''
    headers = {'Content-Type': mimetype}
    f = {'file': open(file_path, 'rb')}
    r = requests.put(uri, headers=headers, auth=auth, files=f)
    r.raise_for_status()
    return r.status_code


def update_metadata(uri, sparql, auth=None):
    '''Update metadata for a single item in Fedora, given the item's URI and a
    SPARQL update query.
    '''
    headers = {'Content-Type': 'application/sparql-update'}
    r = requests.patch(uri, headers=headers, auth=auth, data=sparql)
    r.raise_for_status()
    return r.status_code


# Create a temporary dummy resource to initialize custom RDF namespace prefixes
def initialize_custom_prefixes(fedora_uri, auth=None):
    uri = fedora_uri + 'initialize'
    headers = {'Content-Type': 'application/sparql-update'}
    data = '''
        PREFIX bibo: <http://purl.org/ontology/bibo/>
        PREFIX dcterms: <http://purl.org/dc/terms/>
        PREFIX dctype: <http://purl.org/dc/dcmitype/>
        PREFIX local: <http://example.com/>
        PREFIX mods: <http://www.loc.gov/standards/mods/modsrdf/v1/#>
        PREFIX msl: <http://purl.org/montana-state/library/>
        PREFIX pcdm: <http://pcdm.org/models#>
    INSERT DATA {
        <> a pcdm:Object ;
            bibo:test 'test' ;
            dcterms:test 'test' ;
            dctype:test 'test' ;
            local:test 'test' ;
            mods:test 'test' ;
            msl:test 'test' .
        }'''
    r1 = requests.put(uri, auth=auth)
    r1.raise_for_status()
    r2 = requests.patch(uri, headers=headers, auth=auth,
                        data=data)
    r2.raise_for_status()
    r3 = requests.delete(uri, auth=auth)
    r3.raise_for_status()
    r4 = requests.delete(uri+'/fcr:tombstone', auth=auth)
    r4.raise_for_status()


# Upload a single thesis item and its files to Fedora
def upload_thesis(fedora_uri, collection_name, handle, turtle, pdf_file,
                  pdf_sparql, text_content=None, text_sparql=None, auth=None):
    retries = 0
    while retries < 5:
        try:
            with transaction(fedora_uri, auth=auth) as t:
                parent_uri = t + '/' + collection_name + '/'
                item_uri = parent_uri + handle + '/'
                create_container(item_uri, turtle, auth=auth)

                pdf_uri = item_uri + handle + '.pdf/'
                upload_file(pdf_uri, pdf_file, 'application/pdf', auth=auth)
                update_metadata(pdf_uri + 'fcr:metadata', pdf_sparql,
                                auth=auth)
                u = (fedora_uri + '/' + collection_name + '/' + handle + '/' +
                     handle + '.pdf/')
                query = ('PREFIX pcdm: <http://pcdm.org/models#> INSERT { '
                         '<> pcdm:hasFile <' + u + '> . } WHERE { }')
                update_metadata(item_uri, query, auth=auth)

                if text_content:
                    text_uri = item_uri + handle + '.txt/'
                    upload_content(text_uri, text_content, 'text/plain',
                                   auth=auth)
                    update_metadata(text_uri + 'fcr:metadata', text_sparql,
                                    auth=auth)
                    u = (fedora_uri + '/' + collection_name + '/' + handle +
                         '/' + handle + '.txt/')
                    query = ('PREFIX pcdm: <http://pcdm.org/models#> '
                             'INSERT { <> pcdm:hasFile <' + u + '> . } '
                             'WHERE { }')
                    update_metadata(item_uri, query, auth=auth)
            return 'Success'
        except requests.exceptions.HTTPError as e:
            if str(e).startswith('409'):
                return 'Exists'
            else:
                log.warning('Upload attempt failed, retrying %s' % handle)
                log.debug(e)
                retries += 1
        return 'Failure'
