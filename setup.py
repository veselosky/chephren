#!/usr/bin/env python
from setuptools import setup, find_packages
from setuptools.command.test import test as TestCommand
import sys
from chephren import __version__


class PyTest(TestCommand):
    """Command class to allow `setup.py test` to run py.test.

    http://pytest.org/latest/goodpractises.html#integration-with-setuptools-distribute-test-commands
    """
    def finalize_options(self):
        TestCommand.finalize_options(self)
        self.test_args = []
        self.test_suite = True

    def run_tests(self):
        # import here, because outside the eggs aren't loaded
        import pytest
        errno = pytest.main(self.test_args)
        sys.exit(errno)


with open('README.rst') as thefile:
    README = thefile.read()

setup(
    name="chephren",
    version=__version__,
    packages=find_packages(),
    author="Vince Veselosky",
    author_email="vince@veselosky.com",
    description="An extension to Sphinx for managing a blog or static website",
    long_description=README,
    license="Apache 2.0",
    url="",
    # could also include download_url, classifiers, etc.

    install_requires=[
        'werkzeug >= 0.10',
        'python-dateutil',
        'pytz',
        'sphinx >= 1.3.0',
    ],
    tests_require=[
        'pytest',
    ],
    cmdclass={'test': PyTest},
    classifiers=[
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: Apache Software License',
    ],
)
