## Doodle3D Cura Plugin
#### The plugin that enables you to wirelessly 3D-Print with Cura.


This package is intended to be built using CMake. Alternatively, you can put this folder inside the cura/plugins folder.

Doodle3D.py is the manager that creates and destroys instances of PrinterConnection.py for every 3DPrinter (Connected with a Doodle3D-WiFi Box)  in the Local-Area Network.

The Cura-generated GCode gets divided into multiple chunks, then gets sent chunk by chunk to the Doodle3D-WiFi Box to process:

- `<boxIP>/d3dapi/printer/print"`
- `e.g. 10.0.0.195/d3dapi/printer/print`
