# -*- coding: utf-8 -*-
from __future__ import absolute_import
import csv
import logging
import os
import xml.etree.ElementTree as ET

import rdflib
import requests

from foist.namespaces import BIBO, DCTERMS, DCTYPE, LOCAL, MODS, MSL, PCDM, RDF

log = logging.getLogger(__name__)
ns = {'mets': 'http://www.loc.gov/METS/',
      'mods': 'http://www.loc.gov/mods/v3'}


class ThesisItem(object):
    '''A thesis object representing a single thesis intellectual entity with
    all its associated metadata.
    '''
    def __init__(self, name, output_location, mets):
        self.name = name
        self.output_location = output_location
        tree = ET.parse(mets)
        self.root = tree.getroot()
        self.metadata = rdflib.Graph()
        self.s = rdflib.URIRef('')
        self.metadata.bind('bibo', BIBO)
        self.metadata.bind('dcterms', DCTERMS)
        self.metadata.bind('dctype', DCTYPE)
        self.metadata.bind('local', LOCAL)
        self.metadata.bind('mods', MODS)
        self.metadata.bind('msl', MSL)
        self.metadata.bind('pcdm', PCDM)

    def generate_item_metadata(self):
        self.metadata.add((self.s, DCTERMS.abstract,
                           self.get_field('abstract', 'abstract')))
        self.metadata.add((self.s, MSL.reviewedBy,
                           self.get_field('advisor', ('name/*[mods:roleTerm='
                                          '"advisor"]/../mods:namePart'))))
        self.metadata.add((self.s, DCTERMS.creator,
                           self.get_field('author', ('name/*[mods:roleTerm='
                                          '"author"]/../mods:namePart'))))
        self.metadata.add((self.s, DCTERMS.dateCopyrighted,
                           self.get_field('copyright',
                                          'originInfo/mods:copyrightDate')))
        self.metadata.add((self.s, MSL.associatedDepartment,
                           self.get_field('department', 'subject/mods:topic')))
        self.metadata.add((self.s, BIBO.handle,
                           self.get_field('handle', 'identifier[@type="uri"]',
                                          'uri')))
        self.metadata.add((self.s, RDF.type, BIBO.thesis))
        self.metadata.add((self.s, RDF.type, PCDM.Object))
        self.metadata.add((self.s, DCTERMS.type, DCTYPE.text))
        self.metadata.add((self.s, DCTERMS.dateIssued,
                           self.get_field('publication_date',
                                          'originInfo/mods:dateIssued')))
        self.metadata.add((self.s, DCTERMS.publisher,
                           rdflib.Literal(('Massachusetts Institute of '
                                           'Technology'))))
        self.metadata.add((self.s, DCTERMS.rights,
                           rdflib.Literal(('M.I.T. theses are protected by '
                                           'copyright. They may be viewed from'
                                           ' this source for any purpose, but '
                                           'reproduction or distribution in '
                                           'any format is prohibited without '
                                           'written permission. See provided '
                                           'URL for inquiries about '
                                           'permission.'))))
        self.metadata.add((self.s, DCTERMS.title,
                           self.get_field('title', 'titleInfo/mods:title')))
        if (self.get_field('alternative_title',
                           'titleInfo[@type="alternative"]/mods:title') !=
                rdflib.Literal('None')):
            self.metadata.add((self.s, DCTERMS.title,
                               self.get_field('alternative_title',
                                              ('titleInfo[@type="alternative"]'
                                               '/mods:title'))))
        for f in self.root.findall('./mets:dmdSec/*/*/*/mods:note', ns):
            if f.text.startswith('Thesis'):
                self.metadata.add((self.s, MSL.degreeGrantedForCompletion,
                                   rdflib.Literal(f.text)))
            else:
                self.metadata.add((self.s, MODS.note,
                                   rdflib.Literal(f.text)))

    def create_item_turtle_statements(self):
        turtle_file = os.path.join(self.output_location, self.name,
                                   self.name + '.ttl')
        with open(turtle_file, 'wb') as f:
            f.write(self.metadata.serialize(format='turtle'))

    def create_file_sparql_update(self, file_ext):
        sparql_file = os.path.join(self.output_location, self.name,
                                   self.name + file_ext + '.ru')
        lang = self.get_field('language', 'language/mods:languageTerm')
        query = ('PREFIX dcterms: <http://purl.org/dc/terms/> PREFIX pcdm: '
                 '<http://pcdm.org/models#> INSERT { <> a pcdm:File ; '
                 'dcterms:language "' + lang + '"')
        if file_ext == '.pdf':
            pages = self.get_field('pages', 'physicalDescription/mods:extent')
            query += ' ; dcterms:extent "' + pages + '"'
        query += ' . } WHERE { }'
        with open(sparql_file, 'wb') as f:
            f.write(query.encode('utf-8'))

    def get_field(self, field, search_string, t='string'):
        base = './mets:dmdSec/*/*/*/mods:'
        try:
            result = self.root.find(base + search_string, ns).text
            if t == 'string':
                return rdflib.Literal(result)
            elif t == 'uri':
                return rdflib.URIRef(result)
        except AttributeError as e:
            log.warning(('No ' + field +
                         ' field for item ' + self.name))
            return rdflib.Literal('None')

    def add_text_errors(self, text_errors):
        if self.name in text_errors:
            errors = text_errors[self.name]
            if (errors['PDFBox err'] != '0' or
                (errors['No new text'] != '0' and ['No old text'] != '0') or
                    errors['Encoded'] != '0' or errors['Hex strings'] != '0'):
                self.metadata.add((self.s, LOCAL.no_full_text,
                                   rdflib.Literal('True')))
            if errors['Ligatures'] != '0':
                self.metadata.add((self.s, LOCAL.ligature_errors,
                                   rdflib.Literal('True')))
            if errors['Line ends'] != '0':
                self.metadata.add((self.s, LOCAL.line_ends,
                                   rdflib.Literal('True')))


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


