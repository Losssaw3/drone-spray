from flask import Flask, request, jsonify
import requests
import random
from time import sleep

app = Flask(__name__)

DRONE_START_URL = "http://communication:8000/start_mission"
APPROVAL_PHOTO_URL = "http://communication:8000/confirm_photo"
work_flag = False
start_point = []
ready_flag = False

class Center:
    def __init__(self):
        self.mission = {}
        self.position = [0,0,0]

    def send_mission_to_drone(self):
        global work_flag
        global ready_flag
        global start_point
        mission = self.generate_random_mission()
        if not work_flag and ready_flag:
            try:
                payload = mission
                print(f"Sent mission to drone: {mission}")
                response = requests.post(DRONE_START_URL, json=payload)
                if response.status_code == 200:
                    work_flag = True
                    return jsonify({"status": "mission successfully sent"}), 200
            except Exception as e:
                return {"status": "error", "message": str(e)}
        else:
            print("error! drone already on mission or not ready")
        

    def generate_random_mission(self, num_points=4, x_range=(100, 200), y_range=(100, 200),dispersion = 10):
        global start_point
        route = []
        spray = []
        route[0] = start_point
        mission = {}
        for _ in range(num_points):
            x = random.randint(x_range[0], x_range[1])
            y = random.randint(y_range[0], y_range[1])
            route.append([x, y])
        spray[0] = route[-1]
        spray.append(spray[0][0] , spray[0][1] + dispersion)
        spray.append(spray[0][0] + dispersion , spray[0][1] + dispersion)  
        spray.append(spray[0][0] + dispersion , spray[0][1])
        mission("forward_route") = route
        mission("spray") = spray
        mission("backward_route") = route[::-1]
        return mission
        
center = Center()

@app.route('/init_status', methods=['POST'])
def log_boat_data():
    global start_point
    global ready_flag
    data = request.get_json()
    if ready_flag:
         print(f'Drone data - {data.get("status")}')
         return jsonify({"status": "logged"}), 200
    else:
        status = data.get("status")
        start_point = status.get("coords")
        ready_flag = True
        return jsonify({"status": "Drone data successfully logged"}), 200

@app.route('/validate' , methods=['POST'])
def validate():
    data = request.get_json()
    photo = data.get("photo")
    print(f"validating {photo} ... ")
    sleep(3)
    print("success!")
    try:
        responce = requests.get(APPROVAL_PHOTO_URL)
    except Exception as e:
                return {"status": "error", "message": str(e)}



@app.route('/start', methods=['GET'])
def start():    
    center.send_mission_to_drone()
    return 200

def start_web():
    app.run(host='0.0.0.0', port=8000, threaded=True)
    