from UM.i18n import i18nCatalog
from UM.Signal import signalemitter
from UM.Preferences import Preferences
from UM.Logger import Logger
from UM.OutputDevice.OutputDevicePlugin import OutputDevicePlugin
from UM.Message import Message
from UM.Application import Application

from cura.PrinterOutputDevice import PrinterOutputDevice

from PyQt5.QtNetwork import QHttpMultiPart, QHttpPart, QNetworkRequest, QNetworkAccessManager, QNetworkReply
from PyQt5.QtCore import QUrl, QByteArray
from PyQt5.QtGui import QDesktopServices

import json
import inspect


i18n_catalog = i18nCatalog("cura")
class D3DCloudPrintPlugin(OutputDevicePlugin):
    def __init__(self):
        super().__init__()

    def start(self):
        self.getOutputDeviceManager().addOutputDevice(D3DCloudPrintOutputDevice())

    def stop(self):
        self.getOutputDeviceManager().removeOutputDevice("d3dcloudprint")

@signalemitter
class D3DCloudPrintOutputDevice(PrinterOutputDevice):
    def __init__(self):
        super().__init__("d3dcloudprint")

        self.setPriority(2)
        self.setName("Doodle3D WiFi-box")
        self.setShortDescription(i18n_catalog.i18nc("@action:button", "Print with Doodle3D WiFi-box"))
        self.setDescription(i18n_catalog.i18nc("@properties:tooltip", "Print with Doodle3D WiFi-box"))
        self.setIconName("print")

        self._progress_message = None

        self.base_url = "http://connect.doodle3d.com"

        self._manager = QNetworkAccessManager()
        self._manager.finished.connect(self._onFinished)

        self.uploading = False

    def requestWrite(self, nodes, file_name = None, filter_by_machine = False, file_handler = None, **kwargs):
        if not self.uploading:
            self.startPrint();

    def startPrint(self):
        Logger.log("d", "print started")
        self.uploading = True

        job_name = Application.getInstance().getPrintInformation().jobName.strip()
        if job_name is "":
            job_name = "untitled_print"
            file_name = "%s.gcode" % job_name

        url = QUrl("https://gcodeserver.doodle3d.com/upload")
        self._manager.post(QNetworkRequest(url), QByteArray())

    def uploadGCode(self, data):
        try:
            gcode_list = getattr( Application.getInstance().getController().getScene(), "gcode_list")
            gcode = "";
            for line in gcode_list:
                gcode += line

            Logger.log("d", "{}", gcode)

            multi_part = QHttpMultiPart(QHttpMultiPart.FormDataType)

            for prop_name, prop_value in data["data"]["reservation"]["fields"].items():
                Logger.log("d", "{}: {}", prop_name, prop_value)
                part = QHttpPart()
                part.setHeader(QNetworkRequest.ContentDispositionHeader, "form-data; name=\"%s\"" % prop_name)
                part.setBody(prop_value.encode())
                multi_part.append(part)

            gcode_part = QHttpPart()
            gcode_part.setHeader(QNetworkRequest.ContentDispositionHeader, "form-data; name=\"file\"")
            gcode_part.setBody(gcode.encode())
            multi_part.append(gcode_part)

            upload_url = QUrl(data["data"]["reservation"]["url"])
            Logger.log("d", "{}", upload_url)

            reply = self._manager.post(QNetworkRequest(upload_url), multi_part)
            reply.uploadProgress.connect(self._onProgress)
            self._progress_message = Message(i18n_catalog.i18nc("@info:status", "Sending data to Doodle3D Connect"), 0, False, -1)
            self._progress_message.addAction("Cancel", i18n_catalog.i18nc("@action:button", "Cancel"), None, "")
            self._progress_message.show()
            multi_part.setParent(reply)
        except Exception as e:
            Logger.log("e", "An exception occured during G-code upload: %s" % str(e))

    def _onProgress(self, bytes_sent, bytes_total):
        if bytes_total > 0:
            # Treat upload progress as response. Uploading can take more than 10 seconds, so if we don't, we can get
            # timeout responses if this happens.
            progress = bytes_sent / bytes_total * 100
            if progress < 100:
                if progress > self._progress_message.getProgress():
                    self._progress_message.setProgress(progress)
            else:
                self._progress_message.hide()
                self._progress_message = Message(i18n_catalog.i18nc("@info:status", "Storing data on Doodle3D Connect"), 0, False, -1)
                self._progress_message.show()
        else:
            self._progress_message.setProgress(0)

    def _onFinished(self, reply):
        if reply.error() == QNetworkReply.TimeoutError:
            Logger.log("w", "Received a timeout on a request to the G-code server")

        reply_url = reply.url().toString()
        if "upload" in reply_url:
            json_data = json.loads(bytes(reply.readAll()).decode("utf-8"))
            Logger.log("d", "{}", json_data)

            self.gcodeId = json_data["data"]["id"]

            reply.deleteLater()
            self.uploadGCode(json_data);
        if "amazonaws" in reply_url:
            self._progress_message.hide()
            self._progress_message = Message(i18n_catalog.i18nc("@info:status", "G-code file sent to Doodle3D Connect"))
            self._progress_message.addAction("open_browser", i18n_catalog.i18nc("@action:button", "Open Connect.."), "globe", i18n_catalog.i18nc("@info:tooltip", "Open the Doodle3D Connect web interface"))
            self._progress_message.actionTriggered.connect(self._onMessageActionTriggered)
            self._progress_message.show()
            self.uploading = False
            Logger.log("d", "uploaded to amazon")

    def _onMessageActionTriggered(self, message, action):
        if action == "open_browser":
            QDesktopServices.openUrl(QUrl("%s?uuid=%s" % (self.base_url, self.gcodeId)))



