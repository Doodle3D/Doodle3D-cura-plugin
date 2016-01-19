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
    height: 143;
    minimumWidth: 400;
    minimumHeight: 143;

    maximumWidth: 400;
    maximumHeight:143;
    modality: Qt.ApplicationModal
    // flags: Qt.Raise
    
    // d3dbase.raise();
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
                    text: catalog.i18nc("@label","Extruder Temperature: %1/%2").arg(manager.getExtruderTemperature).arg(manager.getExtruderTargetTemperature)
                }

                Text {
                    text: (manager.getBedTemperature == 0 && manager.getBedTargetTemperature == 0) ? 
                        catalog.i18nc("@label","") : 
                        catalog.i18nc("@label","Bed Temperature: %1/%2").arg(manager.getBedTemperature).arg(manager.getBedTargetTemperature)
                }

                Text {
                    text: catalog.i18nc("@label","Printer State: %1").arg(manager.getPrinterState)
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
                text: catalog.i18nc("@label","%1").arg(manager.getPrintPhase)
                // + "" + manager.getProgress + manager.addPercentOrNot
                anchors.centerIn: parent
                // visible: manager.getProgress >0 ? true : false
            }
        }
    }

    rightButtons: [
        Button
        {
            //: USB Printing dialog cancel print button
            text: catalog.i18nc("@action:button","Cancel");
            enabled: manager.getPrinterState=="printing" || manager.getPrinterState=="buffering"
            onClicked: { 
                manager.cancelPrint()

                //d3dbase.visible = true;
            }
            //enabled: manager.getProgress == 0 ? false:  true
        },

        Button
        {
            //: USB Printing dialog cancel print button
            text: "Test";
            enabled: true
            onClicked: { 
                manager.testButton()

                //d3dbase.visible = true;
            }
            //enabled: manager.getProgress == 0 ? false:  true
        },

        Button
        {
            id: printbutton;
            //: USB Printing dialog start print button
            text: catalog.i18nc("@action:button","Print");
            //enabled: manager.isPrinting? false : true
            enabled: manager.getPrinterState=="idle"
            onClicked: { 
                manager.startPrint()
            }
            //enabled: manager.getProgress == 0 ? false : true
        }
    ]
}
