# -*- coding: utf-8 -*-
from __future__ import absolute_import

import pytest
import requests
import xml.etree.ElementTree as ET

from foist.pipeline import (extract_text, get_collection_names, get_pdf_url,
                            get_record, get_record_list, is_in_fedora,
                            is_thesis, parse_record_list)


def test_extract_text_returns_bytes(pdf):
    text = extract_text(pdf)
    assert type(text) == bytes


def test_get_collection_names_returns_correct_names():
    names = get_collection_names(['hdl_1721.1_7888', 'hdl_1721.1_7710',
                                  'hdl_1721.1_7929', 'hdl_1721.1_7742',
                                  'hdl_1721.1_102296', 'hdl_1721.1_102291',
                                  'not_a_key'])
    assert names == {'Engineering Systems', 'Technology and Policy',
                     'Institute for Data, Systems, and Society'}


def test_get_pdf_url_succeeds(mets_xml):
    mets = ET.parse(mets_xml).getroot()
    pdf_url = get_pdf_url(mets)
    assert pdf_url == ('http://dspace.mit.edu/bitstream/1721.1/'
                       '107085/1/971247903-MIT.pdf')


def test_get_record_succeeds(pipeline):
    '''Correctly-formed request should return XML response.
    '''
    dspace_oai_uri = 'http://example.com/oai/request?'
    dspace_oai_identifier = 'oai:dspace.mit.edu:1721.1/'
    identifier = '12345'
    metadata_format = 'mets'
    r = get_record(dspace_oai_uri, dspace_oai_identifier, identifier,
                   metadata_format)
    assert '<?xml version="1.0" encoding="UTF-8"?>' in r


def test_get_record_list_succeeds(pipeline):
    '''Correctly-formed request should return XML response.
    '''
    dspace_oai_uri = 'http://example.com/oai/request?'
    metadata_format = 'mets'
    start_date = '2017-01-01'
    end_date = '2017-02-01'
    r = get_record_list(dspace_oai_uri, metadata_format, start_date=start_date,
                        end_date=end_date)
    assert '<?xml version="1.0" encoding="UTF-8"?>' in r


def test_is_in_fedora_returns_true_for_ingested_item(fedora):
    handle = 'thesis'
    fedora_uri = 'http://example.com/rest/'
    assert is_in_fedora(handle, fedora_uri, 'theses') is True


def test_is_in_fedora_returns_false_for_uningested_item(fedora):
    handle = 'uningested_thesis'
    fedora_uri = 'http://example.com/rest/'
    assert is_in_fedora(handle, fedora_uri, 'theses') is False


def test_is_in_fedora_error_raises_error(fedora_errors):
    with pytest.raises(requests.exceptions.HTTPError):
        handle = 'no_auth'
        fedora_uri = 'http://example.com/rest/'
        is_in_fedora(handle, fedora_uri, 'theses')


def test_is_thesis_returns_true_for_thesis():
    set_specs = ['hdl_1721.1_7593']
    assert is_thesis(set_specs) is True


def test_is_thesis_returns_false_for_not_thesis():
    set_specs = ['i_am_not_a_thesis_set']
    assert is_thesis(set_specs) is False


def test_parse_record_list_returns_correct_json(record_list):
    json_records = parse_record_list(record_list)
    assert {'identifier': '108425', 'sets': ['hdl_1721.1_494'],
            'handle': '1721.1-108425'} in json_records
