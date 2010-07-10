#!/usr/bin/python
# -*- coding: utf-8 -*-

#Copyright 2010 Steffen Schaumburg
#This program is free software: you can redistribute it and/or modify
#it under the terms of the GNU Affero General Public License as published by
#the Free Software Foundation, version 3 of the License.
#
#This program is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#GNU General Public License for more details.
#
#You should have received a copy of the GNU Affero General Public License
#along with this program. If not, see <http://www.gnu.org/licenses/>.
#In the "official" distribution you can find the license in agpl-3.0.txt.

#import traceback
import threading
import pygtk
pygtk.require('2.0')
import gtk
#import os
#import sys
from time import time, strftime

#import Card
#import fpdb_import
#import Database
import Charset
import TourneyFilters

class GuiTourneyPlayerStats (threading.Thread):
    def __init__(self, config, db, sql, mainwin, debug=True):
        self.conf = config
        self.db = db
        self.cursor = self.db.cursor
        self.sql = sql
        self.main_window = mainwin
        self.debug = debug
        
        self.liststore = []   # gtk.ListStore[]         stores the contents of the grids
        self.listcols = []    # gtk.TreeViewColumn[][]  stores the columns in the grids
        
        filters_display = { "Heroes"    : True,
                            "Sites"     : True,
                            #"Games"     : True,
                            #"Limits"    : True,
                            #"LimitSep"  : True,
                            #"LimitType" : True,
                            #"Type"      : True,
                            "Seats"     : True,
                            #"SeatSep"   : True,
                            "Dates"     : True,
                            #"Groups"    : True,
                            #"GroupsAll" : True,
                            #"Button1"   : True,
                            "Button2"   : True}
        
        self.stats_frame = None
        self.stats_vbox = None
        self.detailFilters = []   # the data used to enhance the sql select

        self.main_hbox = gtk.HPaned()

        self.filters = TourneyFilters.TourneyFilters(self.db, self.conf, self.sql, display = filters_display)
        #self.filters.registerButton1Name("_Filters")
        #self.filters.registerButton1Callback(self.showDetailFilter)
        self.filters.registerButton2Name("_Refresh Stats")
        self.filters.registerButton2Callback(self.refreshStats)
        
        # ToDo: store in config
        # ToDo: create popup to adjust column config
        # columns to display, keys match column name returned by sql, values in tuple are:
        #     is column displayed, column heading, xalignment, formatting, celltype
        self.columns = [ ["tourneyTypeId",  True,  "TTypeId",     0.0, "%s", "str"]
                       , ["tourney",        False, "Tourney",     0.0, "%s", "str"]   # true not allowed for this line
                       #, ["pname",         False, "Name",     0.0, "%s", "str"]   # true not allowed for this line (set in code)
                       , ["tourneyCount",   True,  "#",      1.0, "%1.0f", "str"]
                       , ["1st",            False, "1st",    1.0, "%3.1f", "str"]
                       , ["2nd",            True,  "2nd",     1.0, "%3.1f", "str"]
                       , ["3rd",            True,  "3rd",      1.0, "%3.1f", "str"]
                       , ["unknownRank",    True,  "unknown",      1.0, "%3.1f", "str"]
                       , ["itm",            True,  "ITM",   1.0, "%2.2f", "str"]
                       , ["roi",            True,  "ROI",  1.0, "%3.1f", "str"]
                       , ["profitPerTourney", True,  "$/T",  1.0, "%3.1f", "str"]]
        
        self.stats_frame = gtk.Frame()
        self.stats_frame.show()

        self.stats_vbox = gtk.VPaned()
        self.stats_vbox.show()
        self.stats_frame.add(self.stats_vbox)
        # self.fillStatsFrame(self.stats_vbox)

        #self.main_hbox.pack_start(self.filters.get_vbox())
        #self.main_hbox.pack_start(self.stats_frame, expand=True, fill=True)
        self.main_hbox.pack1(self.filters.get_vbox())
        self.main_hbox.pack2(self.stats_frame)
        self.main_hbox.show()
    #end def __init__

    def addGrid(self, vbox, query, flags, tourneyTypes, playerids, sitenos, seats, dates):
        counter = 0
        row = 0
        sqlrow = 0
        if not flags:  holecards,grid = False,0
        else:          holecards,grid = flags[0],flags[2]

        tmp = self.sql.query[query]
        tmp = self.refineQuery(tmp, flags, tourneyTypes, playerids, sitenos, seats, dates)
        self.cursor.execute(tmp)
        result = self.cursor.fetchall()
        colnames = [desc[0].lower() for desc in self.cursor.description]

        # pre-fetch some constant values:
        self.cols_to_show = [x for x in self.columns if x[colshow]]
        hgametypeid_idx = colnames.index('hgametypeid')

        assert len(self.liststore) == grid, "len(self.liststore)="+str(len(self.liststore))+" grid-1="+str(grid)
        self.liststore.append( gtk.ListStore(*([str] * len(self.cols_to_show))) )
        view = gtk.TreeView(model=self.liststore[grid])
        view.set_grid_lines(gtk.TREE_VIEW_GRID_LINES_BOTH)
        #vbox.pack_start(view, expand=False, padding=3)
        vbox.add(view)
        textcell = gtk.CellRendererText()
        textcell50 = gtk.CellRendererText()
        textcell50.set_property('xalign', 0.5)
        numcell = gtk.CellRendererText()
        numcell.set_property('xalign', 1.0)
        assert len(self.listcols) == grid
        self.listcols.append( [] )

        # Create header row   eg column: ("game",     True, "Game",     0.0, "%s")
        for col, column in enumerate(self.cols_to_show):
            if column[colalias] == 'game' and holecards:
                s = [x for x in self.columns if x[colalias] == 'hand'][0][colheading]
            else:
                s = column[colheading]
            self.listcols[grid].append(gtk.TreeViewColumn(s))
            view.append_column(self.listcols[grid][col])
            if column[colformat] == '%s':
                if column[colxalign] == 0.0:
                    self.listcols[grid][col].pack_start(textcell, expand=True)
                    self.listcols[grid][col].add_attribute(textcell, 'text', col)
                    cellrend = textcell
                else:
                    self.listcols[grid][col].pack_start(textcell50, expand=True)
                    self.listcols[grid][col].add_attribute(textcell50, 'text', col)
                    cellrend = textcell50
                self.listcols[grid][col].set_expand(True)
            else:
                self.listcols[grid][col].pack_start(numcell, expand=True)
                self.listcols[grid][col].add_attribute(numcell, 'text', col)
                self.listcols[grid][col].set_expand(True)
                cellrend = numcell
                #self.listcols[grid][col].set_alignment(column[colxalign]) # no effect?
            self.listcols[grid][col].set_clickable(True)
            self.listcols[grid][col].connect("clicked", self.sortcols, (col,grid))
            if col == 0:
                self.listcols[grid][col].set_sort_order(gtk.SORT_DESCENDING)
                self.listcols[grid][col].set_sort_indicator(True)
            if column[coltype] == 'cash':
                self.listcols[grid][col].set_cell_data_func(numcell, self.ledger_style_render_func)
            else:
                self.listcols[grid][col].set_cell_data_func(cellrend, self.reset_style_render_func)

        rows = len(result) # +1 for title row

        while sqlrow < rows:
            treerow = []
            for col,column in enumerate(self.cols_to_show):
                if column[colalias] in colnames:
                    value = result[sqlrow][colnames.index(column[colalias])]
                    if column[colalias] == 'plposition':
                        if value == 'B':
                            value = 'BB'
                        elif value == 'S':
                            value = 'SB'
                        elif value == '0':
                            value = 'Btn'
                else:
                    if column[colalias] == 'game':
                        if holecards:
                            value = Card.twoStartCardString( result[sqlrow][hgametypeid_idx] )
                        else:
                            minbb = result[sqlrow][colnames.index('minbigblind')]
                            maxbb = result[sqlrow][colnames.index('maxbigblind')]
                            value = result[sqlrow][colnames.index('limittype')] + ' ' \
                                    + result[sqlrow][colnames.index('category')].title() + ' ' \
                                    + result[sqlrow][colnames.index('name')] + ' $'
                            if 100 * int(minbb/100.0) != minbb:
                                value += '%.2f' % (minbb/100.0)
                            else:
                                value += '%.0f' % (minbb/100.0)
                            if minbb != maxbb:
                                if 100 * int(maxbb/100.0) != maxbb:
                                    value += ' - $' + '%.2f' % (maxbb/100.0)
                                else:
                                    value += ' - $' + '%.0f' % (maxbb/100.0)
                    else:
                        continue
                if value and value != -999:
                    treerow.append(column[colformat] % value)
                else:
                    treerow.append(' ')
            iter = self.liststore[grid].append(treerow)
            #print treerow
            sqlrow += 1
            row += 1
        vbox.show_all()
    #end def addGrid

    def createStatsTable(self, vbox, tourneyTypes, playerids, sitenos, seats, dates):
        startTime = time()
        show_detail = True

        # Scrolled window for summary table
        swin = gtk.ScrolledWindow(hadjustment=None, vadjustment=None)
        swin.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        swin.show()
        vbox.pack1(swin)

        # Display summary table at top of page
        # 3rd parameter passes extra flags, currently includes:
        #   holecards - whether to display card breakdown (True/False)
        #   numhands  - min number hands required when displaying all players
        #   gridnum   - index for grid data structures
        flags = [False, self.filters.getNumTourneys(), 0]
        self.addGrid(swin, 'playerDetailedStats', flags, tourneyTypes, playerids
                    ,sitenos, seats, dates)

        if 'allplayers' in groups and groups['allplayers']:
            # can't currently do this combination so skip detailed table
            show_detail = False

        if show_detail: 
            # Separator
            vbox2 = gtk.VBox(False, 0)
            heading = gtk.Label(self.filterText['handhead'])
            heading.show()
            vbox2.pack_start(heading, expand=False, padding=3)

            # Scrolled window for detailed table (display by hand)
            swin = gtk.ScrolledWindow(hadjustment=None, vadjustment=None)
            swin.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
            swin.show()
            vbox2.pack_start(swin, expand=True, padding=3)
            vbox.pack2(vbox2)
            vbox2.show()

            # Detailed table
            flags[0] = True
            flags[2] = 1
            self.addGrid(swin, 'playerDetailedStats', flags, playerids, sitenos, seats, dates)

        self.db.rollback()
        print "Stats page displayed in %4.2f seconds" % (time() - startTime)
    #end def createStatsTable

    def fillStatsFrame(self, vbox):
        tourneyTypes = self.filters.getTourneyTypes()
        #tourneys = self.tourneys.getTourneys()
        sites = self.filters.getSites()
        heroes = self.filters.getHeroes()
        siteids = self.filters.getSiteIds()
        seats  = self.filters.getSeats()
        dates = self.filters.getDates()
        sitenos = []
        playerids = []

        # Which sites are selected?
        for site in sites:
            if sites[site] == True:
                sitenos.append(siteids[site])
                print "heroes",heroes
                _hname = Charset.to_utf8(heroes[site])
                result = self.db.get_player_id(self.conf, site, _hname)
                if result is not None:
                    playerids.append(int(result))

        if not sitenos:
            #Should probably pop up here.
            print "No sites selected - defaulting to PokerStars"
            sitenos = [2]
        if not playerids:
            print "No player ids found"
            return
        
        self.createStatsTable(vbox, tourneyTypes, playerids, sitenos, seats, dates)
    #end def fillStatsFrame

    def get_vbox(self):
        """returns the vbox of this thread"""
        return self.main_hbox
    #end def get_vbox
    
    def refineQuery(self, query, flags, tourneyTypes, playerids, sitenos, seats, dates):
        having = ''
        holecards = flags[0]
        numTourneys = flags[1]

        if playerids:
            nametest = str(tuple(playerids))
            nametest = nametest.replace("L", "")
            nametest = nametest.replace(",)",")")
        else:
            nametest = "1 = 2"
        pname = "p.name"
        # set flag in self.columns to not show player name column
        #[x for x in self.columns if x[0] == 'pname'][0][1] = False #TODO: fix and reactivate
            
        query = query.replace("<player_test>", nametest)
        query = query.replace("<playerName>", pname)
        query = query.replace("<havingclause>", having)

        gametest = ""
        q = []
        for m in self.filters.display.items():
            if m[0] == 'Games' and m[1]:
                for n in games:
                    if games[n]:
                        q.append(n)
                if len(q) > 0:
                    gametest = str(tuple(q))
                    gametest = gametest.replace("L", "")
                    gametest = gametest.replace(",)",")")
                    gametest = gametest.replace("u'","'")
                    gametest = "and gt.category in %s" % gametest
                else:
                    gametest = "and gt.category IS NULL"
        query = query.replace("<game_test>", gametest)
        
        sitetest = ""
        q = []
        for m in self.filters.display.items():
            if m[0] == 'Sites' and m[1]:
                for n in sitenos:
                        q.append(n)
                if len(q) > 0:
                    sitetest = str(tuple(q))
                    sitetest = sitetest.replace("L", "")
                    sitetest = sitetest.replace(",)",")")
                    sitetest = sitetest.replace("u'","'")
                    sitetest = "and gt.siteId in %s" % sitetest
                else:
                    sitetest = "and gt.siteId IS NULL"
        query = query.replace("<site_test>", sitetest)
        
        if seats:
            query = query.replace('<seats_test>', 'between ' + str(seats['from']) + ' and ' + str(seats['to']))
            if 'show' in seats and seats['show']:
                query = query.replace('<groupbyseats>', ',h.seats')
                query = query.replace('<orderbyseats>', ',h.seats')
            else:
                query = query.replace('<groupbyseats>', '')
                query = query.replace('<orderbyseats>', '')
        else:
            query = query.replace('<seats_test>', 'between 0 and 100')
            query = query.replace('<groupbyseats>', '')
            query = query.replace('<orderbyseats>', '')

        #lims = [int(x) for x in limits if x.isdigit()]
        #potlims = [int(x[0:-2]) for x in limits if len(x) > 2 and x[-2:] == 'pl']
        #nolims = [int(x[0:-2]) for x in limits if len(x) > 2 and x[-2:] == 'nl']
        #bbtest = "and ( (gt.limitType = 'fl' and gt.bigBlind in "
                 # and ( (limit and bb in()) or (nolimit and bb in ()) )
        #if lims:
        #    blindtest = str(tuple(lims))
        #    blindtest = blindtest.replace("L", "")
        #    blindtest = blindtest.replace(",)",")")
        #    bbtest = bbtest + blindtest + ' ) '
        #else:
        #    bbtest = bbtest + '(-1) ) '
        #bbtest = bbtest + " or (gt.limitType = 'pl' and gt.bigBlind in "
        #if potlims:
        #    blindtest = str(tuple(potlims))
        #    blindtest = blindtest.replace("L", "")
        #    blindtest = blindtest.replace(",)",")")
        #    bbtest = bbtest + blindtest + ' ) '
        #else:
        #    bbtest = bbtest + '(-1) ) '
        #bbtest = bbtest + " or (gt.limitType = 'nl' and gt.bigBlind in "
        #if nolims:
        #    blindtest = str(tuple(nolims))
        #    blindtest = blindtest.replace("L", "")
        #    blindtest = blindtest.replace(",)",")")
        #    bbtest = bbtest + blindtest + ' ) )'
        #else:
        #    bbtest = bbtest + '(-1) ) )'
        
        #if type == 'ring':
        #    bbtest = bbtest + " and gt.type = 'ring' "
        #elif type == 'tour':
        #bbtest = " and gt.type = 'tour' "
        
        #query = query.replace("<gtbigBlind_test>", bbtest)

        #query = query.replace("<orderbyhgameTypeId>", "")
        
        # process self.detailFilters (a list of tuples)
        flagtest = ''
        #self.detailFilters = [('h.seats', 5, 6)]   # for debug
        if self.detailFilters:
            for f in self.detailFilters:
                if len(f) == 3:
                    # X between Y and Z
                    flagtest += ' and %s between %s and %s ' % (f[0], str(f[1]), str(f[2]))
        query = query.replace("<flagtest>", flagtest)

        # allow for differences in sql cast() function:
        if self.db.backend == self.db.MYSQL_INNODB:
            query = query.replace("<signed>", 'signed ')
        else:
            query = query.replace("<signed>", '')

        # Filter on dates
        query = query.replace("<datestest>", " between '" + dates[0] + "' and '" + dates[1] + "'")

        # Group by position?
        #if groups['posn']:
        #    #query = query.replace("<position>", "case hp.position when '0' then 'Btn' else hp.position end")
        #    query = query.replace("<position>", "hp.position")
        #    # set flag in self.columns to show posn column
        #    [x for x in self.columns if x[0] == 'plposition'][0][1] = True
        #else:
        #    query = query.replace("<position>", "gt.base")
        #    # unset flag in self.columns to hide posn column
        #    [x for x in self.columns if x[0] == 'plposition'][0][1] = False

        print "query at end of refine query:", query
        return(query)
    #end def refineQuery

    def refreshStats(self, widget, data):
        self.last_pos = self.stats_vbox.get_position()
        try: self.stats_vbox.destroy()
        except AttributeError: pass
        self.liststore = []
        self.listcols = []
        #self.stats_vbox = gtk.VBox(False, 0)
        self.stats_vbox = gtk.VPaned()
        self.stats_vbox.show()
        self.stats_frame.add(self.stats_vbox)
        self.fillStatsFrame(self.stats_vbox)
        if self.last_pos > 0:
            self.stats_vbox.set_position(self.last_pos)
    #end def refreshStats
#end class GuiTourneyPlayerStats