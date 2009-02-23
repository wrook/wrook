#!/usr/bin/env python
#
# GUI for UnitTests
# Python license
# (c) 2002 cliechti@gmx.net
# http://homepage.hispeed.ch/py430/python/

import unittest, os, sys, imp, time, traceback

## import all of the wxPython GUI package
from wxPython.wx import *
from wxPython.grid import *

#specify editor, make it return immediately, otherwise the GUI will wait
#until its closed. on win use "start cmd", on un*x "cmd&"
EDITOR = r'start c:\tools\wscite\scite "%(filename)s" -goto:%(lineno)s'
def starteditor(filename, lineno=1):
    if os.path.exists(filename):
        os.system(EDITOR % {'filename':filename, 'lineno':lineno})
    else:
        wxMessageBox("Cannot locate sourcefile:\n%s" % filename, "Can't start editor...", wxOK)
        
#----------------------------------------------------------------

class GUITestResult(unittest.TestResult):
    """A test result class that can print formatted text results to a stream.
    """
    separator1 = '=' * 70
    separator2 = '-' * 70

    def __init__(self, listview, progress, descriptions, verbosity):
        unittest.TestResult.__init__(self)
        self.listview = listview
        self.showAll = verbosity > 1
        self.descriptions = descriptions
        self.progress = progress
        self.testdescr = None
        self.stream = sys.stdout

    def getDescription(self, test):
        if self.descriptions:
            return test.shortDescription() or str(test)
        else:
            return str(test)

    def startTest(self, test):
        unittest.TestResult.startTest(self, test)
        self.testdescr = self.getDescription(test)
        if self.showAll:
            self.stream.write(self.getDescription(test))
            self.stream.write(" ... ")

    def _correctFilename(self, filename):
        if filename[-4:] in ('.pyc', '.pyo'):
            return filename[:-1]
        return filename
            
    def addSuccess(self, test):
        unittest.TestResult.addSuccess(self, test)
        if self.showAll:
            self.stream.write("ok\n")
        self.listview.Append( (
            'Ok',
            self.testdescr,
            '',
            None,
            None
            ) )
        self.progress.tick()
        
    def addError(self, test, err):
        unittest.TestResult.addError(self, test, err)
        if self.showAll:
            self.stream.write("ERROR\n")
        try:
            filename = self._correctFilename(err[2].tb_frame.f_globals['__file__'])
        except KeyError:
            filename = None
        lineno = err[2].tb_lineno
        self.listview.Append( (
            'Error',
            self.testdescr,
            traceback.format_exception(*err)[-1].rstrip(),
            self._exc_info_to_string(err),
            (filename, lineno)
            ) )
        self.progress.tick()

    def addFailure(self, test, err):
        unittest.TestResult.addFailure(self, test, err)
        if self.showAll:
            self.stream.write("FAIL\n")
        try:
            filename = self._correctFilename(err[2].tb_frame.f_globals['__file__'])
        except KeyError:
            filename = None
        lineno = err[2].tb_lineno
        self.listview.Append( (
            'Fail',
            self.testdescr,
            traceback.format_exception(*err)[-1].rstrip(),
            self._exc_info_to_string(err),
            (filename, lineno)
            ) )
        self.progress.tick()

    def printErrors(self):
        if self.showAll:
            self.stream.write("\n")
        self.printErrorList('ERROR', self.errors)
        self.printErrorList('FAIL', self.failures)

    def printErrorList(self, flavour, errors):
        for test, err in errors:
            self.stream.write(self.separator1)
            self.stream.write("\n%s: %s\n" % (flavour,self.getDescription(test)))
            self.stream.write(self.separator2)
            self.stream.write("\n%s\n" % err)

class GUITestRunner:
    """A test runner class that displays results in textual form.

    It prints out the names of tests as they are run, errors as they
    occur, and a summary of the results at the end of the test run.
    """
    def __init__(self, listview, progress, stream=sys.stderr, descriptions=1, verbosity=2):
        self.listview = listview
        self.progress = progress
        self.stream = unittest._WritelnDecorator(stream)
        self.descriptions = descriptions
        self.verbosity = verbosity

    def _makeResult(self):
        return GUITestResult(self.listview, self.progress, self.descriptions, self.verbosity)

    def run(self, test):
        "Run the given test case or test suite."
        result = self._makeResult()
        startTime = time.time()
        test(result)
        stopTime = time.time()
        timeTaken = float(stopTime - startTime)
        result.printErrors()
        self.stream.writeln(result.separator2)
        run = result.testsRun
        self.stream.writeln("Ran %d test%s in %.3fs" %
                            (run, run == 1 and "" or "s", timeTaken))
        self.stream.writeln()
        if not result.wasSuccessful():
            self.stream.write("FAILED (")
            failed, errored = map(len, (result.failures, result.errors))
            if failed:
                self.stream.write("failures=%d" % failed)
            if errored:
                if failed: self.stream.write(", ")
                self.stream.write("errors=%d" % errored)
            self.stream.writeln(")")
        else:
            self.stream.writeln("OK")
        return result

