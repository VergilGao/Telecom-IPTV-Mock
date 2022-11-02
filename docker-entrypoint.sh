#! /bin/sh

USER=abc
config_file="/config/iptv.ini"

echo "---将时区设置为 ${TZ}---"
echo "${TZ}" > /etc/timezone
echo "---检查用户 ${USER} 的 UID 是否为 ${UID}---"
usermod -o -u ${UID} ${USER}
echo "---检查用户 ${USER} 的 GID 是否为 ${GID}---"
groupmod -o -g ${GID} ${USER} > /dev/null 2>&1 ||:
usermod -g ${GID} ${USER}
echo "---将 umask 设置为 ${UMASK}---"
umask ${UMASK}

echo "---修复文件权限---"
if [ ! -d /config ]; then
    echo "---未找到配置文件目录，创建中---"
    mkdir -p /config
fi
chown -R ${UID}:${GID} /app /data /config 

echo "检查是否存在配置文件"
if [ ! -f "${config_file}" ]; then
    cp /app/config.template "${config_file}"
    echo "没有找到配置文件，我们创建了一个新的配置文件，请修改后重启镜像"
    exit 1
fi

echo "程序启动..."
su-exec ${USER} /app/chips --data=/data --config=/config