// Copyright (c) 2015 Ultimaker B.V.
// Cura is released under the terms of the AGPLv3 or higher.

import QtQuick 2.2
import QtQuick.Window 2.2
import QtQuick.Controls 1.2

import UM 1.1 as UM

UM.Dialog
{
    id: base;

    width: 500 * Screen.devicePixelRatio;
    height: 100 * Screen.devicePixelRatio;

    visible: true;
    modality: Qt.ApplicationModal;

    title: catalog.i18nc("@title:window","Doodle3D Settings");

    Column
    {
        anchors.fill: parent;

        Label
        {
            anchors
            {
                left: parent.left;
                right: parent.right;
            }

            text: {
                if (manager.progress == 0)
                {
                    //: Firmware update status label
                    return catalog.i18nc("@label","Starting firmware update, this may take a while.")
                }
                else if (manager.progress > 99)
                {
                    //: Firmware update status label
                    return catalog.i18nc("@label","Firmware update completed.")
                }
                else
                {
                    //: Firmware update status label
                    return catalog.i18nc("@label","Updating firmware.")
                }
            }

            wrapMode: Text.Wrap;
        }

        ProgressBar 
        {
            id: prog;
            value: manager.progress
            minimumValue: 0;
            maximumValue: 100;
            anchors
            {
                left: parent.left;
                right: parent.right;
            }

        }
        
        SystemPalette
        {
           id: palette;
        }

        UM.I18nCatalog { id: catalog; name: "cura"; }
    }

    rightButtons: [
        Button
        {
            text: catalog.i18nc("@action:button","Cancel");
            // enabled: manager.progress >= 100;
            // onClicked: base.visible = false;
        },

        Button
        {
            text: catalog.i18nc("@action:button","Save");
            // enabled: manager.progress >= 100;
            // onClicked: base.visible = false;
        }
    ]
}
