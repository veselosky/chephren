"""
This module contains a Sphinx Domain for web sites.
"""
import os.path
import codecs
from collections import namedtuple
from docutils import nodes
from sphinx.domains import Domain, Index, ObjType
from sphinx.directives import Directive, directives
from sphinx.locale import l_
from sphinx.roles import XRefRole


IndexEntry = namedtuple('IndexEntry',
    "title, subtype, docname, target, extra, qualifier, description"
)  # noqa


class ArticleNode(nodes.Invisible, nodes.Element):
    """Represent article directive content and options in document tree."""
    pass


def _split(a):
    return [s.strip() for s in (a or '').split(',') if s.strip()]


class ArticleDirective(Directive):
    """Handle ``article`` directives."""

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
    roles = {'article': XRefRole()}

    # Note: affected by html_domain_indices setting
    indices = [ChronologicalIndex]

    initial_data = {
        'by_date': {},  # date -> docname, objtype
    }

    def make_index_entry_for(self, docname, doctree):
        """Generate an IndexEntry structure for a given document."""
        # FIXME possible to have no title? Metadata overrides?
        title = doctree.next_node(nodes.title).astext()
        # FIXME. References not resolved yet. Header targets not in place.
        # May not be any. May need to call from doctree-resolved event.
        target = doctree.next_node(nodes.target)['ids'][0]
        extra = ''
        qualifier = ''
        description = ''  # TODO Set description
        return IndexEntry(title, 0, docname, target, extra, qualifier, description)

    def process_doc(self, env, docname, doctree):
        self.env = env
        article_node = doctree.next_node(ArticleNode)
        if not article_node:
            return

        # Create the index entry
        entry = self.make_index_entry_for(docname, doctree)
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
        if not hasattr(data, 'mainfeed_items'):
            data['mainfeed_items'] = {}

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
                'url': app.config.base_url + '/' + ctx['current_page_name'] + ctx['file_suffix'],
                'content': ctx.get('body'),
                'updated': parse_pubdate(metadata['date'])
                }
        if 'author' in metadata:
            item['author'] = metadata['author']

        app.env.domaindata[WebsiteDomain.name]['mainfeed_items'][pagename] = item

        # provide templates with a way to link to the rss output file
        ctx['rss_link'] = app.config.base_url + '/' + app.config.feed_filename

    @staticmethod
    def on_build_finished(app, exc):
        if app.builder.name != 'html':
            return

        domain = app.env.domains[WebsiteDomain.name]
        feed = domain.data['mainfeed']
        index = ChronologicalIndex(domain)
        ixentries = index.get_recent()
        for ix in ixentries:
            feed.add(**domain.data['mainfeed_items'][ix.docname])

        path = os.path.join(app.builder.outdir,
                            app.config.feed_filename)
        outfile = codecs.open(path, 'w', 'utf-8')
        try:
            outfile.write(feed.to_string())
        finally:
            outfile.close()


def generate_atom_feeds(app):
    """Handler for the html-collect-pages event to output atom feeds.

    Field mappings, atom to internal:
    feed.title: site title
    feed.updated: time of file generation
    feed.id: a generated TAG-URI
    feed.author: from conf
    feed.link(rel=self): resolve URI
    feed.link(rel=alternate): calculate depending on feed. site url, category page, etc.
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
    # must return (pagename, context, templatename)
    # domain = app.env.domains[WebsiteDomain.name]
