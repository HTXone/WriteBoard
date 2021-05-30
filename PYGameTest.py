#!/usr/bin/env python
# -*- coding:utf-8 -*-
#Author: ss

import pygame
import sys


class circle:
    def __init__(self,surface):
        self.exit = False
        self.position =0,0
        self.color = 0,0,0
        self.radius = 0
        self.width = 0
        self.surface =surface

    def Draw(self,position,color,radius,width):
        pygame.draw.circle(self.surface, color, position, radius, width)
        self.color =color
        self.position = position
        self.radius = radius
        self.width = width

# 初始化
pygame.init()

size = width,height = 1000,600 # 设置屏幕尺寸
BLUE = 0,0,255
WHITE = 255,255,255
BLACK = 0,0,0
RED = 255,0,0
GREEN = 0,255,0

screen = pygame.display.set_mode(size) # 创建surface对象
screen2 = pygame.display.set_mode(size) # 创建surface对象
pygame.display.set_caption('画圆及拖拽') # 创建标题

# 圆心位置定义
position = size[0] // 2 , size[1] // 2

moving = False

while True:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            sys.exit()
        if event.type == pygame.MOUSEBUTTONDOWN: # 获取点击鼠标事件
            if event.button == 1: # 点击鼠标左键
                moving = True
        if event.type == pygame.MOUSEBUTTONUP: # 获取松开鼠标事件
            if event.button == 1: # 松开鼠标左键
                moving = False
    if moving:
        position = pygame.mouse.get_pos() # 更新圆心位置为鼠标当前位置



    screen.fill(WHITE) # 填充屏幕

    circle1 = circle(screen)
    circle1.Draw(position,BLUE,30,1)

    # 画各种尺寸颜色的圆
    # pygame.draw.circle(screen,BLUE,position,30,1)
    # pygame.draw.circle(screen, BLACK, position, 50, 1)
    # pygame.draw.circle(screen, RED, position, 80, 1)
    # pygame.draw.circle(screen, GREEN, position, 120, 1)
    # 刷新屏幕
    pygame.display.flip()