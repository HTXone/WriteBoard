

# class ToolsFactory(object):
#     def getLine(self, wb):
#         pass
#
#     def getPen(self, wb):
#         pass
#
#     def getRect(self, wb):
#         pass
#
#     def getEllipse(self, wb):
#         pass
#
#     def getCircle(self, wb):
#         pass
#
#     def getEraser(self, wb):
#         pass
#
#     def getColour(self, wb):
#         pass
#
#     def getText(self, wb):
#         pass
#
#     def getFont(self, wb):
#         pass
#
#     def getShape(self, wb):
#         pass

class defalutToolsFactory(object):
    def __init__(self):
        imp = "Tools"
        self.Tools = __import__(imp)  # 这种方式就是通过输入字符串导入你想导入的模块

    def getLineTool(self, wb):
        return self.Tools.LineTool(wb)

    def getPenTool(self, wb):
        return self.Tools.PenTool(wb)

    def getRectTool(self, wb):
        return self.Tools.RectTool(wb)

    def getEllipseTool(self, wb):
        return self.Tools.EllipseTool(wb)

    def getCircleTool(self, wb):
        return self.Tools.CircleTool(wb)

    def getEraserTool(self, wb):
        return self.Tools.EraserTool(wb)

    def getColourTool(self, wb):
        return self.Tools.ColourTool(wb)

    def getTextTool(self, wb):
        return self.Tools.TextTool(wb)

    def getFontTool(self, wb):
        return self.Tools.FontTool(wb)

    def getSelectTool(self,wb):
        return self.Tools.SelectTool(wb)

    def getShapeTool(self, wb):
        return self.Tools.ShapeTool(wb)

if __name__ == '__main__':
    A = defalutToolsFactory()
    print(A.getLine(None))
