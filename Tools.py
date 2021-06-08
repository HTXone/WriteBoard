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
import pygame
import objects

# deferred pygame imports
global pygame
global renderer
global objects

logging.basicConfig(level=logging.DEBUG)

log = logging.getLogger(__name__)


class Tool(object):
    def __init__(self, name, wb):
        self.name = name
        self.wb = wb
        self.viewer = wb.viewer
        self.camera = wb.viewer.camera
        self.obj = None
        self.mouseCursor = "arrow"

    def toolbarItem(self, parent, onActivate):
        btn = wx.Button(parent, label=self.name)
        btn.SetBackgroundColour("#BDBDBD")
        self.btn = btn
        btn.Bind(wx.EVT_BUTTON, lambda evt: onActivate(self,self.btn), btn)

        return btn

    def activate(self):
        pass

    def deactivate(self):
        pass

    def startPos(self, x, y):
        pass

    def addPos(self, x, y):
        pass

    def screenPoint(self, x, y):
        return numpy.array([x, y]) - self.camera.pos

    def end(self, x, y):
        self.obj = None

class SelectTool(Tool):
    def __init__(self, wb):
        Tool.__init__(self, "select", wb)
        self.noRect = pygame.Rect(0, 0, 0, 0)

    def reset(self):
        self.selectionChooserRect = objects.Rectangle({"colour":(0,0,0,50), "rect":self.noRect.copy()}, self.viewer, isUserObject=False)
        self.selectedAreaRect = objects.Rectangle({"colour":(0,255,150,50), "rect":self.noRect.copy()}, self.viewer, isUserObject=False)
        self.selectedObjects = None
        self.selectMode = True

    def activate(self):
        self.reset()

    def deactivate(self):
        self.selectedAreaRect.kill()
        self.selectionChooserRect.kill()

    def startPos(self, x, y):
        self.selectMode = not self.selectedAreaRect.absRect().contains(pygame.Rect(x, y, 1, 1))
        log.debug("selectMode: %s", self.selectMode)
        self.pos1 = self.screenPoint(x, y)
        self.pos2 = self.pos1
        self.offset = numpy.array([0, 0])
        if self.selectMode:
            self.selectedAreaRect.kill()
            self.selectedAreaRect.rect = self.noRect.copy()
            self.selectionChooserRect.pos = (x, y)
            self.selectionChooserRect.setSize(1, 1)
            self.wb.addObject(self.selectionChooserRect)

    def addPos(self, x, y):
        self.pos2= self.screenPoint(x, y)
        if self.selectMode:
            width = self.pos2[0] - self.pos1[0]
            height = self.pos2[1] - self.pos1[1]
            self.selectionChooserRect.setSize(width, height)
        else: # moving selection
            offset = self.pos2 - self.pos1
            self.offset[0] += offset[0]
            self.offset[1] += offset[1]
            self.pos1 = self.pos2
            for o in self.selectedObjects:
                o.offset(*offset)
            self.selectedAreaRect.offset(*offset)

    def end(self, x, y):
        self.processingInputs = False
        if self.selectMode:
            width = self.pos2[0] - self.pos1[0]
            height = self.pos2[1] - self.pos1[1]
            objs =list(filter(lambda o: o.rect.colliderect(pygame.Rect(self.pos1[0], self.pos1[1], width, height)), self.viewer.renderer.userObjects.sprites()))
            log.debug("selected: %s", str(objs))
            self.selectedObjects = objs
            self.selectionChooserRect.kill()
            if len(objs) > 0:
                r = objects.boundingRect(objs)
                self.selectedAreaRect.pos = r.topleft
                self.selectedAreaRect.setSize(*r.size)
                self.wb.addObject(self.selectedAreaRect)
        else:
            self.wb.onObjectsMoved(self.offset, *[o.id for o in self.selectedObjects])

