"""
This module contains the Sphinx extension.
"""

from .domain import WebsiteDomain


def setup(app):
    app.add_domain(WebsiteDomain)
    app.add_config_value('base_url', '', '')
    app.add_config_value('project_description', '', '')
    app.add_config_value('feed_author', '', '')
    app.add_config_value('feed_filename', 'recent.atom', 'html')

    app.connect('builder-inited', WebsiteDomain.on_builder_inited)
    app.connect('html-page-context', WebsiteDomain.on_html_page_context)
    app.connect('build-finished', WebsiteDomain.on_build_finished)

