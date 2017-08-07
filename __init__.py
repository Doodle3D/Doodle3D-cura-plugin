# Copyright (c) 2015 Ultimaker B.V.
# Cura is released under the terms of the AGPLv3 or higher.

from . import D3DCloudPrintPlugin
from UM.i18n import i18nCatalog
i18n_catalog = i18nCatalog("cura")

def getMetaData():
    return {
        "plugin": {
            "name": "Doodle3D WiFi-box print",
            "author": "Doodle3D",
            "version": "2.0",
            "api": 3,
            "description": i18n_catalog.i18nc("@info:whatsthis","Accepts G-Code and sends them over WiFi to a Doodle3D WiFi-Box.")
        }
    }

def register(app):
    return { "output_device": D3DCloudPrintPlugin.D3DCloudPrintPlugin() }
