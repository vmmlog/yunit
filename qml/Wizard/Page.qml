/*
 * Copyright (C) 2013 Canonical, Ltd.
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

import QtQuick 2.3
import Ubuntu.Components 1.2
import MeeGo.QOfono 0.2

Item {
    readonly property real buttonMargin: units.gu(3)
    readonly property real buttonWidth: (width - buttonMargin * 2) / 2 -
                                        buttonMargin / 2
    readonly property real buttonBarHeight: units.gu(5)

    readonly property real topMargin: units.gu(11)
    readonly property real bottomMargin: units.gu(3)
    readonly property real leftMargin: units.gu(3)
    readonly property real rightMargin: units.gu(3)
    readonly property real customMargin: units.gu(4) // margin for the custom (w/o title bar) pages

    // If you want to skip a page, mark skipValid false while you figure out
    // whether to skip, then set it to true once you've determined the value
    // of the skip property.
    property bool skipValid: true
    property bool skip: false

    property bool mobileOnly: true
    property bool desktopOnly: false

    property bool hasBackButton: true
    property string backButtonText: i18n.ctr("Button: Go back one page in the Wizard", "Back")
    property bool customBack: false
    property bool customTitle: false
    property alias forwardButtonSourceComponent: forwardButton.sourceComponent
    property alias content: contentHolder
    property bool lastPage: false

    property string title: ""

    signal backClicked()

    visible: false
    anchors.fill: parent

    property alias modemManager: modemManager
    property alias simManager0: simManager0
    property alias simManager1: simManager1

    OfonoManager { // need it here for the language and country detection
        id: modemManager
        property bool gotSimCard: available && ((simManager0.ready && simManager0.present) || (simManager1.ready && simManager1.present))
        onAvailableChanged: {
            print("== Modem manager AVAILABLE");
        }
        onGotSimCardChanged: {
            print("== Modem has a usable SIM CARD");
        }
    }

    // Ideally we would query the system more cleverly than hardcoding two
    // sims.  But we don't yet have a more clever way.  :(
    OfonoSimManager {
        id: simManager0
        modemPath: modemManager.modems.length >= 1 ? modemManager.modems[0] : ""
        onReadyChanged: {
            print("=== SIM 1 READY!");
            print("SIM 1 present:", simManager0.present);
            print("SIM 1 ready:", simManager0.ready);
            print("SIM 1 languages:", simManager0.preferredLanguages);
            print("SIM 1 country code:", simManager0.mobileCountryCode);
        }
    }

    OfonoSimManager {
        id: simManager1
        modemPath: modemManager.modems.length >= 2 ? modemManager.modems[1] : ""
        onReadyChanged: {
            print("=== SIM 2 READY!");
            print("SIM 2 present:", simManager1.present);
            print("SIM 2 ready:", simManager1.ready);
            print("SIM 2 languages:", simManager1.preferredLanguages);
            print("SIM 2 country code:", simManager1.mobileCountryCode);
        }
    }

    // title
    Image {
        id: titleRect
        visible: !lastPage
        anchors {
            top: parent.top
            left: parent.left
            right: parent.right
        }
        source: customTitle ? "" : "Pages/data/Phone header bkg.png"
        height: customTitle ? customMargin + titleLabel.height + customMargin : topMargin + bottomMargin
        clip: true

        Label {
            id: titleLabel
            anchors {
                left: parent.left
                right: parent.right
                bottom: parent.bottom
                bottomMargin: bottomMargin
                leftMargin: leftMargin
                rightMargin: rightMargin
            }
            wrapMode: Text.Wrap
            text: title
            color: customTitle ? "#525252" : "#fdfdfd"
            fontSize: "x-large"
        }
    }

    // content
    Item {
        id: contentHolder
        anchors {
            top: titleRect.bottom
            left: parent.left
            right: parent.right
            bottom: buttonRect.top
            leftMargin: leftMargin
            rightMargin: rightMargin
        }
    }

    // button bar
    Rectangle {
        id: buttonRect
        visible: !lastPage
        anchors {
            bottom: parent.bottom
            left: parent.left
            right: parent.right
        }
        height: buttonBarHeight
        color: "#f5f5f5"

        StackButton {
            id: backButton
            objectName: "backButton"
            width: buttonWidth
            anchors {
                left: parent.left
                bottom: parent.bottom
                leftMargin: leftMargin
                verticalCenter: parent.verticalCenter
            }
            z: 1
            text: backButtonText
            visible: pageStack.depth > 1 && hasBackButton
            backArrow: true

            onClicked: customBack ? backClicked() : pageStack.prev()
        }

        Loader {
            id: forwardButton
            objectName: "forwardButton"
            width: buttonWidth
            anchors {
                right: parent.right
                bottom: parent.bottom
                rightMargin: rightMargin
                verticalCenter: parent.verticalCenter
            }
            z: 1
        }
    }
}
