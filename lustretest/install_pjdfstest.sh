#!/bin/bash -x

pushd ~
[ -d pjdfstest ] && exit 0 || "Install pjdfstest..."
sudo dnf install -y git ccache gcc make autoconf automake libtool &&
git clone https://github.com/pjd/pjdfstest.git &&
cd pjdfstest/ &&
autoreconf -ifs &&
./configure &&
make pjdfstest -j$(nproc)
pjdfstest_dir=$(pwd)
popd