def create_thesis_item_container(transaction, item, turtle):
    '''Create basic PCDM container for a thesis item.
    '''
    uri = transaction + item
    headers = {'Content-Type': 'text/turtle; charset=utf-8'}
    with open(turtle, 'rb') as payload:
        r = requests.put(uri, headers=headers, data=payload)
    if r.status_code >= 200 and r.status_code < 300:
        log.info(('%s Thesis item created: %s') % (r, r.text))
        return 'Success'
    else:
        log.error(('%s %s ITEM ' + item) % (r, r.text))
        return 'Failure'


def add_thesis_item_file(transaction, item, ext, mimetype, file_path):
    '''Add a file to a thesis item container.
    '''
    uri = transaction + item + '/' + item + ext
    headers = {'Content-Type': mimetype}
    with open(file_path, 'rb') as payload:
        r = requests.put(uri, headers=headers, data=payload)
    if r.status_code >= 200 and r.status_code < 300:
        log.info(('%s Thesis file added: %s') % (r, r.text))
        return 'Success'
    else:
        log.error(('%s %s FILE ' + item + ext) % (r, r.text))
        return 'Failure'


def add_file_metadata(transaction, item, ext, file_path, sparql_path):
    '''Update the metadata for a given file.
    '''
    sparql = sparql_path
    uri = transaction + item + '/' + item + ext + '/fcr:metadata'
    headers = {'Content-Type': 'application/sparql-update'}
    with open(sparql, 'rb') as data:
        r = requests.patch(uri, headers=headers, data=data)
    if r.status_code >= 200 and r.status_code < 300:
        log.info(('%s File metadata updated: ' + item + ext) % (r))
        return 'Success'
    else:
        log.error(('%s %s File metadata NOT updated: ' + item + ext)
                  % (r, r.text))
        return 'Failure'


def create_pcdm_relationships(transaction, item):
    '''Create PCDM relationship statements for a thesis item.
    '''
    uri = transaction + item
    headers = {'Content-Type': 'application/sparql-update'}
    query = ('PREFIX pcdm: <http://pcdm.org/models#> INSERT { <> '
             'pcdm:hasMember <' + uri + '> . } WHERE { }')
    r = requests.patch(transaction, headers=headers, data=query)
    if r.status_code >= 200 and r.status_code < 300:
        log.info(('%s PCDM collection membership created: %s') %
                 (r, item))
    else:
        log.error(('%s PCDM collection membership NOT created: %s') %
                  (r, item))
    pdf = uri + '/' + item + '.pdf'
    text = uri + '/' + item + '.txt'
    query = ('PREFIX pcdm: <http://pcdm.org/models#> INSERT { <> pcdm:hasFile '
             '<' + pdf + '> ; pcdm:hasFile <' + text + '> . } WHERE { }')
    r = requests.patch(uri, headers=headers, data=query)
    if r.status_code >= 200 and r.status_code < 300:
        log.info(('%s PCDM file memberships created: %s') %
                 (r, item))
        return 'Success'
    else:
        log.error(('%s PCDM file memberships NOT created: %s') %
                  (r, item))
        return 'Failure'


def start_transaction(fedora_uri):
    '''Starts a Fedora transaction.
    Returns location header.
    '''
    uri = fedora_uri + 'fcr:tx'
    r = requests.post(uri)
    log.info('%s Transaction started: %s' % (r, r.headers['Location']))
    return r.headers['Location']


def commit_transaction(location):
    '''Commit and close a Fedora transaction.
    Returns status code.
    '''
    uri = location + '/fcr:tx/fcr:commit'
    r = requests.post(uri)
    if r.status_code == 204:
        log.info('%s Transaction committed.' % (r))
        return True
    else:
        log.error('% Transaction failed.' % (r))
        return False