class RectTool(Tool):
    def __init__(self, wb):
        Tool.__init__(self, "rectangle", wb)

    def startPos(self, x, y):
        print(x,y)
        self.obj = objects.Rectangle({"rect": pygame.Rect(x, y, 10, 10), "colour": self.wb.getColour()}, self.viewer)
        return self.obj

    # 鼠标移动时调用，持续改为形状大小
    def addPos(self, x, y):
        if self.obj is None: return
        topLeft = numpy.array([self.obj.rect.left, self.obj.rect.top])
        pos = numpy.array([x, y]) - self.camera.pos
        dim = pos - topLeft
        if dim[0] > 0 and dim[1] > 0:
            self.obj.setSize(dim[0], dim[1])

    # 用户拖拽鼠标松开后调用，只是清空了obj
    def end(self, x, y):
        if self.obj is not None: self.wb.onObjectCreationCompleted(self.obj) #这里没用，空的钩子
        super(RectTool, self).end(x, y)

class LineTool(Tool):
    def __init__(self, wb):
        Tool.__init__(self, "line", wb)

    def startPos(self, x, y):
        # print(x,y)
        self.obj = objects.Line({"rect": pygame.Rect(x, y, 10, 10), "colour": self.wb.getColour(),"start_pos": (x,y),"end_pos": (x+10,y+10)}, self.viewer)
        print(f"{self.obj.pos},{x},{y}")
        return self.obj

    # 鼠标移动时调用，持续改为形状大小
    def addPos(self, x, y):
        if self.obj is None: return
        self.obj.setEnd((x,y))

    # 用户拖拽鼠标松开后调用，只是清空了obj
    def end(self, x, y):
        if self.obj is not None: self.wb.onObjectCreationCompleted(self.obj) #这里没用，空的钩子
        super(LineTool, self).end(x, y)

class EllipseTool(Tool):
    def __init__(self, wb):
        Tool.__init__(self, "ellipse", wb)

    def startPos(self, x, y):
        self.obj = objects.Ellipse({"rect": pygame.Rect(x, y, 10, 10), "colour": self.wb.getColour()}, self.viewer)
        return self.obj

    # 鼠标移动时调用，持续改为形状大小
    def addPos(self, x, y):
        if self.obj is None: return
        topLeft = numpy.array([self.obj.rect.left, self.obj.rect.top])
        pos = numpy.array([x, y]) - self.camera.pos
        dim = pos - topLeft
        if dim[0] > 0 and dim[1] > 0:
            self.obj.setSize(dim[0], dim[1])

    # 用户拖拽鼠标松开后调用，只是清空了obj
    def end(self, x, y):
        if self.obj is not None: self.wb.onObjectCreationCompleted(self.obj) #这里没用，空的钩子
        super(EllipseTool, self).end(x, y)

class CircleTool(Tool):
    def __init__(self, wb):
        Tool.__init__(self, "circle", wb)

    def startPos(self, x, y):
        # print("按下")
        # print(x,y)
        self.obj = objects.Circle({"rect": pygame.Rect(x, y, 10, 10), "colour": self.wb.getColour()},self.viewer)
        # print(f"created circle{pygame.Rect(x, y, 10, 10).center},{pygame.Rect(x-5, y-5, 10, 10).left}")
        return self.obj

    # 鼠标移动时调用，持续改为形状大小
    def addPos(self, x, y):
        if self.obj is None: return
        left = self.obj.rect.left
        pos = numpy.array([x, y]) - self.camera.pos
        # print(f"pos={pos},centerx={centerx},left={self.obj.rect.left}")
        dim = pos[0] - left
        if dim>0:
            print(f"dim = {int(dim)}")
            self.obj.setRadius(int(dim/2))
        # print("changed circle")


    # 用户拖拽鼠标松开后调用，只是清空了obj
    def end(self, x, y):
        if self.obj is not None: self.wb.onObjectCreationCompleted(self.obj) #这里没用，空的钩子
        super(CircleTool, self).end(x, y)

