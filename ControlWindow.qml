// Copyright (c) 2015 Ultimaker B.V.
// Cura is released under the terms of the AGPLv3 or higher.

import QtQuick 2.1
import QtQuick.Controls 1.1
import QtQuick.Layouts 1.1
import QtQuick.Window 2.1

import UM 1.1 as UM

UM.Dialog
{
    id: d3dbase
    width: 400;
    height: 158;
    minimumWidth: 400;
    minimumHeight: 158;

    maximumWidth: 400;
    maximumHeight:158;
    modality: Qt.NonModal;
    flags: Qt.Dialog | Qt.CustomizeWindowHint | Qt.WindowTitleHint | Qt.WindowCloseButtonHint | Qt.WindowStaysOnTopHint;
    title: catalog.i18nc("@title:window", "Print to: %1").arg(manager.getBoxID)

    Column
    {
        anchors.fill: parent;
        spacing: UM.Theme.sizes.default_margin.height;
        
        Row
        {
            spacing: UM.Theme.sizes.default_margin.width;

            Image {
            id: doodle3dlogo;
            source: "doodle3d.png"
            }
            Column{
                Text {
                    text: catalog.i18nc("@label","Extruder Temperature: %1/%2°C").arg(manager.getExtruderTemperature).arg(manager.getExtruderTargetTemperature)
                }

                Text {
                    text: (manager.getBedTemperature == 0) ? 
                        catalog.i18nc("@label","") : 
                        catalog.i18nc("@label","Bed Temperature: %1/%2°C").arg(manager.getBedTemperature).arg(manager.getBedTargetTemperature)
                }

            }
            UM.I18nCatalog{id: catalog; name:"cura"}

        }

        ProgressBar
        {
            id: prog;
            anchors.left: parent.left;
            anchors.right: parent.right;
            minimumValue: 0;
            maximumValue: 100;
            value: manager.getProgress
            Text
            {
                text: catalog.i18nc("@label","%1").arg(manager.getPrintPhase)
                anchors.centerIn: parent
            }
        }
    }

    rightButtons: [
        Button
        {
            text: catalog.i18nc("@action:button","Cancel");
            enabled: manager.getPrinterState=="printing" || manager.getPrinterState=="buffering"
            onClicked: { 
                manager.cancelPrint()
            }
        },
        Button
        {
            id: printbutton;
            text: catalog.i18nc("@action:button","Print");
            enabled: manager.getPrinterState=="idle"
            onClicked: { 
                manager.startPrint()
            }
        }
    ]
}