#----------------------------------------------------------------

def lastline(t):
    t = t.rstrip()
    n = t.rfind('\n')
    if n >= 0:
        return t[n+1:]
    return t

#----------------------------------------------------------------

class ResultView(wxListCtrl):
    PM_DETAIL = wxNewId()
    PM_LOCATE = wxNewId()
    
    def __init__(self, parent):
        wxListCtrl.__init__(self, parent, -1,
                            style=wxLC_REPORT|wxSUNKEN_BORDER|wxLC_VIRTUAL|wxLC_VRULES,#|wxLC_HRULES,
                            size=(500,200))

        self.InsertColumn(0, 'Ok')
        self.InsertColumn(1, 'Description')
        self.InsertColumn(2, 'Details')

        self.SetColumnWidth(0, 40)
        w = self.GetSize()[0] - self.GetColumnWidth(0)
        self.SetColumnWidth(1, w/2)
        self.SetColumnWidth(2, w/2)

        EVT_RIGHT_DOWN(self, self.OnRightClick)
        EVT_LIST_ITEM_SELECTED(self, self.GetId(), self.OnItemSelected)
        EVT_LIST_ITEM_ACTIVATED(self, self.GetId(), self.OnItemActivated)
        
        self.red = wxListItemAttr()
        self.red.SetBackgroundColour(wxRED)
        self.green = wxListItemAttr()
        self.green.SetBackgroundColour(wxColour(200,255,200))   #light green
        self.orange = wxListItemAttr()
        self.orange.SetBackgroundColour(wxColour(255,200,200))  #light red
        self.result = []
        self.currentItem = None

        EVT_SIZE(self, self.OnSize)

        #node menu
        self.nodemenu = wxMenu()
        self.nodemenu.Append(self.PM_DETAIL, "Show Details")
        self.nodemenu.AppendSeparator()
        self.nodemenu.Append(self.PM_LOCATE, "Locate Source")
       
        EVT_MENU(self, self.PM_DETAIL, self.OnDetail)
        EVT_MENU(self, self.PM_LOCATE, self.OnLocate)

    def OnDetail(self, event=None):
        if self.result[self.currentItem][3]:
            wxMessageBox(self.result[self.currentItem][3], "Result details", wxOK)

    def OnLocate(self, event=None):
        filename, lineno = self.result[self.currentItem][4]
        print "locate",filename, lineno
        starteditor(filename, lineno)

    def OnSize(self, event):
        w = self.GetSize()[0] - self.GetColumnWidth(0) - 30
        if w < 180: w = 180
        self.SetColumnWidth(1, w/2)
        self.SetColumnWidth(2, w/2)

    def Append(self, item):
        self.result.append(item)
        self.SetItemCount(len(self.result))
        #wxYield()
        #self.Refresh()

    def DeleteAllItems(self):
        self.result = []
        wxListCtrl.DeleteAllItems(self)

    def OnItemSelected(self, event):
        self.currentItem = event.m_itemIndex

    def OnItemActivated(self, event):
        self.currentItem = event.m_itemIndex
        self.OnDetail()

    def OnRightClick(self, event):
        pt = event.GetPosition()
        item, flags = self.HitTest(pt)
        if not flags & wxLIST_HITTEST_NOWHERE:
            if self.currentItem is not None:
                self.SetItemState(self.currentItem, 0, wxLIST_STATE_SELECTED  )
            self.currentItem = item
            self.SetItemState(item, wxLIST_STATE_SELECTED, wxLIST_STATE_SELECTED  )
            if self.result[self.currentItem][3]:
                self.PopupMenu(self.nodemenu, pt) #display popup menu

    def OnCopyAsText(self, all=0):
        res = []
        item = -1;
        while 1:
            if all:
                item = self.GetNextItem(item, wxLIST_NEXT_ALL, wxLIST_STATE_DONTCARE);
            else:
                item = self.GetNextItem(item, wxLIST_NEXT_ALL, wxLIST_STATE_SELECTED);
            text = '\t'.join(map(str, self.result[item]))
            res.append(text)
            if item == -1:
                break
        clip = wxClipboard()
        clip.Open()
        clip.SetData( wxTextDataObject('\n'.join(res)) )
        clip.Close()
        
    #---------------------------------------------------
    # These methods are callbacks for implementing the
    # "virtualness" of the list...
    def OnGetItemText(self, row, col):
        #print row, col
        try:
            return str(self.result[row][col])
        except IndexError:
            return ''

    def OnGetItemImage(self, item):
        return 0

    def OnGetItemAttr(self, item):
        if self.result[item][0] == 'Error':
            return self.red
        elif self.result[item][0] == 'Fail':
            return self.orange
        elif self.result[item][0] == 'Ok':
            return self.green
        return None