class EraserTool(Tool):
    def __init__(self, wb):
        Tool.__init__(self, "eraser", wb)
        self.mouseCursor = "delete"

    def startPos(self, x, y):
        self.erase(x, y)

    def erase(self, x, y):
        x, y = self.screenPoint(x, y)
        sprites = self.viewer.renderer.userObjects.sprites() # TODO
        matches =list(filter(lambda o: o.rect.collidepoint((x, y)), sprites))
        #log.debug("eraser matches: %s", matches)
        if len(matches) > 0:
            ids = [o.id for o in matches]
            self.wb.deleteObjects(*ids)

    def addPos(self, x, y):
        self.erase(x, y)

class PenTool(Tool):
    def __init__(self, wb):
        Tool.__init__(self, "pen", wb)
        self.lineWidth = 3
        self.syncWhileDrawing = True
        self.lastProcessTime = 0
        self.mouseCursor = "pen"

    def startPos(self, x, y):
        self.pointBuffer = []
        margin = 2 * self.lineWidth
        d = dict(lineWidth=self.lineWidth, colour=self.wb.getColour())
        if not self.syncWhileDrawing:
            self.obj = objects.Scribble(d, self.viewer, startPoint=(x,y))
        else:
            self.obj = objects.PointBasedScribble(d, self.viewer, startPoint=(x,y))
        self.obj.addPoints([(x, y)])
        if self.syncWhileDrawing: self.wb.onObjectCreationCompleted(self.obj)
        return self.obj

    def addPos(self, x, y):
        if self.obj is None: return
        self.obj.addPoints([(x, y)])
        if self.syncWhileDrawing:
            self.pointBuffer.append((x, y))
            t = time.time()
            if t - self.lastProcessTime >= 0.5:
                self.lastProcessTime = t
                self.wb.onObjectUpdated(self.obj.id, "addPoints", (self.pointBuffer,))
                self.pointBuffer = []

    def end(self, x, y):
        self.obj.endDrawing()
        if not self.syncWhileDrawing:
            self.wb.onObjectCreationCompleted(self.obj)
        else:
            pass
            self.wb.onObjectUpdated(self.obj.id, "addPoints", (self.pointBuffer,))
            self.wb.onObjectUpdated(self.obj.id, "endDrawing", ())
        super(PenTool, self).end(x, y)

class ColourTool(Tool):
    def __init__(self, wb):
        Tool.__init__(self, "colour", wb)

    def toolbarItem(self, parent, onActivate):
        self.picker = wx.ColourPickerCtrl(parent)
        return self.picker

    def getColour(self):
        return self.picker.GetColour()

