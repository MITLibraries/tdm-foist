# -*- coding: utf-8 -*-
from __future__ import absolute_import
import glob
import logging
import logging.config
import os

import click

from foist import (add_file_metadata, add_thesis_item_file, commit_transaction,
                   create_pcdm_relationships, create_thesis_item_container,
                   parse_text_encoding_errors, start_transaction, ThesisItem)


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
            'level': 'INFO',
            'handlers': ['console', 'file']
        }
    }
})


@click.group()
def main():
    pass


@main.command()
@click.argument('directory', type=click.Path(exists=True, file_okay=False,
                                             resolve_path=True))
def process_metadata(directory):
    '''Parse metadata for all thesis items in a directory.

    This script traverses the given DIRECTORY of thesis files and for each
    thesis creates a turtle file of metadata statements and SPARQL update
    files for each file representation of the thesis.
    '''
    error_file = glob.glob(os.path.join(directory, '*.tab'))[0]
    text_encoding_errors = parse_text_encoding_errors(error_file)
    dirnames = next(os.walk(os.path.join(directory, '.')))[1]
    count = 0
    for d in dirnames:
        thesis = ThesisItem(d, directory)
        thesis.add_text_errors(text_encoding_errors)
        thesis.create_item_turtle_statements()
        thesis.create_file_sparql_update('.pdf')
        thesis.create_file_sparql_update('-new.txt')
        count += 1
    logger.info('TOTAL: %s theses processed in folder %s' % (str(count),
                                                             directory))


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
    file_count = 0
    error_count = 0
    for d in dirnames:
        turtle = os.path.join(directory, d, d + '.ttl')
        pdf = os.path.join(directory, d, d + '.pdf')
        text = os.path.join(directory, d, d + '-new.txt')
        try:
            t = start_transaction(fedora_uri)
            tt = t + '/theses/'
            if create_thesis_item_container(tt, d, turtle) == 'Success':
                if add_thesis_item_file(tt, d, '.pdf', 'application/pdf',
                                        pdf) == 'Success':
                    add_file_metadata(tt, d, '.pdf', pdf)
                    file_count += 1
                # TODO: Check for 'no_full_text' field in metadata and only do
                # the following if field is not present
                if add_thesis_item_file(tt, d, '.txt', 'text/plain',
                                        text) == 'Success':
                    add_file_metadata(tt, d, '.txt', text)
                    file_count += 1
                create_pcdm_relationships(tt, d)
                thesis_count += 1
            commit_transaction(t)
        except FileNotFoundError as e:
            log.error(e)
            error_count += 1
    logger.info(('TOTAL: %s theses ingested, %s files ingested. %s theses '
                 'not ingested.\n') % (thesis_count, file_count, error_count))


if __name__ == '__main__':
    main()
