#!/bin/bash

set -xe

workspace=${WORKSPACE:-"/home/jenkins/agent/build"}
branch=${BRANCH:-'v1.46.6.wc1-lustre'}
build_id=${BUILD_ID:-'001'}
extra_patches=${EXTRA_PATCHES}
git_remote_repo=${GIT_REPO:-'git://git.whamcloud.com/tools/e2fsprogs.git'}
distro=${DISTRO:-'rhel8.8'}
dist=${distro}

if [[ $dist =~ rhel8 ]]; then
	dist="el8"
fi

arch=$(arch)
build_what="e2fsprogs"
cache_dir="/home/jenkins/agent/cache"
last_build_file="${cache_dir}/build/lastbuild-${build_what}-${branch}"
build_cache_dir=$(dirname $last_build_file)
build_dir=${workspace}/build-${build_what}-${branch}-$build_id
rpm_repo="/home/jenkins/agent/rpm-repo/${build_what}/${branch}/${dist}/${arch}"

local_patch_dir="${cache_dir}/src/patches/${build_what}"
git_local_repo="${cache_dir}/git/e2fsprogs.git"

echo "Cleanup workspace dir"
rm -rf ${workspace}/build-${build_what}-${branch}-*


# Install dependant pkgs for build
sudo dnf install -y dnf-plugins-core
pkgs=()
if [[ $distro =~ rhel ]]; then
	sudo dnf config-manager --set-enabled ha
	sudo dnf config-manager --set-enabled powertools
	sudo dnf install -y epel-release
	pkgs+=(distcc redhat-lsb-core)
fi
sudo dnf update -y
pkgs+=(git ccache gcc make autoconf automake libtool rpm-build wget createrepo)
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
cd e2fsprogs
commit_id=$(git rev-parse --short HEAD)

# Check if need to build
sudo mkdir -p $build_cache_dir
sudo chown jenkins:jenkins -R $build_cache_dir
if [[ -f $last_build_file ]] && [[ "$commit_id" == "$(cat $last_build_file)" ]]; then
	echo "The same build commit $commit_id skip build."
	exit 0
fi

# configure
./configure
sudo dnf builddep -y e2fsprogs-RHEL-7+.spec

# Build
echo "Build rpms..."
RPM_TOPDIR=$build_dir make rpm

# Release
echo "Re-generate rpm repo..."
sudo mkdir -p $rpm_repo
sudo rm -rfv $rpm_repo/*.rpm
sudo mv -fv $build_dir/RPMS/aarch64/*.aarch64.rpm $rpm_repo
sudo mv -fv $build_dir/SRPMS/*src.rpm $rpm_repo
sudo createrepo --update $rpm_repo

echo $commit_id > $last_build_file
echo "Finish build $build_id. branch: $branch, commit ID: $commit_id"
