"""
This module contains the Sphinx extension.
"""

from .domain import WebsiteDomain


def setup(app):
    app.add_domain(WebsiteDomain)
