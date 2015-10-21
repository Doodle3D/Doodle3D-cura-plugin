// Copyright (c) 2015 Ultimaker B.V.
// Cura is released under the terms of the AGPLv3 or higher.

import QtQuick 2.1
import QtQuick.Controls 1.1
import QtQuick.Layouts 1.1
import QtQuick.Window 2.1

import UM 1.1 as UM

UM.Dialog
{
    width: 400 * Screen.devicePixelRatio;
    height: 100 * Screen.devicePixelRatio;
    modality: Qt.NonModal
    id: d3dbase

    title: catalog.i18nc("@title:window", "Print to Doodle3D WiFi-Box")

    Column
    {
        anchors.fill: parent;
        Row
        {
            spacing: UM.Theme.sizes.default_margin.width;
            Text
            {
                //: USB Printing dialog label, %1 is head temperature
                text: catalog.i18nc("@label","Extruder Temperature %1").arg(manager.extruderTemperature)
            }
            Text
            {
                //: USB Printing dialog label, %1 is bed temperature
                text: catalog.i18nc("@label","Bed Temperature %1").arg(manager.bedTemperature)
            }
            Text
            {
                text: "" + manager.error
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
            //: USB Printing dialog start print button
            text: catalog.i18nc("@action:button","Print");
            onClicked: { manager.startPrint() }
            // enabled: manager.progress == 0 ? true : false
        }
    ]
}
