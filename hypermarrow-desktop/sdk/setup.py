from setuptools import setup, find_packages
import os, re

version = '2.1.9'

setup(
    name='hypermarrow-client',
    version=version,
    description='HyperMarrow AI memory & learning system — lightweight client SDK',
    long_description='HyperMarrow AI memory & learning system — lightweight client SDK',
    long_description_content_type='text/plain',
    author='OpenClaw Team',
    url='https://hm.qianshi.cool',
    packages=find_packages(),
    python_requires='>=3.8',
    install_requires=[],
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: Other/Proprietary License',
        'Operating System :: OS Independent',
    ],
)
