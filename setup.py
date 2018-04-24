#!/usr/bin/env python2

from setuptools import setup, find_packages

setup(name='git_activity',
      version='0.9',
      description='Git activity display tool',
      author='tafryn',
      author_email='tafryn@gmail.com',
      url='https://github.com/tafryn/git_activity',
      scripts=['git_activity.py'],
      install_requires=['GitPython>=2.1.8', 'terminaltables>=3.1.0', 'colored>=1.3.5', 'pyparsing>=1.5.6'],
     )
