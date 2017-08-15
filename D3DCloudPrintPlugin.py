from UM.i18n import i18nCatalog
from UM.Signal import signalemitter
from UM.Preferences import Preferences
from UM.Logger import Logger
from UM.OutputDevice.OutputDevicePlugin import OutputDevicePlugin
from UM.Message import Message
from UM.Application import Application

from cura.PrinterOutputDevice import PrinterOutputDevice
from cura.Settings.MachineManager import MachineManager

from PyQt5.QtNetwork import QHttpMultiPart, QHttpPart, QNetworkRequest, QNetworkAccessManager, QNetworkReply
from PyQt5.QtCore import QUrl, QByteArray
from PyQt5.QtGui import QDesktopServices

from . import ConnectPrinterIdTranslation

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
        self.setName("Doodle3D WiFi-Box")
        self.setShortDescription(i18n_catalog.i18nc("@action:button", "Print with Doodle3D WiFi-Box"))
        self.setDescription(i18n_catalog.i18nc("@properties:tooltip", "Print with Doodle3D WiFi-Box"))
        self.setIconName("print")

        self._progress_message = None

        self.base_url = "http://connect.doodle3d.com"

        self._manager = QNetworkAccessManager()
        self._manager.finished.connect(self._onFinished)

        self.uploading = False

    def requestWrite(self, nodes, file_name = None, filter_by_machine = False, file_handler = None, **kwargs):
        if not self.uploading:
            self.startUpload();

    def startUpload(self):
        Logger.log("d", "Upload to Doodle3D connect started")
        self.uploading = True


        self._progress_message = Message(i18n_catalog.i18nc("@info:status", "Connecting to Doodle3D Connect"), 0, False, -1)
        self._progress_message.addAction("Cancel", i18n_catalog.i18nc("@action:button", "Cancel"), None, "")
        self._progress_message.actionTriggered.connect(self._onMessageActionTriggered)
        self._progress_message.show()
        # Request upload credentials
        url = QUrl("https://gcodeserver.doodle3d.com/upload")
        self._post_reply = self._manager.post(QNetworkRequest(url), QByteArray())

    def uploadGCode(self, data):
        try:
            job_name = Application.getInstance().getPrintInformation().jobName.strip()
            if job_name is "":
                job_name = "untitled_print"
            file_name = "%s.gcode" % job_name

            global_stack = Application.getInstance().getGlobalContainerStack()
            machine_manager = Application.getInstance().getMachineManager()

            sliceInfo = {
                'printer': {
                    'type': ConnectPrinterIdTranslation.curaPrinterIdToConnect(machine_manager.activeDefinitionId),
                    'title': global_stack.getName()
                },
                'material': {
                    'type': global_stack.material.getId(),
                    'title': global_stack.material.getName()
                },
                'filamentThickness': global_stack.getProperty("material_diameter", "value"),
                'temperature': global_stack.getProperty("material_print_temperature", "value"),
                'name': job_name
            }

            gcode_list = getattr( Application.getInstance().getController().getScene(), "gcode_list")
            gcode = ";%s\n" % json.dumps(sliceInfo);
            for line in gcode_list:
                gcode += line

            multi_part = QHttpMultiPart(QHttpMultiPart.FormDataType)

            for prop_name, prop_value in data["data"]["reservation"]["fields"].items():
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

            self._post_reply = self._manager.post(QNetworkRequest(upload_url), multi_part)
            self._post_reply.uploadProgress.connect(self._onProgress)
            self._progress_message = Message(i18n_catalog.i18nc("@info:status", "Sending data to Doodle3D Connect"), 0, False, -1)
            self._progress_message.addAction("Cancel", i18n_catalog.i18nc("@action:button", "Cancel"), None, "")
            self._progress_message.actionTriggered.connect(self._onMessageActionTriggered)
            self._progress_message.show()
            multi_part.setParent(self._post_reply)
        except Exception as e:
            self._progress_message.hide()
            self._progress_message =  Message(i18n_catalog.i18nc("@info:status", "Unable to send data to Doodle3D Connect. Is another job still active?"))
            self._progress_message.show()
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
            if self._post_reply:
                self._post_reply.abort()
                self._post_reply.uploadProgress.disconnect(self._onProgress)
                self._post_reply = None
            self._progress_message.hide()
            return
             

        status_code = reply.attribute(QNetworkRequest.HttpStatusCodeAttribute)

        if not status_code:
            Logger.log("d", "A reply from %s did not have status code.", reply.url().toString())
            self.uploading = False
            self._progress_message.hide()
            return

        reply_url = reply.url().toString()
        if "upload" in reply_url:
            try:
                json_data = json.loads(bytes(reply.readAll()).decode("utf-8"))
            except json.decoder.JSONDecodeError:
                Logger.log("w", "Received invalid upload credentials request reply from Connect: Not valid JSON.")
                return

            self.gcodeId = json_data["data"]["id"]

            self._progress_message.hide()
            self.uploadGCode(json_data)
        elif "amazonaws" in reply_url:
            if status_code in [200, 201, 202, 204]:
                self._progress_message.hide()
                self._progress_message = Message(i18n_catalog.i18nc("@info:status", "File sent to Doodle3D Connect"), 0)
                self._progress_message.addAction("open_browser", i18n_catalog.i18nc("@action:button", "Open Connect.."), "globe", i18n_catalog.i18nc("@info:tooltip", "Open the Doodle3D Connect web interface"))
                self._progress_message.actionTriggered.connect(self._onMessageActionTriggered)
                self._progress_message.show()
                self.uploading = False
                Logger.log("d", "uploaded to amazon")
            else:
                self._progress_message.hide()
                Logger.log("w", "Unexpected status code in reply from AWS S3")

        reply.deleteLater()
        if reply == self._post_reply:
            self._post_reply = None

    def _onMessageActionTriggered(self, message, action):
        if action == "open_browser":
            QDesktopServices.openUrl(QUrl("%s?uuid=%s" % (self.base_url, self.gcodeId)))
        elif action == "Cancel":
            Logger.log("d", "canceled upload to Doodle3D Connect")
            self._progress_message.hide()
            if self._post_reply:
                self._post_reply.abort()
                self._post_reply = None
        else:
            Logger.log("d", "unknown action: %s" % action)
