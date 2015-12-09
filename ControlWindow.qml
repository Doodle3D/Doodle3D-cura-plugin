// Copyright (c) 2015 Ultimaker B.V.
// Cura is released under the terms of the AGPLv3 or higher.

import QtQuick 2.1
import QtQuick.Controls 1.1
import QtQuick.Layouts 1.1
import QtQuick.Window 2.1

import UM 1.1 as UM

UM.Dialog
{
    width: 400;
    height: 143;

    minimumWidth: 400;
    minimumHeight: 143;

    maximumWidth: 400;
    maximumHeight:143;
    modality: Qt.NonModal
    id: d3dbase

    title: catalog.i18nc("@title:window", "Print to Doodle3D WiFi-Box")

    Column
    {
        anchors.fill: parent;
        spacing: UM.Theme.sizes.default_margin.height;
        
        Row
        {
            spacing: UM.Theme.sizes.default_margin.width;

            Image {
            id: somepic;
            source: "doodle3d.png"
            }
            Column{
                Text {
                text: catalog.i18nc("@label","Extruder Temperature: %1").arg(manager.getExtruderTemperature)
                anchors.bottom: somepic.bottom
                }

                Text {
                text: catalog.i18nc("@label","Extruder Target: %1").arg(manager.getExtruderTargetTemperature)
                anchors.bottom: somepic.bottom
                }

                Text {
                text: catalog.i18nc("@label","Bed Temperature: %1").arg(manager.getBedTemperature)
                anchors.bottom: somepic.bottom
                }

                Text {
                text: catalog.i18nc("@label","Printer State: %1").arg(manager.getPrinterState)
                anchors.bottom: somepic.bottom
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
                //: USB Printing dialog label, %1 is printer state
                text: catalog.i18nc("@label","%1%").arg(manager.getPrintPhase + "" + manager.getProgress)
                anchors.centerIn: parent
                visible: manager.getProgress >0 ? true : false
            }
        }
    }

    rightButtons: [
        Button
        {
            //: USB Printing dialog cancel print button
            text: catalog.i18nc("@action:button","Cancel");
            onClicked: { 
                manager.cancelPrint();
                //d3dbase.visible = true;
            }
            // enabled: manager.progress == 0 ? false:  true
        },

        Button
        {
            id:printbutton;
            //: USB Printing dialog start print button
            text: catalog.i18nc("@action:button","Print");
            onClicked: { 
                manager.startPrint()
            }
            enabled: manager.getProgress == 0 ? true : false
        }
    ]
}
