# 两组共用项目根目录；每次运行在个人 work/ 下留存独立证据。
SHELL := /bin/bash
.SHELLFLAGS := -eu -o pipefail -c
.DEFAULT_GOAL := all
.NOTPARALLEL:

GROUP ?= A
ifeq ($(GROUP),A)
SERVICE := buildchecker
PROFILE := a
else ifeq ($(GROUP),B)
SERVICE := draft
PROFILE := b
else
$(error GROUP 必须为 A 或 B)
endif

STUDENT_ID := $(or $(shell git config --local user.name 2>/dev/null),local)
IMAGE := e4-$(SERVICE):$(STUDENT_ID)
STAMP := $(shell date +%Y%m%d-%H%M%S)-$(shell python3 -c "import uuid; print(uuid.uuid4().hex[:8])")
RUN := work/e4/$(GROUP)/$(STAMP)
TIMEOUT ?= 600
PROJECT_TIMEOUT ?= 3600
BASE_IMAGE := $(shell sed -n 's/^ARG BASE_IMAGE=//p' services/$(SERVICE)/Dockerfile)
DOCKER_GID := $(or $(shell stat -c %g /var/run/docker.sock 2>/dev/null),0)
COMPOSE := docker compose --profile $(PROFILE) -p e4-$(SERVICE)-$(shell echo $(STUDENT_ID) | tr A-Z a-z)
export STUDENT_ID DOCKER_GID GROUP SERVICE COMPOSE
export E4_RUN_DIR := $(RUN)
export E4_TIMEOUT := $(TIMEOUT)
export E4_PROJECT_TIMEOUT := $(PROJECT_TIMEOUT)

.PHONY: all doctor build test smoke project-smoke scan shell lock clean

all: doctor build test smoke scan
	@echo "证据目录：$(RUN)"

$(RUN):
	@mkdir -p $(RUN)
	@git rev-parse HEAD > $(RUN)/source-sha.txt
	@git status --porcelain=v1 > $(RUN)/worktree-status.txt

.env:
	cp .env.example .env
	chmod 600 .env

doctor: | $(RUN)
	python3 scripts/doctor.py --group $(GROUP) --out $(RUN)/env.json

build: .env | $(RUN)
	$(COMPOSE) build --progress=plain $(SERVICE) 2>&1 | tee $(RUN)/build.log
	docker image inspect $(IMAGE) --format '{"image":"$(IMAGE)","id":"{{.Id}}","arch":"{{.Architecture}}","created":"{{.Created}}"}' | tee $(RUN)/image.json
	$(COMPOSE) run --rm --no-deps -T --interactive=false $(SERVICE) cat /opt/toolchain.lock | tee $(RUN)/toolchain.lock

test: .env | $(RUN)
	timeout $(TIMEOUT) $(COMPOSE) run --rm --no-deps -T --interactive=false $(SERVICE) sh -c 'python3 scripts/validate.py && python3 scripts/e3/check_baselines.py && python3 -m unittest discover -s tests -v && pytest -c services/$(SERVICE)/pytest.ini services/$(SERVICE)/tests' 2>&1 | tee $(RUN)/test.log

smoke: .env | $(RUN)
ifeq ($(GROUP),A)
	timeout $(TIMEOUT) $(COMPOSE) run --rm --no-deps -T --interactive=false $(SERVICE) python3 -m $(SERVICE) smoke | tee $(RUN)/smoke.json
else
	timeout $(TIMEOUT) $(COMPOSE) run --rm --no-deps -T --interactive=false $(SERVICE) python3 -m $(SERVICE) smoke --tag e4-smoke-broken:$(STUDENT_ID)-$(STAMP) | tee $(RUN)/smoke.json
endif
	bash scripts/e4/project_smoke.sh

project-smoke: .env | $(RUN)
	bash scripts/e4/project_smoke.sh

scan: | $(RUN)
	python3 scripts/secret_scan.py . --history --image $(IMAGE) | tee $(RUN)/secret-scan.txt

# work/ 挂载到宿主机目录，退出容器后仍能读取 E5 原始记录。
shell: .env
	@mkdir -p work
	$(COMPOSE) run --rm --no-deps --user $$(id -u):$$(id -g) -e HOME=/tmp -v "$$PWD/work:/repo/work" $(SERVICE) bash

lock:
	docker run --rm --user $$(id -u):$$(id -g) -e HOME=/tmp -v "$$PWD":/src -w /src $(BASE_IMAGE) sh -c '\
	  python3 -m venv /tmp/v && /tmp/v/bin/pip install -q uv==0.12.19 && \
	  /tmp/v/bin/uv pip compile requirements-dev.in --generate-hashes --python-version 3.13 --python-platform linux -o requirements-dev.lock'

# 只清理本人服务镜像，不删除其他同学的镜像或共享缓存。
clean:
	-docker image rm $(IMAGE)