class TextTool(Tool):
    def __init__(self, wb):
        Tool.__init__(self, "text", wb)
        self.mouseCursor = "text"

    def end(self, x, y):
        wx.CallAfter(self.enterText, x, y)

    def enterText(self, x, y):
        sx, sy = self.screenPoint(x, y)
        textSprites = [x for x in filter(lambda o: isinstance(o, objects.Text), self.viewer.renderer.userObjects.sprites())]
        matches = [x for x in filter(lambda o: o.rect.collidepoint((sx, sy)), textSprites)]
        isNewObject = False
        if len(matches) > 0:
            obj = matches[0]
        else:
            isNewObject = True
            obj = objects.Text({"pos": (x, y), "text": "", "colour": self.wb.getColour(), "fontName": self.wb.getFontName(), "fontSize": self.wb.getFontSize()}, self.viewer)
            self.wb.addObject(obj)
            self.wb.onObjectCreationCompleted(obj)
        self.obj = obj
        dlg = TextTool.TextEditDialog(self.wb, "" if obj is None else obj.text, onChange=self.textChanged)
        if dlg.ShowModal() == wx.ID_OK:
            text = dlg.GetValue()
            if text.strip() == "": # delete object
                self.wb.deleteObjects(obj.id)
        else:
            if isNewObject:
                self.wb.deleteObjects(obj.id)

    def textChanged(self, text):
        self.obj.setText(text)
        self.wb.onObjectUpdated(self.obj.id, "setText", (text,))

    class TextEditDialog(wx.Dialog):
        def __init__(self, parent, text="", onChange=None, **kw):
            wx.Dialog.__init__(self, parent, style=wx.RESIZE_BORDER | wx.FRAME_TOOL_WINDOW | wx.CAPTION, **kw)

            self.textControl = wx.TextCtrl(self, 1, value=text, style=wx.TE_MULTILINE)
            if onChange is not None:
                self.textControl.Bind(wx.EVT_TEXT, lambda evt: onChange(self.GetValue()), self.textControl)

            hbox2 = wx.BoxSizer(wx.HORIZONTAL)
            okButton = wx.Button(self, id=wx.ID_OK, label='Ok')
            closeButton = wx.Button(self, id=wx.ID_CANCEL, label='Cancel')
            hbox2.Add(okButton)
            hbox2.Add(closeButton, flag=wx.LEFT, border=5)

            vbox = wx.BoxSizer(wx.VERTICAL)
            vbox.Add(self.textControl, proportion=1,
                flag=wx.ALL|wx.EXPAND, border=5)
            vbox.Add(hbox2,
                flag=wx.ALIGN_CENTER|wx.TOP|wx.BOTTOM, border=10)

            self.SetSizer(vbox)

            self.SetSize((400, 300))
            self.SetTitle("Enter text")

        def GetValue(self):
            return self.textControl.GetValue()

class FontTool(Tool):
    def __init__(self, wb):
        Tool.__init__(self, "font", wb)

    def toolbarItem(self, parent, onActivate):
        font = wx.Font(18, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL, faceName="Arial")
        self.picker = wx.FontPickerCtrl(parent, style=wx.FNTP_FONTDESC_AS_LABEL)
        self.picker.SetSelectedFont(font)
        return self.picker

    def getFont(self):
        return self.picker.GetSelectedFont()

