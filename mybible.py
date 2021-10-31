import os
import wx
import glob
import shutil 

from util.debug import dprint, MESSAGE, WARNING, is_debugging


import config, guiconfig

class MyApp(wx.App):
    
    def Initialize(self):
        pass

    def OnInit(self):
        self.starting = True
        self.restarting = False
        self.reload_restarting = False

        dprint(MESSAGE, "App Init")
        guiconfig.load_icons()

        from wx import xrc 
        self.res = xrc.XmlResource(config.xrc_path + "auifrm.xrc")
        return True


def main():
    dprint(MESSAGE, "Creating App")
    app = MyApp(0)
    app.Initialize()
    app.MainLoop()



if __name__ == "__main__":
    main()
