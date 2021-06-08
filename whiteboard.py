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

# deferred pygame imports
global pygame
global renderer
global objects

logging.basicConfig(level=logging.DEBUG)

log = logging.getLogger(__name__)

#核心显示panel，图形在这里通过viewer显示
class SDLPanel(wx.Panel):
    def __init__(self, parent, ID, tplSize, caption):
        global pygame, level, renderer, objects, canvas
        wx.Panel.__init__(self, parent, ID, size=tplSize)
        self.Fit()

        os.environ['SDL_WINDOWID'] = str(self.GetHandle())
        os.environ['SDL_VIDEODRIVER'] = 'windib'
        import pygame  # this has to happen after setting the environment variables.
        import renderer
        import objects

        pygame.display.init()
        pygame.font.init()

        pygame.display.set_caption(caption)

        icon = pygame.image.load("./img/icon.png")
        pygame.display.set_icon(icon)

        # initialize level viewer
        # 与pygame相关逻辑，工具窗口通过这个接口改变工具状态
        self.viewer = Viewer(tplSize, parent)

    def startRendering(self):
        # start pygame thread
        thread.start_new_thread(self.viewer.mainLoop, ())

    def __del__(self):
        self.viewer.running = False


class Camera(object): # 就是一个记录坐标
    def __init__(self, pos, game):
        self.translate = numpy.array([-game.width / 2, -game.height / 2])
        self.pos = pos + self.translate

    def update(self, game):
        return self.pos

    def offset(self, o):
        self.pos += o

