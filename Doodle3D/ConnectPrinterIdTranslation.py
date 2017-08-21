# Translate a machine definition id to a Doodle3D Connect printer id
# \return Doodle3D Connect printer id or the original
def curaPrinterIdToConnect(id):
	return {
	"rigidbot": "rigidbot",
	"ultimaker": "ultimaker",
	"ultimaker2": "ultimaker2",
	"ultimaker2_go": "ultimaker2go",
	"ultimaker_original_plus": "ultimaker_original_plus",
	"makerbotreplicator": "makerbot_replicator2",
	"printrbot_simple": "printrbot",
	"cartesio": "cartesio",
	"prusa_i3": "prusa_i3",
	"prusa_i3_mk2": "prusa_iteration_2",
	"robo_3d_r1": "robo_3d_printer",
	"renkforce_rf100": "renkforce_rf100"
}.get(id, None)
