# -*- coding: utf-8 -*-

'''


Created on  2018-7-31

@author: Aaron Kitzmiller <aaron_kitzmiller@harvard.edu>
@copyright: 2018 The Presidents and Fellows of Harvard College. All rights reserved.
@license: GPL v2.0
'''

from setuptools import setup, find_packages
import re


def getVersion():
    version = '0.0.0'
    with open('odybcl2fastq/__init__.py', 'r') as f:
        contents = f.read().strip()

    m = re.search(r"__version__ = '([\d\.]+)'", contents)
    if m:
        version = m.group(1)
    return version


setup(
    name="odybcl2fastq",
    version=getVersion(),
    author='Meghan Correa <mportermahoney@g.harvard.edu>, Adam Freedman <afreedman@g.harvard.edu>, Aaron Kitzmiller <aaron_kitzmiller@harvard.edu>',
    author_email='mportermahoney@g.harvard.edu',
    description='bcl2fastq runner for Bauer Sequencing Core',
    license='LICENSE.txt',
    include_package_data=True,
    url='https://https://github.com/harvardinformatics/odybcl2fastq',
    packages=find_packages(),
    package_data={'odybcl2fastq': ['templates/*.html']},
    long_description='bcl2fastq runner for Bauer Sequencing Core',
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Topic :: Utilities",
    ],
    entry_points={
        'console_scripts': [
            'odybcl2fastq=odybcl2fastq.run:bcl2fastq_process_runs',
            'odybcl2fastqProcessRuns=odybcl2fastq.process_runs:main',
            'storage_mgmt=odybcl2fastq.storage_mgmt:manage_storage',
            'load_runs=odybcl2fastq.load_runs:main',
            'centrifugeProcessRuns=odybcl2fastq.centrifuge_process_runs:main',
        ]
    },
    scripts=[
        'odybcl2fastqProcessRuns.sh'
    ],
    install_requires=[
        'Jinja2>=2.2.1',
        'MySQL-python>=1.2.5',
        'argparse>=1.4.0',
        'numpy==1.6.1',
        'requests>=2.19.1',
        'nose',
    ],
    test_requires=[
    ]
)
