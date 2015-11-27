# Doodle3D Cura Plugin for Doodle3D WiFi-Box support. Copyright (c) 2015 Doodle3D
# Based on the Ultimaker's USBPrinting Plugin
# The Doodle3D Cura Plugin is released under the terms of the AGPLv3 or higher.

import threading
import time
import os
import os.path
import sys
import http.client
import json
import urllib

from UM.Application import Application
from UM.Signal import Signal, SignalEmitter
from UM.Logger import Logger
from UM.OutputDevice.OutputDevice import OutputDevice
from UM.PluginRegistry import PluginRegistry
from PyQt5.QtQml import QQmlComponent, QQmlContext
from PyQt5.QtCore import QUrl, QObject, pyqtSlot, pyqtProperty, pyqtSignal
from UM.i18n import i18nCatalog

catalog = i18nCatalog("cura")


class PrinterConnection(OutputDevice, QObject, SignalEmitter):
    def __init__(self, box_IP, parent=None):
        QObject.__init__(self, parent)
        OutputDevice.__init__(self, box_IP)
        SignalEmitter.__init__(self)

        ### Interface related ###
        self.setName(catalog.i18nc("@item:inmenu", "Doodle3D printing"))
        self.setShortDescription(catalog.i18nc("@action:button", "Print with Doodle3D"))
        self.setDescription(catalog.i18nc("@info:tooltip", "Print with Doodle3D WiFi-Box" + " (" + box_IP + ")"))
        self.setIconName("print")
        self._control_view = None     # The print interface window, it gets created later
        #######################################################################

        ### Printer ###
        self._box_IP = box_IP         # IP address of this Doodle3D Wi-Fi box

        self._is_connecting = False   # Printer is connecting
        self._is_connected = False    # Printer is connected
        self._is_printing = False     # Printer is printing
        self._progress = 0            # Printer progress (0 to 100%)
        
        self._heatedUp = False        # Printer heated up
        self._extTemperature = 0     # Extruder temperature
        self._bedTemperature = 0     # Temperature of the bed
        self._extTargetTemperature = 0 # Target Extruder Temperature

        self._currentLine = 0         # Current line (in the gcode_list) in printing
        self._totalLines = 0          # Total lines that's gonna be printed
        self._printPhase = ""         # 3 printer phases: "Heating up... ", "Printing... " and "Print Completed "

        self._gcode_list = []         # Cura-generated GCode
        #######################################################################

        ### Threading ###
        self._printer_info_thread = threading.Thread(target=self.getPrinterInfo)  # The function that gets threaded
        self._printer_info_thread.daemon = True # Daemon threads are automatically killed automatically upon program quit
        self._printer_info_thread.start()       # Starts thread

        self._printing_thread = threading.Thread(target=self.printGCode)  # The function that gets threaded
        self._printing_thread.daemon = True     # Daemon threads are automatically killed automatically upon program quit
        self._printing_thread_started = False   # See if the thread already got started before

        self._connect_thread = threading.Thread(target=self._connect)  # The function that gets threaded
        self._connect_thread.daemon = True      # Daemon threads are automatically killed automatically upon program quit
        #######################################################################
    connectionStateChanged = Signal()

    progressChanged = pyqtSignal()              # Print progress changed (1-100%)
    extruderTemperatureChanged = pyqtSignal()   # Extruder temperature
    extruderTargetChanged = pyqtSignal()        # Target extruder temperature
    bedTemperatureChanged = pyqtSignal()        # Bed temperature (0 if there is no bed)
    bedTargetTemperatureChanged = pyqtSignal()  # Target bed temperature
    printerStateChanged = pyqtSignal()          # Printer states (idle, printing, stopping, etc...)
    printPhaseChanged = pyqtSignal()            # Printing phases ("Heating up... ", "Printing... " and "Print Completed ")

    @pyqtProperty(int, notify=progressChanged)
    def getProgress(self):
        return self._progress

    @pyqtProperty(float, notify=extruderTemperatureChanged)
    def getExtruderTemperature(self):
        return self._extTemperature

    @pyqtProperty(float, notify=extruderTargetChanged)
    def getExtruderTargetTemperature(self):
        return self._extTargetTemperature

    @pyqtProperty(str, notify=printerStateChanged)
    def getPrinterState(self):
        return self.printerState

    @pyqtProperty(float, notify=bedTemperatureChanged)
    def getBedTemperature(self):
        return self._bedTemperature

    @pyqtProperty(float, notify=bedTargetTemperatureChanged)
    def getBedTemperature(self):
        return self._bedTargetTemperature

    @pyqtProperty(str, notify=printPhaseChanged)
    def getPrintPhase(self):
        return self._printPhase

    # Is the printer actively printing
    def isPrinting(self):
        if not self._is_connected:
            return False
        return self._is_printing

    def sendGCode(self, gcode, index):
        if index == 0:
            first = 'true'
        else:
            first = 'false'
        gcodeResponse = self.httppost(self._box_IP, "/d3dapi/printer/print", {
            'gcode': gcode,
            'start': first,
            'first': first
        })

        return gcodeResponse

    # This function runs when you press the "print" button in the control interface
    @pyqtSlot()
    def startPrint(self):
        if self.printerInfo['data']['state'] == "idle":
            Logger.log("d", "startPrint wordt uitgevoerd")
            if self._printing_thread_started is False:
                self._printing_thread.start()
                self._printing_thread_started = True

            else:
                self._is_printing = False
        else:
            pass

    # Start a print based on a g-code.
    # \param gcode_list List with gcode (strings).
    def printGCode(self):
        if self._is_printing is False:
            self._is_printing = True
            self._gcode_list = getattr(Application.getInstance().getController().getScene(), "gcode_list")
            self.joinedString = "".join(self._gcode_list)
            self.decodedList = []
            self.decodedList = self.joinedString.split('\n')

            Logger.log("d", "decodedList is: %s" % self.decodedList)

            blocks = []
            self.tempBlock = []

            for i in range(len(self.decodedList)):
                self.tempBlock.append(self.decodedList[i])

                if sys.getsizeof(self.tempBlock) > 7000:
                    blocks.append(self.tempBlock)
                    Logger.log("d", "New block, size: %s" % sys.getsizeof(self.tempBlock))
                    self.tempBlock = []

            blocks.append(self.tempBlock)
            self.tempBlock = []
            self._totalLines = self.joinedString.count('\n') - self.joinedString.count('\n;') - len(blocks)

            # Size of the print defined in total lines so we can use it to calculate the progress bar
            Logger.log("d", "totalLines is: %s" % self._totalLines)

            currentblock = 0
            total = len(blocks)

            for j in range(len(blocks)):
                successful = False
                while not successful:
                    try:
                        Response = self.sendGCode('\n'.join(blocks[j]), j)
                        if Response['status'] == "success":
                            successful = True
                            currentblock += 1
                            Logger.log("d", "Successfully sent block %s from %s" % (currentblock, total))
                            time.sleep(5)
                        else:
                            time.sleep(5)

                    except:
                        time.sleep(15)  # Send the failed block again after 15 seconds

    # Get the serial port string of this connection.
    # \return serial port
    def getSerialPort(self):
        return self._box_IP

    # Try to connect the serial. This simply starts the thread, which runs _connect.
    def connect(self):
        if not self._connect_thread.isAlive():
            self._connect_thread.start()

    # Private connect function run by thread. Can be started by calling connect.
    def _connect(self):
        Logger.log("d", "Attempting to connect to %s", self._box_IP)
        self._is_connecting = True
        self.setIsConnected(True)
        Logger.log("i", "Established printer connection on port %s" % self._box_IP)
        return

    def setIsConnected(self, state):
        self._is_connecting = False
        if self._is_connected != state:
            self._is_connected = state
            self.connectionStateChanged.emit(self._box_IP)
            # if self._is_connected:
            # self._listen_thread.start()
        else:
            Logger.log("w", "Printer connection state was not changed")

    # Close the printer connection
    def close(self):
        Logger.log("d", "Closing the printer connection.")
        if self._connect_thread.isAlive():
            try:
                self._connect_thread.join()
            except Exception:
                pass

    # Returns the printer's _is_connected True or False
    def isConnected(self):
        return self._is_connected

    # Ensure that close gets called when object is destroyed
    def __del__(self):
        self.close()

    # This creates the control interface if it isn't already created
    def createControlInterface(self):
        if self._control_view is None:
            Logger.log("d", "Creating control interface for printer connection")
            path = QUrl.fromLocalFile(os.path.join(PluginRegistry.getInstance().getPluginPath("Doodle3D"), "ControlWindow.qml"))
            component = QQmlComponent(Application.getInstance()._engine, path)
            self._control_context = QQmlContext(Application.getInstance()._engine.rootContext())
            self._control_context.setContextProperty("manager", self)
            self._control_view = component.create(self._control_context)

    # This will show the control interface, and create the view if its not already created.
    def showControlInterface(self):
        if self._control_view is None:
            self.createControlInterface()
        self._control_view.show()

    # Set the progress of the print. current progress and maximum progress.
    def setProgress(self, progress, max_progress=100):
        self._progress = (progress / max_progress) * 100
        self.progressChanged.emit()

    # Cancels the current print by HTTP POSTing the stop gcode. Resets the progress to 0.
    @pyqtSlot()
    def cancelPrint(self):
        machine = Application.getInstance().getMachineManager().getActiveMachineInstance()
        machine.setMachineSettingValue("machine_start_gcode","M109 S50\nG21 \nG90 \nM107 \nG28 \nG1 Z15 F9000 \nG92 E0 \nG1 F200 E10 \nG92 E0 \nG1 F9000\n M117 Printing Doodle...   \n")
        Application.getInstance().getBackend().forceSlice()
        self.httppost(self._box_IP, "/d3dapi/printer/stop", {'gcode': 'M104 S0\nG28'})
        self.setProgress(0, 100)

    def getPrinterInfo(self):
        while True:
            self.printerInfo = self.httpget(self._box_IP, "/d3dapi/info/status")
            if self.printerInfo is None or not self.printerInfo:
                time.sleep(3)
                return
            continue

            if self.printerInfo['data']['hotend']:  # First checks if we can get info from the printer by looking at the availability of hotend/extruder temperature
                self._extTemperature = self.printerInfo['data']['hotend']  # Get Extruder Temperature 
                self._extTargetTemperature = self.printerInfo['data']['hotend_target']  # Get Extruder Target Temperature          
                self.printerState = self.printerInfo['data']['state']  # Get the state of the printer
                self._bedTemperature = self.printerInfo['data']['bed'] # Get bed temperature
                self._bedTargetTemperature = self.printerInfo['data']['bed'] # Get bed target temperature
                
                self.extruderTemperatureChanged.emit()
                self.extruderTargetChanged.emit() 
                self.printerStateChanged.emit()
                self.bedTemperatureChanged.emit()
                self.bedTargetTemperatureChanged.emit()

            if self.printerInfo['data']['state'] == "printing":
                self._currentLine = self.printerInfo['data']['current_line']
                if (self._extTemperature/self._extTargetTemperature)*100 < 100 and self._heatedUp is False:
                    self.setProgress((self._extTemperature / self._extTargetTemperature) * 100)
                    self._printPhase = "Heating up... "
                    self.printPhaseChanged.emit()

                elif (self._currentLine / self._totalLines) * 100 < 100:
                    self._heatedUp = True
                    self.setProgress((self._currentLine / self._totalLines) * 100)
                    self._printPhase = "Printing... "
                    self.printPhaseChanged.emit()

            elif self.printerInfo['data']['state'] == "idle" and self._progress > 0:
                self.setProgress(100, 100)
                self._printPhase = "Print Completed "
                self.printPhaseChanged.emit()
            else:
                self._heatedUp = False
            time.sleep(4)

    # HTTP GET request to the Doodle3D Wi-Fi box
    # Domain is usually the Doodle3D Wi-Fi box IP, path is usually "d3dapi/info/status"
    def httpget(self, domain, path):
        connect = http.client.HTTPConnection(domain)
        connect.request("GET", path)
        response = connect.getresponse()
        jsonresponse = response.read()
        return json.loads(jsonresponse.decode())

    # HTTP POST request to the Doodle3D Wi-Fi box
    # Domain is usually the Doodle3D Wi-Fi box IP, path is usually "d3dapi/info/status"
    def httppost(self, domain, path, data):
        params = urllib.parse.urlencode(data)
        headers = {"Content-type": "x-www-form-urlencoded", "Accept": "text/plain", "User-Agent": "Cura Doodle3D connection"}
        connect = http.client.HTTPConnection(domain, 80, timeout=30)
        connect.request("POST", path, params, headers)
        response = connect.getresponse()
        jsonresponse = response.read()
        return json.loads(jsonresponse.decode())
