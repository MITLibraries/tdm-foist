# -*- coding: utf-8 -*-
from __future__ import absolute_import
import concurrent.futures
import glob
import logging
import logging.config
import os
import xml.etree.ElementTree as ET

import click
import requests
from timeit import default_timer as timer

from foist import (add_file_metadata, add_thesis_item_file,
                   create_pcdm_relationships, create_theses_container,
                   create_thesis_item_container, initialize_custom_prefixes,
                   parse_text_encoding_errors, Thesis, transaction,
                   upload_thesis)


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
@click.argument('collection_name')
@click.option('-o', '--output_directory', default='',
              type=click.Path(exists=False, file_okay=False,
                              resolve_path=False),
              help=('Output directory for thesis metadata files. Default is '
                    'same as input directory.'))
def process_metadata(input_directory, output_directory, collection_name):
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
        if not os.path.exists(os.path.join(input_directory, d, d + '.pdf')):
            logger.warning(('No PDF file for item %s. Item metadata not '
                           'processed.') % d)
            continue
        try:
            mets = ET.parse(os.path.join(input_directory, d,
                                         d + '.xml')).getroot()
        except IOError as e:
            logger.warning('No XML file for item %s. %s' % (d, e))
        thesis = Thesis(d, mets, collection_name, text_encoding_errors.get(d))
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
@click.option('-u', '--username', default=None)
@click.option('-p', '--password', default=None)
@click.option('-w', '--workers', default=1)
def upload_theses(directory, fedora_uri, username, password, workers):
    '''Uploads all thesis items in a directory to Fedora.

    This script traverses the given DIRECTORY of thesis files exported from
    DSpace@MIT and for each thesis creates an item container, uploads files,
    adds file metadata, and adds PCDM relationship statements between the
    collection, item, and files.
    '''
    auth = (username, password) if username else None
    dirnames = next(os.walk(os.path.join(directory, '.')))[1]
    thesis_count = 0
    start = timer()

    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as\
            executor:
        run_next = {executor.submit(upload_thesis, d, directory, fedora_uri,
                                    auth): d for d in dirnames}
        for future in concurrent.futures.as_completed(run_next):
            d = run_next[future]
            if future.result() == 'Success':
                thesis_count += 1
            elif future.result() == 'Exists':
                logger.warning('Item %s already in collection' % d)
                thesis_count += 1
            elif future.result() == 'Not a thesis':
                logger.warning('No PDF for item %s, not ingested into Fedora.'
                               % d)
            else:
                logger.warning('Thesis %s upload failed' % d)

    end = timer()
    logger.info(end - start)
    logger.info('TOTAL: %s theses ingested.\n' % thesis_count)


@main.command()
@click.option('-f', '--fedora-uri',
              default='http://localhost:8080/fcrepo/rest/',
              help=('Base Fedora REST URI. Default is '
                    'http://localhost:8080/fcrepo/rest/'))
@click.option('-u', '--username', default=None)
@click.option('-p', '--password', default=None)
def initialize_fedora(fedora_uri, username, password):
    auth = (username, password) if username else None
    initialize_custom_prefixes(fedora_uri, auth)
    create_theses_container(fedora_uri, auth)


if __name__ == '__main__':
    main()
