#
# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2000-2003  Donald N. Allingham
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

"Analysis and Exploration/Compare individual events"

#------------------------------------------------------------------------
#
# python modules
#
#------------------------------------------------------------------------
import os

#------------------------------------------------------------------------
#
# GNOME/GTK modules
#
#------------------------------------------------------------------------
import gtk
import gtk.glade

#------------------------------------------------------------------------
#
# GRAMPS modules
#
#------------------------------------------------------------------------
import GenericFilter
import ListModel
import sort
import Utils
import BaseDoc
import OpenSpreadSheet
import const

from QuestionDialog import WarningDialog
from gettext import gettext as _

#------------------------------------------------------------------------
#
# 
#
#------------------------------------------------------------------------
class TableReport:

    def __init__(self,filename,doc):
        self.filename = filename
        self.doc = doc
        
    def initialize(self,cols):

        t = BaseDoc.TableStyle()
        t.set_columns(cols)
        for index in range(0,cols):
            t.set_column_width(index,4)
        self.doc.add_table_style("mytbl",t)

        f = BaseDoc.FontStyle()
        f.set_type_face(BaseDoc.FONT_SANS_SERIF)
        f.set_size(12)
        f.set_bold(1)
        p = BaseDoc.ParagraphStyle()
        p.set_font(f)
        p.set_background_color((0xcc,0xff,0xff))
        p.set_padding(0.1)
        self.doc.add_style("head",p)

        f = BaseDoc.FontStyle()
        f.set_type_face(BaseDoc.FONT_SANS_SERIF)
        f.set_size(10)
        p = BaseDoc.ParagraphStyle()
        p.set_font(f)
        self.doc.add_style("data",p)

        self.doc.open(self.filename)
        self.doc.start_page("Page 1","mytbl")

    def finalize(self):
        self.doc.end_page()
        self.doc.close()
        
    def write_table_data(self,data):
        self.doc.start_row()
        for item in data:
            self.doc.start_cell("data")
            self.doc.write_text(item)
            self.doc.end_cell()
        self.doc.end_row()

    def set_row(self,val):
        self.row = val + 2
        
    def write_table_head(self,data):
        self.prev = 3

        self.doc.start_row()
        for item in data:
            self.doc.start_cell("head")
            self.doc.write_text(item)
            self.doc.end_cell()
        self.doc.end_row()

#------------------------------------------------------------------------
#
# 
#
#------------------------------------------------------------------------
class EventComparison:

    def __init__(self,database):
        self.db = database

        base = os.path.dirname(__file__)
        self.glade_file = base + os.sep + "eventcmp.glade"
        self.qual = 0

        self.filterDialog = gtk.glade.XML(self.glade_file,"filters","gramps")
        self.filterDialog.signal_autoconnect({
            "on_apply_clicked"       : self.on_apply_clicked,
            "on_editor_clicked"      : self.filter_editor_clicked,
            "on_filter_list_enter"   : self.filter_list_enter,
            "destroy_passed_object"  : Utils.destroy_passed_object
            })
    
        top =self.filterDialog.get_widget("filters")
        self.filters = self.filterDialog.get_widget("filter_list")

        Utils.set_titles(top,self.filterDialog.get_widget('title'),
                         _('Event comparison filter selection'))

        self.all = GenericFilter.GenericFilter()
        self.all.set_name(_("Entire Database"))
        self.all.add_rule(GenericFilter.Everyone([]))

        self.filter_menu = GenericFilter.build_filter_menu([self.all])
        self.filters.set_menu(self.filter_menu)
        top.show()

    def filter_editor_clicked(self,obj):
        import FilterEditor

        FilterEditor.FilterEditor(const.custom_filters,self.db)

    def filter_list_enter(self,obj):
        self.filter_menu = GenericFilter.build_filter_menu([self.all])
        self.filters.set_menu(self.filter_menu)
        
    def on_apply_clicked(self,obj):
        cfilter = self.filter_menu.get_active().get_data("filter")

        plist = cfilter.apply(self.db,self.db.getPersonMap().values())

        if len(plist) == 0:
            WarningDialog(_("No matches were found"))
        else:
            DisplayChart(plist)

#------------------------------------------------------------------------
#
# 
#
#------------------------------------------------------------------------
def runTool(database,person,callback):
    EventComparison(database)
    
#-------------------------------------------------------------------------
#
#
#
#-------------------------------------------------------------------------
def by_value(first,second):
    return cmp(second[0],first[0])

#-------------------------------------------------------------------------
#
#
#
#-------------------------------------------------------------------------
def fix(line):
    l = line.strip().replace('&','&amp;').replace(l,'>','&gt;')
    return l.replace(l,'<','&lt;').replace(l,'"','&quot;')

