# Drone sprayer

## Disclaimer 

This is a demo project and shall not be used in production.

## Purpose

This is an example of a sprayer drone control system developed using a cyberimmunnity

## Running the demo

The main option for running the demo is following:
- containerized (using docker containers), then there shall be installed python (tested with version 3.8) with pip and pipenv, also having *make* tool is necessary

There shall be docker-compose locally available - for running message broker (Kafka).

### Running complete demo

#### Normal mode
Execute in VS Code terminal window either in other terminal
- _make prepare_

Then execute
- _make run_

You need to wait system start up. Then open the requests.rest file in Visual Studio Code editor. If you have the REST client extension installed, you will see 'Send request' active text above GET or POST requests, you can click on it.

First need to turn on the drone by clicking first request under "Включение дрона". The output will be the following:

```
HTTP/1.1 200 OK
Server: Werkzeug/3.0.6 Python/3.8.20
Date: Tue, 15 Jul 2025 10:08:00 GMT
Content-Type: application/json
Content-Length: 35
Connection: close

{
  "status": "drone initializing..."
}
```
Now drone is ready for a flight you need to send request under "Начало выполнения миссии". The output will be the following:

HTTP/1.1 200 OK
Server: Werkzeug/3.0.6 Python/3.8.20
Date: Tue, 15 Jul 2025 10:10:01 GMT
Content-Type: application/json
Content-Length: 42
Connection: close

{
  "status": "start successfully requested"
}

Then execute _make logs_ to watch the flight, after the flight is over you see a "flight ended" in mobile and center containers

#### Obstacles mode

You can also try run drone with obstacles: fake servo and movement-calculation modules by executing _make run-obstacles_ further the order of actions is the same as during a normal mode

#### All mode

To run the whole project execute _make all_ (base scenario with all tests in normal mode)

### Tests
- Tests execution integrated in _make all_ scenario, if you want to run it manually use _make test_ when system is running
There are 2 tests files ,
- First e2e test that checks base and some others 
suspicious scenarios execution (Replacing mission , multiple attempts to start drone and more)
- Second security policies test, which checking monitor's security policies

#### Troubleshooting

- if kafka or zookeeper containers don't start, make sure you don't have containers with the same name. If you do, remove the old containers and run the demo again.
- if you use a package manager other than apt, and trying _make all_ you need manually execute commands from the script sys-packages, after clear sys-packages section. Then try _make all_ again
- if after _make all_ you see output like this: [Building wheel for confluent-kafka (pyproject.toml): started
  Building wheel for confluent-kafka (pyproject.toml): finished with status 'error'
Failed to build confluent-kafka] try to install librdkafka package. Then try _make all_ again