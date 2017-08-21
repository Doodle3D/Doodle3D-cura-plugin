# Copyright (c) 2015 Ultimaker B.V.
# Cura is released under the terms of the AGPLv3 or higher.

from . import D3DCloudPrintPlugin

def getMetaData():
    return {}

def register(app):
    return { "output_device": D3DCloudPrintPlugin.D3DCloudPrintPlugin() }
