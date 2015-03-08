"""
This module contains a Sphinx Domain for web sites.
"""
from docutils import nodes
from sphinx.domains import Domain, Index, ObjType
from sphinx.directives import Directive, directives
from sphinx.locale import l_
from sphinx.roles import XRefRole


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

        node['date'] = self.arguments[0] if self.arguments else None
        node['author'] = self.options.get('author', [])
        node['category'] = self.options.get('category', [])
        node['image'] = self.options.get('image', None)
        node['language'] = self.options.get('language', [])
        node['noindex'] = self.options.get('noindex', False)
        node['tags'] = self.options.get('tags', [])

        return [node]


class ChronologicalIndex(Index):
    name = 'bydate'
    localname = 'By Date'
    shortname = 'by date'

    def generate(self, docnames=None):
        dates = self.domain.data['by_date']
        entries_for_date = []
        for date in sorted(dates):
            entries_for_date.append((date, dates[date]))
        return (entries_for_date, True)


class WebsiteDomain(Domain):
    name = "website"
    label = "Website"

    object_types = {
        'article': ObjType(l_('article'), 'article'),
    }

    directives = {'article': ArticleDirective}
    roles = {'article': XRefRole()}

    # TODO Add a setting for which indexes to generate
    # TODO Set indices in __init__ based on setting
    indices = [ChronologicalIndex]

    initial_data = {
        'by_date': {},  # date -> docname, objtype
    }

    def process_doc(self, env, docname, doctree):
        article_node = doctree.next_node(ArticleNode)
        if not article_node:
            return

        # Create the index entry
        docname = env.docname
        # possible to have no title?
        title = doctree.next_node(nodes.title).astext()
        # possible to have no targets?
        target = doctree.next_node(nodes.target)['ids'][0]
        extra = ''
        qualifier = ''
        description = ''  # TODO Set description
        entry = (title, 0, docname, target, extra, qualifier, description)

        by_date = self.data['by_date']
        if article_node['date'] in by_date:
            by_date[article_node['date']].append(entry)
        else:
            by_date[article_node['date']] = [entry]

        # mark as 'orphan' so that "document isn't included in any toctree"
        # warning is not issued. Q: can/should we check the toctrees first?
        env.metadata[docname]['orphan'] = True

        # These nodes have no output, just remove them
        article_node.replace_self([])
