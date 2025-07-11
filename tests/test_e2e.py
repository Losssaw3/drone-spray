from time import sleep
import pytest
import subprocess
import json
import requests

MOBILE_URL_TURN_ON = "http://localhost:8003/turn_on"

MOBILE_URL_START = "http://localhost:8003/start"

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

def test_init(initialize_drone):
    response = initialize_drone
    sleep(5)
    assert response.status_code == 200

def test_second_init(initialize_drone):
    response = initialize_drone
    sleep(5)
    assert response.status_code == 409

def test_start(start_flight):
    response = start_flight
    sleep(5)
    assert response.status_code == 200

def test_second_start(start_flight):
    response = start_flight
    sleep(5)
    assert response.status_code == 409

def test_base_scenario(get_logs):
    sleep(150)

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


