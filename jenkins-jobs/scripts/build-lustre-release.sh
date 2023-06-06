#!/bin/bash

set -xe

branch=${BRANCH:-'master'}
build_id=${BUILD_ID:-'001'}
build_type=${BUILD_TYPE:-'release'}
build_linux=${BUILD_LINUX:-'no'}
extra_patches=${EXTRA_PATCHES}
target=${TARGET:-'4.18-rhel8.8'}
distro=${TARGET##*-}

build_dir=${WORKSPACE}/build-$build_id
kernel_src_dir="/home/jenkins/src/kernel"
linux_dir=$(find  $kernel_src_dir/reused/ -name .config|xargs dirname)
remote_repo="git://git.whamcloud.com/fs/lustre-release.git"
local_repo="/home/jenkins/git/lustre-release.git"
# RPM repo for Lustre and e2fsprogs, Lustre repo also include kernel packages
rpm_repo=/usr/share/nginx/html/repo/lustre

echo "Cleanup workspace dir"
rm -rf ${WORKSPACE}/*

echo "Generate the release tar bz..."
mkdir -p $build_dir
cd $build_dir
git clone --branch $branch --reference $local_repo $remote_repo
cd lustre-release
commit_id=$(git rev-parse --short HEAD)

# Apply extra patches that haven't been merged into the branch.
if [[ -n ${extra_patches} ]]; then
    echo ${extra_patches} | sed -n 1'p' | tr ',' '\n' | while read patch; do
        curl \
            "https://review.whamcloud.com/changes/${patch}/revisions/current/patch" \
            | base64 -d | git apply -v -3
    done
fi

# (TODO): download config from github
cp $kernel_src_dir/kernel-4.18.0-4.18-rhel8.5-aarch64.config-debug \
		$build_dir/lustre-release/lustre/kernel_patches/kernel_configs/

# Generate the source tar file
sh autogen.sh
./configure -C --enable-dist
make dist
code_base=$(find . -name "lustre*tar.gz")
code_base=$(basename $code_base)

echo "Build options prepare..."
build_opts=""
if [[ "$build_type" == "debug" ]]; then
	build_opts+="--enable-kernel-debug "
	build_opts+="--disable-zfs "
fi

if [[ "$build_linux" == "yes" ]]; then
    # Build along with Linux kernel
	build_opts+="--kerneldir=$kernel_src_dir "
else
    # Build with exist Linux kernel
	build_opts+="--with-linux=$linux_dir "
	build_opts+="--disable-zfs "
fi

echo "Build rpms..."
cd $build_dir
$build_dir/lustre-release/contrib/lbuild/lbuild \
	--lustre=$build_dir/lustre-release/$code_base  \
	--target=$target --distro=$distro \
	--ccache --extraversion=$build_id $build_opts

echo "Re-generate rpm repo..."
if [[ "$build_linux" == "yes" ]]; then
	# copy linux src for reused building.
	rm -rf $kernel_src_dir/reused
	mv -f $build_dir/reused $kernel_src_dir
    # Remove all the Lustre packages and Linux packages
    sudo rm -rfv $rpm_repo/*.rpm
else
    # Remove all the Lustre packages
    sudo rm -rfv $rpm_repo/*.el8.aarch64.rpm
fi

sudo mv -f $build_dir/RPMS/aarch64/*.aarch64.rpm $rpm_repo
sudo createrepo --update $rpm_repo

echo "Finish build. branch: $branch, commit ID: $commit_id"
