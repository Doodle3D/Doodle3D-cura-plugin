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
    def __init__(self, box_IP, box_ID, parent=None):
        QObject.__init__(self, parent)
        OutputDevice.__init__(self, box_IP)
        SignalEmitter.__init__(self)

        ### Interface related ###
        self.setName(catalog.i18nc("@item:inmenu", "Doodle3D printing"))
        self.setShortDescription(catalog.i18nc("@action:button", "Print with Doodle3D"))
        self.setDescription(catalog.i18nc("@info:tooltip", "Print with "+ box_ID))
        self.setIconName("print")
        self._control_view = None     # The print interface window, it gets created later
        self.printButton = True
        #######################################################################

        ### Printer ###
        self._box_IP = box_IP         # IP address of this Doodle3D Wi-Fi box
        self._box_ID = box_ID
        self._is_connecting = False   # Printer is connecting
        self._is_connected = False    # Printer is connected
        self._is_printing = False     # Printer is printing
        self._is_cancelling = False   # Printer is cancelling
        self._progress = 0            # Printer progress (0 to 100%)

        self.printBoolean = False
        
        self._heatedUp = False         # Printer heated up
        self._extTemperature = 0       # Extruder temperature
        self._extTargetTemperature = 0 # Target Extruder Temperature
        self._bedTemperature = 0       # Temperature of the bed
        self._bedTargetTemperature = 0     # Target Temperature of the bed

        self._currentLine = 0         # Current line (in the gcode_list) in printing
        self._totalLines = 0          # Total lines that's gonna be printed
        self._progress = 0            # Progress of the print
        self._printPhase = ""         # 3 printer phases: "Heating up... ", "Printing... " and "Print Completed "
        self._printerState = ""

        self._stateLocked = False       

        self._gcode_list = []         # Cura-generated GCode
        #######################################################################

        ### Threading ###
        self._printer_info_thread = threading.Thread(target=self.getPrinterInfo)  # The function that gets threaded
        self._printer_info_thread.daemon = True # Daemon threads are automatically killed automatically upon program quit
        self._printer_info_thread.start()       # Starts thread

        self._connect_thread = threading.Thread(target=self._connect)
        self._connect_thread.daemon = True


        self.flagevent = threading.Event()
        #######################################################################
    
    connectionStateChanged = Signal()

    progressChanged = pyqtSignal()              # Print progress changed (1-100%)
    extruderTemperatureChanged = pyqtSignal()   # Extruder temperature
    extruderTargetChanged = pyqtSignal()        # Target extruder temperature
    bedTemperatureChanged = pyqtSignal()        # Bed temperature (0 if there is no bed)
    bedTargetTemperatureChanged = pyqtSignal()  # Target bed temperature
    printerStateChanged = pyqtSignal()          # Printer states (idle, printing, stopping, etc...)
    printPhaseChanged = pyqtSignal()            # Printing phases ("Heating up... ", "Printing... " and "Print Completed ")
    isPrintingChanged = pyqtSignal()
    boxIDChanged = pyqtSignal()
    printButtonSignal = pyqtSignal()

    @pyqtProperty(str, notify = boxIDChanged)
    def getBoxID(self):
        return self._box_ID

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
        return self._printerState

    @pyqtProperty(float, notify=bedTemperatureChanged)
    def getBedTemperature(self):
        return self._bedTemperature

    @pyqtProperty(float, notify=bedTargetTemperatureChanged)
    def getBedTargetTemperature(self):
        return self._bedTargetTemperature

    @pyqtProperty(str, notify=printPhaseChanged)
    def getPrintPhase(self):
        return self._printPhase

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

    
    # This function runs when you press the "cancel" button in the control interface
    @pyqtSlot()
    def testButton(self):
        #Application.getInstance().getBackend().processingProgress.connect(self.onProcessingProgress)
        #Application.getInstance().getBackend().printDurationMessage.connect(self.onPrintDurationMessage)
        self.setGCodeFlavor("UltiGCode")
        #Application.getInstance().getMachineManager().getActiveMachineInstance().setMachineSettingValue("machine_gcode_flavor","RepRap")
        self.forceSlice()
        self._gcode_list = getattr(Application.getInstance().getController().getScene(), "gcode_list")
        Logger.log("d","GCODE IS:%s" % self._gcode_list)

    @pyqtSlot()
    def cancelPrint(self):
        self.overrideState("stopping")
        self._is_printing = False
        self._is_cancelling = True
        self.setGCodeFlavor("UltiGCode")
        self.httppost(self._box_IP, "/d3dapi/printer/stop", {'gcode': 'M104 S0\nG28'})  # Cancels the current print by HTTP POSTing the stop gcode.
        self.setProgress(0, 100)  # Resets the progress to 0.
        self.forceSlice()

    # This function runs when you press the "print" button in the plugin window
    @pyqtSlot()
    def startPrint(self):
        self.overrideState("printing")
        self._is_printing = True
        Application.getInstance().getBackend().printDurationMessage.connect(self.onFinishedSlicing)
        self._printing_thread = threading.Thread(target=self.printGCode)
        self._printing_thread.daemon = True
        self.setGCodeFlavor("RepRap")
        self.forceSlice()

    def onFinishedSlicing(self, time, amount):
        Logger.log("d","Finished slicing")
        self.time = time
        self.amount = amount
        if self._is_printing == True:
            self._is_printing = False
            self._printing_thread.start()
            Application.getInstance().getBackend().printDurationMessage.disconnect(self.onFinishedSlicing)

    # Starts the print
    def printGCode(self):
        self._is_printing = True
        # self.isPrintingChanged.emit()
        self._is_cancelling = False
        self._gcode_list = getattr(Application.getInstance().getController().getScene(), "gcode_list")
        Logger.log("d","GCODE IS:%s" % self._gcode_list)
        #with open("bimbambom.txt", "w") as text_file:
        #    print("GCode: {}".format(self._gcode_list), file=text_file)

        self.joinedString = "".join(self._gcode_list)
        self.decodedList = []
        self.decodedList = self.joinedString.split('\n')
        self.tempBlock = []
        blocks = []
        
        for i in range(len(self.decodedList)):
            self.tempBlock.append(self.decodedList[i])

            if sys.getsizeof(self.tempBlock) > 7000:
                blocks.append(self.tempBlock)
                Logger.log("d", "New block, size: %s" % sys.getsizeof(self.tempBlock))
                self.tempBlock = []

        blocks.append(self.tempBlock)
        self.tempBlock = []
        self._totalLines = self.joinedString.count('\n') - self.joinedString.count('\n;') - len(blocks)
        self.currentblock = 0
        self.total = len(blocks)
        for j in range(len(blocks)):
            successful = False     # The sent status of the current gcode block 
            while not successful: 
                if self._is_cancelling is True:
                    self._is_cancelling = False
                    self.currentblock = 0
                    self.setGCodeFlavor("UltiGCode")
                    return
                if self.printerInfo['buffered_lines'] <= 150000:
                    try:
                        Response = self.sendGCode('\n'.join(blocks[j]), j)  # Send next block
                        self.releaseStateLock()
                        if Response['status'] == "success":  # If the block is successfully sent
                            successful = True  # Set the variable to True
                            self.currentblock += 1  # Go to the next block in the array
                            Logger.log("d", "Successfully sent block %s from %s" % (self.currentblock, self.total))
                            time.sleep(2)  # Wait 5 seconds before sending the next block to not overload the API

                    except:
                        Logger.log("d","Failed block, sending again in 15 seconds")
                        time.sleep(15)  # Send the failed block again after 15 seconds
                time.sleep(3)
        self.setGCodeFlavor("UltiGCode")

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
            except Exception as e:
                pass

        self._connect_thread = threading.Thread(target=self._connect)
        self._connect_thread.daemon = True
        
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

    ##  Private function to set the temperature of an extruder
    #   \param index index of the extruder
    #   \param temperature recieved temperature
    def _setExtruderTemperature(self, index, temperature):
        try: 
            ##self._extruder_temperatures[index] = temperature
            self.extruderTemperatureChanged.emit()
        except Exception as e:
            pass

    ##  Private function to set the temperature of the bed.
    #   As all printers (as of time of writing) only support a single heated bed,
    #   these are not indexed as with extruders.
    def _setBedTemperature(self, temperature):
        self._bed_temperature = temperature
        self.bedTemperatureChanged.emit()

    def requestWrite(self, node, file_name = None):
        self.showControlInterface()

    # Set the progress of the print. current progress and maximum progress.
    def setProgress(self, progress, max_progress=100):
        self._progress = (progress / max_progress) * 100
        self.progressChanged.emit()

    def releaseStateLock(self):
        self._stateLocked = False

    def overrideState(self, value):
        self.setState(value)
        self._stateLocked = True

    def setState(self, value):
        if self._stateLocked is False:
            self._printerState = value
            self.printerStateChanged.emit()

    def setGCodeFlavor(self,flavor):
        Application.getInstance().getMachineManager().getActiveMachineInstance().setMachineSettingValue("machine_gcode_flavor",flavor)
        return

    def forceSlice(self):
        Application.getInstance().getBackend().forceSlice()
        return

    def getPrinterInfo(self):
        ## #1 First check if the box is on
        #  #2 Check if the box is connected to the printer
        #  #3 Gather all data from printer (Temperatures, Temperature Targets, Printer State etc.)
        #  #4 Check state and act accordingly
        while True:
            try: #1
                self.printerInfo = self.httpget(self._box_IP, "/d3dapi/info/status")
                self.printerInfo = self.printerInfo['data']
            except:
                self._printPhase = "Lost connection"
                self.printPhaseChanged.emit()
                self._extTemperature = 0
                self._bedTemperature = 0
                self.extruderTemperatureChanged.emit()
                self.bedTemperatureChanged.emit()
                self.setProgress(0,100)
                time.sleep(3)
                continue

            if self._printerState == "disconnected": #2
                Logger.log("d","This box is not connected to the printer: %s" % self._box_ID)
                self._printPhase = "Box not connected to a printer "
                self.printPhaseChanged.emit()

            try: #3
                self._extTemperature = self.printerInfo['hotend']  # Get Extruder Temperature 
                self._extTargetTemperature = self.printerInfo['hotend_target']  # Get Extruder Target Temperature
                self._APIState = self.printerInfo['state']
                self.setState(self.printerInfo['state'])
                self._bedTemperature = self.printerInfo['bed'] # Get bed temperature
                self._bedTargetTemperature = self.printerInfo['bed_target'] # Get bed target temperature

                if (self._APIState == self._printerState):
                    self.releaseStateLock()

                self.extruderTemperatureChanged.emit()
                self.extruderTargetChanged.emit() 
                self.printerStateChanged.emit()
                self.bedTemperatureChanged.emit()
                self.bedTargetTemperatureChanged.emit()

            except KeyError:
                time.sleep(3)
                continue

            if self.printerInfo['state'] == "printing": #4
                self._currentLine = self.printerInfo['current_line']

                if self.currentblock == self.total:
                    self._apitotalLines = self.printerInfo['total_lines']
                else:
                    self._apitotalLines = self._totalLines

                if self._extTargetTemperature >= 1 and (self._extTemperature/self._extTargetTemperature)*100 < 100 and self._heatedUp is False:
                    self.setProgress((self._extTemperature / self._extTargetTemperature) * 100, 100)
                    self._printPhase = "Heating up... {0:.1f}%".format(self.getProgress)
                    self.printPhaseChanged.emit()

                elif (self._currentLine / self._apitotalLines) * 100 < 100 and self._currentLine > 2:
                    self._heatedUp = True
                    self.setProgress((self._currentLine / self._apitotalLines) * 100, 100)
                    self._printPhase = "Printing... {0:.1f}%".format(self.getProgress)
                    self.printPhaseChanged.emit()
                else:
                    self._printPhase = "Getting ready to print..."
                    self.printPhaseChanged.emit()

            elif self._printerState == "idle":
                self._heatedUp = False
                self.flagevent.clear()
                if self._progress > 0:
                    self.setProgress(0, 100)
                    self._printPhase = "Print Completed"
                elif self._progress == 0:
                    self._is_printing = False
                    self._printPhase = "Ready to print"
                    
            elif self._printerState == "stopping":
                self.setProgress(0,100)
                self._is_printing = False
                self._printPhase = "Stopping the print, it might take some time"
            else:
                self._printPhase = ""
                self._heatedUp = False 

            self.printPhaseChanged.emit()
            self.isPrintingChanged.emit()         
            time.sleep(2)

    # HTTP GET request to the Doodle3D Wi-Fi box
    # Domain could be the Doodle3D Wi-Fi box IP, path is usually "d3dapi/info/status"
    def httpget(self, domain, path):
        connect = http.client.HTTPConnection(domain,80,timeout=5)
        connect.request("GET", path)
        response = connect.getresponse()
        jsonresponse = response.read()
        return json.loads(jsonresponse.decode())

    # HTTP POST request to the Doodle3D Wi-Fi box
    # Domain could be the Doodle3D Wi-Fi box IP, path is usually "d3dapi/info/status"
    def httppost(self, domain, path, data):
        params = urllib.parse.urlencode(data)
        headers = {"Content-type": "x-www-form-urlencoded", "Accept": "text/plain", "User-Agent": "Cura Doodle3D connection"}
        connect = http.client.HTTPConnection(domain, 80, timeout=30)
        connect.request("POST", path, params, headers)
        response = connect.getresponse()
        jsonresponse = response.read()
        Logger.log("d","Response is: %s" % jsonresponse)
        return json.loads(jsonresponse.decode())
