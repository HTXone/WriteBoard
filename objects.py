# (C) 2014 by Dominik Jain (djain@gmx.net)

import time
import pygame
from pygame import sprite
import numpy

import pickle
import threading
import logging
import utils
from Tools import *
from renderer import ScribbleRenderer

log = logging.getLogger(__name__)



class Alignment(object):
    #参数结构体
    TOP_LEFT, CENTRE, BOTTOM_LEFT = range(3)

class BaseObject(sprite.Sprite):
    ''' basic sprite object '''

    def __init__(self, d, game, persistentMembers = None, isUserObject=False, layer=1, alignment=Alignment.TOP_LEFT):
        self.isUserObject = isUserObject # can be overridden below if "isUserObject" is a persistent member

        if persistentMembers is None: persistentMembers = []    #初始化
        self.persistentMembers = persistentMembers
        self.persistentMembers.extend(["rect", "pos", "id"])    #元素

        sprite.Sprite.__init__(self)

        self.alignment = alignment
        self.layer = layer
        self.id = time.time()

        for member in self.persistentMembers:
            if member in d:
                self.__dict__[member] = self._deserializeValue(member, d[member])

        if not hasattr(self, "pos"):        #具有属性
            if hasattr(self, "rect"):
                if self.alignment == Alignment.TOP_LEFT:
                    self.pos = self.rect.topleft
                elif self.alignment == Alignment.CENTRE:
                    self.pos = self.rect.center
                elif self.alignment == Alignment.BOTTOM_LEFT:
                    self.pos = self.rect.bottomleft
                else:
                    raise Exception("unknown alignment: %s" % self.alignment)
            else:
                self.pos = (0, 0)

    class MovementAnimationThread(threading.Thread):    #运动动画线程
        def __init__(self, obj, pos, duration):
            threading.Thread.__init__(self) #初始化
            self.obj = obj
            self.pos = pos
            self.duration = duration
            self.animating = True

        def run(self):
            startPos = self.obj.pos
            translation = numpy.array(self.pos) - startPos  #偏移
            startTime = time.time()     #计时器
            while self.animating:       #启动动画
                passed = min(time.time() - startTime, self.duration)
                self.obj.pos = startPos + (passed / self.duration) * translation
                if passed == self.duration:
                    break
                time.sleep(0.010)

    def animateMovement(self, pos, duration):       #开启动画线程
        if hasattr(self, "movementAnimationThread"):
            self.movementAnimationThread.animating = False
        self.movementAnimationThread = BaseObject.MovementAnimationThread(self, pos, duration)
        self.movementAnimationThread.start()

    def update(self, game):
        # update the sprite's drawing position relative to the camera
        coord = self.pos - game.camera.pos
        if self.alignment == Alignment.TOP_LEFT:
            self.rect.topleft = coord
        elif self.alignment == Alignment.CENTRE:
            self.rect.center = coord
        elif self.alignment == Alignment.BOTTOM_LEFT:
            self.rect.bottomleft = coord

    def collide(self, group, doKill=False, collided=None):
        return sprite.spritecollide(self, group, doKill, collided)

    def kill(self):
        #self.unbindAll()
        sprite.Sprite.kill(self)

    def offset(self, x, y):
        self.pos += numpy.array([int(x),int(y)])

    def toDict(self):       #打包
        d = {
            "class": "%s.%s" % (self.__class__.__module__, self.__class__.__name__)
        }
        for member in self.persistentMembers:
            if hasattr(self, member):
                d[member] = self._serializeMember(member)
        return d

    def _serializeMember(self, name):
        return self._serializeValue(name, self.__dict__[name])

    def _deserializeValue(self, name, value):
        evalTag = "_EVAL_:"
        if type(value) == str and value[:len(evalTag)] == evalTag:
            value = eval(value[len(evalTag):])
        return value

    def _stringToEval(self, s):
        return "_EVAL_:" + s

    def _serializeValue(self, name, value):
        if name == "rect":
            return self._stringToEval("pygame.Rect(%d, %d, %d, %d)" % (self.rect.left, self.rect.top, self.rect.width, self.rect.height))
        if name == "pos":
            return self._stringToEval("numpy.array([%s, %s])" % (str(self.pos[0]), str(self.pos[1])))
        return value

    def serialize(self):
        return pickle.dumps(self.toDict())

    def absRect(self):  #绝对值矩阵
        ''' returns a rectangle reflecting the abolute extents of the object '''
        return pygame.Rect(self.pos[0], self.pos[1], self.rect.width, self.rect.height)

class Rectangle(BaseObject):
    def __init__(self, d, game, **kwargs):
        if not "isUserObject" in kwargs:
            kwargs["isUserObject"] = True
        BaseObject.__init__(self, d, game, persistentMembers=["colour"], **kwargs)
        self.setSize(self.rect.width, self.rect.height)

    def setSize(self, width, height):
        width, height = max(1, width), max(1, height)
        alpha = len(self.colour) == 4
        surface = pygame.Surface((width, height), flags=pygame.SRCALPHA if alpha else 0)
        surface.fill(self.colour)
        self.image = surface.convert() if not alpha else surface.convert_alpha()
        self.rect.width = width
        self.rect.height = height

