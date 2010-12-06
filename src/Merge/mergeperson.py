#
# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2000-2007  Donald N. Allingham
# Copyright (C) 2010       Michiel D. Nauta
# Copyright (C) 2010       Jakim Friant
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
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#

# $Id$

"""
Provide merge capabilities for persons.
"""

#-------------------------------------------------------------------------
#
# GTK/Gnome modules
#
#-------------------------------------------------------------------------
import pango

#-------------------------------------------------------------------------
#
# Gramps modules
#
#-------------------------------------------------------------------------
from gen.ggettext import sgettext as _
from gen.plug.report import utils as ReportUtils
from gen.display.name import displayer as name_displayer
import const
import GrampsDisplay
import DateHandler
from QuestionDialog import ErrorDialog
from Errors import MergeError
import ManagedWindow

#-------------------------------------------------------------------------
#
# Gramps constants
#
#-------------------------------------------------------------------------
WIKI_HELP_PAGE = "%s_-_Entering_and_Editing_Data:_Detailed_-_part_3" % \
        const.URL_MANUAL_PAGE
WIKI_HELP_SEC = _("manual|Merge_People")
_GLADE_FILE = "mergeperson.glade"

sex = ( _("female"), _("male"), _("unknown") )

def name_of(person):
    """Return string with name and ID of a person."""
    if not person:
        return ""
    return "%s [%s]" % (name_displayer.display(person), person.get_gramps_id())