class ShapeTool(Tool):
    def __init__(self,wb):
        Tool.__init__(self,"shape",wb)
        self.mouseCursor = "shape"

    def startPos(self, x, y):
        self.objectReshape(x,y)
        if self.otype[0] == 'Rectangle':
            return self.RectStart()
        if self.otype[0] == 'Circle':
            return self.CircleStart()
        if self.otype[0] == 'Ellipse':
            return self.EllipseStart()
        if self.otype[0] == 'Line':
            return self.LineStart()
        return None

    def objectReshape(self,x,y):
        x,y = self.screenPoint(x,y)
        sprites = self.viewer.renderer.userObjects.sprites()  # TODO
        matches = list(filter(lambda o: o.rect.collidepoint((x, y)), sprites))
        # log.debug("eraser matches: %s", matches)
        if len(matches) > 0:
            self.otype = [type(matches[0]).__name__]
            self.oid = matches[0].id
            print(self.otype,self.oid)
            self.pos = matches[0].pos
            print(self.pos)
        ids = [self.oid]
        self.wb.deleteObjects(*ids)

    def LineStart(self):
        x,y = self.pos
        self.obj = objects.Line({"rect": pygame.Rect(x, y, 10, 10), "colour": self.wb.getColour(), "start_pos": (x, y),
                                 "end_pos": (x + 10, y + 10)}, self.viewer)
        print(f"{self.obj.pos},{x},{y}")
        return self.obj

    def RectStart(self):
        x, y = self.pos
        print(x, y)
        self.obj = objects.Rectangle({"rect": pygame.Rect(x, y, 10, 10), "colour": self.wb.getColour()}, self.viewer)
        return self.obj

    def EllipseStart(self):
        x, y = self.pos
        self.obj = objects.Ellipse({"rect": pygame.Rect(x, y, 10, 10), "colour": self.wb.getColour()}, self.viewer)
        return self.obj

    def CircleStart(self):
        x, y = self.pos
        self.obj = objects.Circle({"rect": pygame.Rect(x, y, 10, 10), "colour": self.wb.getColour()}, self.viewer)
        # print(f"created circle{pygame.Rect(x, y, 10, 10).center},{pygame.Rect(x-5, y-5, 10, 10).left}")
        return self.obj

    def addPos(self, x, y):
        if self.otype[0] == 'Rectangle':
            return self.addRectPos(x,y)
        if self.otype[0] == 'Circle':
            return self.addCirclePos(x,y)
        if self.otype[0] == 'Ellipse':
            return self.addEllipsePos(x,y)
        if self.otype[0] == 'Line':
            return self.addLinePos(x,y)

    def addCirclePos(self, x, y):
        if self.obj is None: return
        left = self.obj.rect.left
        pos = numpy.array([x, y]) - self.camera.pos
        # print(f"pos={pos},centerx={centerx},left={self.obj.rect.left}")
        dim = pos[0] - left
        if dim > 0:
            print(f"dim = {int(dim)}")
            self.obj.setRadius(int(dim / 2))

        # 鼠标移动时调用，持续改为形状大小

    def addEllipsePos(self, x, y):
        if self.obj is None: return
        topLeft = numpy.array([self.obj.rect.left, self.obj.rect.top])
        pos = numpy.array([x, y]) - self.camera.pos
        dim = pos - topLeft
        if dim[0] > 0 and dim[1] > 0:
            self.obj.setSize(dim[0], dim[1])

        # 鼠标移动时调用，持续改为形状大小

    def addRectPos(self, x, y):
        if self.obj is None: return
        topLeft = numpy.array([self.obj.rect.left, self.obj.rect.top])
        pos = numpy.array([x, y]) - self.camera.pos
        dim = pos - topLeft
        if dim[0] > 0 and dim[1] > 0:
            self.obj.setSize(dim[0], dim[1])

        # 鼠标移动时调用，持续改为形状大小

    def addLinePos(self, x, y):
        if self.obj is None: return
        self.obj.setEnd((x, y))

    def end(self, x, y):
        self.reshapeTime = 0
        if self.otype[0] == 'Rectangle' and not self.reshapeTime:
            self.RectEnd(x,y)
        if self.otype[0] == 'Circle' and not self.reshapeTime:
            self.CircleEnd(x,y)
        if self.otype[0] == 'Ellipse' and not self.reshapeTime:
            self.EllipseEnd(x,y)
        if self.otype[0] == 'Line' and not self.reshapeTime:
            self.LineEnd(x,y)
        self.otype[0] = ''
        self.obj = None
        # self.reshapeTime+=1
        # print(self.reshapeTime)

        # 用户拖拽鼠标松开后调用，只是清空了obj
    def CircleEnd(self, x, y):
        if self.obj is not None: self.wb.onObjectCreationCompleted(self.obj)  # 这里没用，空的钩子
        # super(CircleTool, self).end(x, y)

        # 用户拖拽鼠标松开后调用，只是清空了obj
    def EllipseEnd(self, x, y):
        if self.obj is not None: self.wb.onObjectCreationCompleted(self.obj)  # 这里没用，空的钩子
        # super(EllipseTool, self).end(x, y)

    # 用户拖拽鼠标松开后调用，只是清空了obj
    def RectEnd(self, x, y):
        if self.obj is not None: self.wb.onObjectCreationCompleted(self.obj) #这里没用，空的钩子
        # super(RectTool, self).end(x, y)
    # 用户拖拽鼠标松开后调用，只是清空了obj
    def LineEnd(self, x, y):
        if self.obj is not None: self.wb.onObjectCreationCompleted(self.obj) #这里没用，空的钩子
        # super(LineTool, self).end(x, y)