class TreeView(wxTreeCtrl):
    PM_RUNSEL = wxNewId()
    PM_LOCATE = wxNewId()
    
    def __init__(self, *args, **kwargs):
        wxTreeCtrl.__init__(self, *args, **kwargs)
        EVT_LEFT_DCLICK(self, self.OnLeftDClick)
        EVT_RIGHT_DOWN(self, self.OnRightClick)
        EVT_RIGHT_UP(self, self.OnRightUp)
        EVT_TREE_BEGIN_LABEL_EDIT(self, self.GetId(), self.OnBeginEdit)
        EVT_TREE_END_LABEL_EDIT (self, self.GetId(), self.OnEndEdit)

        #node menu
        self.nodemenu = wxMenu()
        self.nodemenu.Append(self.PM_RUNSEL, "Run selected")
        self.nodemenu.AppendSeparator()
        self.nodemenu.Append(self.PM_LOCATE, "Locate Source")
       
        EVT_MENU(self, self.PM_RUNSEL, self.OnRunSel)
        EVT_MENU(self, self.PM_LOCATE, self.OnLocate)

    #don't allow editnig of node names
    def OnBeginEdit(self, event):  event.Veto()
    def OnEndEdit(self, event):    event.Veto()

    def OnLeftDClick(self, event):
##        pt = event.GetPosition();
##        item, flags = self.HitTest(pt)
##        #print("OnLeftDClick: %s" % self.GetItemText(item))
##        parent = self.GetItemParent(item)
##        #self.SortChildren(parent)
        event.Skip()

    def OnRightClick(self, event):
        pt = event.GetPosition()
        item, flags = self.HitTest(pt)
        if not flags & wxTREE_HITTEST_NOWHERE:
            self.SelectItem(item)
            self.PopupMenu(self.nodemenu, pt) #display node menu

    def OnRightUp(self, event):
        pt = event.GetPosition();
        item, flags = self.HitTest(pt)
        #self.tree.EditLabel(item)

    def OnCompareItems(self, item1, item2):
        t1 = self.GetItemText(item1)
        t2 = self.GetItemText(item2)
        #print('compare: ' + t1 + ' <> ' + t2)
        return cmp(t1,t2)

    def OnRunSel(self, event):
        pass
    def OnLocate(self, event):
        pass

#----------------------------------------------------------------

class ProgressBar(wxGauge):
    def __init__(self, *args, **kwargs):
        wxGauge.__init__(self, *args, **kwargs)
        self.SetBezelFace(5)
        self.SetShadowWidth(5)
        self.increment = 1

    def tick(self):
        self.SetValue(self.GetValue() + self.increment)

#----------------------------------------------------------------

