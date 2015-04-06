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
This module contains a Sphinx Domain for web sites.

Some clues for developers
===============================

This domain uses Sphinx's indexing infrastructure to create a catalog of
blog posts. That catalog is then used to produce standard web site features
like category pages and RSS feeds. As with other domains, the index data
is all stored in ``domain.data``. The indexing system is designed to index
abstract objects that are being documented. We are making the document
itself be the object.

During HTML generation, Sphinx automatically produces pages for each index.
These become our Archive pages.

It turns out domain index pages are not referencable using the standard ``ref``
role, because the ref role is implemented by the "std" domain. Python index
pages are referencable that way only because the std domain is hard coded to
know things about the Python domain. To make its index pages referencable,
we have added the ``archive`` role.
"""
import os.path
import codecs
from collections import namedtuple
from dateutil.parser import parse as parse_datetime
from docutils import nodes

from pytz import timezone
from sphinx.domains import Domain, Index, ObjType
from sphinx.directives import Directive, directives
from sphinx.locale import l_
from sphinx.roles import XRefRole as SphinxXRefRole
from sphinx.util.nodes import make_refnode
from sphinx.util.osutil import ensuredir
from werkzeug.contrib.atom import AtomFeed


"""We create a namedtuple called ``IndexEntry`` for the standard indexing
data structure, for ease of reading."""
IndexEntry = namedtuple('IndexEntry',
    "title, subtype, docname, target, extra, qualifier, description"
)  # noqa


class XRefRole(SphinxXRefRole):
    innernodeclass = nodes.emphasis


class ArticleNode(nodes.Invisible, nodes.Element):
    """ArticleNode holds our metadata in the document tree."""
    pass


def _split(a):
    return [s.strip() for s in (a or '').split(',') if s.strip()]


class ArticleDirective(Directive):
    """ArticleDirective allows writers to assign metadata for indexing.

    A document is marked as interesting to this domain using the ``article``
    directive. The ``article`` directive provides the metadata used for
    indexing the document, though for some standard fields we examine the
    document itself. The article directive leaves no trace in the output, it
    is purely there to provide metadata to the indexing system.
    """

    has_content = True
    required_arguments = 0
    optional_arguments = 1
    final_argument_whitespace = True
    option_spec = {
        'author': _split,
        'category': _split,
        'image': int,
        'language': _split,
        'noindex': directives.flag,
        'tags': _split,
    }

    def run(self):
        self.env = self.state.document.settings.env
        node = ArticleNode()
        self.state.nested_parse(self.content, self.content_offset,
                                node, match_titles=1)

        # TODO Clean and validate these values here.
        node['date'] = self.arguments[0] if self.arguments else None
        node['author'] = self.options.get('author', '')
        node['category'] = self.options.get('category', [])
        node['image'] = self.options.get('image', None)
        node['language'] = self.options.get('language', '')
        node['noindex'] = self.options.get('noindex', False)
        node['tags'] = self.options.get('tags', [])

        return [node]


# TODO implement Year, Month, and Date indexes.
class ChronologicalIndex(Index):
    name = 'bydate'
    localname = 'By Date'
    shortname = 'by date'

    def add_article(self, article, entry, doctree):
        """Add an article object to this index. To be called from the
        domain's ``process_doc`` method.
        """
        by_date = self.domain.data['by_date']

        if 'updated' in article:
            when = self.domain.as_datetime(article['updated'])
        else:
            when = self.domain.as_datetime(article['date'])

        datekey = when.strftime('%Y-%m')
        if datekey in by_date:
            by_date[datekey].append((when.isoformat(), entry))
        else:
            by_date[datekey] = [(when.isoformat(), entry)]

    def sorted_entries(self, pairs, reverse=False):
        return [
            e[1] for e in sorted(pairs,
                                 cmp=lambda a, b: cmp(a[0], b[0]),
                                 reverse=reverse
                                 )
        ]

    def generate(self, docnames=None):
        # FIXME implement docnames filter
        dates = self.domain.data['by_date']
        entries_for_date = []
        for date in sorted(dates, reverse=True):
            entries_for_date.append((date,
                                     self.sorted_entries(dates[date],
                                                         reverse=True)))
        return (entries_for_date, True)

    def get_recent(self, limit=25):
        """Return the index entries for the most recent ``limit`` articles."""
        dates = self.domain.data['by_date']
        entries = []
        for date in sorted(dates, reverse=True):
            for entry in self.sorted_entries(dates[date], reverse=True):
                entries.append(entry)
                if len(entries) >= limit:
                    break
            else:  # executed if the loop ended normally (no break)
                continue  # continues the outer loop
            break  # breaks outer loop if inner loop had break

        return entries


class CategoryIndex(Index):
    name = 'bycategory'
    localname = 'By Category'
    shortname = 'by category'

    def add_article(self, article, entry, doctree):
        """Add an article object to this index. To be called from the
        domain's ``process_doc`` method.
        """
        if 'category' not in article or not article['category']:
            return

        by_cat = self.domain.data['by_category']
        if 'updated' in article:
            when = self.domain.as_datetime(article['updated'])
        else:
            when = self.domain.as_datetime(article['date'])

        for ixkey in article['category']:
            if ixkey in by_cat:
                by_cat[ixkey].append((when.isoformat(), entry))
            else:
                by_cat[ixkey] = [(when.isoformat(), entry)]

    def sorted_entries(self, pairs, reverse=False):
        return [
            e[1] for e in sorted(pairs,
                                 cmp=lambda a, b: cmp(a[0], b[0]),
                                 reverse=reverse
                                 )
        ]

    def generate(self, docnames=None):
        # FIXME implement docnames filter
        cats = self.domain.data['by_category']
        entries_for_cat = []
        for cat in sorted(cats):
            entries_for_cat.append((cat,
                                   self.sorted_entries(cats[cat],
                                                       reverse=True)))
        return (entries_for_cat, True)

    def get_recent(self, category, limit=25):
        """Return the index entries for the most recent ``limit`` articles."""
        cats = self.domain.data['by_category']
        entries = []
        for entry in self.sorted_entries(cats[category], reverse=True):
            entries.append(entry)
            if len(entries) >= limit:
                break

        return entries


class BlogDomain(Domain):
    name = "blog"
    label = "Blog"

    object_types = {'article': ObjType(l_('article'), 'article')}
    directives = {
        'article': ArticleDirective,
        'blogpost': ArticleDirective,
        'post': ArticleDirective,
    }
    roles = {'blogpost': XRefRole(), 'archive': XRefRole()}

    # Note: affected by html_domain_indices setting
    indices = [ChronologicalIndex, CategoryIndex]

    initial_data = {
        'articles': {},  # docname -> ixentry
        'by_date': {},  # date -> date, ixentry
        'by_category': {},  # category -> date, ixentry
    }

    def as_datetime(self, datestr):
        """Parse a string to produce a timezone-aware datetime."""
        zone = timezone(self.env.config.timezone)
        thedate = parse_datetime(datestr)  # raises ValueError on fail
        # Really, we can't have one function that can deal with both?
        if thedate.tzinfo:
            return thedate.astimezone(zone)
        elif thedate:
            return zone.localize(thedate)

    def make_index_entry_for(self, docname, doctree):
        """Generates an IndexEntry structure for a given document."""
        meta = self.env.metadata[docname]
        # FIXME possible to have no title? Metadata overrides?
        title = doctree.next_node(nodes.title).astext()
        target = doctree.next_node(nodes.section)['ids'][0]
        if 'updated' in meta:
            extra = 'updated ' + \
                    self.as_datetime(meta['updated']).date().isoformat()
        else:
            extra = self.as_datetime(meta['date']).date().isoformat()

        qualifier = ''
        description = meta['description'] if 'description' in meta else ''
        return IndexEntry(title, 0, docname, target,
                          extra, qualifier, description)

    def process_doc(self, env, docname, doctree):
        """Adds documents to the domain indexes.

        The domain is given the chance to visit each document just before the
        doctree-read event fires. We use this opportunity to
        examine the document for relevant metadata and add it to the catalog.

        """
        env.app.debug("[BLOG] processing doc %s" % docname)
        article_node = doctree.next_node(ArticleNode)
        if not article_node:
            env.app.debug("[BLOG] skipping non-article %s" % docname)
            return

        # Extract metadata from the doc and stash it in Sphinx's meta.
        meta = env.metadata[docname]
        # mark as 'orphan' so that "document isn't included in any toctree"
        # warning is not issued. Q: can/should we check the toctrees first?
        meta['orphan'] = True
        meta['is_article'] = True
        for metavar, value in article_node.attlist():
            meta[metavar] = value
        if 'description' not in meta:
            meta['description'] = article_node.astext()

        # Create the index entry
        entry = self.make_index_entry_for(docname, doctree)
        self.data['articles'][docname] = entry
        for index in self.indices:
            if hasattr(index, 'add_article'):
                env.app.debug("[BLOG] adding to index %s" % index.name)
                index(self).add_article(article_node, entry, doctree)

        # These nodes have no output, just remove them
        article_node.replace_self([])

    def clear_doc(self, docname):
        """TODO clear_doc"""

    def resolve_xref(self, env, fromdocname, builder,
                     typ, target, node, contnode):
        """Called to resolve the targets for ref roles in this domain.

        When Sphinx encounters a role that is registered by this domain,
        it calls ``resolve_xref`` so that the domain can resolve the
        reference. If you don't do this correctly, links don't work.
        """
        builder.app.debug("[BLOG] Asked to resolve %s of type %s from %s" %
                          (target, typ, fromdocname))
        if target in self.data['articles']:
            name = self.data['articles'].title
            return make_refnode(builder, fromdocname, target, target,
                                contnode, name)
        if target.startswith(self.name):  # domain index
            name = 'By Date'  # FIXME Get name from index class
            return make_refnode(builder, fromdocname, target, '',
                                contnode, name)

    def resolve_any_xref(self, env, fromdocname, builder, target,
                         node, contnode):
        builder.app.debug("[BLOG] Asked to resolve ANY %s from %s" %
                          (target, fromdocname))

    @staticmethod
    def on_missing_reference(app, env, node, contnode):
        app.debug("[BLOG] Missing ref %s of type %s" %
                  (node['reftarget'], node['reftype']))

    @staticmethod
    def on_builder_inited(app):
        """Create the feed container"""
        feed = AtomFeed(app.config.project,
                        feed_url=app.config.base_url,
                        id=app.config.base_url,
                        )
        feed.author = app.config.feed_author
        feed.summary = app.config.project_description

        if app.config.copyright:
            feed.rights = app.config.copyright

        data = app.env.domaindata[BlogDomain.name]
        data['mainfeed'] = feed
        if not hasattr(data, 'feeditems'):
            data['feeditems'] = {}

    @staticmethod
    def on_html_page_context(app, pagename, templatename, ctx, doctree):
        """Here we have access to fully resolved and rendered HTML fragments
        as well as metadata.
        """
        if app.builder.name != 'html':
            return

        self = app.env.domains[BlogDomain.name]
        # Index pages and such don't necessarily have metadata
        metadata = app.env.metadata.get(pagename, {})
        if 'is_article' not in metadata:
            return

        item = {'title': ctx.get('title'),
                'url': app.config.base_url + '/' +
                ctx['current_page_name'] + ctx['file_suffix'],
                'content': ctx.get('body'),
                'updated': self.as_datetime(metadata['date'])
                }
        if 'author' in metadata:
            item['author'] = metadata['author']

        app.env.domaindata[BlogDomain.name]['feeditems'][pagename] = item

        # provide templates with a way to link to the rss output file
        # FIXME This should be structured the same as next and previous
        ctx['rss_link'] = app.config.base_url + '/' + app.config.feed_filename

        app.debug("[SITE] added context for %s" % pagename)

    @staticmethod
    def on_build_finished(app, exc):
        """Handler for the build-finished event to output atom feeds.

        Field mappings, atom to internal:
        feed.title: site title
        feed.updated: time of file generation
        feed.id: a generated TAG-URI
        feed.author: from conf
        feed.link(rel=self): resolve URI
        feed.link(rel=alternate): calculate depending on feed.
        feed.category: from conf?
        feed.contributor: from conf
        feed.rights: from conf
        feed.subtitle: from conf
        feed.icon: from conf
        feed.logo: from conf

        entry.title: document title
        entry.updated: meta.updated or meta.date
        entry.id: a generated TAG URI
        entry.summary: meta.summary or auto (if configured) or none
        entry.link(rel=self): resolve URI
        entry.content: the content (if configured)
        entry.author: meta.author
        entry.published: meta.date
        entry.category: category or tags?
        entry.rights: from conf, inherit
        """
        if app.builder.name != 'html':
            return
        if not app.config.feed_filename:
            return

        domain = app.env.domains[BlogDomain.name]
        feed = domain.data['mainfeed']
        index = ChronologicalIndex(domain)
        ixentries = index.get_recent()
        for ix in ixentries:
            feed.add(**domain.data['feeditems'][ix.docname])

        filepath = os.path.join(app.builder.outdir,
                                app.config.feed_filename)
        ensuredir(os.path.dirname(filepath))
        outfile = codecs.open(filepath, 'w', 'utf-8')
        try:
            outfile.write(feed.to_string())
        finally:
            outfile.close()
