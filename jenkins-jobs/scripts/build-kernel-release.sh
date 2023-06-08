#!/bin/bash

set -xe

kernel_version=${KERNEL_VERSION:-'4.18.0-477.10.1.el8_8'}
workspace=${WORKSPACE:-"/home/jenkins/agent/build"}
build_id=${BUILD_ID:-'001'}
distro=${DISTRO:-'rhel8.8'}
dist=${distro}

if [[ $dist =~ rhel8 ]]; then
	dist="el8"
fi

arch=$(arch)
build_what="kernel"
cache_dir="/home/jenkins/agent/cache"
last_build_file="${cache_dir}/build/lastbuild-${build_what}"
build_cache_dir=$(dirname $last_build_file)
build_dir=${workspace}/build-${build_what}-$build_id
kernel_src_dir="${cache_dir}/src/kernel"
rpm_repo="/home/jenkins/agent/rpm-repo/${build_what}/${dist}/${arch}"

srpm_download_url="https://repo.almalinux.org/vault/8/BaseOS/Source/Packages/"
top_dir="${build_dir}/rpmbuild"
append_version="_4k"

# Check if need to build
sudo mkdir -p $build_cache_dir
sudo chown jenkins:jenkins -R $build_cache_dir
if [[ -f $last_build_file ]] &&
   [[ "$kernel_version" == "$(cat $last_build_file)" ]]; then
	echo "The same build kernel version $kernel_version skip build."
	exit 0
fi


echo "Cleanup workspace dir"
rm -rf ${workspace}/build-${build_what}-*

# Install dependant pkgs for build
sudo dnf install -y dnf-plugins-core
pkgs=()
if [[ $distro =~ rhel ]]; then
	sudo dnf config-manager --set-enabled ha
	sudo dnf config-manager --set-enabled powertools
	sudo dnf install -y epel-release
	pkgs+=(distcc)
fi
sudo dnf update -y
pkgs+=(ccache gcc make autoconf automake libtool rpm-build wget createrepo)
sudo dnf install -y ${pkgs[@]}
sudo ln -s $(which ccache) /usr/local/bin/gcc &&
sudo ln -s $(which ccache) /usr/local/bin/g++ &&
sudo ln -s $(which ccache) /usr/local/bin/cc &&
sudo ln -s $(which ccache) /usr/local/bin/c++

# Prepare
echo "Prepare..."
sudo chown jenkins:jenkins -R $kernel_src_dir
mkdir -p $build_dir
srpm="kernel-${kernel_version}.src.rpm"
wget -c ${srpm_download_url}/$srpm -O ${kernel_src_dir}/$srpm
rpm -ivh --define "_topdir $top_dir" ${kernel_src_dir}/$srpm
cd $top_dir
sudo dnf builddep -y SPECS/kernel.spec
# (TODO): download config from github
if [[ $distro =~ rhel ]]; then
    cp -vf $kernel_src_dir/kernel-4.18-rhel8.8-aarch64-4k.config \
  	$top_dir/SOURCES/kernel-aarch64.config
fi

# Build
echo "Build rpms..."
rpmbuild --define "_topdir $top_dir" \
	--define "buildid $append_version" \
       	--without debug \
	--without kabichk \
       	-ba SPECS/kernel.spec

# Release
echo "Re-generate rpm repo..."
sudo mkdir -p $rpm_repo
sudo rm -rfv $rpm_repo/*.rpm
sudo mv -fv $top_dir/RPMS/aarch64/*.aarch64.rpm $rpm_repo
sudo mv -fv $top_dir/SRPMS/*.src.rpm $rpm_repo
sudo createrepo --update $rpm_repo

echo $kernel_version > $last_build_file
echo "Finish build $build_id. original kernel_version: $kernel_version, new version: $kernel_version$append_vesion"
