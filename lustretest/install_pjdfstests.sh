#!/bin/bash

sudo dnf install -y git ccache gcc make autoconf automake libtool
git clone https://github.com/pjd/pjdfstest.git
cd pjdfstest/
autoreconf -ifs
./configure
make pjdfstest
pjdfstest_dir=$(pwd)
