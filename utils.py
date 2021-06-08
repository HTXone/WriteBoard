import pygame
import logging

log = logging.getLogger(__name__)
#计算线条框
def aaline(surface, colour, pos1, pos2, lineWidth=3):
    log.debug("aaline: %s -> %s", pos1, pos2)
    if True: #pos1[0] != pos2[0] and pos1[1] != pos2[1]:
        x1, y1 = pos1
        x2, y2 = pos2
        offset = (lineWidth - 1) / 2
        if x2 == x1:
            m = 1000
        else:
            m = float(y2 - y1) / (x2 - x1)
        #log.debug("m = %s", m)
        if m > 0:
            if m >= 1:
                offs1 = (-(offset), 0)
                offs2 = (offset, 0)
            else:
                offs1 = (lineWidth-2, -(offset))
                offs2 = (0, offset)
        else:
            if m <= -1:
                offs1 = (-offset, 0)
                offs2 = (offset, 0)
            else:
                offs1 = (0, -offset)
                offs2 = (lineWidth-2, offset)
        #log.debug("offsets: %s, %s", offs1, offs2)
        pygame.draw.aaline(surface, colour, (pos1[0]+offs1[0], pos1[1]+offs1[1]), (pos2[0]+offs1[0], pos2[1]+offs1[1]))
        pygame.draw.aaline(surface, colour, (pos1[0]+offs2[0], pos1[1]+offs2[1]), (pos2[0]+offs2[0], pos2[1]+offs2[1]))
    pygame.draw.line(surface, colour, pos1, pos2, lineWidth)


def boundingRect(objects):
    r = objects[0].absRect()
    return r.unionall([o.absRect() for o in objects[1:]])