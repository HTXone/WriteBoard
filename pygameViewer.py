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
import renderer

global renderer

class pygameViewer(object):
    def __init__(self, size, app):
        self.isLeftMouseButtonDown = False      #鼠标状态初始化
        self.scroll = False                     #移动初始化
        self.activeTool = None                  #激活工具初始化
        self.screen = pygame.display.set_mode(size, pygame.RESIZABLE)   #pygame
        self.width = size[0]                    #宽度
        self.height = size[1]                   #高度
        self.running = False                    #线程执行状态
        self.renderer = renderer.WhiteboardWindow(self)     #画框对象
        self.cameraPos = (0,0) + numpy.array([-self.width / 2, -self.height / 2])       #视角位置（移动用）
        self.app = app                          #WXapp
        self.objectsById = {}                   #图像对象ID
        # self.userCursors = {}                   #用户鼠标

        pygame.mouse.set_visible(False)

        self.MouseSetInit()


    def MouseSetInit(self):             #箭头图标初始化
        self.mouseArrow = None
        self.mouseCursorName = None
        self.haveMouseFocus = False


        self.mouseArrows = {}
        self.mouseArrows["arrow"] = objects.ImageFromResource(os.path.join("img", "Arrow.png"), self, layer=1000,
                                                               ppAlpha=True)
        self.mouseArrows["pen"] = objects.ImageFromResource(os.path.join("img", "Handwriting.png"), self, layer=1000,
                                                             ppAlpha=True, alignment=objects.Alignment.BOTTOM_LEFT)
        self.mouseArrows["text"] = objects.ImageFromResource(os.path.join("img", "IBeam.png"), self, layer=1000,
                                                              ppAlpha=True)
        self.mouseArrows["delete"] = objects.ImageFromResource(os.path.join("img", "Delete.png"), self, layer=1000,
                                                                ppAlpha=True)
        self.mouseArrows["hand"] = objects.ImageFromResource(os.path.join("img", "Hand.png"), self, layer=1000,
                                                              ppAlpha=True, alignment=objects.Alignment.CENTRE)
        self.mouseArrows["shape"] = objects.ImageFromResource(os.path.join("img", "Shape.png"), self, layer=1000,
                                                               ppAlpha=True, alignment=objects.Alignment.CENTRE)

        self.setMouseArrow("arrow")

    def TheadRunning(self):         #线程循环函数
        self.running = True
        try:
            clock = pygame.time.Clock()

            while self.running == True:
                try:
                    clock.tick(30)

                    for event in pygame.event.get():
                        self.eventDeal(event)
                    # 在这里更新和显示
                    self.renderer.update(self) # 偏移对象
                    self.renderer.draw()        #绘制
                except:
                    log.warning("rendering pass failed")
                    e, v, tb = sys.exc_info()
                    print(v)
                    traceback.print_tb(tb)

        except:
            e, v, tb = sys.exc_info()
            print(v)
            traceback.print_tb(tb)

    def eventDeal(self,event):          #事件处理函数
        # 处理用户动作——在这里改变状态

        # 鼠标移动
        if event.type == pygame.MOUSEMOTION:
            self.mouseMove(*(event.pos + event.rel))

        #鼠标按下
        elif event.type == pygame.MOUSEBUTTONDOWN:
            x, y = event.pos
            if event.button == 3:
                self.rightMouseButtonDown()

            elif event.button == 1:
                self.leftMouseButtonDown(x, y)

        #鼠标松开
        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1:
                self.leftMouseButtonUp(*event.pos)

            elif event.button == 3:
                self.rightMouseButtonUp()

        #窗口大小变化
        elif event.type == pygame.VIDEORESIZE:
            log.debug("resized window: %s", event.size)
            #重新适应
            self.screen = pygame.display.set_mode(event.size, pygame.RESIZABLE)

            self.width, self.height = event.size
            self.renderer.setBackgroundSize(event.size)

        #窗口激活
        elif event.type == pygame.ACTIVEEVENT:

            if event.state == 1:
                self.haveMouseFocus = event.gain
                if event.gain:
                    self.renderer.add(self.mouseArrow)

                else:
                    self.mouseArrow.kill()

        #按键操作（为写）
        elif event.type == pygame.KEYDOWN:
            pass
            # self.app.onKeyDown(event)

    def setActiveTool(self, tool):      #设置激活工具
        if self.activeTool is not None:
            self.activeTool.deactivate()    #取消上个激活工具

        self.activeTool = tool

        self.setMouseArrow(tool.mouseCursor)    #工具样式
        tool.activate()

    def setMouseArrow(self, ArrowName):  #工具鼠标图像变化
        if ArrowName not in self.mouseArrows:
            ArrowNameName = "arrow"

        self.mouseCursorName = ArrowName

        if self.mouseArrow is not None:
            self.mouseArrow.kill()
        self.mouseArrow = self.mouseArrows[ArrowName]

        if self.haveMouseFocus:
            self.renderer.add(self.mouseArrow)

    def setObjects(self, objects):      #设置图对象

        for obj in self.getObjects():   #对象重置
            obj.kill()

        for obj in objects:
            self.addObject(obj)

    def getObjects(self):       #获取图对象
        return self.renderer.userObjects.sprites()

    def addObject(self, object):    #增加图对象
        self.objectsById[object.id] = object

        self.renderer.add(object)   #绘制

    def deleteObjects(self, *ids):  #删除对象
        deletedIds = []

        for id in ids:
            obj = self.objectsById.get(id)  #获取对象ID

            if obj is not None:
                obj.kill()
                del self.objectsById[id]
                deletedIds.append(id)

        return deletedIds

    def moveObjects(self, offset, *ids):    #移动对象

        for id in ids:
            obj = self.objectsById.get(id)  #获取

            if obj is not None:
                obj.offset(*offset)         #偏移

    def rightMouseButtonDown(self): #右键按下时进行拖动操作
        self.setMouseArrow("hand")

        self.prevMouseCursorName = self.mouseCursorName
        self.scroll = True

    def rightMouseButtonUp(self): #右键放开 取消移动操作

        self.setMouseArrow(self.prevMouseCursorName)
        self.scroll = False

    def leftMouseButtonDown(self, x, y): # 鼠标按下时创建图形对象
        self.isLeftMouseButtonDown = True

        if self.activeTool is not None:     #开始画图
            pos = numpy.array([x, y]) + self.cameraPos
            createdObject = self.activeTool.startPos(pos[0], pos[1])
            if createdObject is not None:
                self.addObject(createdObject)

    def leftMouseButtonUp(self, x, y):    #放开左键

        pos = numpy.array([x, y]) + self.cameraPos
        self.isLeftMouseButtonDown = False

        if self.activeTool is not None:     #完成画图
            self.activeTool.end(*pos)

    def mouseMove(self, x, y, dx, dy):   #鼠标移动操作
        pos = numpy.array([x, y]) + self.cameraPos  #偏移计算
        self.mouseArrow.pos = pos

        if not self.isLeftMouseButtonDown and self.scroll:     #右键拖动函数
            self.cameraPos +=numpy.array([-dx, -dy])

        elif self.isLeftMouseButtonDown and self.activeTool is not None:   #画图
            self.activeTool.addPos(*pos)

        self.app.onCursorMoved(pos)

    # def addUser(self, name):    #在图上显示新的客户
    #     sprite = objects.ImageFromResource(os.path.join("img", "HandPointer.png"), self, layer=1000, ppAlpha=True)
    #     self.addObject(sprite)
    #     self.userCursors[name] = sprite
    #     return sprite
    #
    # def deleteUser(self, name):  #用户推出
    #     sprite = self.userCursors.get(name)
    #     if sprite is not None:
    #         sprite.kill()
    #
    # def deleteAllUsers(self):
    #     for name in self.userCursors:
    #         self.deleteUser(name)
    # def moveUserCursor(self, userName, pos):
    #     sprite = self.userCursors.get(userName)
    #     if sprite is not None:
    #         sprite.pos = pos
    # def update(self): # 通过更新对象的偏移来进行显示偏移的实现
    #     self.renderer.update(self) # 偏移对象
    #
    # def reDraw(self): # 重绘屏幕
    #     self.renderer.draw()

