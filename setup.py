#!/usr/bin/env python

from setuptools import setup

setup(
    name='Chez Tache',
    version='0.0.1',
    description='A home for your tasks. A task manager.',
    author='Kelvin Hammond',
    author_email='hammond.kelvin@gmail.com',
    url='',
    packages=['chez.tache'],
    platforms='any',
    entry_points={
        'console_scripts': [
            'ct = chez.tache.commands:cli',
        ]
    },
)
