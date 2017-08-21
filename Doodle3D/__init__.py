# Copyright (c) 2017 Doodle3D.
# Cura is released under the terms of the AGPLv3 or higher.

from . import D3DCloudPrintOutputDevicePlugin
from . import D3DCloudPrintPlugin

def getMetaData():
    return {}

def register(app):
    return {
        "extension": D3DCloudPrintPlugin.D3DCloudPrintPlugin(),
        "output_device": D3DCloudPrintOutputDevicePlugin.D3DCloudPrintOutputDevicePlugin()
    }
