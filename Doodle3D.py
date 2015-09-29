# Copyright (c) 2015 Ultimaker B.V.
# Cura is released under the terms of the AGPLv3 or higher.

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
            result = self.getSerialPortList(only_list_usb = True)
            self._addRemovePorts(result)
            time.sleep(5)

    ##  Show firmware interface.
    #   This will create the view if its not already created.
    def spawnFirmwareInterface(self, serial_port):
        if self._firmware_view is None:
            path = QUrl.fromLocalFile(os.path.join(PluginRegistry.getInstance().getPluginPath("Doodle3D"), "FirmwareUpdateWindow.qml"))
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
    def getSerialPortList(self, only_list_usb = False):
        base_list = []
        if platform.system() == "Windows":
            import winreg
            try:
                key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,"HARDWARE\\DEVICEMAP\\SERIALCOMM")
                i = 0
                while True:
                    values = winreg.EnumValue(key, i)
                    if not only_list_usb or "USBSER" in values[0]:
                        base_list += [values[1]]
                    i += 1
            except Exception as e:
                pass
        else:
            if only_list_usb:
                base_list = base_list + glob.glob("/dev/ttyUSB*") + glob.glob("/dev/ttyACM*") + glob.glob("/dev/cu.usb*")
                base_list = filter(lambda s: "Bluetooth" not in s, base_list) # Filter because mac sometimes puts them in the list
            else:
                base_list = base_list + glob.glob("/dev/ttyUSB*") + glob.glob("/dev/ttyACM*") + glob.glob("/dev/cu.*") + glob.glob("/dev/tty.usb*") + glob.glob("/dev/rfcomm*") + glob.glob("/dev/serial/by-id/*")
        return list(base_list)

    _instance = None