FROM quay.io/centos/centos:7

ENV container=docker \
    LANG=en_US.UTF-8 \
    LC_ALL=en_US.UTF-8 \
    ISABEL_BOOTSTRAP_MARKER=/var/lib/issabel/.bootstrapped \
    WORKSPACE_ROOT=/workspace

STOPSIGNAL SIGTERM

COPY .build/issabel-root /opt/issabel-root

RUN set -eux; \
    printf '%s\n' \
      '[issabel-local]' \
      'name=Issabel Local ISO' \
      'baseurl=file:///opt/issabel-root' \
      'enabled=1' \
      'gpgcheck=0' \
      > /etc/yum.repos.d/issabel-local.repo

RUN set -eux; \
    yum --disablerepo='*' --enablerepo=issabel-local -y install \
      systemd \
      systemd-sysv \
      initscripts \
      sudo \
      which \
      rsync \
      curl \
      net-tools \
      procps-ng \
      openssh-server \
      mariadb-server \
      httpd \
      php \
      php-cli \
      php-mysql \
      php-process \
      issabel \
      issabel-pbx \
      asterisk16; \
    yum clean all; \
    rm -rf /var/cache/yum; \
    mkdir -p /workspace /var/lib/issabel /etc/systemd/system/multi-user.target.wants

COPY docker/issabel/rootfs/ /

RUN set -eux; \
    chmod +x /usr/local/bin/bootstrap-issabel /usr/local/bin/issabel-firstboot /usr/local/bin/sync-workspace /usr/local/bin/healthcheck-issabel

VOLUME ["/sys/fs/cgroup"]

ENTRYPOINT ["/usr/local/bin/bootstrap-issabel"]
CMD ["/usr/sbin/init"]
