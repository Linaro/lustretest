import paramiko
from paramiko import ssh_exception
import random
import string
import os
import json
import subprocess
from os.path import exists
import const
import time
from datetime import datetime
import logging
import threading


class Provisioner(object):
    def __init__(self, logger):
        self.logger = logger
        self.node_map = None
        self.tf_conf_dir = None
        self.node_ip_list = []
        self.ssh_user = const.DEFAULT_SSH_USER
        self.ssh_clients = []

    def _debug(self, msg, *args):
        self.logger.debug(msg, *args)

    def _error(self, msg, *args):
        self.logger.error(msg, *args)

    def host_name_gen(self):
        # Generate 8-bit strings from a-zA-Z0-9
        return ''.join(random.sample(string.ascii_letters + string.digits, 8))

    def ssh_connection(self, ip):
        private_key = paramiko.RSAKey.from_private_key_file(const.SSH_PRIVATE_KEY)
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            ssh_client.connect(hostname=ip, port=22, username=self.ssh_user, pkey=private_key)
        except ssh_exception.NoValidConnectionsError as e:
            self._debug("Not yet connected to this node: " + e)
            return

        # Test SSH connection
        stdin, stdout, stderr = ssh_client.exec_command('ls /')
        error = stderr.read()
        if error.strip():
            self._error(error)
            return

        self._debug("SSH client for IP: " + ip + " initialization is finished")
        return ssh_client

    def ssh_close(self, ssh_client):
        ssh_client.close()

    def ssh_exec(self, ssh_client, cmd):
        # Test SSH connection
        stdin, stdout, stderr = ssh_client.exec_command(cmd)
        while True:
            line = stdout.readline()
            if not line:
                break
            print(line)
        error = stderr.read()
        if error.strip():
            self._error(error)
            return False
        return True

    #
    # Copy the terraform template from the source file to another destination
    #
    def copy_dir(self, test_name):
        tf_conf_dir = const.TERRAFORM_CONF_DIR + test_name
        source_dir = const.TERRAFORM_CONF_TEMPLATE_DIR
        if not os.path.exists(tf_conf_dir):
            try:
                os.mkdir(tf_conf_dir)
            except OSError:
                self._error("mkdir failed: " + tf_conf_dir)
        for f in os.listdir(source_dir):
            if f.endswith("tf") or f == "cloud-init":
                source_file = os.path.join(source_dir, f)
                target_file = os.path.join(tf_conf_dir, f)
                if not os.path.exists(target_file) or (
                        os.path.exists(target_file) and (
                        os.path.getsize(target_file) != os.path.getsize(source_file))):
                    open(target_file, "wb").write(open(source_file, "rb").read())

    #
    # Prepare the terraform configuration, all the args are defined at TERRAFORM_VARIABLES_JSON
    #
    def prepare_tf_conf(self):
        test_hash = self.host_name_gen()
        test_name = "lustre-" + test_hash
        self.copy_dir(test_name)
        self.tf_conf_dir = const.TERRAFORM_CONF_DIR + test_name + "/"

        network_port_prefix = "lustre_" + test_hash
        tf_vars = {
            "node01": test_name + "-01",
            "node02": test_name + "-02",
            "node03": test_name + "-03",
            "node04": test_name + "-04",
            "node05": test_name + "-05",
            "lustre_client01_port": network_port_prefix + "_client01_port",
            "lustre_client02_port": network_port_prefix + "_client02_port",
            "lustre_mds01_port": network_port_prefix + "_mds01_port",
            "lustre_mds02_port": network_port_prefix + "_mds02_port",
            "lustre_ost01_port": network_port_prefix + "_ost01_port"
        }
        # Write the file to json file
        with open(self.tf_conf_dir + const.TERRAFORM_VARIABLES_JSON, "w") as f:
            json.dump(tf_vars, f)

    #
    # Terraform Init command
    #
    def terraform_init(self):
        os.chdir(self.tf_conf_dir)
        if os.path.exists(const.TERRAFORM_VARIABLES_JSON):
            p = subprocess.Popen([const.TERRAFORM_BIN, 'init'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            self.realtime_output(p)
            if p.returncode == 0:
                self._debug('Terraform init success')
                return True
            else:
                self._error('Terraform init failed')
                return False

        else:
            self._error("Terraform init failed: terraform args does not exist: " + const.TERRAFORM_VARIABLES_JSON)
            return False

    def realtime_output(self, p):
        while p.poll() is None:
            line = p.stdout.readline()
            line = line.strip()
            if line:
                print(line.decode('utf-8'))

    #
    # Terraform Apply
    #
    def terraform_apply(self):
        os.chdir(self.tf_conf_dir)
        if self.terraform_init():
            p = subprocess.Popen([const.TERRAFORM_BIN, 'apply', '-auto-approve'],
                                 stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            self.realtime_output(p)
            if p.returncode == 0:
                self._debug('Terraform apply success')
                return True
            else:
                self._error('Terraform apply failed')
                return False
        else:
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
                client01_ip = eval(node_info[1])
                self.node_ip_list.append(client01_ip)
            elif node_info[0] == const.TERRAFORM_CLIENT02_IP:
                client02_ip = eval(node_info[1])
                self.node_ip_list.append(client02_ip)
            elif node_info[0] == const.TERRAFORM_MDS01_IP:
                mds01_ip = eval(node_info[1])
                self.node_ip_list.append(mds01_ip)
            elif node_info[0] == const.TERRAFORM_MDS02_IP:
                mds02_ip = eval(node_info[1])
                self.node_ip_list.append(mds02_ip)
            elif node_info[0] == const.TERRAFORM_OST01_IP:
                ost01_ip = eval(node_info[1])
                self.node_ip_list.append(ost01_ip)
            elif node_info[0] == const.TERRAFORM_CLIENT01_HOSTNAME:
                client01_hostname = eval(node_info[1])
            elif node_info[0] == const.TERRAFORM_CLIENT02_HOSTNAME:
                client02_hostname = eval(node_info[1])
            elif node_info[0] == const.TERRAFORM_MDS01_HOSTNAME:
                mds01_hostname = eval(node_info[1])
            elif node_info[0] == const.TERRAFORM_MDS02_HOSTNAME:
                mds02_hostname = eval(node_info[1])
            elif node_info[0] == const.TERRAFORM_OST01_HOSTNAME:
                ost01_hostname = eval(node_info[1])
            else:
                self._error("The node info is not correct.")

        # Generate the NODE_INFO, which will be used in the future process
        with open(const.NODE_INFO, 'w+') as node_conf:
            node_conf.write(client01_hostname + ' ' + client01_ip + ' ' + const.CLIENT + '\n')
            node_conf.write(client02_hostname + ' ' + client02_ip + ' ' + const.CLIENT + '\n')
            node_conf.write(mds01_hostname + ' ' + mds01_ip + ' ' + const.MDS + '\n')
            node_conf.write(mds02_hostname + ' ' + mds02_ip + ' ' + const.MDS + '\n')
            node_conf.write(ost01_hostname + ' ' + ost01_ip + ' ' + const.OST)

    #
    # Check the node is alive and the cloud-init is finished.
    # Using SSH, all the ssh keys credential is the same
    #
    def node_check(self):

        if len(self.node_ip_list) == 5:
            ssh_check_cmd = "ls -l " + const.CLOUD_INIT_FINISH
            while True:
                for ip in self.node_ip_list:
                    ssh_client = self.ssh_connection(ip)
                    if ssh_client is not None:
                        if ssh_client not in self.ssh_clients:
                            self.ssh_clients.append(ssh_client)

                ready_clients = len(self.ssh_clients)
                if ready_clients == 5:
                    self._debug("All the clients is ready")
                    break
                else:
                    self._debug("Ready clients are: " + str(ready_clients))
                    time.sleep(10)

            t1 = datetime.now()
            node_status = []
            while (datetime.now() - t1).seconds <= const.CLOUD_INIT_TIMEOUT:
                for client in self.ssh_clients:
                    if client in node_status:
                        continue
                    else:
                        if self.ssh_exec(client, ssh_check_cmd):
                            node_status.append(client)
                        else:
                            self._error("The cloud-init process is not finished")
                ready_node = len(node_status)
                self._debug("Ready nodes: " + str(ready_node))
                if ready_node == 5:
                    break
                time.sleep(10)

            if len(node_status) == 5:
                return True
            else:
                self._error("The cloud-init processes of nodes are "
                            "not totally ready, only ready: " + str(len(node_status)))
                return False

        else:
            self._error("Cluster node count is not right")
            return False

    def clean_node_info(self):
        p = subprocess.Popen(['rm', '-rf', const.NODE_INFO],
                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        self.realtime_output(p)
        if p.returncode == 0:
            self._debug('Terraform apply success')
            return True
        else:
            self._error('Terraform apply failed')
            return False

    #
    # The main process
    # For stablity, we can set provision_new to False, and then set the terraform dir
    # then each running will use the same 5 nodes for test.
    # Note: This will not install all the packages, so we needs to do some procedures which
    # is in cloud-init to another function.
    #
    def provision(self):
        provision_new = False
        if provision_new:
            self.prepare_tf_conf()
        else:
            self.tf_conf_dir = const.TERRAFORM_CONF_DIR + const.TERRAFORM_EXIST_CONF

        self.clean_node_info()
        tf_return = self.terraform_apply()
        if tf_return:
            self.gen_node_info()
        else:
            return False

        # check the file is there
        if exists(const.NODE_INFO):
            if self.node_check():
                if not provision_new:
                    self._debug("Does not provision new instances, we need to reinstall Lustre from the repo")
                    return self.node_operate()
                else:
                    return True
            else:
                self._error("The node_check is failed")
                return False
        else:
            self._error("The config file does not exist: " + const.NODE_INFO)
            return False

    def install_lustre(self, client):
        cmd1 = "sudo dnf config-manager --set-enabled ha"
        cmd2 = "sudo dnf config-manager --set-enabled powertools"
        cmd3 = "sudo dnf install epel-release pdsh pdsh-rcmd-ssh net-tools dbench fio linux-firmware -y"
        cmd4 = "sudo dnf --disablerepo = \"*\"  --enablerepo = \"lustre\" install kernel kernel-debuginfo kernel-debuginfo-common-aarch64 kernel-devel kernel-core kernel-headers kernel-modules kernel-modules-extra kernel-tools kernel-tools-libs kernel-tools-libs-devel kernel-tools-debuginfo -y"
        cmd5 = "sudo dnf install e2fsprogs e2fsprogs-devel e2fsprogs-debuginfo e2fsprogs-static e2fsprogs-libs e2fsprogs-libs-debuginfo libcom_err libcom_err-devel libcom_err-debuginfo libss libss-devel libss-debuginfo -y"
        cmd6 = "sudo dnf install lustre lustre-debuginfo lustre-debugsource lustre-devel lustre-iokit lustre-osd-ldiskfs-mount lustre-osd-ldiskfs-mount-debuginfo lustre-resource-agents lustre-tests lustre-tests-debuginfo kmod-lustre kmod-lustre-debuginfo kmod-lustre-osd-ldiskfs kmod-lustre-tests -y"

        if not self.ssh_exec(client, cmd1):
            self._error("cmd1 Failed")
        if not self.ssh_exec(client, cmd2):
            self._error("cmd2 Failed")
        if not self.ssh_exec(client, cmd3):
            self._error("cmd3 Failed")
        if not self.ssh_exec(client, cmd4):
            self._error("cmd4 Failed")
        if not self.ssh_exec(client, cmd5):
            self._error("cmd5 Failed")
        if not self.ssh_exec(client, cmd6):
            self._error("cmd6 Failed")

    def node_operate(self):
        thread_list = []
        for client in self.ssh_clients:
            x = threading.Thread(target=self.install_lustre, args=(client,))
            x.start()
            thread_list.append(x)

        for x in thread_list:
            x.join()
        return True


def main():
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)

    lustre_cluster_provisioner = Provisioner(logger)
    lustre_cluster_provisioner.provision()

if __name__ == "__main__":
    main()
