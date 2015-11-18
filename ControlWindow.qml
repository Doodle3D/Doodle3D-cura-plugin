// Copyright (c) 2015 Ultimaker B.V.
// Cura is released under the terms of the AGPLv3 or higher.

import QtQuick 2.1
import QtQuick.Controls 1.1
import QtQuick.Layouts 1.1
import QtQuick.Window 2.1

import UM 1.1 as UM

UM.Dialog
{
<<<<<<< HEAD
    width: 400;
    height: 143;

    minimumWidth: 400;
    minimumHeight: 143;

    maximumWidth: 400;
    maximumHeight:143;
=======
    width: 400 * Screen.devicePixelRatio;
    height: 100 * Screen.devicePixelRatio;
>>>>>>> 43e1a0231bfa300d63e65959474bf3f137e7e620
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
                text: catalog.i18nc("@label","Extruder Temperature: %1").arg(manager.extruderTemperature)
                anchors.bottom: somepic.bottom
                }

                Text {
                text: catalog.i18nc("@label","Extruder Target: %1").arg(manager.extruderTarget)
                anchors.bottom: somepic.bottom
                }

                Text {
                text: catalog.i18nc("@label","Bed Temperature: %1").arg(manager.bedTemperature)
                anchors.bottom: somepic.bottom
                }

                Text {
                text: catalog.i18nc("@label","Printer State: %1").arg(manager.printerStateGet)
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
            value: manager.progress
            Text
            {
                //: USB Printing dialog label, %1 is printer state
                text: catalog.i18nc("@label","%1%").arg(manager.printPhase + "" + manager.progress)
                anchors.centerIn: parent
                visible: manager.progress >0 ? true : false
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
            enabled: manager.progress == 0 ? true : false
        }
    ]
}
