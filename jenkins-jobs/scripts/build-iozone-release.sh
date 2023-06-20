#!/bin/bash

set -xe

version=${VERSION:-'3.494-1.fc38'}
workspace=${WORKSPACE:-"/home/jenkins/agent/build"}
build_id=${BUILD_ID:-'001'}
dist=${DIST:-'el8'}

arch=$(arch)
build_what="iozone"
cache_dir="/home/jenkins/agent/cache"
subname="${build_what}-${dist}"
rpm_repo_dir="${build_what}/${dist}/${arch}"
last_build_file="${cache_dir}/build/lastbuild-${subname}"
build_cache_dir=$(dirname $last_build_file)
build_dir="${workspace}/build-${subname}-${build_id}"
srpm_cache_dir="${cache_dir}/src/${build_what}"
rpm_repo="/home/jenkins/agent/rpm-repo/${rpm_repo_dir}"
rpm_repo_base_url="https://uk.linaro.cloud/repo"
rpm_repo_url="${rpm_repo_base_url}/${rpm_repo_dir}"
rpm_repo_file="${rpm_repo}/${build_what}.repo"

srpm_download_url="https://rpmfind.net/linux/rpmfusion/nonfree/fedora/releases/38/Everything/source/SRPMS/i/"
srpm="${build_what}-${version}.src.rpm"
top_dir="${build_dir}/rpmbuild"
spec_file="${build_what}.spec"

# check dist rpm macro existence
dist_macro=$(rpm -E %{?dist})
if [[ -z "$dist_macro" ]]; then
	echo "%dist .$dist" >> ~/.rpmmacros
fi

# Check if need to build
sudo mkdir -p $build_cache_dir
sudo chown jenkins:jenkins -R $build_cache_dir
if [[ -f $last_build_file ]] &&
   [[ "$version" == "$(cat $last_build_file)" ]]; then
	echo "The same build version $version skip build."
	exit 0
fi


echo "Cleanup workspace dir"
rm -rf ${workspace}/build-${subname}-*

# Install dependant pkgs for build
sudo dnf install -y dnf-plugins-core
pkgs=()
if [[ $dist =~ el8 ]]; then
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
sudo mkdir -p $srpm_cache_dir
sudo chown jenkins:jenkins -R $srpm_cache_dir
mkdir -p $build_dir
wget -c ${srpm_download_url}/$srpm -O ${srpm_cache_dir}/$srpm
rpm -ivh --define "_topdir $top_dir" ${srpm_cache_dir}/$srpm
cd $top_dir
sudo dnf builddep -y --spec SPECS/${spec_file}

# Build
echo "Build rpms..."
rpmbuild --define "_topdir $top_dir" \
       	-ba SPECS/${spec_file}

# Release
echo "Re-generate rpm repo..."
sudo mkdir -p $rpm_repo
sudo rm -rfv $rpm_repo/*.rpm
sudo mv -fv $top_dir/RPMS/aarch64/*.aarch64.rpm $rpm_repo
sudo mv -fv $top_dir/SRPMS/*.src.rpm $rpm_repo
sudo createrepo --update $rpm_repo

cat <<EOF | sudo tee ${rpm_repo_file}
[${build_what}]
name=${build_what}
baseurl=${rpm_repo_url}
enabled=1
gpgcheck=0
EOF

echo $version > $last_build_file
echo "Finish build $build_id. original version: $version, new version: ${version/fc38/${dist}}"