#-------------------------------------------------------------------------
#
#
#
#-------------------------------------------------------------------------
class DisplayChart:
    def __init__(self,people_list):
        self.my_list = people_list
        self.row_data = []
        
        base = os.path.dirname(__file__)
        self.glade_file = base + os.sep + "eventcmp.glade"

        self.topDialog = gtk.glade.XML(self.glade_file,"view","gramps")
        self.topDialog.signal_autoconnect({
            "on_write_table"        : self.on_write_table,
            "destroy_passed_object" : Utils.destroy_passed_object
            })

        self.top = self.topDialog.get_widget("view")
        self.eventlist = self.topDialog.get_widget('treeview')

        Utils.set_titles(self.top, self.topDialog.get_widget('title'),
                         _('Event Comparison'))
    
        self.my_list.sort(sort.by_last_name)

        self.event_titles = self.make_event_titles()
        self.build_row_data()
        self.draw_clist_display()
        self.top.show()

    def draw_clist_display(self):

        titles = []
        index = 0
        for v in self.event_titles:
            titles.append((v,index,150))
            index = index + 1
            
        self.list = ListModel.ListModel(self.eventlist,titles)
        for data in self.row_data:
            self.list.add(data)

    def build_row_data(self):
        for individual in self.my_list:
            name = individual.getPrimaryName().getName()
            birth = individual.getBirth()
            death = individual.getDeath()
            map = {}
            elist = individual.getEventList()[:]
            for ievent in elist:
                event_name = ievent.getName()
                if map.has_key(event_name):
                    map[event_name].append(ievent)
                else:
                    map[event_name] = [ievent]

            first = 1
            done = 0
            while done == 0:
                added = 0
                if first:
                    tlist = [name,"%s\n%s" % (birth.getDate(),birth.getPlaceName()),
                             "%s\n%s" % (death.getDate(),death.getPlaceName())]
                else:
                    tlist = ["","",""]
                for ename in self.event_titles[3:]:
                    if map.has_key(ename) and len(map[ename]) > 0:
                        event = map[ename][0]
                        del map[ename][0]
                        tlist.append("%s\n%s" % (event.getDate(), event.getPlaceName()))
                        added = 1
                    else:
                        tlist.append("")
                
                if first:
                    first = 0
                    self.row_data.append(tlist)
                elif added == 0:
                    done = 1
                else:
                    self.row_data.append(tlist)

    def make_event_titles(self):
        """Creates the list of unique event types, along with the person's
        name, birth, and death. This should be the column titles of the report"""
        map = {}
        for individual in self.my_list:
            elist = individual.getEventList()
            for event in elist:
                name = event.getName()
                if not name:
                    break
                if map.has_key(name):
                    map[name] = map[name] + 1
                else:
                    map[name] = 1

        unsort_list = []
        for item in map.keys():
            unsort_list.append((map[item],item))
        unsort_list.sort(by_value)

        sort_list = []
        for item in unsort_list:
            sort_list.append(item[1])

        return [_("Person"),_("Birth"),_("Death")] + sort_list

    def on_write_table(self,obj):
        self.form = gtk.glade.XML(self.glade_file,"dialog1","gramps")
        self.form.signal_autoconnect({
            "on_save_clicked"       : self.on_save_clicked,
            "on_html_toggled"       : self.on_html_toggled,
            "destroy_passed_object" : Utils.destroy_passed_object
            })
        self.save_form = self.form.get_widget("dialog1")
        self.save_form.show()

    def on_html_toggled(self,obj):
        active = self.form.get_widget("html").get_active()
        self.form.get_widget("htmltemplate").set_sensitive(active)

    def on_save_clicked(self,obj):
        
        name = unicode(self.form.get_widget("filename").get_text())

        pstyle = BaseDoc.PaperStyle("junk",10,10)
        doc = OpenSpreadSheet.OpenSpreadSheet(pstyle,BaseDoc.PAPER_PORTRAIT)
        spreadsheet = TableReport(name,doc)
        spreadsheet.initialize(len(self.event_titles))

        spreadsheet.write_table_head(self.event_titles)

        index = 0
        for (top,bottom) in self.row_data:
            spreadsheet.set_row(index%2)
            index = index + 1
            spreadsheet.write_table_data(top)
            spreadsheet.write_table_data(bottom)

        spreadsheet.finalize()
        Utils.destroy_passed_object(obj)

#-------------------------------------------------------------------------
#
#
#
#-------------------------------------------------------------------------
from Plugins import register_tool

register_tool(
    runTool,
    _("Compare individual events"),
    category=_("Analysis and Exploration"),
    description=_("Aids in the analysis of data by allowing the "
                  "development of custom filters that can be applied "
                  "to the database to find similar events")
    )

