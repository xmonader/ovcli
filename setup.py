#!/usr/bin/env python3
from setuptools import setup

setup(name='ovcli',
      version='0.2',
      description='OpenvCloud command line client',
      author='Jo De Boeck',
      author_email='deboeck.jo@gmail.com',
      url='http://github.com/grimpy/ovcli',
      install_requires=['prompt-toolkit'],
      packages=['ovcli'],
      entry_points={'console_scripts': ['ovcli=ovcli.__main__:main', 'ovcsh=ovcli.shell:main']}
      )