# 显示、处理事件
class Viewer(object):
    def __init__(self, size, app):
        self.screen = pygame.display.set_mode(size, pygame.RESIZABLE)
        self.width, self.height = size
        self.running = False
        self.renderer = renderer.WhiteboardRenderer(self)
        self.camera = Camera((0, 0), self)
        self.app = app
        self.objectsById = {}
        self.userCursors = {}
        self.isLeftMouseButtonDown = False
        self.scroll = False
        self.activeTool = None
        pygame.mouse.set_visible(False)
        self.mouseCursors = {}
        self.mouseCursors["arrow"] = objects.ImageFromResource(os.path.join("img", "Arrow.png"), self, layer=1000, ppAlpha=True)
        self.mouseCursors["pen"] = objects.ImageFromResource(os.path.join("img", "Handwriting.png"), self, layer=1000, ppAlpha=True, alignment=objects.Alignment.BOTTOM_LEFT)
        self.mouseCursors["text"] = objects.ImageFromResource(os.path.join("img", "IBeam.png"), self, layer=1000, ppAlpha=True)
        self.mouseCursors["delete"] = objects.ImageFromResource(os.path.join("img", "Delete.png"), self, layer=1000, ppAlpha=True)
        self.mouseCursors["hand"] = objects.ImageFromResource(os.path.join("img", "Hand.png"), self, layer=1000, ppAlpha=True, alignment=objects.Alignment.CENTRE)
        self.mouseCursor = None
        self.mouseCursorName = None
        self.haveMouseFocus = False
        self.setMouseCursor("arrow")

    def update(self): # 可能只更新对象状态，并不更新显示
        self.camera.update(self) # 刷新视角
        self.renderer.update(self) # 刷新显示对象

    def draw(self): # 根据状态重绘屏幕
        self.renderer.draw()

    def mainLoop(self):
        self.running = True
        try:
            clock = pygame.time.Clock()
            while self.running:
                try:
                    clock.tick(60)
                    for event in pygame.event.get():
                        # log(event)

                        # 处理用户动作——在这里改变状态
                        if event.type == pygame.MOUSEBUTTONDOWN:
                            x, y = event.pos
                            if event.button == 3:
                                self.onRightMouseButtonDown(x, y)
                            elif event.button == 1:
                                self.onLeftMouseButtonDown(x, y)

                        elif event.type == pygame.MOUSEBUTTONUP:
                            if event.button == 3:
                                self.onRightMouseButtonUp()
                            elif event.button == 1:
                                self.onLeftMouseButtonUp(*event.pos)

                        elif event.type == pygame.MOUSEMOTION:
                            self.onMouseMove(*(event.pos + event.rel))

                        elif event.type == pygame.KEYDOWN:
                            self.app.onKeyDown(event)

                        elif event.type == pygame.VIDEORESIZE:
                            log.debug("resized window: %s", event.size)
                            self.screen = pygame.display.set_mode(event.size, pygame.RESIZABLE)
                            self.width, self.height = event.size
                            self.renderer.setBackgroundSize(event.size)

                        elif event.type == pygame.ACTIVEEVENT:
                            if event.state == 1:
                                self.haveMouseFocus = event.gain
                                if event.gain:
                                    self.renderer.add(self.mouseCursor)
                                else:
                                    self.mouseCursor.kill()
                    # 在这里更新和显示
                    self.update()
                    self.draw()
                except:
                    log.warning("rendering pass failed")
                    e, v, tb = sys.exc_info()
                    print(v)
                    traceback.print_tb(tb)

        except:
            e, v, tb = sys.exc_info()
            print(v)
            traceback.print_tb(tb)

    def setActiveTool(self, tool):
        if self.activeTool is not None:
            self.activeTool.deactivate()
        self.activeTool = tool
        self.setMouseCursor(tool.mouseCursor)
        tool.activate()

    def setMouseCursor(self, cursorName):
        if cursorName not in self.mouseCursors:
            cursorName = "arrow"
        self.mouseCursorName = cursorName
        if self.mouseCursor is not None: self.mouseCursor.kill()
        self.mouseCursor = self.mouseCursors[cursorName]
        if self.haveMouseFocus:
            self.renderer.add(self.mouseCursor)

    def setObjects(self, objects):
        for o in self.getObjects():
            o.kill()
        for o in objects:
            self.addObject(o)

    def getObjects(self):
        return self.renderer.userObjects.sprites()

    def addObject(self, object):
        self.objectsById[object.id] = object
        self.renderer.add(object)

    def deleteObjects(self, *ids):
        deletedIds = []
        for id in ids:
            obj = self.objectsById.get(id)
            if obj is not None:
                obj.kill()
                del self.objectsById[id]
                deletedIds.append(id)
        return deletedIds

    def moveObjects(self, offset, *ids):
        for id in ids:
            obj = self.objectsById.get(id)
            if obj is not None:
                obj.offset(*offset)

    def addUser(self, name):
        sprite = objects.ImageFromResource(os.path.join("img", "HandPointer.png"), self, layer=1000, ppAlpha=True)
        self.addObject(sprite)
        self.userCursors[name] = sprite
        return sprite

    def deleteUser(self, name):
        sprite = self.userCursors.get(name)
        if sprite is not None:
            sprite.kill()

    def deleteAllUsers(self):
        for name in self.userCursors:
            self.deleteUser(name)

    def moveUserCursor(self, userName, pos):
        sprite = self.userCursors.get(userName)
        if sprite is not None:
            sprite.pos = pos

    def onRightMouseButtonDown(self, x, y):
        self.prevMouseCursorName = self.mouseCursorName
        self.setMouseCursor("hand")
        self.scroll = True

    def onLeftMouseButtonDown(self, x, y): # 鼠标按下时创建图形对象
        self.isLeftMouseButtonDown = True
        if self.activeTool is not None:
            pos = numpy.array([x, y]) + self.camera.pos
            createdObject = self.activeTool.startPos(pos[0], pos[1])
            if createdObject is not None:
                self.addObject(createdObject)

    def onRightMouseButtonUp(self):
        self.scroll = False
        self.setMouseCursor(self.prevMouseCursorName)

    def onLeftMouseButtonUp(self, x, y):
        self.isLeftMouseButtonDown = False
        pos = numpy.array([x, y]) + self.camera.pos
        if self.activeTool is not None:
            self.activeTool.end(*pos)

    def onMouseMove(self, x, y, dx, dy):
        pos = numpy.array([x, y]) + self.camera.pos
        self.mouseCursor.pos = pos

        if self.scroll:
            self.camera.offset(numpy.array([-dx, -dy]))

        if self.isLeftMouseButtonDown and self.activeTool is not None:
            self.activeTool.addPos(*pos)

        self.app.onCursorMoved(pos)

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


