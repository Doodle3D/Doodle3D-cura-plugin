project(Doodle3D)

cmake_minimum_required(VERSION 2.8.12)

find_package(PythonInterp 3.4.0 REQUIRED)

install(FILES
    __init__.py
    D3DCloudPrintPlugin.py
    ConnectPrinterIdTranslation.py
    DESTINATION lib/cura/plugins/Doodle3D
)