class Ellipse(BaseObject):
    def __init__(self,d,game,**kwargs):
        if not "isUserObject" in kwargs:
            kwargs["isUserObject"] = True
        BaseObject.__init__(self, d, game, persistentMembers=["colour"], **kwargs)
        self.setSize(self.rect.width, self.rect.height)

    def setSize(self, width,height):
        width, height = max(1, width), max(1, height)
        alpha = len(self.colour) == 4
        surface = pygame.Surface((width, height), flags=pygame.SRCALPHA if alpha else 0)
        pygame.draw.ellipse(surface, self.colour, pygame.Rect(0, 0, width,height))
        self.image = surface.convert() if not alpha else surface.convert_alpha()
        self.rect.width = width
        self.rect.height = height

class Circle(BaseObject):
    def __init__(self, d, game, **kwargs):
        if not "isUserObject" in kwargs:
            kwargs["isUserObject"] = True
        BaseObject.__init__(self, d, game, persistentMembers=["colour"], **kwargs)
        self.setRadius(int(self.rect.width/2))

    def setRadius(self, radius):
        radius = max(1, radius)
        alpha = len(self.colour) == 4
        width,height = (radius * 2, radius * 2)
        surface = pygame.Surface((width,height), flags=pygame.SRCALPHA if alpha else 0)
        pygame.draw.circle(surface, self.colour, (radius,radius),radius)
        self.image = surface.convert() if not alpha else surface.convert_alpha()
        self.rect.width = width
        self.rect.height = height

class Line(BaseObject):
    def __init__(self,d,game,**kwargs):
        if not "isUserObject" in kwargs:
            kwargs["isUserObject"] = True
        BaseObject.__init__(self, d, game, persistentMembers=["colour","start_pos","end_pos"], **kwargs)
        self.setEnd(self.end_pos)

    def setEnd(self, end_pos):
        alpha = len(self.colour) == 4
        self.end_pos = end_pos
        #按起点和终点绘制一个surface
        surface = self.drawSurface()

        #根据起点和终点更新pos
        self.updatePos()

        self.image = surface.convert() if not alpha else surface.convert_alpha()

        self.rect.width = abs(surface.get_width())
        self.rect.height = abs(surface.get_height())
        print()

    def drawSurface(self):
        alpha = len(self.colour) == 4
        surface = pygame.Surface((abs(self.end_pos[0]-self.start_pos[0])+5,abs(self.end_pos[1]-self.start_pos[1])+5), flags=pygame.SRCALPHA if alpha else 0)

        print(f"{self.pos},{self.start_pos},{self.end_pos}")
        # surface.fill((25,25,25))

        chx = self.end_pos[0] - self.start_pos[0]
        chy = self.end_pos[1] - self.start_pos[1]

        if chx>=0 and chy>=0:
            pygame.draw.line(surface, self.colour, (0,0), (chx,chy),4)
        elif chx>=0 and chy<=0:
            pygame.draw.line(surface, self.colour, (0,-chy), (chx,0),4)
        elif chx<=0 and chy>=0:
            pygame.draw.line(surface, self.colour, (0, chy), (-chx, 0),4)
        else:
            pygame.draw.line(surface, self.colour, (0, 0), (-chx, -chy),4)

        return surface

    def updatePos(self):
        self.pos = (min(self.start_pos[0],self.end_pos[0]),min(self.start_pos[1],self.end_pos[1]))

class Image(BaseObject):
    def __init__(self, d, game, persistentMembers = None, **kwargs):
        if persistentMembers is None: persistentMembers = []
        BaseObject.__init__(self, d, game, persistentMembers=persistentMembers+["isUserObject", "image"], **kwargs)

    def setSurface(self, surface, ppAlpha = False):
        self.image = surface.convert() if not ppAlpha else surface.convert_alpha()
        self.rect = self.image.get_rect()

    def _serializeValue(self, name, value):
        if name == "image":
            format = "RGBA"
            s = pygame.image.tostring(self.image, format)
            cs = s
            print("compression: %d -> %d" % (len(s), len(cs)))
            return (cs, self.image.get_size(), format)
        return super(Image, self)._serializeValue(name, value)

    def _deserializeValue(self, name, value):
        if name == "image" and type(value) == tuple:
            dim = value[1:][0]
            if dim[0] == 0 or dim[1] == 0:
                return pygame.Surface((10,10)).convert()
            return pygame.image.frombuffer(value[0], *value[1:])
        return super(Image, self)._deserializeValue(name, value)

class ImageFromResource(Image):
    def __init__(self, filename, game, ppAlpha=False, **kwargs):
        Image.__init__(self, {}, game, **kwargs)
        surface = pygame.image.load(filename)
        self.setSurface(surface, ppAlpha=ppAlpha)

