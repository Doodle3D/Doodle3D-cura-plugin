# Copyright (c) 2015 Ultimaker B.V.
# Cura is released under the terms of the AGPLv3 or higher.

from . import D3DCloudPrintPlugin
from UM.i18n import i18nCatalog
i18n_catalog = i18nCatalog("cura")

def getMetaData():
    return {}

def register(app):
    return { "output_device": D3DCloudPrintPlugin.D3DCloudPrintPlugin() }
