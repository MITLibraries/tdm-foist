# -*- coding: utf-8 -*-
from __future__ import absolute_import
import glob
import logging
import logging.config
import os
import xml.etree.ElementTree as ET

import click

from foist import (add_file_metadata, add_thesis_item_file,
                   create_pcdm_relationships, create_thesis_item_container,
                   parse_text_encoding_errors, Thesis, transaction)


logger = logging.getLogger(__name__)
logging.config.dictConfig({
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'full': {
            'format': '%(levelname)s: [%(asctime)s] %(message)s'
        }
    },
    'handlers': {
        'console': {
            'formatter': 'full',
            'class': 'logging.StreamHandler',
            'stream': 'ext://sys.stdout'
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'formatter': 'full',
            'filename': 'logfile.log',
            'maxBytes': 1024*1024,
            'backupCount': 3
        }
    },
    'loggers': {
        'foist': {
            'level': 'DEBUG',
            'handlers': ['console', 'file']
        }
    }
})


@click.group()
def main():
    pass


@main.command()
@click.argument('input_directory', type=click.Path(exists=True,
                                                   file_okay=False,
                                                   resolve_path=True))
@click.option('-o', '--output_directory', default='',
              type=click.Path(exists=False, file_okay=False,
                              resolve_path=False),
              help=('Output directory for thesis metadata files. Default is '
                    'same as input directory.'))
def process_metadata(input_directory, output_directory):
    '''Parse metadata for all thesis items in a directory.

    This script traverses the given INPUT_DIRECTORY of thesis files and for
    each thesis creates a turtle file of metadata statements and SPARQL update
    files for each file representation of the thesis. These get stored in the
    OUTPUT_DIRECTORY, which if not specified defaults to the INPUT_DIRECTORY.
    '''
    if output_directory == '':
        output_directory = input_directory
    error_file = glob.glob(os.path.join(input_directory, '*.tab'))[0]
    text_encoding_errors = parse_text_encoding_errors(error_file)
    dirnames = next(os.walk(os.path.join(input_directory, '.')))[1]
    count = 0
    for d in dirnames:
        try:
            mets = ET.parse(os.path.join(input_directory, d, d + '.xml')).getroot()
        except IOError as e:
            logger.error('No XML file for item %s. %s' % (d, e))
        thesis = Thesis(d, mets, text_encoding_errors)
        with open(os.path.join(output_directory, thesis.name, thesis.name +
                               '.ttl'), 'wb') as f:
            f.write(thesis.get_metadata())
        with open(os.path.join(output_directory, thesis.name, thesis.name +
                               '.pdf.ru'), 'wb') as f:
            f.write(thesis.create_file_sparql_update('.pdf').encode('utf-8'))
        with open(os.path.join(output_directory, thesis.name, thesis.name +
                               '.txt.ru'), 'wb') as f:
            f.write(thesis.create_file_sparql_update('.txt').encode('utf-8'))
        count += 1
    logger.info('TOTAL: %s theses processed in folder %s' % (str(count),
                                                             input_directory))


@main.command()
@click.argument('directory', type=click.Path(exists=True, file_okay=False,
                                             resolve_path=True))
@click.option('-f', '--fedora-uri',
              default='http://localhost:8080/fcrepo/rest/',
              help=('Base Fedora REST URI. Default is '
                    'http://localhost:8080/fcrepo/rest/'))
def upload_theses(directory, fedora_uri):
    '''Uploads all thesis items in a directory to Fedora.

    This script traverses the given DIRECTORY of thesis files exported from
    DSpace@MIT and for each thesis creates an item container, uploads files,
    adds file metadata, and adds PCDM relationship statements between the
    collection, item, and files.
    '''
    dirnames = next(os.walk(os.path.join(directory, '.')))[1]
    thesis_count = 0
    for d in dirnames:
        turtle_path = os.path.join(directory, d, d + '.ttl')
        pdf_path = os.path.join(directory, d, d + '.pdf')
        text_path = os.path.join(directory, d, d + '-new.txt')
        with transaction(fedora_uri) as t:
            parent_loc = t + '/theses/'
            item_loc = parent_loc + d + '/'
            pdf_loc = item_loc + d + '.pdf/'
            pdf_sparql = os.path.join(directory, d, d + '.pdf.ru')
            text_loc = item_loc + d + '.txt/'
            text_sparql = os.path.join(directory, d, d + '.txt.ru')

            create_thesis_item_container(parent_loc, d, turtle_path)

            add_thesis_item_file(item_loc, d, '.pdf', 'application/pdf',
                                 pdf_path)
            add_file_metadata(pdf_loc, d, '.pdf', pdf_path, pdf_sparql)
            # TODO: Check for 'no_full_text' field in metadata and only do
            # the following if field is not present
            add_thesis_item_file(item_loc, d, '.txt', 'text/plain',
                                 text_path)
            add_file_metadata(text_loc, d, '.txt', text_path, text_sparql)

            query = ('PREFIX pcdm: <http://pcdm.org/models#> INSERT { <> '
                     'pcdm:hasMember <' + parent_loc + d + '> . } WHERE '
                     '{ }')
            create_pcdm_relationships(t + '/theses', query)

            query = ('PREFIX pcdm: <http://pcdm.org/models#> INSERT { <> '
                     'pcdm:hasFile <' + pdf_loc + '> ; pcdm:hasFile'
                     ' <' + text_loc + '> . } WHERE { }')
            create_pcdm_relationships(item_loc, query)
            thesis_count += 1
    logger.info('TOTAL: %s theses ingested.\n' % thesis_count)


if __name__ == '__main__':
    main()