class PointBasedScribble(Image):
    ''' a point-based scribble sprite, which, when persisted, is reconstructed from the individual points '''
    def __init__(self, d, game, startPoint=None,persistentMembers=None):
        pos = None
        if "pos" in d:
            pos = self._deserializeValue("pos", d["pos"])
        if startPoint is None:
            if "points" in d and len(d["points"]) > 0:
                startPoint = d["points"][0]
            else:
                raise Exception('construction requires either startPoint or non-empty d["points"]"')
        else:
            if "points" in d: raise Exception('cannot provide both startPoint and d["points"]')
        persistentMembers=["points"]

        if startPoint is not None:
            if "lineWidth" not in d: raise Exception("construction with startPoint requires lineWidth")
            margin = 2 * d["lineWidth"]
            d["rect"] = pygame.Rect(startPoint[0] - margin/2, startPoint[1] - margin/2, margin, margin)
            if "pos" in d: del d["pos"] # will be set from rect
        if persistentMembers is None: persistentMembers = []
        Image.__init__(self, d, game, isUserObject=True, persistentMembers=persistentMembers+["lineWidth", "colour"])


        self.persistentMembers.remove("image")
        self.persistentMembers.remove("rect")
        if not hasattr(self, "points"):
            self.points = []
        else:
            self.addPoints(self, self.points)
        if pos is not None:
            self.pos = pos

    def addPoints(self, points):
        self.points.extend(points)
        if not hasattr(self, "scribbleRenderer"):
                self.scribbleRenderer = ScribbleRenderer(self)
        self.scribbleRenderer.addPoints(points)
        #log.debug("relative points: %s", map(list, [numpy.array(p)-self.pos for p in self.points]))

    def endDrawing(self):
        self.scribbleRenderer.end()
        del self.scribbleRenderer


class Text(Image):
    def __init__(self, d, game):
        Image.__init__(self, d, game, persistentMembers=["text", "colour", "fontSize", "fontName"], isUserObject=True)
        self.font = pygame.font.SysFont(self.fontName, self.fontSize)
        self.setText(self.text)

    def setText(self, text):
        #font = pygame.freetype.get_default_font()
        #self.image = font.render(self.text, fgcolor=self.colour, size=10)
        self.text = text
        lines = text.split("\n")
        width = 0
        height = 0
        for l in lines:
            w, h = self.font.size(l)
            width = max(w, width)
            height += h

        surface = pygame.Surface((width, height))
        surface.fill((255, 255, 255))

        y = 0
        for l in lines:
            s = self.font.render(l, True, self.colour, (255,255,255))
            surface.blit(s, (0, y))
            y += s.get_height()

        self.setSurface(surface)

# class Scribble(Image):
#     ''' an image-based scribble sprite '''
#     def __init__(self, d, game, startPoint=None, persistentMembers=None):
#         if startPoint is not None:
#             if "lineWidth" not in d: raise Exception("construction with startPoint requires lineWidth")
#             margin = 2 * d["lineWidth"]
#             d["rect"] = pygame.Rect(startPoint[0] - margin/2, startPoint[1] - margin/2, margin, margin)
#             if "pos" in d: del d["pos"] # will be set from rect
#         if persistentMembers is None: persistentMembers = []
#         Image.__init__(self, d, game, isUserObject=True, persistentMembers=persistentMembers+["lineWidth", "colour"])
#
#     def addPoints(self, points):
#         if not hasattr(self, "scribbleRenderer"):
#             self.scribbleRenderer = ScribbleRenderer(self)
#         self.scribbleRenderer.addPoints(points)
#
#     def endDrawing(self):
#         self.scribbleRenderer.end()
#         del self.scribbleRenderer
#
# class PointBasedScribble(Scribble):
#     ''' a point-based scribble sprite, which, when persisted, is reconstructed from the individual points '''
#     def __init__(self, d, game, startPoint=None):
#         pos = None
#         if "pos" in d:
#             pos = self._deserializeValue("pos", d["pos"])
#         if startPoint is None:
#             if "points" in d and len(d["points"]) > 0:
#                 startPoint = d["points"][0]
#             else:
#                 raise Exception('construction requires either startPoint or non-empty d["points"]"')
#         else:
#             if "points" in d: raise Exception('cannot provide both startPoint and d["points"]')
#         Scribble.__init__(self, d, game, persistentMembers=["points"], startPoint=startPoint)
#         self.persistentMembers.remove("image")
#         self.persistentMembers.remove("rect")
#         if not hasattr(self, "points"):
#             self.points = []
#         else:
#             Scribble.addPoints(self, self.points)
#         if pos is not None:
#             self.pos = pos
#
#     def addPoints(self, points):
#         self.points.extend(points)
#         Scribble.addPoints(self, points)
#         #log.debug("relative points: %s", map(list, [numpy.array(p)-self.pos for p in self.points]))



