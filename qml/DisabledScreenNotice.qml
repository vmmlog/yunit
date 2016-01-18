/*
 * Copyright (C) 2015 Canonical, Ltd.
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; version 3.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */

import QtQuick 2.4
import QtQuick.Layouts 1.1
import Ubuntu.Components 1.3
import QtQuick.Window 2.2
import "Components"
import "Rotation"

Item {
    id: root

    property bool infoNoteDisplayed: true

    property int physicalOrientation: Screen.orientation

    WallpaperResolver {
        width: root.width
        id: wallpaperResolver
    }

    Item {
        id: contentContainer
        anchors.centerIn: parent
        height: rotationAngle == 90 || rotationAngle == 270 ? parent.width : parent.height
        width: rotationAngle == 90 || rotationAngle == 270 ? parent.height : parent.width

        property int rotationAngle: {
            print("changed something", Screen.orientation)
            switch (Screen.orientation) {
            case Qt.PortraitOrientation:
                return 0;
            case Qt.LandscapeOrientation:
                return 270;
            case Qt.InvertedPortraitOrientation:
                return 180;
            case Qt.InvertedLandscapeOrientation:
                return 90;
            }
        }

        transform: Rotation {
            origin.x: contentContainer.width / 2
            origin.y: contentContainer.height / 2; axis { x: 0; y: 0; z: 1 }
            angle: contentContainer.rotationAngle
        }

        VirtualTouchPad {
            anchors.fill: parent
        }

        Image {
            anchors.fill: parent
            source: wallpaperResolver.background
        }

        MouseArea {
            objectName: "infoNoticeMouseArea"
            anchors.fill: parent
            opacity: infoNoteDisplayed ? 1 : 0
            visible: opacity > 0
            enabled: visible
            Behavior on opacity {
                UbuntuNumberAnimation { }
            }

            onClicked: root.infoNoteDisplayed = false;

            Rectangle {
                anchors.fill: parent
                color: "black"
                opacity: 0.4
            }

            Label {
                id: text
                anchors.centerIn: parent
                width: parent.width - units.gu(8)
                text: i18n.tr("Your device is now connected to an external display. Use this screen as a touch pad to interact with the mouse.")
                color: "white"
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
                fontSize: "x-large"
                wrapMode: Text.Wrap
            }
        }
    }
}
