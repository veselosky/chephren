Chephren
=============================================================================

.. Description of project goes here. This file will also be slurped by
    setup.py and used as long_description, which means this will be the home
    page on PyPI.

:Description: An extension to Sphinx for managing blogs and static websites.
:Status: Alpha - incomplete, backwards incompatible changes likely
:Python Support: 2.7, further compatibility to come in beta

Chephren is an extension for `Sphinx`_ that adds features for managing static
websites that are not software documentation. Sphinx is a great tool for
documenting software projects, but it is missing some common features that
would make it just as good for managing static websites. Features provided by
Chephren include:

* Marking a distinction between "posts" and utility pages like the search or about page
* Allow posts to bypass the "not found in any toctree" warning
* RSS feed for your posts
* Date-based archive page for your posts
* A category system with an archive listing posts by category

.. _`Sphinx`: http://sphinx-doc.org/

What's Missing
-----------------------------------------------------------------------------

Lots of planned features don't yet exist, even features you might expect.
Here's a list of things you cannot do (yet).

* Rename the archive pages (you're stuck with blog-bydate and blog-bycategory
  for now)
* Create a separate page for each category
* Paginate the feed
* Produce a feed in any format except Atom (but Atom is widely supported)
* Create a traditional-looking blog home page (without custom coding anyway)
* Apply a custom template to a post

Copyright and License
-----------------------------------------------------------------------------

Copyright 2015 Vincent Veselosky and contributors.

Unless otherwise noted, files in this distribution are licensed under the
Apache License, Version 2.0 (the "License"); you may not use these files
except in compliance with the License.

You may obtain a copy of the License at
http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

Documentation and non-software assets included in this distribution are
licensed under `Creative Commons Attribution 4.0 International License
<http://creativecommons.org/licenses/by/4.0/>`_.
