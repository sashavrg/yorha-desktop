import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import SddmComponents 2.0 as SDDM
import "components"

Pane {
    id: root
    width: Screen.width
    height: Screen.height
    padding: 0
    font.family: config.fontFamily
    font.pointSize: config.fontSize || 14
    property string iconFont: icons.name
    property bool animationsEnabled: false
    FontLoader { id: icons; source: "assets/icons.ttf" }
    SDDM.TextConstants { id: text_const }
    palette {
        text: config.primaryColour
        placeholderText: config.primaryColour
        accent: config.accentColour
        highlight: config.accentColour
        highlightedText: config.backgroundColour
        button: config.popupsBackgroundColour
        buttonText: config.popupsForegroundColour
        base: config.backgroundColour
        window: config.backgroundColour
    }
    LayoutMirroring.enabled: Qt.locale().textDirection === Qt.RightToLeft
    LayoutMirroring.childrenInherit: true
    background: Rectangle {
        color: config.backgroundColour
        Image {
            anchors.fill: parent
            source: root.height > root.width ? config.backgroundPortrait : config.backgroundLandscape
            fillMode: Image.PreserveAspectCrop
        }
    }
    Text {
        x: 64; y: 70
        text: "■  YoRHa : ACCESS CONTROL"
        color: root.palette.text
        font.family: root.font.family
        font.pixelSize: 15
        font.letterSpacing: 2
        opacity: 0.8
    }
    Column {
        id: panel
        anchors.centerIn: parent
        width: Math.min(800, root.width * 0.88)
        spacing: 18
        Image {
            anchors.horizontalCenter: parent.horizontalCenter
            width: 120; height: 145
            source: config.backgroundColour === "#242220" ? "assets/emblem-night.png" : "assets/emblem-day.png"
            fillMode: Image.PreserveAspectFit
            opacity: 0.8
        }
        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: "YoRHa"
            font.family: root.font.family
            font.pixelSize: 44
            font.letterSpacing: 9
            color: root.palette.text
        }
        Rectangle {
            anchors.horizontalCenter: parent.horizontalCenter
            width: parent.width * 0.5; height: 1
            color: root.palette.text; opacity: 0.55
        }
        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: "OPERATOR AUTHENTICATION"
            font.family: root.font.family
            font.pixelSize: 12
            font.letterSpacing: 2
            color: root.palette.text
        }
        LoginForm {
            id: login_form
            width: parent.width
            onLoginRequest: login(session.currentIndex)
        }
        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: "FOR THE GLORY OF MANKIND"
            font.family: root.font.family
            font.pixelSize: 11
            font.letterSpacing: 2
            color: root.palette.text
            opacity: 0.75
        }
    }
    RowLayout {
        anchors { left: parent.left; right: parent.right; bottom: parent.bottom; margins: 64 }
        spacing: 28
        SessionSelection {
            id: session
            Layout.preferredWidth: 32; Layout.preferredHeight: 32
            KeyNavigation.tab: layout
        }
        Item { Layout.fillWidth: true }
        LayoutSelection {
            id: layout
            Layout.preferredWidth: 40; Layout.preferredHeight: 32
            KeyNavigation.tab: power
        }
        PowerMenu {
            id: power
            Layout.preferredWidth: 32; Layout.preferredHeight: 32
            KeyNavigation.tab: login_form
        }
    }
    Connections {
        target: sddm
        function onLoginSucceeded() {}
        function onLoginFailed() { login_form.loginFailed() }
    }
}
