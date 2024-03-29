from ast import literal_eval
from concurrent import futures
from datetime import datetime
import json
import os
from os.path import exists as path_exists, join as path_join
import random
import shutil
import string
import subprocess
import sys
import time

import paramiko

import const
from const import LOG


def host_name_gen():
    # Generate 8-bit strings from a-zA-Z0-9
    return ''.join(random.sample(string.ascii_letters + string.digits, 8))


class Provision():
    def __init__(self, provision_new, dist='el8',
                 arch='aarch64', lustre_branch='master',
                 kernel_version=None,
                 rpm_repo_host="https://uk.linaro.cloud/repo"):
        self.node_map = None
        self.cluster_dir = None
        self.node_ip_list = []
        self.ssh_user = const.CLOUD_INIT_CHECK_USER
        self.ssh_clients = {}
        self.clusters_top_dir = const.TEST_WORKSPACE
        self.provision_new = provision_new
        self.dist = dist
        self.arch = arch
        self.lustre_branch = lustre_branch
        self.rpm_repo_host = rpm_repo_host
        self.kernel_version = kernel_version
        if provision_new:
            LOG.info("Prepare to provision the new cluster")
            self.prepare_tf_conf()
        # checking args
        if not (dist.startswith('el') or dist.startswith('oe')):
            msg = f"{dist} is not support!"
            sys.exit(msg)

    def ssh_connection(self, ip):
        private_key = \
            paramiko.RSAKey.from_private_key_file(const.SSH_PRIVATE_KEY)
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh_client.connect(hostname=ip,
                           port=22,
                           username=self.ssh_user,
                           pkey=private_key)

        # # Test SSH connection
        # stdin, stdout, stderr = ssh_client.exec_command('ls /')
        # error = stderr.read()
        # if error.strip():
        #     LOG.error(error)
        #     return

        msg = f"SSH client for IP: {ip} initialization is finished"
        LOG.info(msg)
        return ssh_client

    def ssh_exec(self, ssh_client, cmd):
        # pty make stderr stream into stdout, so we can
        # print stdout and stderr in realtime
        _, stdout, _ = ssh_client.exec_command(cmd, get_pty=True)
        for line in iter(stdout.readline, ""):
            LOG.info(line.strip())

        rc = stdout.channel.recv_exit_status()
        if rc != 0:
            return False
        return True

    def ssh_exec_ret_std(self, ssh_client, cmd):
        _, stdout, _ = ssh_client.exec_command(cmd)
        lines = stdout.readlines()
        output = "\n".join(lines)
        return output.strip()

    #
    # Copy the terraform template from the source file to another destination
    #
    def copy_dir(self):
        source_dir = const.TERRAFORM_CONF_TEMPLATE_DIR
        if not path_exists(self.cluster_dir):
            try:
                os.makedirs(self.cluster_dir)
            except OSError:
                msg = f"mkdir failed: {self.cluster_dir}"
                LOG.error(msg)
                raise
        for f in os.listdir(source_dir):
            if f.endswith("tf") or f == "cloud-init":
                source_file = path_join(source_dir, f)
                target_file = path_join(self.cluster_dir, f)
                if not path_exists(target_file) or (
                        path_exists(target_file) and (
                        os.path.getsize(target_file) !=
                        os.path.getsize(source_file))):
                    with open(target_file, "wb") as fout:
                        with open(source_file, "rb") as fin:
                            fout.write(fin.read())

    #
    # Prepare the terraform configuration, all the args are defined at
    # TERRAFORM_VARIABLES_JSON
    #
    def prepare_tf_conf(self):
        cluster_name = const.LUSTRE_CLUSTER_PREFIX + host_name_gen().lower()
        self.cluster_dir = path_join(self.clusters_top_dir, self.dist,
                                     cluster_name)
        self.copy_dir()

        # rename Terraform Resources vars to duplicated name between
        # clusters
        vm_image = const.VM_IMAGES[self.dist]
        tf_vars = {
            const.TF_VAR_VM_IMAGE: vm_image
        }

        # node name
        for num in range(1, const.MAX_NODE_NUM+1):
            var = f"{const.TF_VAR_NODE_PREFIX}{num:02d}"
            value = f"{cluster_name}-{num:02d}"
            tf_vars[var] = value

        # port name
        for num in range(1, const.MAX_CLIENT_NUM+1):
            var = f"{const.TF_VAR_CLIENT_PORT_PREFIX}{num:02d}_port"
            value = f"{cluster_name}-client{num:02d}-port"
            tf_vars[var] = value
        for num in range(1, const.MAX_MDS_NUM+1):
            var = f"{const.TF_VAR_MDS_PORT_PREFIX}{num:02d}_port"
            value = f"{cluster_name}-mds{num:02d}-port"
            tf_vars[var] = value
        for num in range(1, const.MAX_OST_NUM+1):
            var = f"{const.TF_VAR_OST_PORT_PREFIX}{num:02d}_port"
            value = f"{cluster_name}-ost{num:02d}-port"
            tf_vars[var] = value

        # volume name
        for num in range(1, const.MAX_MDS_VOL_NUM+1):
            var = f"{const.TF_VAR_MDS_VOL_PREFIX}{num:02d}"
            value = f"{cluster_name}-mds-volume{num:02d}"
            tf_vars[var] = value
        for num in range(1, const.MAX_OST_VOL_NUM+1):
            var = f"{const.TF_VAR_OST_VOL_PREFIX}{num:02d}"
            value = f"{cluster_name}-ost-volume{num:02d}"
            tf_vars[var] = value

        # Write the file to json file
        with open(path_join(self.cluster_dir, const.TERRAFORM_VARIABLES_JSON), "w") as f:
            json.dump(tf_vars, f)

    #
    # Terraform Init command
    #
    def terraform_init(self):
        os.chdir(self.cluster_dir)
        if path_exists(const.TERRAFORM_VARIABLES_JSON):
            with subprocess.Popen([const.TERRAFORM_BIN, 'init'],
                                  stdout=subprocess.PIPE,
                                  stderr=subprocess.STDOUT) as p:
                self.realtime_output(p)
                if p.returncode == 0:
                    LOG.info('Terraform init success')
                    return True

                LOG.error('Terraform init failed')
                return False

        msg = "Terraform init failed: terraform args does not exist: "\
            f"{const.TERRAFORM_VARIABLES_JSON}"
        LOG.error(msg)
        return False

    def realtime_output(self, p):
        while p.poll() is None:
            line = p.stdout.readline()
            line = line.strip()
            if line:
                LOG.info(line.decode('utf-8'))

    #
    # Terraform Apply
    #
    def terraform_apply(self):
        os.chdir(self.cluster_dir)
        if self.terraform_init():
            n = 0  # muliple tries
            while n < 5:
                with subprocess.Popen([const.TERRAFORM_BIN, 'apply', '-auto-approve'],
                                      stdout=subprocess.PIPE,
                                      stderr=subprocess.STDOUT) as p:
                    self.realtime_output(p)
                    n += 1
                    if p.returncode == 0:
                        msg = f"Terraform apply success, try {n} times"
                        LOG.info(msg)
                        return True
            msg = f"Terraform apply failed, try {n} times"
            LOG.error(msg)
        return False

    #
    # Terraform destroy command
    #
    def terraform_destroy(self):
        os.chdir(self.cluster_dir)
        with subprocess.Popen([const.TERRAFORM_BIN, 'destroy', '-auto-approve'],
                              stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT) as p:
            self.realtime_output(p)
            if p.returncode == 0:
                LOG.info('Terraform destroy success')
                shutil.rmtree(self.cluster_dir, ignore_errors=True)
                return True

            LOG.error('Terraform destroy failed')
            return False

    #
    # After configuration, write the node hostname/IP/TYPE to NODE_INFO
    #
    def gen_node_info(self):
        result = subprocess.check_output([const.TERRAFORM_BIN, 'output'])
        lustre_node_info = result.splitlines()
        client01_ip = None
        client01_hostname = None
        client02_ip = None
        client02_hostname = None
        mds01_ip = None
        mds01_hostname = None
        mds02_ip = None
        mds02_hostname = None
        ost01_ip = None
        ost01_hostname = None

        for info in lustre_node_info:
            node_info_str = info.decode('utf-8')
            node_info = node_info_str.split(" = ")
            if node_info[0] == const.TERRAFORM_CLIENT01_IP:
                client01_ip = literal_eval(node_info[1])
                self.node_ip_list.append(client01_ip)
            elif node_info[0] == const.TERRAFORM_CLIENT02_IP:
                client02_ip = literal_eval(node_info[1])
                self.node_ip_list.append(client02_ip)
            elif node_info[0] == const.TERRAFORM_MDS01_IP:
                mds01_ip = literal_eval(node_info[1])
                self.node_ip_list.append(mds01_ip)
            elif node_info[0] == const.TERRAFORM_MDS02_IP:
                mds02_ip = literal_eval(node_info[1])
                self.node_ip_list.append(mds02_ip)
            elif node_info[0] == const.TERRAFORM_OST01_IP:
                ost01_ip = literal_eval(node_info[1])
                self.node_ip_list.append(ost01_ip)
            elif node_info[0] == const.TERRAFORM_CLIENT01_HOSTNAME:
                client01_hostname = literal_eval(node_info[1])
                client01_hostname = client01_hostname.lower()
            elif node_info[0] == const.TERRAFORM_CLIENT02_HOSTNAME:
                client02_hostname = literal_eval(node_info[1])
                client02_hostname = client02_hostname.lower()
            elif node_info[0] == const.TERRAFORM_MDS01_HOSTNAME:
                mds01_hostname = literal_eval(node_info[1])
                mds01_hostname = mds01_hostname.lower()
            elif node_info[0] == const.TERRAFORM_MDS02_HOSTNAME:
                mds02_hostname = literal_eval(node_info[1])
                mds02_hostname = mds02_hostname.lower()
            elif node_info[0] == const.TERRAFORM_OST01_HOSTNAME:
                ost01_hostname = literal_eval(node_info[1])
                ost01_hostname = ost01_hostname.lower()
            else:
                sys.exit("The node info is not correct.")

        # Generate the NODE_INFO, which will be used in the future process
        with open(path_join(self.cluster_dir, const.NODE_INFO), 'w+') as node_conf:
            node_conf.write(client01_hostname + ' ' +
                            client01_ip + ' ' + const.CLIENT + '\n')
            node_conf.write(client02_hostname + ' ' +
                            client02_ip + ' ' + const.CLIENT + '\n')
            node_conf.write(mds01_hostname + ' ' +
                            mds01_ip + ' ' + const.MDS + '\n')
            node_conf.write(mds02_hostname + ' ' +
                            mds02_ip + ' ' + const.MDS + '\n')
            node_conf.write(ost01_hostname + ' ' +
                            ost01_ip + ' ' + const.OST + '\n')

    #
    # Check the node is alive and the cloud-init is finished.
    # Using SSH, all the ssh keys credential is the same
    #
    def node_check(self):
        if len(self.node_ip_list) == const.MAX_NODE_NUM:
            ssh_check_cmd = "ls -l " + const.CLOUD_INIT_FINISH
            while True:
                for ip in self.node_ip_list:
                    try:
                        ssh_client = self.ssh_connection(ip)
                        if ssh_client is not None:
                            if ssh_client not in self.ssh_clients:
                                self.ssh_clients[ip] = ssh_client
                        else:
                            LOG.info("The node reboot is not finished")
                    except paramiko.ssh_exception.NoValidConnectionsError:
                        msg = f"can not connect to the node: {ip}"
                        LOG.info(msg)
                    except paramiko.ssh_exception.SSHException:
                        msg = "Error reading SSH protocol banner[Errno 104] " \
                            f"Connection reset by peer: {ip}"
                        LOG.info(msg)
                    except TimeoutError:
                        msg = f"Timeout on  connect to the node: {ip}"
                        LOG.info(msg)

                ready_clients = len(self.ssh_clients)
                if ready_clients == const.MAX_NODE_NUM:
                    LOG.info("All the clients is ready")
                    break
                msg = f"Ready clients are: {ready_clients}"
                LOG.info(msg)
                time.sleep(10)

            t1 = datetime.now()
            node_status = []
            LOG.info(
                "====================check cloud init=======================")
            while (datetime.now() - t1).seconds <= const.CLOUD_INIT_TIMEOUT:
                for ip, client in self.ssh_clients.items():
                    if ip in node_status:
                        continue
                    if self.ssh_exec(client, ssh_check_cmd):
                        node_status.append(ip)
                    else:
                        msg = f"The cloud-init process is not finished: {ip}"
                        LOG.info(msg)
                ready_node = len(node_status)
                msg = f"Ready nodes: {node_status}"
                LOG.info(msg)
                if ready_node == const.MAX_NODE_NUM:
                    break
                time.sleep(10)

            if len(node_status) == const.MAX_NODE_NUM:
                return True

            msg = "The cloud-init processes of nodes are not totally ready, " \
                f"Only ready: {len(node_status)}"
            LOG.error(msg)
            return False

        LOG.error("Cluster node count is not right")
        return False

    def clean_node_info(self):
        with subprocess.Popen(['rm', '-rf', path_join(self.cluster_dir, const.NODE_INFO)],
                              stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT) as p:
            self.realtime_output(p)
            if p.returncode == 0:
                LOG.info('Cluster clean success')
                return True

            LOG.error('Cluster clean failed')
            return False

    #
    # The main process
    # For stability, we can set provision_new to False, and then set the
    # terraform dir then each running will use the same 5 nodes for test.
    # Note: This will not install all the packages, so we needs to do some
    # procedures which is in cloud-init to another function.
    #
    def provision(self, cluster_dir=None):
        if not self.provision_new:
            msg = f"Prepare to use the exist cluster: {cluster_dir}"
            LOG.info(msg)
            self.cluster_dir = cluster_dir
            self.clean_node_info()

        msg = f"tf conf dir: {self.cluster_dir}"
        LOG.info(msg)
        tf_return = self.terraform_apply()
        if not tf_return:
            return False
        self.gen_node_info()

        # check the file is there
        if path_exists(path_join(self.cluster_dir, const.NODE_INFO)):
            if self.node_check():
                LOG.info("Install Lustre from the repo...")
                return self.node_operate()

            LOG.error("The node_check is failed")
            return False

        msg = "The config file does not exist: " \
            f"{path_join(self.cluster_dir, const.NODE_INFO)}"
        LOG.error(msg)
        return False

    def run_cmd(self, node, client, cmd):
        msg = f"{node}:  {cmd}"
        LOG.info(msg)
        if self.ssh_exec(client, cmd):
            msg = f"{node}:  Success run cmd: {cmd}"
            LOG.info(msg)
        else:
            msg = f"{node}:  Failed run cmd: {cmd}"
            sys.exit(msg)

    def run_cmd_ret_std(self, node, client, cmd):
        LOG.info(node + ":  " + cmd)
        return self.ssh_exec_ret_std(client, cmd)

    def run_cmds(self, node, client, cmds):
        for cmd in cmds:
            self.run_cmd(node, client, cmd)

    def add_rpm_repo(self, node, client, what):
        if what == 'lustre':
            rpm_repo = \
                f"{self.rpm_repo_host}/{what}/{self.lustre_branch}/" \
                f"{self.dist}/{self.arch}/{what}.repo"
        else:
            rpm_repo = \
                f"{self.rpm_repo_host}/{what}/" \
                f"{self.dist}/{self.arch}/{what}.repo"

        cmd = f"sudo dnf config-manager --add-repo {rpm_repo}"
        self.run_cmd(node, client, cmd)

    def install_tool_by_sh(self, node, client, what):
        sh_dir_url = "https://raw.githubusercontent.com/" \
            "Linaro/lustretest/main/lustretest"
        install_sh = f"install_{what}.sh"

        cmd = "sudo dnf install -y wget"
        self.run_cmd(node, client, cmd)
        cmd = f"(wget -O {install_sh} {sh_dir_url}/{install_sh} && " \
            f"bash {install_sh})"
        self.run_cmd(node, client, cmd)

    def install_tools(self, node, client):
        self.add_rpm_repo(node, client, 'iozone')
        if self.dist.startswith("oe"):
            self.add_rpm_repo(node, client, 'pdsh')
            self.add_rpm_repo(node, client, 'dbench')
            self.add_rpm_repo(node, client, 'bonnie++')

        tool_pkgs = "pdsh pdsh-rcmd-ssh net-tools dbench fio " \
            "bc attr gcc iozone rsync bonnie++ chrony"
        cmd = f"sudo dnf install -y {tool_pkgs}"
        self.run_cmd(node, client, cmd)
        cmd = f"sudo dnf update -y {tool_pkgs}"
        self.run_cmd(node, client, cmd)

        self.install_tool_by_sh(node, client, 'pjdfstest')
        self.install_tool_by_sh(node, client, 'ior')

    def install_latest_pkg(self, node, client, what):
        version = None
        # not need to add kernel repo, use official provided
        if what == 'kernel':
            repo_option = ''
            version = self.kernel_version
        else:
            self.add_rpm_repo(node, client, what)
            repo_option = f"--repo {what}"

        if not version:
            cmd = f"sudo dnf repoquery {repo_option} --latest-limit=1 " \
                f"--qf '%{{VERSION}}-%{{RELEASE}}' {what}.{self.arch}"
            version = self.run_cmd_ret_std(node, client, cmd)
        if not version:
            msg = f"{node}: {what} version is empty! Failed run cmd: {cmd}"
            sys.exit(msg)

        if what == 'lustre':
            pkgs = f"lustre-{version} " \
                f"lustre-iokit-{version} " \
                f"lustre-osd-ldiskfs-mount-{version} " \
                f"lustre-resource-agents-{version} " \
                f"lustre-tests-{version} " \
                f"kmod-lustre-{version} " \
                f"kmod-lustre-osd-ldiskfs-{version} " \
                f"kmod-lustre-tests-{version}"
        else:
            pkgs = f"{what}-{version}"

        cmd = f"sudo dnf install -y {pkgs}"
        self.run_cmd(node, client, cmd)
        if what == 'kernel':
            kernel_path = f"/boot/vmlinuz-{version}.{self.arch}"
            cmd = f"sudo grubby --set-default={kernel_path}"
            self.run_cmd(node, client, cmd)

    def install_test_pkgs(self, node, client):
        cmd = "sudo dnf install -y dnf-plugins-core bc"
        self.run_cmd(node, client, cmd)

        cmds = []
        if self.dist == 'el8':
            cmd = "sudo dnf config-manager --set-enabled ha"
            cmds.append(cmd)
            cmd = "sudo dnf config-manager --set-enabled powertools"
            cmds.append(cmd)
        if self.dist == 'el9':
            cmd = "sudo dnf config-manager --set-enabled highavailability"
            cmds.append(cmd)
            cmd = "sudo dnf config-manager --set-enabled crb"
            cmds.append(cmd)
        cmd = "sudo dnf install epel-release -y || true"
        cmds.append(cmd)
        cmd = "sudo dnf update -y --refresh || true"
        cmds.append(cmd)
        self.run_cmds(node, client, cmds)

        self.install_latest_pkg(node, client, 'kernel')
        self.install_latest_pkg(node, client, 'e2fsprogs')
        self.install_latest_pkg(node, client, 'lustre')
        self.install_tools(node, client)
        return True

    def node_operate(self):
        with futures.ThreadPoolExecutor(max_workers=const.MAX_NODE_NUM) as executor:
            future_to_node = {
                executor.submit(self.install_test_pkgs, node, client): node
                for node, client in self.ssh_clients.items()
            }
            for future in futures.as_completed(future_to_node):
                node = future_to_node[future]
                try:
                    data = future.result()
                except SystemExit as e:
                    msg = f"{node}: install lustre failed!! \n{e}"
                    LOG.info(msg)
                    return False
                except:
                    msg = f"{node}: install lustre failed!!"
                    LOG.info(msg)
                    raise
                msg = f"{node}: install lustre success. result={data}"
                LOG.info(msg)

        for node, client in self.ssh_clients.items():
            self.node_volume_check(node, client)
        return True

    def node_volume_check(self, node, client):
        check_volume = 'lsblk'
        msg = f"The node {node} volumes info: "
        LOG.info(msg)
        self.ssh_exec(client, check_volume)

    def get_cluster_dir(self):
        return self.cluster_dir
