project(Doodle3D)

cmake_minimum_required(VERSION 2.8.12)

find_package(PythonInterp 3.4.0 REQUIRED)

install(FILES
    __init__.py
    Doodle3D.py
    PrinterConnection.py
    ControlWindow.qml
    SettingsWindow.qml
    doodle3d.png
    DESTINATION lib/cura/plugins/Doodle3D
)