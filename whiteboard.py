# (C) 2014 by Dominik Jain (djain@gmx.net)

import wx
import os
import _thread as thread
import traceback
import sys
import numpy
from pprint import pprint
import pickle
import time
import logging
import platform
import utils
from Tools import *
from ToolsFactory import *

from pygameViewer import pygameViewer

# deferred pygame imports
global pygame
global renderer
global objects


logging.basicConfig(level=logging.DEBUG)

log = logging.getLogger(__name__)

# pygame的显示、处理事件

#白板
class Whiteboard(wx.Frame):
    def __init__(self, strTitle, WindowsSize=(1400, 1000)):
        self.isMultiWindow = platform.system() != "Windows"

        self.ToolsFactoryName = 'defalutToolsFactory'
        parent = None
        size = WindowsSize
        style = wx.DEFAULT_FRAME_STYLE

        wx.Frame.__init__(self, parent, wx.ID_ANY, strTitle, size=size, style=style)
        self.pnlSDL = ShowPanel(self, -1, WindowsSize, strTitle)
        self.clipboard = wx.Clipboard()

        # Menu Bar
        self.frame_menubar = wx.MenuBar()
        self.SetMenuBar(self.frame_menubar)
        # - file Menu
        self.file_menu = wx.Menu()
        self.file_menu.Append(101, "&Open", "Open contents from file")
        self.file_menu.Append(102, "&Save", "Save contents to file")
        self.file_menu.Append(104, "&Export", "Export contents to image file")
        self.file_menu.AppendSeparator()
        self.file_menu.Append(103, "&Exit", "Quit the application")
        self.Bind(wx.EVT_MENU, self.onOpen, id=101)
        self.Bind(wx.EVT_MENU, self.onSave, id=102)
        self.Bind(wx.EVT_MENU, self.onExport, id=104)
        self.Bind(wx.EVT_MENU, self.onExit, id=103)
        # - edit menu
        self.edit_menu = wx.Menu()
        self.edit_menu.Append(201, "&Paste image", "Paste an image")
        self.Bind(wx.EVT_MENU, self.onPasteImage, id=201)

        menus = ((self.file_menu, "File"), (self.edit_menu, "Edit"))

        for menu, name in menus:
            self.frame_menubar.Append(menu, name)

        self.viewer = self.pnlSDL.viewer

        self.ToolsFactory = eval(self.ToolsFactoryName)()

        toolbar = wx.Panel(self)
        self.toolbar = toolbar
        self.fontTool = self.ToolsFactory.getFontTool(self)
        self.colourTool = self.ToolsFactory.getColourTool(self)
        self.penTool = self.ToolsFactory.getPenTool(self)
        self.lineTool = self.ToolsFactory.getLineTool(self)
        self.textTool = self.ToolsFactory.getTextTool(self)
        self.rectTool = self.ToolsFactory.getRectTool(self)
        self.circleTool = self.ToolsFactory.getCircleTool(self)
        self.ellipseTool = self.ToolsFactory.getEllipseTool(self)
        self.eraserTool = self.ToolsFactory.getEraserTool(self)
        self.selectTool = self.ToolsFactory.getSelectTool(self)
        self.shapeTool = self.ToolsFactory.getShapeTool(self)
        tools = [
             self.fontTool,
             self.colourTool,
             self.penTool,
             self.lineTool,
             self.rectTool,
             self.circleTool,
             self.ellipseTool,
             self.textTool,
             self.selectTool,
             self.eraserTool,
            self.shapeTool
        ]

        box = wx.BoxSizer(wx.VERTICAL)
        self.btnList = []
        for i, tool in enumerate(tools):
            control = tool.toolbarItem(toolbar, self.onSelectTool)
            self.btnList.append(control)
            box.Add(control, 0, flag=wx.EXPAND)
        toolbar.SetSizer(box)

        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(toolbar, flag=wx.EXPAND | wx.BOTTOM, border=0)
        sizer.Add(self.pnlSDL, 1, flag=wx.EXPAND)
        self.SetSizer(sizer)


    def startRendering(self):
        self.pnlSDL.startRun()

    def onSelectTool(self, tool,btn):
        for i in self.btnList:
            i.SetBackgroundColour("#BDBDBD")
        self.viewer.setActiveTool(tool)
        btn.SetBackgroundColour("#5858FA")
        log.debug("selected tool %s" % tool.name)

    def getColour(self):
        return self.colourTool.getColour()

    def getFontName(self):
        return self.fontTool.getFont().GetFaceName()

    def getFontSize(self):
        return self.fontTool.getFont().GetPointSize()

    def onOpen(self):
        log.debug("selected 'open'")
        dlg = wx.FileDialog(self, "Choose a file", ".", "", "*.wb", wx.FD_OPEN)
        if dlg.ShowModal() == wx.ID_OK:
            path = os.path.join(dlg.GetDirectory(), dlg.GetFilename())
            dlg.Destroy()

            f = open(path, "rb")
            d = pickle.load(f)
            f.close()
            self.viewer.setObjects([utils.deserialize(o, self.viewer) for o in d["objects"]])

    def onSave(self):
        log.debug("selected 'save'")
        dlg = wx.FileDialog(self, "Choose a file", ".", "", "*.wb", wx.FD_SAVE)
        if dlg.ShowModal() == wx.ID_OK:
            path = os.path.join(dlg.GetDirectory(), dlg.GetFilename())
            dlg.Destroy()

            f = open(path, "wb")
            pickle.dump({"objects": [o.serialize() for o in self.viewer.getObjects()]}, f)
            f.close()

    def onExport(self):
        log.debug("selected 'export'")
        dlg = wx.FileDialog(self, "Choose a file", ".", "", "*.png", wx.FD_SAVE)
        if dlg.ShowModal() == wx.ID_OK:
            path = os.path.join(dlg.GetDirectory(), dlg.GetFilename())
            dlg.Destroy()

            objs = self.getObjects()
            rect = utils.boundingRect(objs)
            translate = numpy.array(rect.topleft) * -1
            surface = pygame.Surface(rect.size)
            surface.fill((255,255,255))
            for o in objs:
                surface.blit(o.image, numpy.array(o.absRect().topleft) + translate)
            pygame.image.save(surface, path)

    def onExit(self):
        self.viewer.running = False
        sys.exit(0)

    def onKeyDown(self, event):
        pass

    def onPasteImage(self, event):
        dlg = wx.FileDialog(self, "Open WD file", wildcard="WriteBoard files (*.wb)|*.wb",
                            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST)
        filename = ""
        if dlg.ShowModal() == wx.ID_OK:
            filename = dlg.GetPath()
            image = pygame.image.load(r'{}'.format(filename))
            obj = objects.Image({"image": image, "rect": image.get_rect()}, self.viewer, isUserObject=True)
            self.addObject(obj)
            self.onObjectCreationCompleted(obj)

    def addObject(self, object):
        self.viewer.addObject(object)

    def onObjectCreationCompleted(self, object):
        pass

    def onObjectsDeleted(self, *objectIds):
        pass

    def onObjectsMoved(self, offset, *objectIds):
        pass

    def onCursorMoved(self, pos):
        pass

    def onObjectUpdated(self, objectId, operation, args):
        pass

    def deleteObjects(self, *objectIds):
        deletedIds = self.viewer.deleteObjects(*objectIds)
        if len(deletedIds) > 0:
            self.onObjectsDeleted(*deletedIds)

    def moveObjects(self, offset, *objectIds):
        self.viewer.moveObjects(offset, *objectIds)

    def setObjects(self, objects):
        self.viewer.setObjects(objects)

    def getObjects(self):
        return self.viewer.getObjects()

    def addUser(self, name):
        # self.viewer.addUser(name)
        None

    # def deleteUser(self, name):
    #     self.viewer.deleteUser(name)

    # def deleteAllUsers(self):
    #     self.viewer.deleteAllUsers()

    # def moveUserCursor(self, userName, pos):
    #     self.viewer.moveUserCursor(userName, pos)

    def errorDialog(self, errormessage):
        """Display a simple error dialog.
        """
        edialog = wx.MessageDialog(self, errormessage, 'Error', wx.OK | wx.ICON_ERROR)
        edialog.ShowModal()

    def questionDialog(self, message, title = "Error"):
        """Displays a yes/no dialog, returning true if the user clicked yes, false otherwise
        """
        return wx.MessageDialog(self, message, title, wx.YES_NO | wx.ICON_QUESTION).ShowModal() == wx.ID_YES

