# Doodle3D Cura Plugin for Doodle3D WiFi-Box support. Copyright (c) 2015 Doodle3D
# Based on the Ultimaker's USBPrinting Plugin      
# Cura is released under the terms of the AGPLv3 or higher.
# The Doodle3D Cura Plugin is released under the terms of the AGPLv3 or higher.

from .avr_isp import stk500v2, ispBase, intelHex
import serial
import threading
import time
import queue
import re
import functools
import os
import os.path
import sys

import http.client
import json
import urllib

from UM.Application import Application
from UM.Signal import Signal, SignalEmitter
from UM.Resources import Resources
from UM.Logger import Logger
from UM.OutputDevice.OutputDevice import OutputDevice
from UM.OutputDevice import OutputDeviceError
from UM.PluginRegistry import PluginRegistry

from PyQt5.QtQuick import QQuickView
from PyQt5.QtQml import QQmlComponent, QQmlContext
from PyQt5.QtCore import QUrl, QObject, pyqtSlot, pyqtProperty, pyqtSignal, Qt

from UM.i18n import i18nCatalog
catalog = i18nCatalog("cura")

class PrinterConnection(OutputDevice, QObject, SignalEmitter):
    def __init__(self, serial_port, parent = None):
        QObject.__init__(self, parent)
        OutputDevice.__init__(self, serial_port)
        SignalEmitter.__init__(self)
        #super().__init__(serial_port)
        self.setName(catalog.i18nc("@item:inmenu", "Doodle3D printing"))
        self.setShortDescription(catalog.i18nc("@action:button", "Print with Doodle3D"))
        self.setDescription(catalog.i18nc("@info:tooltip", "Print with Doodle3D WiFi-Box" + " (" + serial_port + ")"))
        self.setIconName("print")

        self._serial = None
        self._serial_port = serial_port
        ##self._error_state = None

        self._connect_thread = threading.Thread(target = self._connect)
        self._connect_thread.daemon = True
        # Printer is connected
        self._is_connected = False

        # Printer is connecting
        self._is_connecting = False

<<<<<<< HEAD
        # Printer is printing
        self._is_printing = False

        # Progress of the print
        self._progress = 0
=======
        # The baud checking is done by sending a number of m105 commands to the printer and waiting for a readable
        # response. If the baudrate is correct, this should make sense, else we get giberish.
        self._required_responses_auto_baud = 3

        self._progress = 0

        self._update_firmware_thread = threading.Thread(target= self._updateFirmware)
        self._update_firmware_thread.daemon = True
        
        self._heatup_wait_start_time = time.time()

        ## Queue for commands that need to be send. Used when command is sent when a print is active.
        self._command_queue = queue.Queue()

        self._is_printing = False

        ## G-code list
        self.gcode_list = []

        ## Set when print is started in order to check running time.
        self._print_start_time = None
        self._print_start_time_100 = None
>>>>>>> 43e1a0231bfa300d63e65959474bf3f137e7e620

        self.heatedUp = False
        # Gcode
        self.gcode_list = []

        # Temperature of the printer extruder
        self.extTemperature = 0

        self._printPhase = ""

<<<<<<< HEAD
        # Current line (in the gcode_list) in printing
        self.currentLine = 0
=======
        self.extTemperature = 0
        self.currentLine = 0
        self.totalLines = 0

        # Temperatures of all extruders
        self._extruder_temperatures = [0] * self._extruder_count
