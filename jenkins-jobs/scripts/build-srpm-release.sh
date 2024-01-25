#!/bin/bash

set -xe

version=${VERSION:-'4.0-20.el8'}
workspace=${WORKSPACE:-"/home/jenkins/agent/build"}
build_id=${BUILD_ID:-'001'}
dist=${DIST:-'oe2203sp1'}
what=${WHAT:-'dbench'}

arch=$(arch)
cache_dir="/home/jenkins/agent/cache"
first_ch=${what:0:1}
subname="${what}-${dist}"
rpm_repo_dir="${what}/${dist}/${arch}"
last_build_file="${cache_dir}/build/lastbuild-${subname}"
build_cache_dir=$(dirname $last_build_file)
build_dir="${workspace}/build-${subname}-${build_id}"
srpm_cache_dir="${cache_dir}/src/${what}"
rpm_repo="/home/jenkins/agent/rpm-repo/${rpm_repo_dir}"
rpm_repo_base_url="https://uk.linaro.cloud/repo"
rpm_repo_url="${rpm_repo_base_url}/${rpm_repo_dir}"
rpm_repo_file="${rpm_repo}/${what}.repo"

top_dir="${build_dir}/rpmbuild"
spec_file="${what}.spec"

case "$what" in
    "iozone")
	srpm_download_url="https://download1.rpmfusion.org/nonfree/fedora/development/rawhide/Everything/source/SRPMS/${first_ch}"
        ;;
    "kernel")
	srpm_download_url="https://download.rockylinux.org/pub/rocky/8/BaseOS/source/tree/Packages/${first_ch}"
	version=$(sudo dnf repoquery --latest-limit=1 \
		--qf '%{VERSION}-%{RELEASE}' kernel.${arch})
        ;;
    *)
        srpm_download_url="https://download.fedoraproject.org/pub/epel/8/Everything/SRPMS/Packages/${first_ch}"
        ;;
esac

srpm="${what}-${version}.src.rpm"

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
	echo "The same build ${what} version $version skip build."
	exit 0
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
		pkgs+=(distcc)
	fi
	sudo dnf config-manager --set-enabled devel
	sudo dnf install -y epel-release
fi
sudo dnf update -y || true
pkgs+=(ccache gcc make autoconf automake libtool rpm-build wget createrepo)
pkgs+=(gcc-c++ popt-devel dos2unix)
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
build_options=""
if [[ "$what" == "pdsh" ]] && [[ $dist =~ oe ]]; then
	sudo dnf install -y libgenders-devel  perl-generators readline-devel
	build_options="--nodeps --without nodeupdown --without torque --without slurm"
else
	sudo dnf builddep -y --srpm ${srpm_cache_dir}/$srpm
fi

# Build
echo "Build rpms..."
# (TODO): download config from github
if [[ "$what" == "kernel" ]] && [[ $dist =~ el8 ]]; then
    rpm -ivh --define "_topdir $top_dir" ${srpm_cache_dir}/$srpm
    kernel_src_dir="${cache_dir}/src/kernel"
    cp -vf $kernel_src_dir/kernel-4.18-rhel8.8-aarch64-4k.config \
  	$top_dir/SOURCES/kernel-aarch64.config

    append_version="_4k"
    build_options="--without debug --without kabichk"

    rpmbuild --define "_topdir $top_dir" \
	${build_options} \
	${append_version:+--define "buildid $append_version"} \
	-ba SPECS/${spec_file}
else
    rpmbuild --define "_topdir $top_dir" \
	${build_options} \
	--rebuild -ra ${srpm_cache_dir}/$srpm
fi


# Release
echo "Re-generate rpm repo..."
sudo mkdir -p $rpm_repo
sudo rm -rfv $rpm_repo/*.rpm
sudo mv -fv $top_dir/RPMS/aarch64/*.aarch64.rpm $rpm_repo
sudo mv -fv $top_dir/SRPMS/*.src.rpm $rpm_repo ||
	sudo cp -v ${srpm_cache_dir}/$srpm $rpm_repo
sudo createrepo --update $rpm_repo

cat <<EOF | sudo tee ${rpm_repo_file}
[${what%%+*}]
name=${what}
baseurl=${rpm_repo_url}
enabled=1
gpgcheck=0
EOF

echo $version > $last_build_file
sudo cp -fv $last_build_file $rpm_repo/current-build.txt
echo "Finish ${what} build $build_id. original version: $version, new version: ${version%.*}.${dist}}"
