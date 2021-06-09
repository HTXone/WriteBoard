# (C) 2014 by Dominik Jain (djain@gmx.net)

import os
import pygame
from pygame import sprite
import numpy
import utils
from objects import *

global pygame
global renderer
global objects

#画图类
class WhiteboardRenderer(sprite.LayeredUpdates):
    def __init__(self, game):
        #这里传入的game就是viewer对象
        sprite.LayeredUpdates.__init__(self)

        self.game = game

        # 将对象添加到这两个容器中就会被自动绘制出
        self.userObjects = sprite.Group()
        self.uiObjects = sprite.Group()

        #sprite.LayeredUpdates.add(self, self.userObjects, self.uiObjects)

        self.setBackgroundSize(self.game.screen.get_size())

    def add(self, *objects):
        sprite.LayeredUpdates.add(self, *objects)
        for object in objects:
            if object.isUserObject:
                self.userObjects.add(object)
            else:
                self.uiObjects.add(object)

    def setBackgroundSize(self, size):
        self.background = pygame.Surface(self.game.screen.get_size())
        self.background.fill((255,255,255))
        self.game.screen.blit(self.background, [0,0])

    def draw(self):
        self.clear(self.game.screen, self.background)
        things = sprite.LayeredUpdates.draw(self, self.game.screen)
        pygame.display.update(things)
        pygame.display.flip()

class ScribbleRenderer(object):
    def __init__(self, scribble):
        self.antialiasing = False
        self.margin = 2*scribble.lineWidth
        self.colour = scribble.colour
        self.lineWidth = scribble.lineWidth
        surface = pygame.Surface((self.margin, self.margin), flags=pygame.SRCALPHA if self.antialiasing else 0) # TODO: aaline does not work with SRCALPHA!
        self.backgroundColour = (255, 0, 255) if not self.antialiasing else (255, 255, 255, 0)
        surface.fill(self.backgroundColour)
        if not self.antialiasing:
            surface.set_colorkey(self.backgroundColour)
        self.surface = surface
        self.isFirstPoint = True
        self.obj = scribble
        self.inputBuffer = []

    def addPoint(self, x, y, draw=True):
        if self.isFirstPoint:
            self.lineStartPos = numpy.array([x, y])
            self.translateOrigin = numpy.array([-x, -y])
            self.minX = self.maxX = x
            self.minY = self.maxY = y
            self.isFirstPoint = False

        self.inputBuffer.append((x, y))

        if draw:
            self._processInputs()

    def addPoints(self, points):
        for point in points:
            self.addPoint(*point, draw=False)
        self._processInputs()

    def _processInputs(self):
        padLeft = 0
        padTop = 0

        oldWidth = self.surface.get_width()
        oldHeight = self.surface.get_height()
        newWidth = oldWidth
        newHeight = oldHeight

        # determine growth
        for x, y in self.inputBuffer:
            #print "\nminX=%d maxX=%d" % (self.minX, self.maxX)
            #print "x=%d y=%d" % (x,y)
            growRight = x - self.maxX if x > self.maxX else 0
            growLeft = self.minX - x if x < self.minX else 0
            growBottom = y - self.maxY if y > self.maxY else 0
            growTop = self.minY - y if y < self.minY else 0

            padLeft += growLeft
            padTop += growTop

            #print "grow: right=%d left=%d top=%d bottom=%d" % (growRight, growLeft, growTop, growBottom)
            self.maxX = max(self.maxX, x)
            self.maxY = max(self.maxY, y)
            self.minX = min(self.minX, x)
            self.minY = min(self.minY, y)
            #print "new: minX=%d maxX=%d" % (self.minX, self.maxX)

            newWidth += growLeft + growRight
            newHeight += growBottom + growTop

        # create new larger surface and copy old surface content
        if newWidth > oldWidth or newHeight > oldHeight:
            #print "newDim: (%d, %d)" % (newWidth, newHeight)
            surface = pygame.Surface((newWidth, newHeight), pygame.SRCALPHA if self.antialiasing else 0)
            surface.fill(self.backgroundColour)
            if not self.antialiasing:
                surface.set_colorkey(self.backgroundColour)
            surface.blit(self.surface, (padLeft, padTop))
            self.surface = surface

        # translate pos
        self.obj.offset(-padLeft, -padTop)

        # draw new lines
        for x, y in self.inputBuffer:
            self._drawLineTo(x, y)

        # apply new surface
        self.obj.setSurface(self.surface, ppAlpha=self.antialiasing)

        # reset input buffer
        self.inputBuffer = []

    def _drawLineTo(self, x, y):
        # draw line
        margin = self.margin
        self.translateOrigin = -self.obj.pos + numpy.array([-margin, -margin])
        #print "translateOrigin=%s" % str(self.translateOrigin)
        marginTranslate = numpy.array([margin, margin])
        pos1 = self.lineStartPos + self.translateOrigin + marginTranslate
        pos2 = numpy.array([x, y]) + self.translateOrigin + marginTranslate
        #print "drawing from %s to %s" % (str(pos1), str(pos2))
        if not self.antialiasing:
            pygame.draw.line(self.surface, self.colour, pos1, pos2, self.lineWidth)
        else:
            utils.aaline(self.surface, self.colour, pos1, pos2, self.lineWidth)
        self.lineStartPos = numpy.array([x, y])

    def end(self):
        self._processInputs()

