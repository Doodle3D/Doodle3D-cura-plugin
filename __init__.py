# Copyright (c) 2015 Ultimaker B.V.
# Cura is released under the terms of the AGPLv3 or higher.

from . import Doodle3D
from PyQt5.QtQml import qmlRegisterType, qmlRegisterSingletonType
from UM.i18n import i18nCatalog
i18n_catalog = i18nCatalog("cura")

def getMetaData():
    return {
        "type": "extension",
        "plugin": {
            "name": i18n_catalog.i18nc("@label", "Doodle3D"),
            "author": "Doodle3D",
            "version": "1.0",
            "api": 2,
            "description": i18n_catalog.i18nc("@info:whatsthis","Accepts G-Code and sends them over WiFi to a Doodle3D WiFi-Box.")
        }
    }

def register(app):
    qmlRegisterSingletonType(Doodle3D.Doodle3D, "UM", 1, 0, "Doodle3D", Doodle3D.Doodle3D.getInstance)
    return {"extension":Doodle3D.Doodle3D.getInstance(),"output_device": Doodle3D.Doodle3D.getInstance() }
