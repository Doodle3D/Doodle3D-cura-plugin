from UM.i18n import i18nCatalog
from UM.Signal import signalemitter
from UM.Preferences import Preferences
from UM.Logger import Logger
from UM.OutputDevice.OutputDevicePlugin import OutputDevicePlugin
from UM.Application import Application

from cura.PrinterOutputDevice import PrinterOutputDevice

from PyQt5.QtNetwork import QHttpMultiPart, QHttpPart, QNetworkRequest, QNetworkAccessManager, QNetworkReply
from PyQt5.QtCore import QUrl, QByteArray

import json
import inspect


i18n_catalog = i18nCatalog("cura")
class D3DCloudPrintPlugin(OutputDevicePlugin):
    def __init__(self):
        super().__init__()

        Preferences.getInstance().addPreference("d3dcloudprint/gcode_server", "")
    
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
        self.setDescription(i18n_catalog.i18nc("@properties:tooltip", "Print with OctoPrint"))
        self.setIconName("print")

        self._manager = QNetworkAccessManager()
        self._manager.finished.connect(self._onFinished)

    def requestWrite(self, nodes, file_name = None, filter_by_machine = False, file_handler = None, **kwargs):
        self.startPrint();

    def startPrint(self):
        Logger.log("d", "print started")


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
            multi_part.setParent(reply)
        except Exception as e:
            Logger.log("e", "An exception occured during G-code upload: %s" % str(e))

    def _onFinished(self, reply):
        if reply.error() == QNetworkReply.TimeoutError:
            Logger.log("w", "Received a timeout on a request to the G-code server")

        reply_url = reply.url().toString()
        if "upload" in reply_url:
            json_data = json.loads(bytes(reply.readAll()).decode("utf-8"))
            Logger.log("d", "{}", json_data)

            reply.deleteLater()
            self.uploadGCode(json_data);
        if "amazonaws" in reply_url:
            Logger.log("d", "uploaded to amazon")



