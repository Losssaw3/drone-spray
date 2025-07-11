SHELL := bash

PATH_PREFIX := $(CURDIR)

MODULES := monitor \
           communication \
		   encryption \
		   camera \
		   complex \
		   center \
		   gps \
		   internal \
		   drone-status-control \
		   movement-calculation \
		   limiter \
		   message-sending \
		   mission-control \
		   sprayer \
		   sprayer-control \
		   task-orchestrator \
		   servo \

FAKE_MODULES := monitor \
           communication \
		   encryption \
		   camera \
		   complex \
		   center \
		   gps \
		   internal \
		   drone-status-control \
		   movement-calculation \
		   limiter \
		   message-sending \
		   mission-control \
		   sprayer \
		   sprayer-control \
		   task-orchestrator \
		   servo \
		   
SLEEP_TIME := 20

run:
	docker-compose -f docker-compose-base.yml up -d --build
	sleep ${SLEEP_TIME}

	for MODULE in ${MODULES}; do \
		echo Creating $${MODULE} topic; \
		docker exec broker \
			kafka-topics --create --if-not-exists \
			--topic $${MODULE} \
			--bootstrap-server localhost:9092 \
			--replication-factor 1 \
			--partitions 1; \
	done

run-obstacles:
	docker-compose -f docker-compose-obstacles.yml up -d --build
	sleep ${SLEEP_TIME}

	for MODULE in ${MODULES}; do \
		echo Creating $${MODULE} topic; \
		docker exec broker \
			kafka-topics --create --if-not-exists \
			--topic $${MODULE} \
			--bootstrap-server localhost:9092 \
			--replication-factor 1 \
			--partitions 1; \
	done

permissions:
	chmod a+w $(PATH_PREFIX)/shared/coords
	chmod a+w $(PATH_PREFIX)/shared/init
	chmod a+w $(PATH_PREFIX)/shared/flight_status

all: clean run delay30s test

delay30s:
	sleep 30

clean:
	docker-compose -f docker-compose-base.yml down
	@echo "0, 0, 0" > $(PATH_PREFIX)/shared/coords
	@echo "0" > $(PATH_PREFIX)/shared/init
	@echo "0" > $(PATH_PREFIX)/shared/flight_status
logs:
	docker-compose -f docker-compose-base.yml logs -f --tail 100

pipenv:
	pipenv install -r requirements.txt

prepare: permissions pipenv

test:
	pipenv run pytest -sv