class Frame(wxFrame):
    ID_BUTTON   = wxNewId()
    M_NEW       = wxNewId()
    M_OPEN      = wxNewId()
    M_EXIT      = wxNewId()
    M_COPYALL   = wxNewId()
    M_COPYSEL   = wxNewId()
    M_RUN       = wxNewId()

    def __init__(self, parent, id, title = "Python Unit Testing Frontend"):
        # First, call the base class' __init__ method to create the frame
        wxFrame.__init__(self, parent, id, title, wxPoint(100, 100), wxSize(100, 100))
        #variables
        self.suite = None
        
        #menu
        menuBar = wxMenuBar()
        menu = wxMenu()
        menu.Append(self.M_NEW, "&New")
        menu.Append(self.M_OPEN, "&Open file...")
        menu.AppendSeparator()
        menu.Append(self.M_EXIT, "E&xit")
        EVT_MENU(self, self.M_NEW,  self.OnNew)
        EVT_MENU(self, self.M_OPEN, self.OnMenuOpen)
        EVT_MENU(self, self.M_EXIT, self.OnCloseWindow)
        menuBar.Append(menu, "&File");

        menu = wxMenu()
        menu.Append(self.M_COPYALL, "&Copy all results")
        menu.Append(self.M_COPYSEL, "&Copy selected results")
        EVT_MENU(self, self.M_COPYALL, self.OnCopyAll)
        EVT_MENU(self, self.M_COPYSEL, self.OnCopySelection)
        menuBar.Append(menu, "&Edit");

        menu = wxMenu()
        menu.Append(self.M_RUN, "&Run all")
        EVT_MENU(self, self.M_RUN, self.OnRun)
        menuBar.Append(menu, "&Testing");

        self.SetMenuBar(menuBar)

        #GUI
        panel = wxPanel(self, 0)
        button = wxButton(panel, self.ID_BUTTON, "Run Tests" )
        button.SetDefault()
        EVT_BUTTON(panel, self.ID_BUTTON, self.OnRun )

        self.tree = TreeView(panel, -1, size=(300,250), style=wxTR_HAS_BUTTONS | wxTR_EDIT_LABELS)# | wxTR_MULTIPLE
        
        self.progress =  ProgressBar(panel, -1, 100, style=wxGA_HORIZONTAL|wxGA_SMOOTH)
        
        self.list = ResultView(panel)
        
        sizer = wxBoxSizer(wxVERTICAL)
        sizer.Add(self.tree, 1, wxEXPAND)
        sizer.Add(button, 0, wxEXPAND)
        sizer.Add(self.progress, 0, wxEXPAND)
        sizer.Add(self.list, 1, wxEXPAND)

        panel.SetAutoLayout(1)
        panel.SetSizer(sizer)
        sizer.Fit(panel)

        basesizer = wxBoxSizer(wxVERTICAL)
        basesizer.Add(panel, 1, wxEXPAND)
        self.SetAutoLayout(1)
        self.SetSizer(basesizer)
        self.Fit()

        #create a statusbar
        sb = self.CreateStatusBar(1)
        sb.SetStatusWidths([-1])
        self.SetStatusText('Open a file', 0)
        #update controls
        self.OnNew()

    def UpdateTree(self, root=None, testlist=None):
        if root is None:
            root = self.root
        if testlist is None and self.suite:
            testlist = self.suite._tests #grmpf accessing a _ member, oh well

        if root and testlist:
            for testcase in testlist:
                if isinstance(testcase, unittest.TestSuite):
                    child = self.tree.AppendItem(root, "%s (%d)" % (testcase.__class__.__name__,len(testcase._tests)))
                    self.tree.SetPyData(child, None)
                    self.UpdateTree(child, testcase._tests)
                    #self.tree.SortChildren(child)
                else:
                    child = self.tree.AppendItem(root, "%s" % testcase)
                    self.tree.SetPyData(child, None)
                ##self.tree.SetItemImage(child, idx2, wxTreeItemIcon_Expanded)
                ##self.tree.SetItemSelectedImage(child, idx3)
            self.tree.Expand(root)

    def OnRun(self, event=None):
        """ """
        if self.suite:
            runner = GUITestRunner(self.list, self.progress)
            self.SetStatusText('Runing tests...', 0)
            ln = self.suite.countTestCases()
            self.progress.SetValue(0)
            self.progress.SetRange(ln)
            self.list.DeleteAllItems()
            
            result = runner.run(self.suite)
            
            self.SetStatusText('Ran %d tests, %d errors, %d failures' % (ln, len(result.errors), len(result.failures)), 0)
        else:
            self.SetStatusText('No test found', 0)


    def OnMenuOpen(self, event=None):
        """ """
        dlg = wxFileDialog(self, "Choose a module", ".", "", "*.*", wxOPEN)#|wxMULTIPLE)
        if dlg.ShowModal() == wxID_OK:
##            for path in dlg.GetPaths():
##                log.WriteText('You selected: %s\n' % path)
            self.OnNew()
            self.filename = dlg.GetPath()
            modname, modtype = os.path.splitext(os.path.basename(self.filename))
            if modtype.lower() == '.py':
                moduleToTest = imp.load_source(modname, self.filename, file(self.filename))
            elif modtype.lower() in {'.pyc':0, '.pyo':0}:
                moduleToTest = imp.load_compiled(modname, self.filename, file(self.filename, 'rb'))
            #print moduleToTest, dir(moduleToTest)
            self.suite = unittest.defaultTestLoader.loadTestsFromModule(moduleToTest)
            #print self.suite
        dlg.Destroy()
        self.UpdateTree()

    def OnNew(self, event=None):
        self.list.DeleteAllItems()
        self.tree.DeleteAllItems()
        self.root = self.tree.AddRoot("UnitTests")
        self.tree.SetPyData(self.root, None)
        self.progress.SetValue(0)
        self.suite = None
        self.filename = None

    def OnCopySelection(self,event=None):
        self.list.OnCopyAsText()

    def OnCopyAll(self,event=None):
        self.list.OnCopyAsText(all=1)

    def OnCloseWindow(self, event=None):
        self.Destroy()



#---------------------------------------------------------------------------
# Every wxWindows application must have a class derived from wxApp
class App(wxApp):
    # wxWindows calls this method to initialize the application
    def OnInit(self):
        # Create an instance of our customized Frame class
        frame = Frame(NULL, -1)
        frame.Show(true)
        # Tell wxWindows that this is our main window
        self.SetTopWindow(frame)
        # Return a success flag
        return true

#---------------------------------------------------------------------------
if __name__ == "__main__":
    app = App(0)    # Create an instance of the application class
    app.MainLoop()     # Tell it to start processing events

