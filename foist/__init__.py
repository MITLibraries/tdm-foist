# -*- coding: utf-8 -*-
"""
FOIST
"""

from .app import (add_file_metadata, add_thesis_item_file,
                  create_pcdm_relationships, create_theses_container,
                  create_thesis_item_container, initialize_custom_prefixes,
                  parse_text_encoding_errors, Thesis, transaction,
                  upload_thesis)

__version__ = '0.1.0'
