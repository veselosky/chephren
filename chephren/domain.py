"""
This module contains a Sphinx Domain for web sites.

Some clues for developers
===============================

This domain uses Sphinx's indexing infrastructure to create a catalog of
articles. That catalog is then used to produce standard web site features
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
from docutils import nodes
from sphinx.domains import Domain, Index, ObjType
from sphinx.directives import Directive, directives
from sphinx.locale import l_
from sphinx.roles import XRefRole as SphinxXRefRole
from sphinx.util.nodes import make_refnode


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


# TODO implement Year, Month, and Date indexes. Parse date correctly.
class ChronologicalIndex(Index):
    name = 'bydate'
    localname = 'By Date'
    shortname = 'by date'

    def add_article(self, article, entry, doctree):
        """Add an article object to this index. To be called from the
        domain's ``process_doc`` method.
        """
        by_date = self.domain.data['by_date']
        if article['date'] in by_date:
            by_date[article['date']].append(entry)
        else:
            by_date[article['date']] = [entry]

    def generate(self, docnames=None):
        # FIXME implement docnames filter
        dates = self.domain.data['by_date']
        entries_for_date = []
        for date in sorted(dates):
            entries_for_date.append((date, dates[date]))
        return (entries_for_date, True)

    def get_recent(self, limit=25):
        """Return the index entries for the most recent ``limit`` articles."""
        dates = self.domain.data['by_date']
        entries = []
        for date in sorted(dates):
            for entry in dates[date]:
                entries.append(entry)
                if len(entries) >= limit:
                    break
            else:  # executed if the loop ended normally (no break)
                continue  # continues the outer loop
            break  # breaks outer loop if inner loop had break

        return entries


class WebsiteDomain(Domain):
    name = "website"
    label = "Website"

    object_types = {'article': ObjType(l_('article'), 'article')}
    directives = {'article': ArticleDirective}
    roles = {'article': XRefRole(), 'archive': XRefRole()}

    # Note: affected by html_domain_indices setting
    indices = [ChronologicalIndex]

    initial_data = {
        'articles': {},  # docname -> ixentry
        'by_date': {},  # date -> docname, objtype
    }

    def make_index_entry_for(self, docname, doctree):
        """Generates an IndexEntry structure for a given document."""
        # FIXME possible to have no title? Metadata overrides?
        title = doctree.next_node(nodes.title).astext()
        target = doctree.next_node(nodes.section)['ids'][0]
        extra = ''
        qualifier = ''
        description = ''  # TODO Set description
        return IndexEntry(title, 0, docname, target,
                          extra, qualifier, description)

    def process_doc(self, env, docname, doctree):
        """Adds documents to the domain indexes.

        The domain is given the chance to visit each document just before the
        doctree-read event fires. We use this opportunity to
        examine the document for relevant metadata and add it to the catalog.

        """
        self.env = env
        env.app.debug("[Website] processing doc %s" % docname)
        article_node = doctree.next_node(ArticleNode)
        if not article_node:
            return

        # Create the index entry
        entry = self.make_index_entry_for(docname, doctree)
        self.data['articles'][docname] = entry
        for index in self.indices:
            if hasattr(index, 'add_article'):
                index(self).add_article(article_node, entry, doctree)

        # Extract metadata from the doc and stash it in Sphinx's meta.
        meta = env.metadata[docname]
        # mark as 'orphan' so that "document isn't included in any toctree"
        # warning is not issued. Q: can/should we check the toctrees first?
        meta['orphan'] = True
        meta['is_article'] = True
        for metavar, value in article_node.attlist():
            meta[metavar] = value

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
        builder.app.debug("[Website] Asked to resolve %s of type %s from %s" %
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
        builder.app.debug("[Website] Asked to resolve ANY %s from %s" %
                          (target, fromdocname))

    @staticmethod
    def on_missing_reference(app, env, node, contnode):
        app.debug("[Website] Missing ref %s of type %s" %
                  (node['reftarget'], node['reftype']))

    @staticmethod
    def on_builder_inited(app):
        """Create the feed container"""
        from werkzeug.contrib.atom import AtomFeed
        feed = AtomFeed(app.config.project,
                        feed_url=app.config.base_url,
                        id=app.config.base_url,
                        )
        feed.author = app.config.feed_author
        feed.summary = app.config.project_description

        if app.config.copyright:
            feed.rights = app.config.copyright

        data = app.env.domaindata[WebsiteDomain.name]
        data['mainfeed'] = feed
        if not hasattr(data, 'feeditems'):
            data['feeditems'] = {}

    @staticmethod
    def on_html_page_context(app, pagename, templatename, ctx, doctree):
        """Here we have access to fully resolved and rendered HTML fragments
        as well as metadata.
        """
        from datetime import datetime
        if app.builder.name != 'html':
            return

        def parse_pubdate(pubdate):
            try:
                date = datetime.strptime(pubdate, '%Y-%m-%d %H:%M')
            except ValueError:
                date = datetime.strptime(pubdate, '%Y-%m-%d')
            return date

        # Index pages and such don't necessarily have metadata
        metadata = app.env.metadata.get(pagename, {})
        if 'is_article' not in metadata:
            return

        item = {'title': ctx.get('title'),
                'url': app.config.base_url + '/' +
                ctx['current_page_name'] + ctx['file_suffix'],
                'content': ctx.get('body'),
                'updated': parse_pubdate(metadata['date'])
                }
        if 'author' in metadata:
            item['author'] = metadata['author']

        app.env.domaindata[WebsiteDomain.name]['feeditems'][pagename] = item

        # provide templates with a way to link to the rss output file
        ctx['rss_link'] = app.config.base_url + '/' + app.config.feed_filename

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

        domain = app.env.domains[WebsiteDomain.name]
        feed = domain.data['mainfeed']
        index = ChronologicalIndex(domain)
        ixentries = index.get_recent()
        for ix in ixentries:
            feed.add(**domain.data['feeditems'][ix.docname])

        path = os.path.join(app.builder.outdir,
                            app.config.feed_filename)
        outfile = codecs.open(path, 'w', 'utf-8')
        try:
            outfile.write(feed.to_string())
        finally:
            outfile.close()
