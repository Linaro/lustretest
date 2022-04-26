import paramiko
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
import sys
import utils
from distutils.util import strtobool


class Provision(object):
    def __init__(self, logger, test_suites_num, provision_new):
        self.logger = logger
        self.node_map = None
        self.tf_conf_dir = None
        self.node_ip_list = []
        self.ssh_user = const.CLOUD_INIT_CHECK_USER
        self.ssh_clients = {}
        self.test_suites_num = test_suites_num
        self.node_conf_dir = utils.find_node_conf_dir(self.test_suites_num)
        self.provision_new = provision_new

    def _debug(self, msg, *args):
        self.logger.debug(msg, *args)

    def _info(self, msg, *args):
        self.logger.info(msg, *args)

    def _error(self, msg, *args):
        self.logger.error(msg, *args)

    def host_name_gen(self):
        # Generate 8-bit strings from a-zA-Z0-9
        return ''.join(random.sample(string.ascii_letters + string.digits, 8))

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
        #     self._error(error)
        #     return

        self._info("SSH client for IP: " +
                   ip + " initialization is finished")
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
            self._info(line.strip())
        error = stderr.read()
        if error.strip():
            self._error(error)
            return False
        return True

    #
    # Copy the terraform template from the source file to another destination
    #
    def copy_dir(self, dir_path, test_name):
        tf_conf_dir = dir_path + test_name
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
                        os.path.getsize(target_file) !=
                        os.path.getsize(source_file))):
                    open(target_file, "wb").write(open(source_file,
                                                       "rb").read())

    #
    # Prepare the terraform configuration, all the args are defined at
    # TERRAFORM_VARIABLES_JSON
    #
    def prepare_tf_conf(self):
        test_hash = self.host_name_gen()
        test_name = const.LUSTRE_CLUSTER_PREFIX + test_hash.lower()
        self.tf_conf_dir = self.node_conf_dir + test_name + "/"
        self.copy_dir(self.node_conf_dir, test_name)

        network_port_prefix = const.LUSTRE_CLUSTER_PREFIX + test_hash
        tf_vars = {
            const.LUSTRE_NODE_01: test_name + const.LUSTRE_NODE_NUM_01,
            const.LUSTRE_NODE_02: test_name + const.LUSTRE_NODE_NUM_02,
            const.LUSTRE_NODE_03: test_name + const.LUSTRE_NODE_NUM_03,
            const.LUSTRE_NODE_04: test_name + const.LUSTRE_NODE_NUM_04,
            const.LUSTRE_NODE_05: test_name + const.LUSTRE_NODE_NUM_05,
            const.LUSTRE_CLIENT01_PORT: network_port_prefix + const.LUSTRE_CLIENT01_PORT_PREFIX,
            const.LUSTRE_CLIENT02_PORT: network_port_prefix + const.LUSTRE_CLIENT02_PORT_PREFIX,
            const.LUSTRE_MDS01_PORT: network_port_prefix + const.LUSTRE_MDS01_PORT_PREFIX,
            const.LUSTRE_MDS02_PORT: network_port_prefix + const.LUSTRE_MDS02_PORT_PREFIX,
            const.LUSTRE_OST01_PORT: network_port_prefix + const.LUSTRE_OST01_PORT_PREFIX
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
            p = subprocess.Popen([const.TERRAFORM_BIN, 'init'],
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.STDOUT)
            self.realtime_output(p)
            if p.returncode == 0:
                self._info('Terraform init success')
                return True
            else:
                self._error('Terraform init failed')
                return False

        else:
            self._error("Terraform init failed: terraform args does not exist: "
                        + const.TERRAFORM_VARIABLES_JSON)
            return False

    def realtime_output(self, p):
        while p.poll() is None:
            line = p.stdout.readline()
            line = line.strip()
            if line:
                self._info(line.decode('utf-8'))

    #
    # Terraform Apply
    #
    def terraform_apply(self):
        os.chdir(self.tf_conf_dir)
        self._info(self.tf_conf_dir)
        if self.terraform_init():
            p = subprocess.Popen([const.TERRAFORM_BIN, 'apply', '-auto-approve'],
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.STDOUT)
            self.realtime_output(p)
            if p.returncode == 0:
                self._info('Terraform apply success')
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
                client01_hostname = client01_hostname.lower()
            elif node_info[0] == const.TERRAFORM_CLIENT02_HOSTNAME:
                client02_hostname = eval(node_info[1])
                client02_hostname = client02_hostname.lower()
            elif node_info[0] == const.TERRAFORM_MDS01_HOSTNAME:
                mds01_hostname = eval(node_info[1])
                mds01_hostname = mds01_hostname.lower()
            elif node_info[0] == const.TERRAFORM_MDS02_HOSTNAME:
                mds02_hostname = eval(node_info[1])
                mds02_hostname = mds02_hostname.lower()
            elif node_info[0] == const.TERRAFORM_OST01_HOSTNAME:
                ost01_hostname = eval(node_info[1])
                ost01_hostname = ost01_hostname.lower()
            else:
                self._error("The node info is not correct.")

        # Generate the NODE_INFO, which will be used in the future process
        with open(self.node_conf_dir + const.NODE_INFO, 'w+') as node_conf:
            node_conf.write(const.TEST_SUITES_PREFIX + ' ' +
                            self.test_suites_num + '\n')
            node_conf.write(client01_hostname + ' ' +
                            client01_ip + ' ' + const.CLIENT + '\n')
            node_conf.write(client02_hostname + ' ' +
                            client02_ip + ' ' + const.CLIENT + '\n')
            node_conf.write(mds01_hostname + ' ' +
                            mds01_ip + ' ' + const.MDS + '\n')
            node_conf.write(mds02_hostname + ' ' +
                            mds02_ip + ' ' + const.MDS + '\n')
            node_conf.write(ost01_hostname + ' ' +
                            ost01_ip + ' ' + const.OST)

    #
    # Check the node is alive and the cloud-init is finished.
    # Using SSH, all the ssh keys credential is the same
    #
    def node_check(self):
        if len(self.node_ip_list) == 5:
            ssh_check_cmd = "ls -l " + const.CLOUD_INIT_FINISH
            while True:
                for ip in self.node_ip_list:
                    try:
                        ssh_client = self.ssh_connection(ip)
                        if ssh_client is not None:
                            if ssh_client not in self.ssh_clients:
                                self.ssh_clients[ip] = ssh_client
                        else:
                            self._error("The node reboot is not finished")
                    except paramiko.ssh_exception.NoValidConnectionsError:
                        self._info("can not connect to the node: " + ip)
                    except paramiko.ssh_exception.SSHException:
                        self._info("Error reading SSH protocol banner[Errno 104] "
                                   "Connection reset by peer: " + ip)

                ready_clients = len(self.ssh_clients)
                if ready_clients == 5:
                    self._info("All the clients is ready")
                    break
                else:
                    self._info("Ready clients are: " + str(ready_clients))
                    time.sleep(10)

            t1 = datetime.now()
            node_status = []
            self._info("====================check cloud init=======================")
            while (datetime.now() - t1).seconds <= const.CLOUD_INIT_TIMEOUT:
                for ip, client in self.ssh_clients.items():
                    if ip in node_status:
                        continue
                    else:
                        if self.ssh_exec(client, ssh_check_cmd):
                            node_status.append(ip)
                        else:
                            self._info("The cloud-init process is not finished: " + ip)
                ready_node = len(node_status)
                self._info("Ready nodes: " + str(node_status))
                if ready_node == 5:
                    break
                time.sleep(10)

            if len(node_status) == 5:
                return True
            else:
                self._error("The cloud-init processes of nodes are "
                            "not totally ready, only ready: "
                            + str(len(node_status)))
                return False

        else:
            self._error("Cluster node count is not right")
            return False

    def clean_node_info(self):
        p = subprocess.Popen(['rm', '-rf', self.node_conf_dir + const.NODE_INFO],
                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        self.realtime_output(p)
        if p.returncode == 0:
            self._info('Terraform apply success')
            return True
        else:
            self._error('Terraform apply failed')
            return False

    #
    # The main process
    # For stability, we can set provision_new to False, and then set the
    # terraform dir then each running will use the same 5 nodes for test.
    # Note: This will not install all the packages, so we needs to do some
    # procedures which is in cloud-init to another function.
    #
    def provision(self,exist_tf_dir):
        if self.provision_new:
            self._info("Prepare to provision the new cluster")
            self.prepare_tf_conf()
        else:
            self._info("Prepare to use the exist cluster: " + exist_tf_dir)
            self.tf_conf_dir = self.node_conf_dir + exist_tf_dir

        if not os.path.exists(self.tf_conf_dir):
            self._error("No exist terraform config path exist")
            return False
        self.clean_node_info()
        tf_return = self.terraform_apply()
        if tf_return:
            self.gen_node_info()
        else:
            return False

        # check the file is there
        if exists(self.node_conf_dir + const.NODE_INFO):
            if self.node_check():
                if not self.provision_new:
                    self._info("Does not provision new instances, we "
                               "need to reinstall Lustre from the repo")
                    return self.node_operate()
                else:
                    return True
            else:
                self._error("The node_check is failed")
                return False
        else:
            self._error("The config file does not exist: " + self.node_conf_dir + const.NODE_INFO)
            return False

    def install_lustre(self, node, client):
        cmd1 = "sudo dnf config-manager --set-enabled ha"
        cmd2 = "sudo dnf config-manager --set-enabled powertools"
        cmd3 = "sudo dnf update libmodulemd -y"
        cmd4 = "sudo dnf install epel-release -y"
        cmd5 = "sudo dnf install pdsh pdsh-rcmd-ssh net-tools dbench fio linux-firmware -y"
        cmd6 = "sudo dnf --disablerepo=* --enablerepo=lustre " \
               "install kernel kernel-debuginfo " \
               "kernel-debuginfo-common-aarch64 kernel-devel kernel-core " \
               "kernel-headers kernel-modules kernel-modules-extra " \
               "kernel-tools kernel-tools-libs kernel-tools-libs-devel " \
               "kernel-tools-debuginfo -y"
        cmd7 = "sudo dnf install e2fsprogs e2fsprogs-devel " \
               "e2fsprogs-debuginfo e2fsprogs-static e2fsprogs-libs " \
               "e2fsprogs-libs-debuginfo libcom_err libcom_err-devel " \
               "libcom_err-debuginfo libss libss-devel libss-debuginfo -y"
        cmd8 = "sudo dnf install lustre lustre-debuginfo lustre-debugsource " \
               "lustre-devel lustre-iokit lustre-osd-ldiskfs-mount " \
               "lustre-osd-ldiskfs-mount-debuginfo lustre-resource-agents " \
               "lustre-tests lustre-tests-debuginfo kmod-lustre " \
               "kmod-lustre-debuginfo kmod-lustre-osd-ldiskfs " \
               "kmod-lustre-tests -y"

        cmd_result = {}
        if self.ssh_exec(client, cmd1):
            cmd_result["1"] = "Success"
        else:
            cmd_result["1"] = "Failed"

        if self.ssh_exec(client, cmd2):
            cmd_result["2"] = "Success"
        else:
            cmd_result["2"] = "Failed"

        if self.ssh_exec(client, cmd3):
            cmd_result["3"] = "Success"
        else:
            cmd_result["3"] = "Failed"

        if self.ssh_exec(client, cmd4):
            cmd_result["4"] = "Success"
        else:
            cmd_result["4"] = "Failed"

        if self.ssh_exec(client, cmd5):
            cmd_result["5"] = "Success"
        else:
            cmd_result["5"] = "Failed"

        if self.ssh_exec(client, cmd6):
            cmd_result["6"] = "Success"
        else:
            cmd_result["6"] = "Failed"

        if self.ssh_exec(client, cmd7):
            cmd_result["7"] = "Success"
        else:
            cmd_result["7"] = "Failed"

        if self.ssh_exec(client, cmd8):
            cmd_result["8"] = "Success"
        else:
            cmd_result["8"] = "Failed"

        for key, value in cmd_result.items():
            result = node + " Install Lustre: procedure: " + key + " " + value
            self._info(result)

    def node_operate(self):
        thread_list = []
        for node, client in self.ssh_clients.items():
            x = threading.Thread(target=self.install_lustre, args=(node, client,))
            x.start()
            thread_list.append(x)

        for x in thread_list:
            x.join()

        for node, client in self.ssh_clients.items():
            self.node_volume_check(node, client)
        return True

    def node_volume_check(self, node, client):
        check_volume = 'lsblk'
        self._info("The node " + node + " volumes info: ")
        self.ssh_exec(client, check_volume)


def main():
    logging.basicConfig(level=logging.INFO,
                        format='%(message)s')
    logger = logging.getLogger(__name__)
    args = sys.argv[1:]
    if len(args) < 2 or len(args) > 3:
        logger.error("no exact args specified")
        return
    test_suites_num = args[0]
    if test_suites_num not in const.LUSTRE_TEST_SUITE_NUM_LIST:
        logger.error("The test suites: " + args[0] + " is not support")
        return

    provision_new = bool(strtobool(args[1]))
    exist_tf_dir = ""
    if not provision_new:
        if len(args) == 3:
            exist_tf_dir = args[2]
        else:
            logger.error("Choose not provision new cluster, "
                         "please specify the lustre terraform dir")
            return

    cluster_provision = Provision(logger, test_suites_num, provision_new)
    result = cluster_provision.provision(exist_tf_dir)
    if result:
        logger.info("The provision process is successful")
        for node, client in cluster_provision.ssh_clients.items():
            cluster_provision.ssh_close(client)
    else:
        logger.error("The provision process is not successful")

# Args:                   test_suites_num provision_new    lustre-exist-tf-dir
# E.g 3 args:                    1              False          lustre-abdg1b
# E.g 2 args if provision new:   2              True


if __name__ == "__main__":
    main()
