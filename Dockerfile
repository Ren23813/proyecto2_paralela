# Construir:  docker build -t mpi-cluster-image .
FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
      build-essential openmpi-bin libopenmpi-dev openssh-server \
      libssl-dev iproute2 iputils-ping net-tools \
    && rm -rf /var/lib/apt/lists/*

    
RUN mkdir -p /run/sshd \
    && sed -i 's/^#\?PermitRootLogin.*/PermitRootLogin yes/' /etc/ssh/sshd_config \
    && echo "StrictHostKeyChecking no" >> /etc/ssh/ssh_config \
    && echo "UserKnownHostsFile /dev/null" >> /etc/ssh/ssh_config

# OpenMPI no quiere correr como root si no se le obliga
ENV OMPI_ALLOW_RUN_AS_ROOT=1
ENV OMPI_ALLOW_RUN_AS_ROOT_CONFIRM=1

WORKDIR /root/proyecto
COPY compat ./compat
COPY bruteforce.c texto.txt Makefile ./
RUN make bruteforce

EXPOSE 22
CMD ["/bin/bash"]
