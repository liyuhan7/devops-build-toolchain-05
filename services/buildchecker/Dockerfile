# BuildChecker 服务镜像（A 组）。构建上下文是仓库根目录：docker compose build 或 make build。
#   1. 基础镜像按 digest 固定；升级时只改 BASE_IMAGE 这一行，并在提交说明里写新 digest
#   2. 系统工具和 Python 包的实际版本在构建时写入 /opt/toolchain.lock
#   3. Python 依赖按锁文件和哈希安装
#   4. 以普通用户 app 运行；.env、work/、.git 不会进入镜像（见 .dockerignore）
# 默认使用官方镜像；服务器可通过构建参数选择可访问的同 digest 镜像源。
ARG BASE_IMAGE=python@sha256:f82c96458eedc847b233e582eb31336f4954b39cae020b6dcf5b3ed0e5cbcd74
FROM ${BASE_IMAGE}

ENV LC_ALL=C.UTF-8 \
    TZ=UTC \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN sed -i \
      -e 's|http://deb.debian.org|https://deb.debian.org|g' \
      /etc/apt/sources.list.d/debian.sources \
 && apt-get update \
 && apt-get install -y --no-install-recommends gcc make libc6-dev strace git \
 && rm -rf /var/lib/apt/lists/* \
 && dpkg-query -W -f='${Package}=${Version}\n' gcc make libc6-dev strace git > /opt/toolchain.lock \
 && echo "python3=$(python3 -c 'import platform; print(platform.python_version())')" >> /opt/toolchain.lock \
 && echo "arch=$(dpkg --print-architecture)" >> /opt/toolchain.lock

COPY requirements-dev.lock requirements-contracts.lock /tmp/
RUN pip install --no-cache-dir --require-hashes -r /tmp/requirements-dev.lock \
 && pip freeze | sed 's/^/pip:/' >> /opt/toolchain.lock

# 原项目源码与验证入口在同一服务镜像中，运行副本由普通用户创建。
RUN useradd --create-home --uid 10001 app && install -d -o app -g app /repo
WORKDIR /repo
COPY --chown=app:app . /repo/
ENV PYTHONPATH=/repo/services/buildchecker
USER app

CMD ["python3", "-m", "buildchecker", "--help"]
