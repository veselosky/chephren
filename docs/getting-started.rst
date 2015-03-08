.. article:: 2015-03-01

Using Indexes
==========================

Chephren uses Sphinx's indexing mechanism to do the heavy lifting. To add a page
to an index, use one of the directives Chephren provides. The indexes are 
rendered using the ``domainindex.html`` template, which you can override in
your theme.

.. rst:directive:: .. article:: YYYY-MM-DD

    Marks the document as an article to be added to the chronological index. The
    date argument must be in :RFC:`3339` format (the One True Date Format). If
    desired, you may also include a time component.
