from flask import Flask, request, jsonify
import requests
import random
from time import sleep
import json
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.serialization import load_pem_private_key, load_pem_public_key
from cryptography.hazmat.backends import default_backend


app = Flask(__name__)

DRONE_START_URL = "http://communication:8000/start_mission"
APPROVAL_PHOTO_URL = "http://communication:8000/confirm_photo"
PRIVATE_KEY_PATH = "../../../private_key.pem"
PUBLIC_KEY_PATH = "../../../public_key.pem"

work_flag = False
start_point = []
ready_flag = False



def load_private_key(password: bytes = None):
    """Загружает приватный ключ из PEM-файла"""
    with open(PRIVATE_KEY_PATH, "rb") as key_file:
        return load_pem_private_key(
            key_file.read(),
            password=password,
            backend=default_backend()
        )

def load_public_key():
    """Загружает публичный ключ из PEM-файла"""
    with open(PUBLIC_KEY_PATH, "rb") as key_file:
        return load_pem_public_key(
            key_file.read(),
            backend=default_backend()
        )

def sign_json(data: dict, private_key) -> str:
    """Подписывает JSON-данные и возвращает подпись в base64"""
    # Конвертируем словарь в стабильный JSON-формат (с сортировкой ключей)
    json_str = json.dumps(data, sort_keys=True, ensure_ascii=False)
    
    # Подписываем текст (предварительно конвертировав в bytes)
    signature = private_key.sign(
        json_str.encode('utf-8'),
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.MAX_LENGTH
        ),
        hashes.SHA256()
    )
    
    # Возвращаем подпись в base64 для удобной передачи
    import base64
    return base64.b64encode(signature).decode('ascii')

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
        

    def generate_random_mission(self, num_points=4, x_range=(100, 200), y_range=(100, 200), dispersion = 15):
        global start_point
        route = [start_point]
        mission = {}
        for _ in range(num_points - 1):
            x = random.randint(x_range[0], x_range[1])
            y = random.randint(y_range[0], y_range[1])
            route.append([x, y])
        route.append([random.randint(205 , 220) , random.randint(205 , 220)])
        last_point = route[-1]
        spray = [last_point]
        spray.append([last_point[0] , last_point[1] + dispersion])
        spray.append([last_point[0] + dispersion , last_point[1] + dispersion])  
        spray.append([last_point[0] + dispersion , last_point[1]])
        mission["forward_route"] = route
        mission["spray"] = spray
        mission["backward_route"] = route[::-1]
        return mission
        
center = Center()

@app.route('/init_status', methods=['POST'])
def log_boat_data():
    global start_point
    global ready_flag
    data = request.get_json()
    if ready_flag:
         print(f'Drone data - {data.get("status")} starting point {start_point}')
         return jsonify({"status": "logged"}), 200
    else:
        status = data.get("status")
        start_point = status["coords"]
        ready_flag = True
        return jsonify({"status": "Drone data successfully logged"}), 200

@app.route('/validate' , methods=['POST'])
def validate():
    data = request.get_json()
    photo = data.get("photo")
    print(f"validating {photo} ... ")
    sleep(3)
    try:
        responce = requests.get(APPROVAL_PHOTO_URL)
        return jsonify({"status": "success!"}), 200
    except Exception as e:
                return {"status": "error", "message": str(e)}



@app.route('/start', methods=['GET'])
def start():    
    center.send_mission_to_drone()
    return jsonify({"status": "Mission started"}), 200

def start_web():
    app.run(host='0.0.0.0', port=8000, threaded=True)
    