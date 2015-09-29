import http.client
import json
import urllib
import pprint

pp = pprint.PrettyPrinter(indent=2)

def get (domain,path):
    print('get: ',domain,path)
    connect = http.client.HTTPConnection(domain)
    connect.request("GET", path)
    response = connect.getresponse()
    print('  response: ',response.status, response.reason)
    jsonresponse = response.read()
    print('  ',jsonresponse)
    return json.loads(jsonresponse.decode())

def post (domain,path,data):
    print('post: ',domain,path)
    print('  data: ',data)
    # jsonData = json.dump(data)
    # print('  json: ',jsonData)
    params = urllib.parse.urlencode(data)
    print('  params: ',params)
    headers = {"Content-type": "x-www-form-urlencoded", "Accept": "text/plain", "User-Agent": "Cura Doodle3D connection"}
    connect = http.client.HTTPConnection(domain)
    connect.request("POST", path, params, headers)
    response = connect.getresponse()
    print('  response: ',response.status, response.reason)
    jsonresponse = response.read()
    print('  ',jsonresponse)
    return json.loads(jsonresponse.decode())

listResponse = get("connect.doodle3d.com","/api/list.php")
boxes = listResponse['data']
print('')
print('boxes:')
# pprint.pprint(boxes)
# for box in boxes:
for index in range(len(boxes)):
    box = boxes[index]
    print(index,':',box['wifiboxid'],'(',box['localip'],')')

# boxID = 'Doodle3D-rood'
# boxID = input('Select WiFi-Box: ')
# box = [box for box in boxes if box['wifiboxid'] == boxID][0]
boxIndex = int(input('Select WiFi-Box: '))
box = boxes[boxIndex]
boxIP = box['localip']
boxID = box['wifiboxid']
print('Selected: ',boxID,':',box)

def getstatus():
    statusResponse = get(boxIP,"/d3dapi/info/status")
    print('')
    print('status:')
    pprint.pprint(statusResponse)
    # print('hotend:',statusResponse['data']['hotend'])

def heatup():
    post(boxIP,"/d3dapi/printer/heatup","")

def movePrinter():
    sendGCode("G1 X100 Y100")

def homePrinter():
    sendGCode("G28")

def sendGCode(gcode):
    post(boxIP,"/d3dapi/printer/print",{
        'gcode': gcode,
        'start': 'true',
        'first': 'true'
    })

def coolDown():
    sendGCode("M104 S0")

actions = {
    'getstatus':getstatus,
    'heatup':heatup,
    'moveprinter':movePrinter,
    'home':homePrinter,
    'cool':coolDown
}

keys = "/".join(actions.keys())
while True:
    action = input('\nAction [' + keys + ']: ')
    print('Performing: ',action)
    actions[action]()

# post(boxIP,"/d3dapi/printer/print","")