>>>>>>> 43e1a0231bfa300d63e65959474bf3f137e7e620

        # Total lines that's gonna be printed
        self.totalLines = 0

        # Target temperature of the bed
        self._target_bed_temperature = 0 

        # Temperature of the bed
        self._bed_temperature = 0

        # In order to keep the connection alive we request the temperature every so often from a different extruder.
        # This index is the extruder we requested data from the last time.
        self._temperature_requested_extruder_index = 0 

        self._updating_firmware = False

        self._firmware_file_name = None

        self._control_view = None

        self._printer_info_thread = threading.Thread(target = self.getPrinterInfo)
        self._printer_info_thread.daemon = True
        self.connectPrinterInfo()

        self._printing_thread = threading.Thread(target = self.printGCode)
        self._printing_thread.daemon = True
        ## Should only start thread once
        self.startedThread = False

    onError = pyqtSignal()
    progressChanged = pyqtSignal()
    extruderTemperatureChanged = pyqtSignal()
    extruderTargetChanged = pyqtSignal()
    printerStateChanged = pyqtSignal()
    bedTemperatureChanged = pyqtSignal()
    printPhaseChanged = pyqtSignal()

    @pyqtProperty(int, notify = progressChanged)
    def progress(self):
        return self._progress

    @pyqtProperty(float, notify = extruderTemperatureChanged)
    def extruderTemperature(self):
        return self.extTemperature

    @pyqtProperty(float, notify = extruderTargetChanged)
    def extruderTarget(self):
        return self.extTargetTemperature

    @pyqtProperty(str, notify = printerStateChanged)
    def printerStateGet(self):
        return self.printerState

    @pyqtProperty(float, notify = bedTemperatureChanged)
    def bedTemperature(self):
        return self._bed_temperature

    @pyqtProperty(str, notify = printPhaseChanged)
    def printPhase(self):
        return self._printPhase

    ##  Is the printer actively printing
    def isPrinting(self):
        if not self._is_connected or self._serial is None:
            return False
        return self._is_printing

    def sendGCode(self,gcode,index):
        if index == 0:
            first = 'true'
        else:
            first = 'false'
        gcodeResponse = self.httppost(self._serial_port,"/d3dapi/printer/print",{
            'gcode': gcode,
            'start': first,
            'first': first
        })

        return gcodeResponse

    @pyqtSlot()
    def startPrint(self):
        if self.stateReply['data']['state'] == "idle":
            Logger.log("d", "startPrint wordt uitgevoerd")
<<<<<<< HEAD
            if self.startedThread is False:
                self._printing_thread.start()
                self.startedThread = True

            else:
                self._is_printing = False
        else:
            pass


=======
            self.writeStarted.emit(self)
            ##self.printGCode(gcode_list)
            if self.startedThread is False:
                self._printing_thread.start()
                self.startedThread = True

            elif self.startedThread is True:
                self._is_printing = False
            else:
                pass

        else:
            pass

>>>>>>> 43e1a0231bfa300d63e65959474bf3f137e7e620
    ##  Start a print based on a g-code.
    #   \param gcode_list List with gcode (strings).
    def printGCode(self):
        while True:
            if self._is_printing is False:
                self._is_printing = True
                self.gcode_list = getattr( Application.getInstance().getController().getScene(), "gcode_list")
                self.joinedString = "".join(self.gcode_list)


                self.decodedList = []
                self.decodedList = self.joinedString.split('\n')

                Logger.log("d", "decodedList is: %s" % self.decodedList)

                blocks = []
                self.tempBlock = []

                for i in range(len(self.decodedList)):
                    self.tempBlock.append(self.decodedList[i])

<<<<<<< HEAD
                    if sys.getsizeof(self.tempBlock) > 30000:
                        blocks.append(self.tempBlock)
                        Logger.log("d", "New block, size: %s" % sys.getsizeof(self.tempBlock))
                        self.tempBlock = []
=======
                    if sys.getsizeof(self.tempBlock) > 7000:
                        self.blocks.append(self.tempBlock)
                        Logger.log("d", "New block, size: %s" % sys.getsizeof(self.tempBlock))
                        ##self.getPrinterInfo()
                        ##Logger.log("d", "self.extTemperature is: %s" % self.extTemperature)
                        self.tempBlock = []
                        ##self.setProgress((  / self.totalLines) * 100)
                        ##self.progressChanged.emit()
>>>>>>> 43e1a0231bfa300d63e65959474bf3f137e7e620

                
                blocks.append(self.tempBlock)
                self.tempBlock = []
                
                self.totalLines = self.joinedString.count('\n') - self.joinedString.count('\n;') - len(blocks)

                ## Size of the print defined in total lines so we can use it to calculate the progress bar
                Logger.log("d","totalLines is: %s" % self.totalLines)

<<<<<<< HEAD
                currentblock = 0
                total = len(blocks)

=======
>>>>>>> 43e1a0231bfa300d63e65959474bf3f137e7e620
                for j in range(len(blocks)):
                    successful = False
                    while not successful:
                        try: 
                            Response = self.sendGCode('\n'.join(blocks[j]),j)
                            if Response['status'] == "success":
<<<<<<< HEAD
                                successful = True
                                currentblock+=1
                                Logger.log("d", "Successfully sent block %s from %s" % (currentblock, total))
=======
                                successful = True   
>>>>>>> 43e1a0231bfa300d63e65959474bf3f137e7e620
                            else:
                                time.sleep(5)

                        except:
<<<<<<< HEAD
=======
                            Logger.log("d","Couldn't send the block")  
