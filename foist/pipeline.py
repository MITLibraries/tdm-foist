import datetime
import json
import logging
import tempfile
import os
import requests
import xml.etree.ElementTree as ET

from io import BytesIO, StringIO
from tika import parser

CUR_DIR = os.path.dirname(os.path.realpath(__file__))
with open(CUR_DIR + '/resources/thesis_set_list.json', 'r') as f:
    THESIS_SET_LIST = json.loads(f.read())

mets_namespace = {'mets': 'http://www.loc.gov/METS/',
                  'mods': 'http://www.loc.gov/mods/v3',
                  'oai': 'http://www.openarchives.org/OAI/2.0/'}

log = logging.getLogger(__name__)


def extract_text(pdf_file):
    try:
        parsed = parser.from_file(pdf_file)
        return parsed['content'].encode('utf-8')
    except Exception as e:
        raise e


def get_collection_names(set_specs):
    '''Gets and returns set of normalized collection names from set spec list.
    '''
    names = []
    for set_spec in set_specs:
        try:
            name = THESIS_SET_LIST[set_spec]
            name = name.replace(' - ', '(').replace(' (', '(')
            split_name = name.split('(')
            names.append(split_name[0])
        except KeyError as e:
            pass
    return set(names)


def get_pdf(url):
    '''Gets PDF file from specified URL and returns binary PDF content.
    '''
    try:
        r = requests.get(url)
        r.raise_for_status()
        return r.content
    except requests.exceptions.HTTPError as e:
        raise e


def get_pdf_url(mets):
    '''Gets and returns download URL for PDF from METS record.
    '''
    record = mets.find('.//mets:file[@MIMETYPE="application/pdf"]/',
                       mets_namespace)
    url = record.get('{http://www.w3.org/1999/xlink}href')
    return url


def get_record(dspace_oai_uri, dspace_oai_identifier, identifier,
               metadata_format):
    '''Gets metadata record for a single item in OAI-PMH repository in
    specified metadata format.
    '''
    url = (dspace_oai_uri + 'verb=GetRecord&identifier=' +
           dspace_oai_identifier + identifier + '&metadataPrefix=' +
           metadata_format)
    r = requests.get(url)
    return r.text


def get_record_list(dspace_oai_uri, metadata_format, start_date=None,
                    end_date=None):
    '''Returns a list of record headers for items in OAI-PMH repository. Must
    pass in desired metadata format prefix. Can optionally pass bounding dates
    to limit harvest to.
    '''
    url = (dspace_oai_uri + 'verb=ListIdentifiers&metadataPrefix=' +
           metadata_format)

    if start_date:
        _validate_date(start_date)
        url += '&from=' + start_date
    if end_date:
        _validate_date(end_date)
        url += '&until=' + end_date

    r = requests.get(url)
    return r.text


def is_in_fedora(handle, fedora_uri, parent_container, auth=None):
    '''Returns True if given thesis item is already in the given Fedora
    repository, otherwise returns False.
    '''
    url = fedora_uri + parent_container + '/' + handle
    r = requests.head(url, auth=auth)
    if r.status_code == 200:
        return True
    elif r.status_code == 404:
        return False
    else:
        raise requests.exceptions.HTTPError(r)


def is_thesis(sets):
    '''Returns True if any set_spec in given sets is in the
    thesis_set_spec_list, otherwise returns false.
    '''
    for set_spec in sets:
        if set_spec in THESIS_SET_LIST.keys():
            return True
    return False


def parse_record_list(record_xml):
    result = []
    xml = ET.fromstring(record_xml)
    records = xml.findall('.//oai:header', mets_namespace)
    for record in records:
        handle = record.find('oai:identifier', mets_namespace).text\
            .replace('oai:dspace.mit.edu:', '').replace('/', '-')
        identifier = handle.replace('1721.1-', '')
        setSpecs = record.findall('oai:setSpec', mets_namespace)
        sets = [s.text for s in setSpecs]
        result.append({'handle': handle, 'identifier': identifier,
                      'sets': sets})
    return result


def _validate_date(date_text):
    try:
        datetime.datetime.strptime(date_text, '%Y-%m-%d')
    except ValueError:
        raise ValueError('Incorrect date format, should be YYYY-MM-DD')
