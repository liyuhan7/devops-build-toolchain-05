#!/usr/bin/env bash
# 每组服务器初始化（执行一次）：Ubuntu 22.04 / 24.04 LTS。
# 用法：sudo bash setup/bootstrap_ubuntu.sh
# 需要镜像加速时：sudo DOCKER_MIRROR=https://<镜像加速地址> bash setup/bootstrap_ubuntu.sh
# 老师为每组分配一台服务器、一个登录账号；本脚本把这个账号加入 docker 组。
set -euo pipefail

if [ "$(id -u)" -ne 0 ]; then echo "请用 sudo 执行"; exit 1; fi
. /etc/os-release
echo "系统：$PRETTY_NAME  架构：$(uname -m)"

apt-get update
# Ubuntu 仓库自带的 Docker 组件；如需 Docker 官方仓库版本，按 docs.docker.com 的 Ubuntu 安装说明替换这一行
apt-get install -y docker.io docker-compose-v2 docker-buildx git make python3 jq
systemctl enable --now docker

if [ -n "${DOCKER_MIRROR:-}" ] && [ ! -f /etc/docker/daemon.json ]; then
  printf '{\n  "registry-mirrors": ["%s"]\n}\n' "$DOCKER_MIRROR" > /etc/docker/daemon.json
  systemctl restart docker
  echo "已配置镜像加速：$DOCKER_MIRROR"
elif [ -f /etc/docker/daemon.json ]; then
  echo "已存在 /etc/docker/daemon.json，未修改"
fi

# 登录账号加入 docker 组（docker 组权限基本等同 root）
LOGIN_USER="${SUDO_USER:-}"
if [ -n "$LOGIN_USER" ] && [ "$LOGIN_USER" != root ]; then
  usermod -aG docker "$LOGIN_USER"
  echo "已把 $LOGIN_USER 加入 docker 组，重新登录后生效"
fi

docker version --format 'Docker {{.Server.Version}}'
docker compose version
echo "完成。安全组只开放 22 端口；不要开放 2375/2376 Docker API 端口。"
