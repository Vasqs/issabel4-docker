FROM quay.io/centos/centos:7

ARG ASTERISK_PACKAGE=asterisk18
ARG OPTIONAL_PACKAGES=""
ARG INSTALL_ISSABELBR_POST_PATCH=1

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
    install_packages="systemd systemd-sysv initscripts sudo which rsync curl wget net-tools procps-ng openssh-server mariadb-server httpd php php-cli php-mysql php-process issabel issabel-pbx ${ASTERISK_PACKAGE}"; \
    if [ -n "${OPTIONAL_PACKAGES}" ]; then \
      install_packages="${install_packages} ${OPTIONAL_PACKAGES}"; \
    fi; \
    yum --disablerepo='*' --enablerepo=issabel-local -y install \
      ${install_packages}; \
    yum clean all; \
    rm -rf /var/cache/yum; \
    mkdir -p /workspace /var/lib/issabel /etc/systemd/system/multi-user.target.wants

COPY docker/issabel/rootfs/ /

RUN set -eux; \
    chmod +x /usr/bin/issabel-helper /usr/local/bin/bootstrap-issabel /usr/local/bin/issabel-firstboot /usr/local/bin/sync-workspace /usr/local/bin/healthcheck-issabel /usr/local/bin/issabelbr-mysql-wrapper /usr/local/bin/configure-el7-repositories /usr/local/bin/apply-issabelbr-build-assets /usr/local/bin/apply-issabelbr-post-restore; \
    INSTALL_ISSABELBR_POST_PATCH="${INSTALL_ISSABELBR_POST_PATCH}" ASTERISK_PACKAGE="${ASTERISK_PACKAGE}" /usr/local/bin/apply-issabelbr-build-assets; \
    yum clean all; \
    rm -rf /var/cache/yum /usr/src/IssabelBR

VOLUME ["/sys/fs/cgroup"]

ENTRYPOINT ["/usr/local/bin/bootstrap-issabel"]
CMD ["/usr/sbin/init"]
