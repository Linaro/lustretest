#!/bin/bash

set -xe

kernel_version=${KERNEL_VERSION:-'4.18.0-477.10.1.el8_4k'}
kernel_release=${kernel_version##*-}
kernel_main_version=${kernel_version%%.0-*}
workspace=${WORKSPACE:-"/home/jenkins/agent/build"}
branch=${BRANCH:-'master'}
build_id=${BUILD_ID:-'001'}
extra_patches=${EXTRA_PATCHES}
distro=${DISTRO:-'rhel8.8'}
target="${kernel_main_version}-${distro}"
dist=${distro}

if [[ $dist =~ rhel8 ]]; then
	dist="el8"
fi

arch=$(arch)
build_what="lustre"
cache_dir="/home/jenkins/agent/cache"
last_build_file="${cache_dir}/build/lastbuild-${build_what}"
build_cache_dir=$(dirname $last_build_file)
build_dir=${workspace}/build-${build_what}-$build_id
kernel_src_dir="${cache_dir}/src/kernel"
rpm_repo="/home/jenkins/agent/rpm-repo/${build_what}/${branch}/${dist}/${arch}"

local_patch_dir="${cache_dir}/src/patches/${build_what}"
git_remote_repo="git://git.whamcloud.com/fs/lustre-release.git"
git_local_repo="${cache_dir}/git/lustre-release.git"
kernel_rpm_repo="https://uk.linaro.cloud/repo/kernel/${dist}/${arch}/"

echo "Cleanup workspace dir"
rm -rf ${workspace}/build-${build_what}-*


# Install dependant pkgs for build
sudo dnf install -y dnf-plugins-core
pkgs=()
if [[ $distro =~ rhel ]]; then
	sudo dnf config-manager --set-enabled ha
	sudo dnf config-manager --set-enabled powertools
	sudo dnf config-manager --add-repo $kernel_rpm_repo
	sudo dnf install -y epel-release
	pkgs+=(distcc redhat-lsb-core)
fi
sudo dnf update -y
pkgs+=(git ccache gcc make autoconf automake libtool rpm-build wget createrepo)
pkgs+=(audit-libs-devel binutils-devel elfutils-devel kabi-dw ncurses-devel newt-devel numactl-devel \
	openssl-devel pciutils-devel perl perl-devel python3-docutils xmlto xz-devel elfutils-libelf-devel \
	libcap-devel libcap-ng-devel libyaml libyaml-devel kernel-rpm-macros libblkid-devel libtirpc-devel \
	libnl3-devel mpich libmount-devel llvm-devel clang)
pkgs+=(libtirpc-devel libblkid-devel libuuid-devel libudev-devel openssl-devel zlib-devel libaio-devel \
	libattr-devel elfutils-libelf-devel python3 python3-devel python3-setuptools \
	python3-cffi libffi-devel git ncompress libcurl-devel keyutils-libs-devel)
pkgs+=(python3-packaging dkms bash-completion openmpi-devel texinfo e2fsprogs-devel bison yum-utils)
sudo dnf install -y ${pkgs[@]}
sudo ln -s $(which ccache) /usr/local/bin/gcc &&
sudo ln -s $(which ccache) /usr/local/bin/g++ &&
sudo ln -s $(which ccache) /usr/local/bin/cc &&
sudo ln -s $(which ccache) /usr/local/bin/c++

# Prepare
echo "Generate the release tar bz..."
mkdir -p $build_dir
cd $build_dir
git clone --branch $branch --reference $git_local_repo $git_remote_repo
cd lustre-release
commit_id=$(git rev-parse --short HEAD)

# Check if need to build
sudo mkdir -p $build_cache_dir
sudo chown jenkins:jenkins -R $build_cache_dir
if [[ -f $last_build_file ]] && [[ "$commit_id" == "$(cat $last_build_file)" ]]; then
	echo "The same build commit $commit_id skip build."
	exit 0
fi

# Apply extra patches that haven't been merged into the branch.
if [[ -n ${extra_patches} ]]; then
    echo ${extra_patches} | sed -n 1'p' | tr ',' '\n' | while read patch; do
        curl \
            "https://review.whamcloud.com/changes/${patch}/revisions/current/patch" \
            | base64 -d | git apply -v -3
    done
fi

# Apply more extra patches from local cache dir which are only for build not for upstream
mkdir -p tmp-patches
cp -rv $local_patch_dir/*.patch tmp-patches
cp -rv $local_patch_dir/${distro}/*.patch tmp-patches || true
if [[ $distro =~ rhel8 ]]; then
    sed -i "s/KRELEASE/${kernel_release}/" tmp-patches/*.patch
fi
git apply -v tmp-patches/*.patch

# Generate the source tar file
sh autogen.sh
./configure -C --enable-dist
make dist
code_base=$(find . -name "lustre*tar.gz")
code_base=$(basename $code_base)

sudo dnf builddep -y lustre.spec

# Build
echo "Build rpms..."
sudo chown jenkins:jenkins -R $kernel_src_dir
cd $build_dir
$build_dir/lustre-release/contrib/lbuild/lbuild \
	--lustre=$build_dir/lustre-release/$code_base  \
	--target=$target --distro=$distro \
	--kerneldir=$kernel_src_dir --kernelrpm=$kernel_src_dir \
	--ccache --disable-zfs --patchless-server

# Release
echo "Re-generate rpm repo..."
sudo mkdir -p $rpm_repo
sudo rm -rfv $rpm_repo/*.rpm
sudo mv -fv $build_dir/RPMS/aarch64/*.aarch64.rpm $rpm_repo
sudo mv -fv $build_dir/SRPMS/*src.rpm $rpm_repo
sudo createrepo --update $rpm_repo

echo $commit_id > $last_build_file
echo "Finish build $build_id. branch: $branch, commit ID: $commit_id"