>>>>>>> 43e1a0231bfa300d63e65959474bf3f137e7e620
                            time.sleep(15) #Send the failed block again after 15 seconds
            else:
                pass


    ##  Get the serial port string of this connection.
    #   \return serial port
    def getSerialPort(self):
        return self._serial_port

    def connectPrinterInfo(self):
        self._printer_info_thread.start()

    ##  Try to connect the serial. This simply starts the thread, which runs _connect.
    def connect(self):
        if not self._connect_thread.isAlive():
            self._connect_thread.start()

    ##  Private connect function run by thread. Can be started by calling connect.
    def _connect(self):
        Logger.log("d", "Attempting to connect to %s", self._serial_port)
        self._is_connecting = True
        self.setIsConnected(True)
        Logger.log("i", "Established printer connection on port %s" % self._serial_port)
        return 

    def setIsConnected(self, state):
        self._is_connecting = False
        if self._is_connected != state:
            self._is_connected = state
            self.connectionStateChanged.emit(self._serial_port)
            # if self._is_connected: 
                # self._listen_thread.start() #Start listening
        else:
            Logger.log("w", "Printer connection state was not changed")

    connectionStateChanged = Signal()

    ##  Close the printer connection
    def close(self):
        Logger.log("d", "Closing the printer connection.")
        if self._connect_thread.isAlive():
            try:
                self._connect_thread.join()
            except Exception as e:
                pass # This should work, but it does fail sometimes for some reason

        self._connect_thread = threading.Thread(target=self._connect)
        self._connect_thread.daemon = True

    def isConnected(self):
        return self._is_connected 

    ##  Ensure that close gets called when object is destroyed
    def __del__(self):
        self.close()

    def createControlInterface(self):
        if self._control_view is None:
            Logger.log("d", "Creating control interface for printer connection")
            path = QUrl.fromLocalFile(os.path.join(PluginRegistry.getInstance().getPluginPath("Doodle3D"), "ControlWindow.qml"))
            component = QQmlComponent(Application.getInstance()._engine, path)
            self._control_context = QQmlContext(Application.getInstance()._engine.rootContext())
            self._control_context.setContextProperty("manager", self)
            self._control_view = component.create(self._control_context)

    ##  Show control interface.
    #   This will create the view if its not already created.
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

    ##  Set the progress of the print. 
    #   It will be normalized (based on max_progress) to range 0 - 100
    def setProgress(self, progress, max_progress = 100):
        self._progress  = (progress / max_progress) * 100 #Convert to scale of 0-100
        self.progressChanged.emit()
    
    ##  Cancel the current print. Printer connection wil continue to listen.
    @pyqtSlot()
    def cancelPrint(self):
<<<<<<< HEAD
        """
        self.printersetting = Application.getInstance().getMachineManager().getActiveMachineInstance().getMachineSettingValue("machine_start_gcode")
        Logger.log("d","printer setting is: %s" % self.printersetting)

        self.active_machine_definition= Application.getInstance().getMachineManager().getActiveMachineInstance()
        Logger.log("d","printer active machine definition is: %s" % self.active_machine_definition)

        self.printergcode = Application.getInstance().getMachineManager().getActiveMachineInstance().getMachineSettingValue("machine_gcode_flavor")
        Logger.log("d","printer flavor is: %s" % self.printergcode)
        Application.getInstance().getMachineManager().getActiveMachineInstance().setMachineSettingValue("machine_gcode_flavor","RepRap (Marlin/Sprinter)")
        Application.getInstance().getMachineManager().getActiveMachineInstance().setMachineSettingValue("machine_start_gcode","M109 S210 ;set target temperature\nG21 ;metric values\nG90 ;absolute positioning\nM107 ;start with the fan off\nG28 ; home to endstops\nG1 Z15 F9000 ;move the platform down 15mm\nG92 E0 ;zero the extruded length\nG1 F200 E10 ;extrude 10mm of feed stock\nG92 E0 ;zero the extruded length again\nG1 F9000\nM117 Printing Doodle...   ")
        self.printersetting = Application.getInstance().getMachineManager().getActiveMachineInstance().getMachineSettingValue("machine_start_gcode")
        Logger.log("d","printer setting is: %s" % self.printersetting)
        
        Application.getInstance().getBackend().forceSlice()
        time.sleep(5)
        Application.getInstance().getController().getScene().sceneChanged.emit(None)
        self.gcode_list = getattr( Application.getInstance().getController().getScene(), "gcode_list")
        Logger.log("d", "testing is: %s" % self.gcode_list)
        """
        
        self.httppost(self._serial_port,"/d3dapi/printer/stop",{'gcode': 'M104 S0\nG28'})
        self.setProgress(0,100)

    def httppost(self,domain,path,data):
        params = urllib.parse.urlencode(data)
        headers = {"Content-type": "x-www-form-urlencoded", "Accept": "text/plain", "User-Agent": "Cura Doodle3D connection"}
        connect = http.client.HTTPConnection(domain, 80, timeout=30)
