#!/bin/bash

set -xe

workspace=${WORKSPACE:-"/home/jenkins/agent/build"}
branch=${BRANCH:-'master-lustre'}
build_id=${BUILD_ID:-'001'}
git_remote_repo=${GIT_REPO:-'git://git.whamcloud.com/tools/e2fsprogs.git'}
dist=${DIST:-'el8'}
dist_main=${dist%sp*}

arch=$(arch)
build_what="e2fsprogs"
cache_dir="/home/jenkins/agent/cache"
subname="${build_what}-${dist}"
rpm_repo_dir="${build_what}/${dist}/${arch}"
last_build_file="${cache_dir}/build/lastbuild-${subname}"
build_cache_dir=$(dirname $last_build_file)
build_dir="${workspace}/build-${subname}-${build_id}"
rpm_repo="/home/jenkins/agent/rpm-repo/${rpm_repo_dir}"
rpm_repo_base_url="https://uk.linaro.cloud/repo"
rpm_repo_url="${rpm_repo_base_url}/${rpm_repo_dir}"
rpm_repo_file="${rpm_repo}/${build_what}.repo"

git_local_repo="${cache_dir}/git/${build_what}.git"
local_patch_dir="${cache_dir}/src/patches/${build_what}"

# check dist rpm macro existence
dist_macro=$(rpm -E %{?dist})
if [[ -z "$dist_macro" ]]; then
	echo "%dist .$dist" >> ~/.rpmmacros
fi

echo "Cleanup workspace dir"
rm -rf ${workspace}/build-${subname}-*


# Install dependant pkgs for build
sudo dnf install -y dnf-plugins-core
pkgs=()
if [[ $dist =~ el ]]; then
	if [[ $dist =~ el9 ]]; then
		sudo dnf config-manager --set-enabled highavailability
		sudo dnf config-manager --set-enabled crb
	else
		sudo dnf config-manager --set-enabled ha
		sudo dnf config-manager --set-enabled powertools
		pkgs+=(distcc redhat-lsb-core)
	fi
	sudo dnf install -y epel-release
elif [[ $dist =~ oe ]]; then
	sudo dnf install -y openeuler-lsb
fi
#sudo dnf update -y
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

# Apply more extra patches from local cache dir which are only for build not for upstream
# TODO: download such patches from git repo
if [[ $dist =~ el9 ]]; then
mkdir -p tmp-patches
cp -rv $local_patch_dir/*.patch tmp-patches || true
cp -rv $local_patch_dir/${dist_main}/*.patch tmp-patches || true
cp -rv $local_patch_dir/${dist}/*.patch tmp-patches || true
git apply -v tmp-patches/*.patch
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

cat <<EOF | sudo tee ${rpm_repo_file}
[${build_what}]
name=${build_what}
baseurl=${rpm_repo_url}
enabled=1
gpgcheck=0
EOF

echo $commit_id > $last_build_file
echo "Finish build $build_id. branch: $branch, commit ID: $commit_id"
