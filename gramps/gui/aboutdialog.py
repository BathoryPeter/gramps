#
# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2008  Zsolt Foldvari
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#

"About dialog"

#-------------------------------------------------------------------------
#
# Python modules
#
#-------------------------------------------------------------------------
import os
import sys
import io
import bsddb3 as bsddb

##import logging
##_LOG = logging.getLogger(".GrampsAboutDialog")

try:
    from xml.sax import make_parser, handler, SAXParseException
except ImportError:
    from _xmlplus.sax import make_parser, handler, SAXParseException

#-------------------------------------------------------------------------
#
# Gtk modules
#
#-------------------------------------------------------------------------
from gi.repository import GObject
from gi.repository import Gtk
from gi.repository import GdkPixbuf

#-------------------------------------------------------------------------
#
# GRAMPS modules
#
#-------------------------------------------------------------------------
from gramps.gen.const import (AUTHORS, AUTHORS_FILE, COMMENTS, COPYRIGHT_MSG, 
                       DOCUMENTERS, LICENSE_FILE, PROGRAM_NAME, SPLASH, 
                       URL_HOMEPAGE, VERSION)
from gramps.gen.const import GRAMPS_LOCALE as glocale
_ = glocale.translation.gettext
from gramps.gen.constfunc import get_env_var
from .display import display_url

#-------------------------------------------------------------------------
#
# GrampsAboutDialog
#
#-------------------------------------------------------------------------
class GrampsAboutDialog(Gtk.AboutDialog):
    """Create an About dialog with all fields set."""
    def __init__(self, parent):
        """Setup all the fields shown in the About dialog."""
        Gtk.AboutDialog.__init__(self)
        self.set_transient_for(parent)
        self.set_modal(True)
        
        self.set_name(PROGRAM_NAME)
        self.set_version(VERSION)
        self.set_copyright(COPYRIGHT_MSG)
        artists = _("Much of Gramps' artwork is either from\n"
                    "the Tango Project or derived from the Tango\n"
                    "Project. This artwork is released under the\n"
                    "Creative Commons Attribution-ShareAlike 2.5\n"
                    "license.")
        self.set_artists(artists.split('\n'))
        
        try:
            ifile = open(LICENSE_FILE, "r")
            self.set_license(ifile.read().replace('\x0c', ''))
            ifile.close()
        except IOError:
            self.set_license("License file is missing")

        self.set_comments(_(COMMENTS) + self.get_versions())
        self.set_website_label(_('Gramps Homepage'))
        self.set_website(URL_HOMEPAGE)
        
        authors, contributors = _get_authors()
        self.set_authors(authors)
        if len(contributors) > 0:
            self.add_credit_section(_('Contributions by'), contributors)
        
        # TRANSLATORS: Translate this to your name in your native language
        self.set_translator_credits(_("translator-credits"))

        self.set_documenters(DOCUMENTERS)
        self.set_logo(GdkPixbuf.Pixbuf.new_from_file(SPLASH))

    def get_versions(self):
        """
        Obtain version information of core dependencies
        """
        if hasattr(os, "uname"):
            operatingsystem = os.uname()[0]
            distribution = os.uname()[2]
        else:
            operatingsystem = sys.platform
            distribution = " "

        return (("\n\n" +
                 "GRAMPS: %s \n" +
                 "Python: %s \n" +
                 "BSDDB: %s \n" +
                 "LANG: %s\n" +
                 "OS: %s\n" +
                 "Distribution: %s")
                % (ellipses(str(VERSION)),
                   ellipses(str(sys.version).replace('\n','')),
                   ellipses(str(bsddb.__version__) + " " + str(bsddb.db.version())),
                   ellipses(get_env_var('LANG','')),
                   ellipses(operatingsystem),
                   ellipses(distribution)))

def ellipses(text):
    """
    Ellipsize text on length 40
    """
    if len(text) > 40:
        return text[:40] + "..."
    return text

#-------------------------------------------------------------------------
#
# AuthorParser
#
#-------------------------------------------------------------------------
class AuthorParser(handler.ContentHandler):
    """Parse the ``authors.xml`` file to show in the About dialog.
    
    The ``authors.xml`` file has the same format as the one in the `svn2cl
    <http://ch.tudelft.nl/~arthur/svn2cl/>`_ package, with an additional
    ``title`` tag in the ``author`` element. For example::
    
      <author uid="dallingham" title="author">
        Don Allingham &lt;<html:a href="mailto:don@gramps-project.org">don@gramps-project.org</html:a>&gt;
      </author>}
    
    """
    def __init__(self, author_list, contributor_list):
        """Setup initial instance variable values."""
        handler.ContentHandler.__init__(self)
        
        self.author_list = author_list
        self.contributor_list = contributor_list
        
        # initialize all instance variables to make pylint happy
        self.uid = ""
        self.title = ""
        self.text = ""
        
    def startElement(self, tag, attrs):
        """Handle the start of an element."""
        if tag == "author":
            self.uid = attrs['uid']
            self.title = attrs['title']
            self.text = ""
            
    def endElement(self, tag):
        """Handle the end of an element."""
        if tag == "author":
            developer = self.text.strip()
            if (self.title == 'author' and
                developer not in self.author_list):
                self.author_list.append(developer)
            elif (self.title == 'contributor' and
                  developer not in self.contributor_list):
                self.contributor_list.append(developer)
        
    def characters(self, chunk):
        """Receive notification of character data."""
        if chunk != '\n':
            self.text += chunk

#-------------------------------------------------------------------------
#
# _get_authors
#
#-------------------------------------------------------------------------
def _get_authors():
    """Return all the authors and contributors in a string.
    
    Parse the ``authors.xml`` file if found, or return the default
    list from :mod:`.const` module in case of I/O or parsing failure.
    
    If the ``authors.xml`` file is successfully parsed the *Authors* and
    *Contributors* are grouped separately with an appropriate header.
    
    """
    try:
        authors = []
        contributors = []
        
        parser = make_parser()
        parser.setContentHandler(AuthorParser(authors, contributors))
        
        authors_file = io.open(AUTHORS_FILE, encoding='utf-8')
        parser.parse(authors_file)
        authors_file.close()
        
        authors_text = [authors, contributors]
        
    except (IOError, OSError, SAXParseException):
        authors_text = [AUTHORS, []]

    return authors_text
