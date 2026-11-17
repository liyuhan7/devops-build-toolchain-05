# DRAFT 服务镜像（B 组）。构建上下文是仓库根目录：docker compose build 或 make build。
#   1. 基础镜像按 digest 固定；升级时只改 ARG 这一行，并在提交说明里写新 digest
#   2. 镜像里只放 docker 命令行（客户端），不放 Docker 引擎；运行时通过挂载的
#      /var/run/docker.sock 使用宿主机的 Docker（见 compose.yaml）
#   3. 工具和 Python 包的实际版本在构建时写入 /opt/toolchain.lock
#   4. 以普通用户 app 运行；访问 docker.sock 所需的用户组在运行时由 group_add 加入
ARG BASE_IMAGE=m.daocloud.io/docker.io/library/python@sha256:f82c96458eedc847b233e582eb31336f4954b39cae020b6dcf5b3ed0e5cbcd74
# docker CLI 镜像默认与 BASE_IMAGE 走同一加速器；境外 CI 可传 DOCKER_CLI_IMAGE 使用官方地址。
ARG DOCKER_CLI_IMAGE=m.daocloud.io/docker.io/library/docker@sha256:9190b0613792e658a7783cf14b2d5ace5941bb68ede7276922ea36ee457d76ad
# APT 与 PyPI 默认使用阿里云 HTTPS 镜像，与 A 组一致；境外 CI 可传官方源参数覆盖。
ARG APT_MIRROR=https://mirrors.aliyun.com
ARG PIP_INDEX=https://mirrors.aliyun.com/pypi/simple/

FROM ${DOCKER_CLI_IMAGE} AS docker-cli

FROM ${BASE_IMAGE}

ARG APT_MIRROR
ARG PIP_INDEX

ENV LC_ALL=C.UTF-8 \
    TZ=UTC \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# 从官方 docker:cli 镜像复制客户端与 buildx 插件（只复制文件，不安装 Docker 引擎）
COPY --from=docker-cli /usr/local/bin/docker /usr/local/bin/docker
COPY --from=docker-cli /usr/local/libexec/docker/cli-plugins/docker-buildx /usr/local/libexec/docker/cli-plugins/docker-buildx

# 镜像源为空时保留基础镜像自带地址，便于改用官方源或内网缓存。
RUN if [ -n "${APT_MIRROR}" ]; then \
      sed -i "s|http://deb.debian.org|${APT_MIRROR}|g" /etc/apt/sources.list.d/debian.sources; \
    fi \
 && apt-get update \
 && apt-get install -y --no-install-recommends gcc make libc6-dev git \
 && rm -rf /var/lib/apt/lists/* \
 && dpkg-query -W -f='${Package}=${Version}\n' gcc make libc6-dev git > /opt/toolchain.lock \
 && echo "docker-cli=$(docker --version)" >> /opt/toolchain.lock \
 && echo "python3=$(python3 -c 'import platform; print(platform.python_version())')" >> /opt/toolchain.lock \
 && echo "arch=$(dpkg --print-architecture)" >> /opt/toolchain.lock

COPY requirements-dev.lock requirements-contracts.lock /tmp/
RUN if [ -n "${PIP_INDEX}" ]; then \
      pip install --no-cache-dir --require-hashes -i "${PIP_INDEX}" -r /tmp/requirements-dev.lock; \
    else \
      pip install --no-cache-dir --require-hashes -r /tmp/requirements-dev.lock; \
    fi \
 && pip freeze | sed 's/^/pip:/' >> /opt/toolchain.lock

RUN useradd --create-home --uid 10001 app && install -d -o app -g app /repo
WORKDIR /repo
COPY --chown=app:app . /repo/
ENV PYTHONPATH=/repo/services/draft
USER app

CMD ["python3", "-m", "draft", "--help"]
