#!/bin/bash -x

pushd ~
command -v mdtest && exit 0 || "Install ior and mdtest ..."
sudo dnf install -y git ccache gcc make autoconf \
	automake libtool openmpi openmpi-devel &&
module load mpi/openmpi-$(arch) &&
git clone https://github.com/hpc/ior.git &&
cd ior/ &&
./bootstrap &&
./configure &&
make -j$(nproc) &&
sudo make install
ior_dir=$(pwd)
popd
