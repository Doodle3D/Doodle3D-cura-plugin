from UM.Extension import Extension

from PyQt5.QtCore import QUrl
from PyQt5.QtGui import QDesktopServices

class D3DCloudPrintPlugin(Extension):
    def __init__(self):
        super().__init__()
        self.addMenuItem("Open Doodle3D Connect", self.openConnect)

    def openConnect(self):
        QDesktopServices.openUrl(QUrl("http://connect.doodle3d.com"))
