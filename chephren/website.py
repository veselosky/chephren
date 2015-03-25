# Copyright 2015 Vince Veselosky and contributors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
This module contains the Sphinx extension.
"""

from .domain import BlogDomain


def setup(app):
    app.add_domain(BlogDomain)
    app.add_config_value('base_url', '', '')
    app.add_config_value('project_description', '', '')
    app.add_config_value('feed_author', '', '')
    app.add_config_value('feed_filename', 'recent.atom', 'html')
    app.add_config_value('timezone', 'UTC', '')

    app.connect('builder-inited', BlogDomain.on_builder_inited)
    app.connect('html-page-context', BlogDomain.on_html_page_context)
    app.connect('build-finished', BlogDomain.on_build_finished)
    app.connect('missing-reference', BlogDomain.on_missing_reference)