=======
        self.httppost(self._serial_port,"/d3dapi/printer/stop",{
            'gcode': 'M104 S0\nG28'
        })
        ## Turn of temperatures
        ## self._sendCommand("M104 S0")
        self.setProgress(0,100)

    ##  Check if the process did not encounter an error yet.
    def hasError(self):
        return self._error_state != None

    ##  private read line used by printer connection to listen for data on serial port.
    def _readline(self):
        if self._serial is None:
            return None
        try:
            ret = self._serial.readline()
        except Exception as e:
            Logger.log("e","Unexpected error while reading serial port. %s" %e)
            self._setErrorState("Printer has been disconnected") 
            self.close()
            return None
        return ret

    ##  Create a list of baud rates at which we can communicate.
    #   \return list of int
    def _getBaudrateList(self):
        ret = [115200, 250000, 230400, 57600, 38400, 19200, 9600]
        return ret

    def _onFirmwareUpdateComplete(self):
        self._update_firmware_thread.join()
        self._update_firmware_thread = threading.Thread(target= self._updateFirmware)
        self._update_firmware_thread.daemon = True

        self.connect()


    def httppost(self,domain,path,data):
        params = urllib.parse.urlencode(data)
        headers = {
        "Content-type": "x-www-form-urlencoded", 
        "Accept": "text/plain", 
        "User-Agent": "Cura Doodle3D connection"
        }

        connect = http.client.HTTPConnection(domain, 80, timeout=5)
>>>>>>> 43e1a0231bfa300d63e65959474bf3f137e7e620
        connect.request("POST", path, params, headers)
        response = connect.getresponse()
        jsonresponse = response.read()
        return json.loads(jsonresponse.decode())

    def getPrinterInfo(self):
        while True:
            try:
                self.stateReply = self.get(self._serial_port,"/d3dapi/info/status")
                if self.stateReply['data']['hotend']:
<<<<<<< HEAD
                    ##Logger.log("d", "stateReply is: %s" % self.stateReply)

                    ##Get Extruder Temperature and emit it to the pyqt framework
                    self.extTemperature = self.stateReply['data']['hotend']
                    self.extruderTemperatureChanged.emit()

                    ##Get Extruder Target Temperature and emit it to the pyqt framework
                    self.extTargetTemperature = self.stateReply['data']['hotend_target']
                    self.extruderTargetChanged.emit()
                    
                    ##Get the state of the printer and emit it to the pyqt framework
                    self.printerState = self.stateReply['data']['state']
                    self.printerStateChanged.emit()

=======
                    Logger.log("d", "stateReply is: %s" % self.stateReply)
                ##Get Extruder Temperature and emit it to the pyqt framework
                    self.extTemperature = self.stateReply['data']['hotend']
                    self.extruderTemperatureChanged.emit()
>>>>>>> 43e1a0231bfa300d63e65959474bf3f137e7e620
                else:
                    continue
                
                if self.stateReply['data']['state'] == "printing":
                    self.currentLine = self.stateReply['data']['current_line']
<<<<<<< HEAD
                    if (self.extTemperature/self.extTargetTemperature)*100<100 and self.heatedUp==False:
                        self.setProgress((self.extTemperature / self.extTargetTemperature) * 100)
                        self._printPhase = "Heating up... "
                        self.printPhaseChanged.emit()

                    elif (self.currentLine / self.totalLines) * 100<100:
                        self.heatedUp=True
                        self.setProgress((self.currentLine / self.totalLines) * 100)
                        self._printPhase = "Printing... "
                        self.printPhaseChanged.emit()

                    time.sleep(4)
                elif self.stateReply['data']['state'] == "idle" and self._progress > 0:
                    self.setProgress(100,100)
                    self._printPhase = "Print Completed "
                    self.printPhaseChanged.emit()
                else:
                    self.heatedUp=False
                    
                    
                    

=======
                    ##Logger.log("d", "currentLine is: %s" % self.currentLine)
                    ##Logger.log("d", "totalLines is: %s" % self.totalLines)
                    self.setProgress((self.currentLine / self.totalLines) * 100)
                    time.sleep(4)
                else:
                    self.setProgress(0,100)
                    time.sleep(10)
>>>>>>> 43e1a0231bfa300d63e65959474bf3f137e7e620
            except:
                time.sleep(3)
            

    def get (self,domain,path):
        connect = http.client.HTTPConnection(domain)
        connect.request("GET", path)
        response = connect.getresponse()
        jsonresponse = response.read()
        return json.loads(jsonresponse.decode())