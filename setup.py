#!/usr/bin/env python

import sys
import os
try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup


import webclient

setup(name='webcleint',
      version=webclient.__version__,
      description='simple Web Client.',
      url='https://github.com/thomashuang/webclient',
      py_modules=['webclient'],
      license='GPL',
      platforms = 'any',
      classifiers=['Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GPL License',
        'Topic :: Internet :: WWW/HTTP :: HTTP  WEB Client',
        'Programming Language :: Python :: 2.5',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.2',
        'Programming Language :: Python :: 3.3',
        ],
     )
