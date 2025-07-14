from time import sleep
import pytest
import subprocess
import json
import requests

MOBILE_URL_TURN_ON = "http://localhost:8003/turn_on"

MOBILE_URL_START = "http://localhost:8003/start"

COMMUNICATION_DRONE_URL = "http://localhost:8004/start_mission"

fake_mission = {
            'mission':  
             {'forward_route': [[80.0, 80.0], [191, 143], [170, 159], [161, 158], [207, 206]],
              'spray': [[207, 206], [207, 221], [222, 221], [222, 206]],
              'backward_route': [[207, 206], [161, 158], [170, 159], [191, 143], [80.0, 80.0]]},

            'signature': 'pF9AWNmpGl4GE2DrjjQyNcDQRamYCVPanAtGZtoD+4i8xLrWqtCElWEuDMq5uTNmIXuea6YPyDjGT2uVOP/XR69uL//pBr1Tvegpp6VQ1U5BAcx0+jus+B5u/KBbHk9WccaOrjfXbqBaT2DWVCJnWZRdazXkmpUEKf4ZCMPEiSXu1MDFCqUBjbVbNiVpqaMrXATPM9MzvJg9hFOAeC/eb8Td0WLa3nj5N/EFpmAhh/WVFSQ/maABXgoOJ6IRwkW3fC9hLGPRQ1NYgxRIGKUfWlFySU/6+q+PUda+Ux749gCvtkwhFQ3bLBS6YoWj6KofmF6OO9lvpgpO3WHCS1BY1g==', 
 
            'check':
             {'forward_route': [[80.0, 80.0], [191, 143], [170, 159], [161, 158], [207, 206]],
             'spray': [[207, 206], [207, 221], [222, 221], [222, 206]],
             'backward_route': [[207, 206], [161, 158], [170, 159], [191, 143], [80.0, 80.0]]}}

@pytest.fixture
def get_logs():
    def _get_logs(container_name):
        return subprocess.check_output(
            ['docker-compose', '-f', 'docker-compose-base.yml' , 'logs', '--no-color', container_name],
            text=True,
        )
    return _get_logs

@pytest.fixture
def initialize_drone():
    response = requests.get(url = MOBILE_URL_TURN_ON)
    return response

@pytest.fixture
def start_flight():
    response = requests.get(url = MOBILE_URL_START)
    return response

@pytest.fixture
def send_fake_mission():
    payload = fake_mission
    responce = requests.post(url= COMMUNICATION_DRONE_URL , json=payload)
    return responce

def test_init(initialize_drone):
    response = initialize_drone
    sleep(5)
    assert response.status_code == 200

def test_second_init(initialize_drone):
    response = initialize_drone
    sleep(5)
    assert response.status_code == 409

def test_fake_route(send_fake_mission , get_logs):
    response = send_fake_mission
    sleep(5)
    logs = get_logs("encryption")
    assert "Mission was rejected due invalid signature!" in logs

def test_start(start_flight):
    response = start_flight
    sleep(5)
    assert response.status_code == 200

def test_second_start(start_flight):
    response = start_flight
    sleep(5)
    assert response.status_code == 409

def test_base_scenario(get_logs):
    sleep(170)

    #sprayer test
    logs_sprayer = get_logs("sprayer")
    assert ("Опрыскиватель включен...") in logs_sprayer
    assert ("Опрыскиватель выключен...") in logs_sprayer
    
    #checking the stages of the route
    logs_limiter = get_logs("limiter")
    assert ("Окончание маршрута до места распрыскивания") in logs_limiter
    assert ("Окончание маршрута распрыскивания") in logs_limiter
    assert ("Окончание маршрута") in logs_limiter

    #check if mission is complete
    logs_mobile = get_logs("mobile")
    assert ("flight ended") in logs_mobile