#WX显示窗口
class ShowPanel(wx.Panel):
    def __init__(self, parent, ID, tplSize, caption):
        global pygame, level, renderer, objects, canvas
        wx.Panel.__init__(self, parent, ID, size=tplSize)   #初始化
        self.Fit()

        os.environ['SDL_WINDOWID'] = str(self.GetHandle())    #将pygame嵌套在wx中
        os.environ['SDL_VIDEODRIVER'] = 'windib'

        import pygame  # 加载全局组件
        import renderer
        import objects

        #初始化pygame
        self.pygameInit(caption)

        # 初始化Viewer
        # 与pygame窗口
        self.viewer = pygameViewer(tplSize, parent)

    #关闭进程
    def __del__(self):
        self.viewer.running = False

    def pygameInit(self,caption,iconPath = "./img/icon.png"):
        pygame.display.init()
        pygame.font.init()

        icon = pygame.image.load(iconPath)  # 加载图标
        pygame.display.set_icon(icon)
        pygame.display.set_caption(caption)

    def startRun(self,thread_args = ()):
        # 开启pygame线程
        args = thread_args
        thread.start_new_thread(self.viewer.TheadRunning, args)

#WX扩展窗口
class ExpandPanel(ShowPanel):

    def __init__(self,showPanel):
        self.parentPanel = showPanel

    def __del__(self):
        self.kill()

    def ExpandTools(self,Tools):

        toolbar = wx.Panel(self)
        self.toolbar = toolbar
        box = wx.BoxSizer(wx.VERTICAL)
        self.btnList = []
        for i, tool in enumerate(Tools):
            control = tool.toolbarItem(toolbar, self.onSelectTool)
            self.btnList.append(control)
            box.Add(control, 0, flag=wx.EXPAND)
        toolbar.SetSizer(box)

    def addTools(self,Tool):
        self.toolbar.append(Tool)

    def deleteTools(self,Tool):
        self.toolbar.pop(Tool)

if __name__ == '__main__':      #测试
    app = wx.App(False)
    whiteboard = Whiteboard("WriteBoard")
    whiteboard.startRendering()
    whiteboard.Show()
    app.MainLoop()