class Whiteboard(wx.Frame):
    def __init__(self, strTitle, canvasSize=(1200, 1000)):
        self.isMultiWindow = platform.system() != "Windows"
        parent = None
        size = canvasSize
        style = wx.DEFAULT_FRAME_STYLE

        wx.Frame.__init__(self, parent, wx.ID_ANY, strTitle, size=size, style=style)
        self.pnlSDL = SDLPanel(self, -1, canvasSize, strTitle)
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

        toolbar = wx.Panel(self)
        self.toolbar = toolbar
        self.fontTool = FontTool(self)
        self.colourTool = ColourTool(self)
        self.penTool = PenTool(self)
        self.lineTool = LineTool(self)
        self.textTool = TextTool(self)
        self.rectTool = RectTool(self)
        self.circleTool = CircleTool(self)
        self.ellipseTool = EllipseTool(self)
        self.eraserTool = EraserTool(self)
        self.selectTool = SelectTool(self)
        self.shapeTool = ShapeTool(self)
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
        # self.toolKeys = {
        #     (pygame.K_p, pygame.KMOD_NONE): self.penTool,
        #     (pygame.K_d, pygame.KMOD_NONE): self.penTool,
        #     (pygame.K_r, pygame.KMOD_NONE): self.rectTool,
        #     (pygame.K_e, pygame.KMOD_NONE): self.eraserTool,
        #     (pygame.K_s, pygame.KMOD_NONE): self.selectTool,
        #     (pygame.K_t, pygame.KMOD_NONE): self.textTool
        # }
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
        self.pnlSDL.startRendering()

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

    def onOpen(self, event):
        log.debug("selected 'open'")
        dlg = wx.FileDialog(self, "Choose a file", ".", "", "*.wb", wx.FD_OPEN)
        if dlg.ShowModal() == wx.ID_OK:
            path = os.path.join(dlg.GetDirectory(), dlg.GetFilename())
            dlg.Destroy()

            f = open(path, "rb")
            d = pickle.load(f)
            f.close()
            self.viewer.setObjects([objects.deserialize(o, self.viewer) for o in d["objects"]])

    def onSave(self, event):
        log.debug("selected 'save'")
        dlg = wx.FileDialog(self, "Choose a file", ".", "", "*.wb", wx.FD_SAVE)
        if dlg.ShowModal() == wx.ID_OK:
            path = os.path.join(dlg.GetDirectory(), dlg.GetFilename())
            dlg.Destroy()

            f = open(path, "wb")
            pickle.dump({"objects": [o.serialize() for o in self.viewer.getObjects()]}, f)
            f.close()

    def onExport(self, event):
        log.debug("selected 'export'")
        dlg = wx.FileDialog(self, "Choose a file", ".", "", "*.png", wx.FD_SAVE)
        if dlg.ShowModal() == wx.ID_OK:
            path = os.path.join(dlg.GetDirectory(), dlg.GetFilename())
            dlg.Destroy()

            objs = self.getObjects()
            rect = objects.boundingRect(objs)
            translate = numpy.array(rect.topleft) * -1
            surface = pygame.Surface(rect.size)
            surface.fill((255,255,255))
            for o in objs:
                surface.blit(o.image, numpy.array(o.absRect().topleft) + translate)
            pygame.image.save(surface, path)

    def onExit(self, event):
        self.viewer.running = False
        sys.exit(0)

    def onKeyDown(self, event):
        # key = (event.key, event.mod)
        # tool = self.toolKeys.get(key)
        # if tool is not None:
        #     self.onSelectTool(tool)
        pass

    def onPasteImage(self, event):
        # bdo = wx.BitmapDataObject()
        # self.clipboard.Open()
        # self.clipboard.GetData(bdo)
        # self.clipboard.Close()
        # bmp = bdo.GetBitmap()
        # print (bmp.SaveFile("foo.png", wx.BITMAP_TYPE_PNG))
        # buf = bytearray([0]*4*bmp.GetWidth()*bmp.GetHeight())
        # bmp.CopyToBuffer(buf, wx.BitmapBufferFormat_RGBA)
        # image = pygame.image.frombuffer(buf, (bmp.getWidth(), bmp.getHeight()), "RBGA")
        # data = bmp.ConvertToImage().GetData()
        # image = pygame.image.fromstring(data, (bmp.GetWidth(), bmp.GetHeight()), "RGB")
        dlg = wx.FileDialog(self, "Open XYZ file", wildcard="XYZ files (*.*)|*.*",
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
        self.viewer.addUser(name)

    def deleteUser(self, name):
        self.viewer.deleteUser(name)

    def deleteAllUsers(self):
        self.viewer.deleteAllUsers()

    def moveUserCursor(self, userName, pos):
        self.viewer.moveUserCursor(userName, pos)

    def errorDialog(self, errormessage):
        """Display a simple error dialog.
        """
        edialog = wx.MessageDialog(self, errormessage, 'Error', wx.OK | wx.ICON_ERROR)
        edialog.ShowModal()

    def questionDialog(self, message, title = "Error"):
        """Displays a yes/no dialog, returning true if the user clicked yes, false otherwise
        """
        return wx.MessageDialog(self, message, title, wx.YES_NO | wx.ICON_QUESTION).ShowModal() == wx.ID_YES

if __name__ == '__main__':
    app = wx.App(False)
    whiteboard = Whiteboard("WriteBoard")
    whiteboard.startRendering()
    whiteboard.Show()
    app.MainLoop()
