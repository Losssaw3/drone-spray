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
PRIVATE_KEY_PATH = "/shared/private_key.pem"
PUBLIC_KEY_PATH = "/shared/public_key.pem"

work_flag = False
start_point = []
ready_flag = False



def load_private_key(password: bytes = None):
    """
    Loads the private key from a PEM file.
    
    Args:
        password (bytes, optional): Password for the private key.
    
    Returns:
        Private key object.
    """
    print("Loading private key...")
    with open(PRIVATE_KEY_PATH, "rb") as key_file:
        key_data = key_file.read()
        print("Private key loaded.")
        return load_pem_private_key(
            key_data,
            password=password,
            backend=default_backend()
        )


def load_public_key():
    """
    Loads the public key from a PEM file.
    
    Returns:
        Public key object.
    """
    """Загружает публичный ключ из PEM-файла"""
    with open(PUBLIC_KEY_PATH, "rb") as key_file:
        return load_pem_public_key(
            key_file.read(),
            backend=default_backend()
        )

def sign_json(data: dict, private_key) -> str:
    """
    Signs JSON data and returns the signature in base64.
    
    Args:
        data (dict): JSON data to sign.
        private_key: Private key object.
    
    Returns:
        str: Base64-encoded signature.
    """
    """Подписывает JSON-данные и возвращает подпись в base64"""
    json_str = json.dumps(data, sort_keys=True, ensure_ascii=False)
    signature = private_key.sign(
        json_str.encode('utf-8'),
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.MAX_LENGTH
        ),
        hashes.SHA256()
    )
    
    import base64
    return base64.b64encode(signature).decode('ascii')

def verify(details):
    """
    Verifies the signature of a message.
    
    Args:
        details (dict): Message details containing signature and check data.
    
    Returns:
        bool: True if the signature is valid, False otherwise.
    """
    """ Проверяет подпись сообщения. """
    if "signature" in details and "check" in details:
        import base64

        signature_b64 = details.get("signature")
        check = details.get("check")

        signature = base64.b64decode(signature_b64)
        public_key = load_public_key()

        try:
            public_key.verify(
                signature,
                json.dumps(check, sort_keys=True, ensure_ascii=False).encode('utf-8'),
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            return True
        except Exception as e:
            print(f"Signature verification failed: {e}")
            return False
    return False

class Center:
    def __init__(self):
        """
        Initializes the Center class with default mission and position.
        """
        self.mission = {}
        self.position = [0,0,0]

    def send_mission_to_drone(self):
        """
        Sends a mission to the drone if it is ready and not already on a mission.
        
        Returns:
            Response: JSON response indicating the status.
        """
        global work_flag
        global ready_flag
        global start_point
        mission = self.generate_random_mission()
        if not work_flag and ready_flag:
            try:
                signature = sign_json(mission, load_private_key())
                payload = {
                    "mission": mission,
                    "signature": signature,
                    "check": mission
                }
                print(f"Sent mission to drone: {payload}")
                response = requests.post(DRONE_START_URL, json=payload)
                if response.status_code == 200:
                    work_flag = True
                    return jsonify({"status": "mission successfully sent"}), 200
            except Exception as e:
                return {"status": "error", "message": str(e)}
        else:
            print("error! drone already on mission or not ready")
        

    def generate_random_mission(self, num_points=4, x_range=(100, 200), y_range=(100, 200), dispersion=15):
        """
        Generates a random mission with forward, spray, and backward routes.
        
        Args:
            num_points (int): Number of points in the route.
            x_range (tuple): Range for x-coordinates.
            y_range (tuple): Range for y-coordinates.
            dispersion (int): Dispersion for spray points.
        
        Returns:
            dict: Generated mission details.
        """
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
        


@app.route('/init_status', methods=['POST'])
def log_boat_data():
    """
    Logs the drone's initialization status and handles mission requests.
    
    Returns:
        Response: JSON response indicating the status.
    """
    global start_point , ready_flag , work_flag
    data = request.get_json()
    if verify(data):
        if ready_flag:
            print(f'Drone data - {data.get("status")}')
            if data.get("status") == "request new mission":
                work_flag = False
                new_mission = Center()
                new_mission.send_mission_to_drone()
            return jsonify({"status": "logged"}), 200
        else:
            status = data.get("status")
            start_point = status["coords"]
            ready_flag = True
            return jsonify({"status": "Drone data successfully logged"}), 200

@app.route('/validate' , methods=['POST'])
def validate():
    """
    Validates a photo and sends it for approval.
    
    Returns:
        Response: JSON response indicating the status.
    """
    data = request.get_json()
    photo = data.get("photo")
    print(f"validating {photo} ... ")
    sleep(3)
    try:
        signature = sign_json(photo, load_private_key())
        payload = {
            "photo": photo,
            "signature": signature,
            "check": photo
        }
        responce = requests.get(APPROVAL_PHOTO_URL ,json=payload)
        return jsonify({"status": "success!"}), 200
    except Exception as e:
                return {"status": "error", "message": str(e)}


center = Center()

@app.route('/start', methods=['GET'])
def start():    
    """
    Starts the mission by sending it to the drone.
    
    Returns:
        Response: JSON response indicating the status.
    """
    return center.send_mission_to_drone()

def start_web():
    """
    Starts the Flask web server.
    """
    app.run(host='0.0.0.0', port=8000, threaded=True, debug=True)

