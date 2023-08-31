#!/bin/bash

set -xe

workspace=${WORKSPACE:-"/home/jenkins/agent/build"}
branch=${BRANCH:-'master'}
build_id=${BUILD_ID:-'001'}
extra_patches=${EXTRA_PATCHES}
git_remote_repo=${GIT_REPO:-'git://git.whamcloud.com/fs/lustre-release.git'}
distro=${DISTRO:-'rhel8.8'}
dist_main=${distro%sp*}

co_branch=$branch
if [[ $distro =~ rhel8 ]]; then
	target="4.18-${distro}"
	dist="el8"
elif [[ $distro =~ rhel9 ]]; then
	target="5.14-${distro}"
	dist="el9"
elif [[ $distro =~ oe2003 ]]; then
	target="4.19-${distro}"
	dist=${distro}
        if [[ $branch =~ b2_15 ]]; then
		co_branch="b2_15-openeuler"
	fi
elif [[ $distro =~ oe2203 ]]; then
	target="5.10-${distro}"
	dist=${distro}
        if [[ $branch =~ b2_15 ]]; then
		co_branch="b2_15-openeuler"
	fi
fi

arch=$(arch)
build_what="lustre"
cache_dir="/home/jenkins/agent/cache"
subname="${build_what}-${branch}-${dist}"
rpm_repo_dir="${build_what}/${branch}/${dist}/${arch}"
last_build_file="${cache_dir}/build/lastbuild-${subname}"
build_cache_dir=$(dirname $last_build_file)
build_dir="${workspace}/build-${subname}-${build_id}"
kernel_src_dir="${cache_dir}/src/kernel"
rpm_repo="/home/jenkins/agent/rpm-repo/${rpm_repo_dir}"
rpm_repo_base_url="https://uk.linaro.cloud/repo"
rpm_repo_url="${rpm_repo_base_url}/${rpm_repo_dir}"
rpm_repo_remote="${rpm_repo_base_url}/${rpm_repo_dir}/${build_what}.repo"
rpm_repo_file="${rpm_repo}/${build_what}.repo"
repoid_base="uk.linaro.cloud_repo"

local_patch_dir="${cache_dir}/src/patches/${build_what}"
git_local_repo="${cache_dir}/git/lustre-release.git"
kernel_rpm_repo_dir="kernel/${dist}/${arch}"
e2fsprogs_rpm_repo_dir="e2fsprogs/${dist}/${arch}"
kernel_rpm_repo="${rpm_repo_base_url}/${kernel_rpm_repo_dir}/kernel.repo"
e2fsprogs_rpm_repo="${rpm_repo_base_url}/${e2fsprogs_rpm_repo_dir}/e2fsprogs.repo"
release_num=""

# check dist rpm macro existence
dist_macro=$(rpm -E %{?dist})
if [[ -z "$dist_macro" ]]; then
	echo "%dist .$dist" >> ~/.rpmmacros
fi

echo "Cleanup workspace dir"
rm -rf ${workspace}/build-${subname}-*
sudo rm -rf /etc/yum.repos.d/${build_what}.repo

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
		sudo dnf config-manager --add-repo $kernel_rpm_repo
		pkgs+=(distcc redhat-lsb-core)
	fi
	sudo dnf install -y epel-release
	pkgs+=(yum-utils)
	sudo dnf update -y
elif [[ $dist =~ oe ]]; then
	if [[ $dist =~ oe2003 ]]; then
		sudo dnf install -y \
			https://repo.openeuler.org/openEuler-22.03-LTS-SP2/everything/aarch64/Packages/kernel-rpm-macros-30-35.oe2203sp2.aarch64.rpm
	fi
	sudo dnf install -y openeuler-lsb
fi

sudo dnf config-manager --add-repo $e2fsprogs_rpm_repo
sudo dnf config-manager --add-repo $rpm_repo_remote || true
pkgs+=(git ccache gcc make autoconf automake libtool rpm-build wget createrepo)
pkgs+=(audit-libs-devel binutils-devel elfutils-devel kabi-dw ncurses-devel newt-devel numactl-devel \
	openssl-devel pciutils-devel perl perl-devel python3-docutils xmlto xz-devel \
	libcap-devel libcap-ng-devel libyaml libblkid-devel libtirpc-devel \
	llvm-devel clang)
pkgs+=(libtirpc-devel libblkid-devel libuuid-devel libudev-devel openssl-devel libaio-devel \
	libattr-devel python3 python3-devel python3-setuptools \
	python3-cffi libffi-devel git ncompress libcurl-devel keyutils-libs-devel)
pkgs+=(python3-packaging texinfo openmpi openmpi-devel)
sudo dnf install -y ${pkgs[@]}
sudo ln -s $(which ccache) /usr/local/bin/gcc &&
sudo ln -s $(which ccache) /usr/local/bin/g++ &&
sudo ln -s $(which ccache) /usr/local/bin/cc &&
sudo ln -s $(which ccache) /usr/local/bin/c++
. /etc/profile.d/modules.sh &&
module load mpi/openmpi-${arch}

# Prepare
echo "Generate the release tar bz..."
mkdir -p $build_dir
cd $build_dir
git clone --branch $co_branch --reference $git_local_repo $git_remote_repo
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
            | base64 -d | git apply -v
    done
fi

# Apply more extra patches from local cache dir which are only for build not for upstream
# TODO: download such patches from git repo
mkdir -p tmp-patches
cp -rv $local_patch_dir/*.patch tmp-patches || true
cp -rv $local_patch_dir/${branch}/*.patch tmp-patches || true
cp -rv $local_patch_dir/${dist_main}/*.patch tmp-patches || true
cp -rv $local_patch_dir/${dist_main}/${branch}/*.patch tmp-patches || true
cp -rv $local_patch_dir/${dist}/*.patch tmp-patches || true
cp -rv $local_patch_dir/${dist}/${branch}/*.patch tmp-patches || true
repo_option=""
if [[ $distro =~ rhel8 ]]; then
	repo_option="--repo kernel"
fi
kernel_release=$(sudo dnf repoquery  ${repo_option} \
	--latest-limit=1  --qf '%{RELEASE}' kernel.${arch})
sed -i "s/KRELEASE/${kernel_release}/" tmp-patches/*.patch
git apply -v tmp-patches/*.patch

# releae number +1
version=$(sudo dnf repoquery --repo lustre \
	--latest-limit=1  --qf '%{VERSION}-%{RELEASE}' lustre.${arch}) || true
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
build_distro=$(echo ${distro}| sed -E -e 's/(sp[0-9])+/.\1/')
$build_dir/lustre-release/contrib/lbuild/lbuild \
	--lustre=$build_dir/lustre-release/$code_base \
	--target=$target --distro=$build_distro \
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
echo "Finish build $build_id. branch: $co_branch, commit ID: $commit_id"
