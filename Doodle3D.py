# Copyright (c) 2015 Ultimaker B.V.
# Cura is released under the terms of the AGPLv3 or higher.

from . import httptest

from UM.Signal import Signal, SignalEmitter
from . import PrinterConnection
from UM.Application import Application
from UM.Scene.Iterator.DepthFirstIterator import DepthFirstIterator
from UM.Scene.SceneNode import SceneNode
from UM.Resources import Resources
from UM.Logger import Logger
from UM.PluginRegistry import PluginRegistry
from UM.OutputDevice.OutputDevicePlugin import OutputDevicePlugin
from UM.Qt.ListModel import ListModel

from cura.CuraApplication import CuraApplication

import threading
import platform
import glob
import time
import os
import os.path
import sys

import http.client
import json

from UM.Extension import Extension

from PyQt5.QtQuick import QQuickView
from PyQt5.QtQml import QQmlComponent, QQmlContext
from PyQt5.QtCore import QUrl, QObject, pyqtSlot, pyqtProperty, pyqtSignal, Qt
from UM.i18n import i18nCatalog
i18n_catalog = i18nCatalog("cura")

class Doodle3D(QObject, SignalEmitter, OutputDevicePlugin, Extension):
    def __init__(self, parent = None):
        QObject.__init__(self, parent)
        SignalEmitter.__init__(self)
        OutputDevicePlugin.__init__(self)
        Extension.__init__(self)
        self._serial_port_list = []
        self._printer_connections = {}
        self._printer_connections_model = None
        self._update_thread = threading.Thread(target = self._updateThread)
        self._update_thread.setDaemon(True)

        self._check_updates = True
        self._firmware_view = None

        ## Add menu item to top menu of the application.
        self.setMenuName(i18n_catalog.i18nc("@title:menu","Doodle3D"))
        self.addMenuItem(i18n_catalog.i18nc("@item:inmenu", "Settings..."), self.updateAllFirmware)

        Application.getInstance().applicationShuttingDown.connect(self.stop)
        self.addConnectionSignal.connect(self.addConnection) #Because the model needs to be created in the same thread as the QMLEngine, we use a signal.

    addConnectionSignal = Signal()
    printerConnectionStateChanged = pyqtSignal()

    def start(self):
        self._check_updates = True
        self._update_thread.start()

    def stop(self):
        self._check_updates = False
        try:
            self._update_thread.join()
        except RuntimeError:
            pass

    def _updateThread(self):
        while self._check_updates:
            result = self.getSerialPortList()
            self._addRemovePorts(result)
            time.sleep(5)

    ##  Show firmware interface.
    #   This will create the view if its not already created.
    def spawnFirmwareInterface(self, serial_port):
        if self._firmware_view is None:
            path = QUrl.fromLocalFile(os.path.join(PluginRegistry.getInstance().getPluginPath("Doodle3D"), "SettingsWindow.qml"))
            component = QQmlComponent(Application.getInstance()._engine, path)

            self._firmware_context = QQmlContext(Application.getInstance()._engine.rootContext())
            self._firmware_context.setContextProperty("manager", self)
            self._firmware_view = component.create(self._firmware_context)

        self._firmware_view.show()

    def updateAllFirmware(self):
        self.spawnFirmwareInterface("")
        for printer_connection in self._printer_connections:
            try:
                self._printer_connections[printer_connection].updateFirmware(Resources.getPath(CuraApplication.ResourceTypes.Firmware, self._getDefaultFirmwareName()))
            except FileNotFoundError:
                continue

    @pyqtSlot(str, result = bool)
    def updateFirmwareBySerial(self, serial_port):
        if serial_port in self._printer_connections:
            self.spawnFirmwareInterface(self._printer_connections[serial_port].getSerialPort())
            try:
                self._printer_connections[serial_port].updateFirmware(Resources.getPath(CuraApplication.ResourceTypes.Firmware, self._getDefaultFirmwareName()))
            except FileNotFoundError:
                self._firmware_view.close()
                Logger.log("e", "Could not find firmware required for this machine")
                return False
            return True
        return False

    ##  Return the singleton instance of the USBPrinterManager
    @classmethod
    def getInstance(cls, engine = None, script_engine = None):
        # Note: Explicit use of class name to prevent issues with inheritance.
        if Doodle3D._instance is None:
            Doodle3D._instance = cls()

        return Doodle3D._instance

    def _getDefaultFirmwareName(self):
        machine_type = Application.getInstance().getMachineManager().getActiveMachineInstance().getMachineDefinition().getId()
        firmware_name = ""
        baudrate = 250000
        if sys.platform.startswith("linux"):
                baudrate = 115200
        if machine_type == "ultimaker_original":
            firmware_name = "MarlinUltimaker"
            firmware_name += "-%d" % (baudrate)
        elif machine_type == "ultimaker_original_plus":
            firmware_name = "MarlinUltimaker-UMOP-%d" % (baudrate)
        elif machine_type == "Witbox":
            return "MarlinWitbox.hex"
        elif machine_type == "ultimaker2go":
            return "MarlinUltimaker2go.hex"
        elif machine_type == "ultimaker2extended":
            return "MarlinUltimaker2extended.hex"
        elif machine_type == "ultimaker2":
            return "MarlinUltimaker2.hex"

        ##TODO: Add check for multiple extruders

        if firmware_name != "":
            firmware_name += ".hex"
        return firmware_name

    def _addRemovePorts(self, serial_ports):
        # First, find and add all new or changed keys
        for serial_port in list(serial_ports):
            if serial_port not in self._serial_port_list:
                self.addConnectionSignal.emit(serial_port) #Hack to ensure its created in main thread
                continue
        self._serial_port_list = list(serial_ports)

    ##  Because the model needs to be created in the same thread as the QMLEngine, we use a signal.
    def addConnection(self, serial_port):
        connection = PrinterConnection.PrinterConnection(serial_port)
        connection.connect()
        connection.connectionStateChanged.connect(self._onPrinterConnectionStateChanged)
        self._printer_connections[serial_port] = connection

    def _onPrinterConnectionStateChanged(self, serial_port):
        if self._printer_connections[serial_port].isConnected():
            self.getOutputDeviceManager().addOutputDevice(self._printer_connections[serial_port])
        else:
            self.getOutputDeviceManager().removeOutputDevice(serial_port)
        self.printerConnectionStateChanged.emit()

    @pyqtProperty(QObject , notify = printerConnectionStateChanged)
    def connectedPrinterList(self):
        self._printer_connections_model  = ListModel()
        self._printer_connections_model.addRoleName(Qt.UserRole + 1,"name")
        self._printer_connections_model.addRoleName(Qt.UserRole + 2, "printer")
        for connection in self._printer_connections:
            if self._printer_connections[connection].isConnected():
                self._printer_connections_model.appendItem({"name":connection, "printer": self._printer_connections[connection]})
        return self._printer_connections_model

    ##  Create a list of serial ports on the system.
    #   \param only_list_usb If true, only usb ports are listed
    def getSerialPortList(self):
        base_list = []
        
        #Get response from api/list.php and retrieve local ip 
        ## from each individual boxes found on the local network
        boxesListResponse = self.get("connect.doodle3d.com","/api/list.php")
        boxes = boxesListResponse['data']

        for index in range(len(boxes)):
            box = boxes[index]
            
            try:#Check if the boxes are alive
                boxesAliveCheck = self.get(box['localip'],"/d3dapi/network/alive")
            
            except:#Run this exception for the boxes that aren't alive (anymore)

                if box['localip'] in self._printer_connections:
                    self._printer_connections[box['localip']]._is_connected = False
                    self._printer_connections[box['localip']].close()
                    del self._printer_connections[box['localip']]
                    self.getOutputDeviceManager().removeOutputDevice(box['localip'])
                else:
                    pass

                ##Logger.log("d", "Value of _printer_connections: %s" % self._printer_connections)
                ##Logger.log("d", "Value of _printer_connections: %s" % self._printer_connections_model)
            
            else:#Boxes that are alive will be formed together into the base_list
                base_list.append(box['localip'])

        return list(base_list)

    #Takes Domain and Path and returns decoded JSON response back
    def get (self,domain,path):
        print('get: ',domain,path)
        connect = http.client.HTTPConnection(domain)
        connect.request("GET", path)
        response = connect.getresponse()
        print('  response: ',response.status, response.reason)
        jsonresponse = response.read()
        print('  ',jsonresponse)
        return json.loads(jsonresponse.decode())

    _instance = None


