#!/bin/bash

set -xe

workspace=${WORKSPACE:-"/home/jenkins/agent/build"}
branch=${BRANCH:-'master'}
build_id=${BUILD_ID:-'001'}
extra_patches=${EXTRA_PATCHES}
git_remote_repo=${GIT_REPO:-'git://git.whamcloud.com/fs/lustre-release.git'}
distro=${DISTRO:-'rhel8.8'}
dist=${distro}
e2fsprogs_branch=${E2FSPROGS_BRANCH:-'v1.46.6.wc1-lustre'}

if [[ $distro =~ rhel8 ]]; then
	target="4.18-${distro}"
	dist="el8"
fi

arch=$(arch)
build_what="lustre"
cache_dir="/home/jenkins/agent/cache"
last_build_file="${cache_dir}/build/lastbuild-${build_what}-${branch}"
build_cache_dir=$(dirname $last_build_file)
build_dir=${workspace}/build-${build_what}-${branch}-$build_id
kernel_src_dir="${cache_dir}/src/kernel"
rpm_repo_dir="${build_what}/${branch}/${dist}/${arch}"
rpm_repo="/home/jenkins/agent/rpm-repo/${rpm_repo_dir}"
rpm_repo_base_url="https://uk.linaro.cloud/repo"
rpm_repo_url="${rpm_repo_base_url}/${rpm_repo_dir}"
rpm_repo_file="${rpm_repo}/${build_what}.repo"
repoid_base="uk.linaro.cloud_repo"

local_patch_dir="${cache_dir}/src/patches/${build_what}"
git_local_repo="${cache_dir}/git/lustre-release.git"
kernel_rpm_repo_dir="kernel/${dist}/${arch}"
e2fsprogs_rpm_repo_dir="e2fsprogs/${e2fsprogs_branch}/${dist}/${arch}"
kernel_rpm_repo_url="${rpm_repo_base_url}/${kernel_rpm_repo_dir}"
e2fsprogs_rpm_repo_url="${rpm_repo_base_url}/${e2fsprogs_rpm_repo_dir}"
lustre_repoid="${repoid_base}_${rpm_repo_dir//\//_}"
kernel_repoid="${repoid_base}_${kernel_rpm_repo_dir//\//_}"
release_num=""

echo "Cleanup workspace dir"
rm -rf ${workspace}/build-${build_what}-${branch}-*


# Install dependant pkgs for build
sudo dnf install -y dnf-plugins-core
pkgs=()
if [[ $distro =~ rhel ]]; then
	sudo dnf config-manager --set-enabled ha
	sudo dnf config-manager --set-enabled powertools
	sudo dnf config-manager --add-repo $kernel_rpm_repo_url
	sudo dnf install -y epel-release
	pkgs+=(distcc redhat-lsb-core)
fi
sudo dnf config-manager --add-repo $e2fsprogs_rpm_repo_url
sudo dnf config-manager --add-repo $rpm_repo_url
sudo dnf config-manager --save --setopt="uk.linaro.cloud_*.gpgcheck=0"
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
# TODO: download such patches from git repo
mkdir -p tmp-patches
cp -rv $local_patch_dir/*.patch tmp-patches
cp -rv $local_patch_dir/${distro}/*.patch tmp-patches || true
cp -rv $local_patch_dir/${branch}/*.patch tmp-patches || true
if [[ $distro =~ rhel8 ]]; then
	kernel_release=$(sudo dnf repoquery --repo ${kernel_repoid} \
	--latest-limit=1  --qf '%{RELEASE}' kernel.${arch})
    sed -i "s/KRELEASE/${kernel_release}/" tmp-patches/*.patch
fi
git apply -v tmp-patches/*.patch

# releae number +1
version=$(sudo dnf repoquery --repo ${lustre_repoid} \
	--latest-limit=1  --qf '%{VERSION}-%{RELEASE}' lustre.${arch})
version_num=${version%%-*}
release_num=${version##*-}
release_num=${release_num%%.*}
cur_version_num=$(bash LUSTRE-VERSION-GEN)
if [[ "$version_num" != "$cur_version_num" ]]; then
	release_num="" # reset
fi
if [[ -n "${release_num}" ]];then
	(( release_num++ ))
	sed -i "s/Release: 1/Release: ${release_num}/" lustre.spec.in
fi

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
	--lustre=$build_dir/lustre-release/$code_base \
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

cat <<EOF | sudo tee ${rpm_repo_file}
[${build_what}]
name=${build_what}
baseurl=${rpm_repo_url}
enabled=1
gpgcheck=0
EOF

echo $commit_id > $last_build_file
echo "Finish build $build_id. branch: $branch, commit ID: $commit_id"