class MergePeople(ManagedWindow.ManagedWindow):
    """
    Displays a dialog box that allows the persons to be combined into one.
    """
    def __init__(self, dbstate, uistate, handle1, handle2, cb_update=None,
            expand_context_info=False):
        ManagedWindow.ManagedWindow.__init__(self, uistate, [], self.__class__)
        self.dbstate = dbstate
        database = dbstate.db
        self.pr1 = database.get_person_from_handle(handle1)
        self.pr2 = database.get_person_from_handle(handle2)
        self.update = cb_update

        self.define_glade('mergeperson', _GLADE_FILE)
        self.set_window(self._gladeobj.toplevel,
                        self.get_widget("person_title"),
                        _("Merge People"))

        # Detailed selection widgets
        name1 = name_displayer.display_name(self.pr1.get_primary_name())
        name2 = name_displayer.display_name(self.pr2.get_primary_name())
        entry1 = self.get_widget("name1")
        entry2 = self.get_widget("name2")
        entry1.set_text(name1)
        entry2.set_text(name2)
        if entry1.get_text() == entry2.get_text():
            for widget_name in ('name1', 'name2', 'name_btn1', 'name_btn2'):
                self.get_widget(widget_name).set_sensitive(False)

        entry1 = self.get_widget("gender1")
        entry2 = self.get_widget("gender2")
        entry1.set_text(sex[self.pr1.get_gender()])
        entry2.set_text(sex[self.pr2.get_gender()])
        if entry1.get_text() == entry2.get_text():
            for widget_name in ('gender1', 'gender2', 'gender_btn1',
                    'gender_btn2'):
                self.get_widget(widget_name).set_sensitive(False)

        gramps1 = self.pr1.get_gramps_id()
        gramps2 = self.pr2.get_gramps_id()
        entry1 = self.get_widget("gramps1")
        entry2 = self.get_widget("gramps2")
        entry1.set_text(gramps1)
        entry2.set_text(gramps2)
        if entry1.get_text() == entry2.get_text():
            for widget_name in ('gramps1', 'gramps2', 'gramps_btn1',
                    'gramps_btn2'):
                self.get_widget(widget_name).set_sensitive(False)

        # Main window widgets that determine which handle survives
        rbutton1 = self.get_widget("handle_btn1")
        rbutton_label1 = self.get_widget("label_handle_btn1")
        rbutton_label2 = self.get_widget("label_handle_btn2")
        rbutton_label1.set_label(name1 + " [" + gramps1 + "]")
        rbutton_label2.set_label(name2 + " [" + gramps2 + "]")
        rbutton1.connect("toggled", self.on_handle1_toggled)
        expander2 = self.get_widget("expander2")
        self.expander_handler = expander2.connect("notify::expanded",
                                                  self.cb_expander2_activated)
        expander2.set_expanded(expand_context_info)

        self.connect_button("person_help", self.cb_help)
        self.connect_button("person_ok", self.cb_merge)
        self.connect_button("person_cancel", self.close)
        self.show()

    def on_handle1_toggled(self, obj):
        """Preferred person changes"""
        if obj.get_active():
            self.get_widget("name_btn1").set_active(True)
            self.get_widget("gender_btn1").set_active(True)
            self.get_widget("gramps_btn1").set_active(True)
        else:
            self.get_widget("name_btn2").set_active(True)
            self.get_widget("gender_btn2").set_active(True)
            self.get_widget("gramps_btn2").set_active(True)

    def cb_expander2_activated(self, obj, param_spec):
        """Context Information expander is activated"""
        if obj.get_expanded():
            text1 = self.get_widget('text1')
            text2 = self.get_widget('text2')
            self.display(text1.get_buffer(), self.pr1)
            self.display(text2.get_buffer(), self.pr2)
            obj.disconnect(self.expander_handler)

    def add(self, tobj, tag, text):
        """Add text text to text buffer tobj with formatting tag."""
        text += "\n"
        tobj.insert_with_tags(tobj.get_end_iter(), text, tag)

    def display(self, tobj, person):
        """Fill text buffer tobj with detailed info on person person."""
        database = self.dbstate.db
        normal = tobj.create_tag()
        normal.set_property('indent', 10)
        normal.set_property('pixels-above-lines', 1)
        normal.set_property('pixels-below-lines', 1)
        indent = tobj.create_tag()
        indent.set_property('indent', 30)
        indent.set_property('pixels-above-lines', 1)
        indent.set_property('pixels-below-lines', 1)
        title = tobj.create_tag()
        title.set_property('weight', pango.WEIGHT_BOLD)
        title.set_property('scale', pango.SCALE_LARGE)
        self.add(tobj, title, name_displayer.display(person))
        self.add(tobj, normal, "%s:\t%s" % (_('ID'), 
                 person.get_gramps_id()))
        self.add(tobj, normal, "%s:\t%s" % (_('Gender'), 
                 sex[person.get_gender()]))
        bref = person.get_birth_ref()
        if bref:
            self.add(tobj, normal, "%s:\t%s" % (_('Birth'), 
                     self.get_event_info(bref.ref)))
        dref = person.get_death_ref()
        if dref:
            self.add(tobj, normal, "%s:\t%s" % (_('Death'), 
                     self.get_event_info(dref.ref)))

        nlist = person.get_alternate_names()
        if len(nlist) > 0:
            self.add(tobj, title, _("Alternate Names"))
            for name in nlist:
                self.add(tobj, normal, 
                         name_displayer.display_name(name))

        elist = person.get_event_ref_list()
        if len(elist) > 0:
            self.add(tobj, title, _("Events"))
            for event_ref in person.get_event_ref_list():
                event_handle = event_ref.ref
                name = str(
                    database.get_event_from_handle(event_handle).get_type())
                self.add(tobj, normal, "%s:\t%s" % 
                            (name, self.get_event_info(event_handle)))
        plist = person.get_parent_family_handle_list()

        if len(plist) > 0:
            self.add(tobj, title, _("Parents"))
            for fid in person.get_parent_family_handle_list():
                (fname, mname, gid) = self.get_parent_info(fid)
                self.add(tobj, normal, "%s:\t%s" % (_('Family ID'), gid))
                if fname:
                    self.add(tobj, indent, "%s:\t%s" % (_('Father'), fname))
                if mname:
                    self.add(tobj, indent, "%s:\t%s" % (_('Mother'), mname))
        else:
            self.add(tobj, normal, _("No parents found"))
            
        self.add(tobj, title, _("Spouses"))
        slist = person.get_family_handle_list()
        if len(slist) > 0:
            for fid in slist:
                (fname, mname, pid) = self.get_parent_info(fid)
                family = database.get_family_from_handle(fid)
                self.add(tobj, normal, "%s:\t%s" % (_('Family ID'), pid))
                spouse_id = ReportUtils.find_spouse(person, family)
                if spouse_id:
                    spouse = database.get_person_from_handle(spouse_id)
                    self.add(tobj, indent, "%s:\t%s" % (_('Spouse'), 
                             name_of(spouse)))
                relstr = str(family.get_relationship())
                self.add(tobj, indent, "%s:\t%s" % (_('Type'), relstr))
                event = ReportUtils.find_marriage(database, family)
                if event:
                    self.add(tobj, indent, "%s:\t%s" % (
                            _('Marriage'), 
                            self.get_event_info(event.get_handle())))
                for child_ref in family.get_child_ref_list():
                    child = database.get_person_from_handle(child_ref.ref)
                    self.add(tobj, indent, "%s:\t%s" % (_('Child'), 
                             name_of(child)))
        else:
            self.add(tobj, normal, _("No spouses or children found"))

        alist = person.get_address_list()
        if len(alist) > 0:
            self.add(tobj, title, _("Addresses"))
            for addr in alist:
                location = ", ".join([addr.get_street(), addr.get_city(), 
                                     addr.get_state(), addr.get_country(),
                                     addr.get_postal_code(), addr.get_phone()])
                self.add(tobj, normal, location.strip())

    def get_parent_info(self, fid):
        """Return tuple of father name, mother name and family ID"""
        database = self.dbstate.db
        family = database.get_family_from_handle(fid)
        father_id = family.get_father_handle()
        mother_id = family.get_mother_handle()
        if father_id:
            father = database.get_person_from_handle(father_id)
            fname = name_of(father)
        else:
            fname = u""
        if mother_id:
            mother = database.get_person_from_handle(mother_id)
            mname = name_of(mother)
        else:
            mname = u""
        return (fname, mname, family.get_gramps_id())

    def get_event_info(self, handle):
        """Return date and place of an event as string."""
        date = ""
        place = ""
        if handle:
            event = self.dbstate.db.get_event_from_handle(handle)
            date = DateHandler.get_date(event)
            place = self.place_name(event)
            if date:
                return ("%s, %s" % (date, place)) if place else date
            else:
                return place or ""
        else:
            return ""

    def place_name(self, event):
        """Return place name of an event as string."""
        place_id = event.get_place_handle()
        if place_id:
            place = self.dbstate.db.get_place_from_handle(place_id)
            return place.get_title()
        else:
            return ""

    def cb_help(self, obj):
        """Display the relevant portion of Gramps manual"""
        GrampsDisplay.help(webpage = WIKI_HELP_PAGE, section = WIKI_HELP_SEC)

    def cb_merge(self, obj):
        """
        Perform the merge of the persons when the merge button is clicked.
        """
        self.uistate.set_busy_cursor(True)
        use_handle1 = self.get_widget("handle_btn1").get_active()
        if use_handle1:
            phoenix = self.pr1
            titanic = self.pr2
            unselect_path = (1,)
        else:
            phoenix = self.pr2
            titanic = self.pr1
            unselect_path = (0,)

        if self.get_widget("name_btn1").get_active() ^ use_handle1:
            swapname = phoenix.get_primary_name()
            phoenix.set_primary_name(titanic.get_primary_name())
            titanic.set_primary_name(swapname)
        if self.get_widget("gender_btn1").get_active() ^ use_handle1:
            phoenix.set_gender(titanic.get_gender())
        if self.get_widget("gramps_btn1").get_active() ^ use_handle1:
            swapid = phoenix.get_gramps_id()
            phoenix.set_gramps_id(titanic.get_gramps_id())
            titanic.set_gramps_id(swapid)

        try:
            query = MergePersonQuery(self.dbstate, phoenix, titanic)
            query.execute()
        except MergeError, err:
            ErrorDialog( _("Cannot merge people"), str(err))
        self.uistate.viewmanager.active_page.selection.unselect_path(
                unselect_path)
        self.uistate.set_busy_cursor(False)
        self.close()
        if self.update:
            self.update()

