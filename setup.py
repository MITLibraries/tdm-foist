# -*- coding: utf-8 -*-

'''
FOIST
=========
Fedora Object Ingest Service for Theses.
'''

import io
import re
from setuptools import find_packages, setup

with io.open('LICENSE') as f:
    license = f.read()


with io.open('foist/__init__.py', 'r') as fp:
    version = re.search(r'^__version__\s*=\s*[\'"]([^\'"]*)[\'"]', fp.read(),
                        re.MULTILINE).group(1)

setup(
    name='foist',
    version=version,
    description='Fedora Object Ingest Service for Theses',
    url='https://github.com/mitlib-tdm/foist',
    long_description=__doc__,
    license=license,
    author='Helen Bailey',
    author_email='hbailey@mit.edu',
    packages=find_packages(exclude=['tests']),
    install_requires=[
        'click',
        'rdflib',
        'requests',
    ],
    entry_points={
        'console_scripts': [
            'foist=foist.cli:main',
        ]
    },
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Programming Language :: Python :: 3.4',
    ],
)
