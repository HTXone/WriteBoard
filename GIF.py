# -*- coding:utf-8 -*-
import wx


class Frame(wx.Frame):
    def __init__(self):
        wx.Frame.__init__(self, None, title=u"测试界面", size=(1340, 670))
        self.Center()
        self.SetMaxSize((1340, 670))
        self.SetMinSize((1340, 670))
        self.panel = wx.Panel(self, size=(1340, 670))
        self.locale = wx.Locale(wx.LANGUAGE_ENGLISH)

        global Test_Button

        fontButton = wx.Font(15, wx.SWISS, wx.NORMAL, wx.NORMAL)
        Test_Button = wx.Button(self.panel, label=u"测试按钮", pos=(100, 155), size=(200, 45))
        Test_Button.SetFont(fontButton)
        Test_Button.SetBackgroundColour("#90EE90")
        self.Bind(wx.EVT_BUTTON, self.Test_Button, Test_Button)

    ### 按钮
    def Test_Button(self, event):
        Test_Button.SetBackgroundColour("#CCCCCC")

        self.Train_Text = wx.StaticText(self.panel, -1, "按钮颜色改变"
                                        , pos=(100, 25), size=(200, 110))


if __name__ == "__main__":
    app = wx.App()
    frame = Frame()
    frame.Show()
    app.MainLoop()