class MergePersonQuery(object):
    """
    Create database query to merge two persons.
    """
    def __init__(self, dbstate, phoenix, titanic):
        self.database = dbstate.db
        self.phoenix = phoenix
        self.titanic = titanic
        if self.check_for_spouse(self.phoenix, self.titanic):
            raise MergeError(_("Spouses cannot be merged. To merge these "
                "people, you must first break the relationship between them."))
        if self.check_for_child(self.phoenix, self.titanic):
            raise MergeError(_("A parent and child cannot be merged. To merge "
                "these people, you must first break the relationship between "
                "them"))

    def check_for_spouse(self, person1, person2):
        """Return if person1 and person2 are spouses of eachother."""
        fs1 = set(person1.get_family_handle_list())
        fs2 = set(person2.get_family_handle_list())
        return len(fs1.intersection(fs2)) != 0

    def check_for_child(self, person1, person2):
        """Return if person1 and person2 have a child-parent relationship."""
        fs1 = set(person1.get_family_handle_list())
        fp1 = set(person1.get_parent_family_handle_list())
        fs2 = set(person2.get_family_handle_list())
        fp2 = set(person2.get_parent_family_handle_list())
        return len(fs1.intersection(fp2)) != 0 or len(fs2.intersection(fp1))

    def merge_families(self, main_family_handle, family, trans):
        new_handle = self.phoenix.get_handle()
        family_handle = family.get_handle()
        main_family = self.database.get_family_from_handle(main_family_handle)
        main_family.merge(family)
        for childref in family.get_child_ref_list():
            child = self.database.get_person_from_handle(
                    childref.get_reference_handle())
            if main_family_handle in child.parent_family_list:
                child.remove_handle_references('Family', [family_handle])
            else:
                child.replace_handle_reference('Family', family_handle, 
                    main_family_handle)
            self.database.commit_person(child, trans)
        self.phoenix.remove_family_handle(family_handle)
        family_father_handle = family.get_father_handle()
        spouse_handle = family.get_mother_handle() if \
                new_handle == family_father_handle else family_father_handle
        spouse = self.database.get_person_from_handle(spouse_handle)
        spouse.remove_family_handle(family_handle)
        self.database.commit_person(spouse, trans)
        self.database.remove_family(family_handle, trans)
        self.database.commit_family(main_family, trans)

    def execute(self, trans=None):
        """
        Merges two persons into a single person.
        """
        new_handle = self.phoenix.get_handle()
        old_handle = self.titanic.get_handle()

        self.phoenix.merge(self.titanic)

        # For now use a batch transaction, because merger of persons is
        # complicated, thus is done in several steps and the database should
        # be updated after each step for the calculation of the next step.
        # Normal Gramps transactions only touch the database upon
        # transaction_commit, not after each commit_person/commit_family.
        # Unfortunately batch transactions are no transactions at all, so there
        # is not possibility of rollback in case of trouble.
        if trans is None:
            need_commit = True
            trans = self.database.transaction_begin("", True)
        else:
            need_commit = False
        
        commit_persons = []
        for person in self.database.iter_people():
            if person.has_handle_reference('Person', old_handle):
                person.replace_handle_reference('Person', old_handle,new_handle)
                #self.database.commit_person(person, trans) # DEADLOCK
                person_handle = person.get_handle()
                if person_handle == new_handle:
                    self.phoenix.replace_handle_reference('Person', old_handle,
                                                          new_handle)
                elif person_handle != old_handle:
                    commit_persons.append(person)
        for person in commit_persons:
            self.database.commit_person(person, trans)

        for family_handle in self.phoenix.get_parent_family_handle_list():
            family = self.database.get_family_from_handle(family_handle)
            if family.has_handle_reference('Person', old_handle):
                family.replace_handle_reference('Person', old_handle,new_handle)
                self.database.commit_family(family, trans)

        parent_list = []
        family_handle_list = self.phoenix.get_family_handle_list()[:]
        for family_handle in family_handle_list:
            family = self.database.get_family_from_handle(family_handle)
            parents = (family.get_father_handle(), family.get_mother_handle())
            if family.has_handle_reference('Person', old_handle):
                family.replace_handle_reference('Person', old_handle,new_handle)
                parents = (family.get_father_handle(),
                           family.get_mother_handle())
                # prune means merging families in this case.
                if parents in parent_list:
                    # also merge when father_handle or mother_handle == None!
                    idx = parent_list.index(parents)
                    main_family_handle = family_handle_list[idx]
                    self.merge_families(main_family_handle, family, trans)
                    continue
                self.database.commit_family(family, trans)
            parent_list.append(parents)

        self.database.remove_person(old_handle, trans)
        self.database.commit_person(self.phoenix, trans)
        if need_commit:
            self.database.transaction_commit(trans, _('Merge Person'))
        self.database.emit('person-rebuild')
