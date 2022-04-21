import logging
import paramiko
from scp import SCPClient
import const
from datetime import datetime
import time

class Node(object):
    def __init__(self, host, ip, node_type, node_map, logger):
        self.host = host
        self.ip = ip
        self.type = node_type
        self.ssh_user = const.DEFAULT_SSH_USER
        self.ssh_private_key = None
        self.node_map = node_map
        self.ssh_client = None
        self.logger = logger

    def _debug(self, msg, *args):
        self.logger.debug(msg, *args)

    def _info(self, msg, *args):
        self.logger.info(msg, *args)

    def _error(self, msg, *args):
        self.logger.error(msg, *args)

    def ssh_connection(self):
        private_key = paramiko.RSAKey.from_private_key_file(const.SSH_PRIVATE_KEY)
        self.ssh_client = paramiko.SSHClient()
        self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.ssh_client.connect(hostname=self.ip, port=22, username=self.ssh_user, pkey=private_key)

        # # Test SSH connection
        # stdin, stdout, stderr = self.ssh_client.exec_command('ls /')
        # result = stdout.read()
        # self._info(result.decode('utf-8'))
        return self.ssh_client

    def ssh_close(self):
        self.ssh_client.close()

    def ssh_exec(self, cmd):
        stdin, stdout, stderr = self.ssh_client.exec_command(cmd)
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

    def scp_send(self, filename, remote_path):
        scp_client = SCPClient(self.ssh_client.get_transport(), socket_timeout=15.0)
        local_path = filename
        try:
            scp_client.put(local_path, remote_path, True)
        except FileNotFoundError:
            self._error("SCP failed: " + local_path)
        else:
            self._info("SCP success: " + local_path)

    def scp_get(self, remote_path, local_path):
        scp_client = SCPClient(self.ssh_client.get_transport(), socket_timeout=15.0)
        try:
            scp_client.get(remote_path, local_path)
        except FileNotFoundError:
            self._error("SCP failed: " + local_path)
        else:
            self._info("SCP success: " + local_path)

    def init(self):
        # Install the Lustre client packages on two machines, and the Lustre server
        # packages on the other four, using the same version of Lustre
        # Follow this guide to install Lustre RPMs and e2fsprogs
        # Install PDSH and ensure you can execute commands across the cluster
        # Install the epel-release package to enable the EPEL repo
        # Install the net-tools package for netstat

        # Add user 'runas' with UID 500 and GID 500 to all the nodes
        # Disable SELINUX
        # Set SELINUX=disabled in /etc/sysconfig/selinux
        # Disable the firewall
        # service firewalld stop && systemctl disable firewalld.service

        # The above process can be done in cloud-init

        # Generate passwordless ssh keys for hosts and exchange identities across
        # all nodes, and also accept the host fingerprints
        # The goal is to be able to pdsh using ssh from all machines without requiring any user input
        # All the node use the same keys to login
        self.ssh_connection()
        if self.ssh_connection() is None:
            self._error("SSH client initialization failed: " + self.ip)
            return
        # please make sure to remove the file first
        self.ssh_exec("yes | rm -i " + const.SSH_CFG_DIR + "/" + "id_rsa")
        self.scp_send(const.SSH_PRIVATE_KEY, const.SSH_CFG_DIR)

        # Create an NFS share that is mounted on all the nodes
        # A small number of tests will make use of a shared storage location

        self.ssh_exec("yes | sudo rm -i " + "/etc/hosts")
        # Configure hostnames and populate /etc/hosts
        host_info = "127.0.0.1   localhost localhost.localdomain localhost4 localhost4.localdomain4\n" \
                    "::1         localhost localhost.localdomain localhost6 localhost6.localdomain6\n"
        for key, node_info in self.node_map.items():
            host_info += node_info[1] + ' ' + node_info[0] + '\n'

        write_hosts = 'echo \"' + host_info + "\"" + ' | sudo tee -a /etc/hosts'
        if not self.ssh_exec(write_hosts):
            self._error("Write the /etc/hosts failed")

        remote_cfg_location = const.LUSTRE_TEST_CFG_DIR + '/' + const.MULTI_NODE_CONFIG
        self.ssh_exec("yes | sudo rm -i " + remote_cfg_location)
        self.scp_send(const.TEST_WORKSPACE + const.MULTI_NODE_CONFIG, "/home/jenkins")
        self.ssh_exec("yes | sudo mv /home/jenkins/" + const.MULTI_NODE_CONFIG + " " + remote_cfg_location)

        # SSH .ssh/config add like below:
        # Host *
        #     StrictHostKeyChecking   no
        # chmod 600
        self.ssh_exec("yes | sudo rm -i " + const.REMOTE_SSH_CONFIG)
        self.scp_send(const.SSH_CONFIG, const.REMOTE_SSH_CONFIG)

        # /etc/hostname remove the .novalocal
        self.ssh_exec("yes | sudo rm -i /etc/hostname")
        write_hostname = 'echo \"' + self.host + "\"" + ' | sudo tee -a /etc/hostname'
        if not self.ssh_exec(write_hostname):
            self._error("Write the /etc/hostname failed")

    def reboot(self):
        self.ssh_connection()
        self.ssh_exec("sudo reboot")


def multinode_conf_gen(node_map):
    total_client = 0
    total_mds = 0
    total_clients = ""

    with open(const.TEST_WORKSPACE + const.MULTI_NODE_CONFIG, 'w+') as test_conf:
        for key, node_info in node_map.items():
            if node_info[2] == const.CLIENT:
                if total_client == 0:
                    total_clients = node_info[0]
                    total_client += 1
                    print(total_clients)
                elif total_client == 1:
                    total_client += 1
                    total_clients += ' ' + node_info[0]
                    print(total_clients)
                    rclient_write = "RCLIENTS=\"" + total_clients + "\"\n"
                    test_conf.write("CLIENTCOUNT=2\n")
                    test_conf.write(rclient_write)
            if node_info[2] == const.MDS:
                if total_mds == 0:
                    mds_host = "mds_HOST=\"" + node_info[0] + "\"\n"
                    mds_dev1 = "MDSDEV1=\"" + const.MDS_DISK1 + "\"\n"
                    mds3_host = "mds3_HOST=\"" + node_info[0] + "\"\n"
                    mds_dev3 = "MDSDEV3=\"" + const.MDS_DISK2 + "\"\n"
                    test_conf.write(mds_host)
                    test_conf.write(mds_dev1)
                    test_conf.write(mds3_host)
                    test_conf.write(mds_dev3)
                    total_mds += 1
                elif total_mds == 1:
                    mds2_host = "mds2_HOST=\"" + node_info[0] + "\"\n"
                    mds_dev2 = "MDSDEV2=\"" + const.MDS_DISK1 + "\"\n"
                    mds4_host = "mds4_HOST=\"" + node_info[0] + "\"\n"
                    mds_dev4 = "MDSDEV4=\"" + const.MDS_DISK2 + "\"\n"
                    test_conf.write(mds2_host)
                    test_conf.write(mds_dev2)
                    test_conf.write(mds4_host)
                    test_conf.write(mds_dev4)
                    total_mds += 1
                    mds_count = "MDSCOUNT=4\n"
                    test_conf.write(mds_count)
            if node_info[2] == const.OST:
                ost_count = "OSTCOUNT=8\n"
                ost1_host = "ost_HOST=\"" + node_info[0] + "\"\n"
                ost_dev1 = "OSTDEV1=\"" + const.OST_DISK2 + "\"\n"
                test_conf.write(ost_count)
                test_conf.write(ost1_host)
                test_conf.write(ost_dev1)
                for num in range(2, 9):
                    ost_disk = None
                    if num == 2:
                        ost_disk = const.OST_DISK2
                    elif num == 3:
                        ost_disk = const.OST_DISK3
                    elif num == 4:
                        ost_disk = const.OST_DISK4
                    elif num == 5:
                        ost_disk = const.OST_DISK5
                    elif num == 6:
                        ost_disk = const.OST_DISK6
                    elif num == 7:
                        ost_disk = const.OST_DISK7
                    elif num == 8:
                        ost_disk = const.OST_DISK8

                    ost_host = "ost" + str(num) + "_HOST=\"" + node_info[0] + "\"\n"
                    ost_dev = "OSTDEV" + str(num) + "=\"" + ost_disk + "\"\n"
                    test_conf.write(ost_host)
                    test_conf.write(ost_dev)

        pdsh_cmd = "PDSH=\"/usr/bin/pdsh -S -Rssh -w\"\n"
        test_conf.write(pdsh_cmd)

        share_dir = "SHARED_DIRECTORY=${SHARED_DIRECTORY:-/opt/testing/shared}\n"
        test_conf.write(share_dir)

        ncli_sh_cmd = ". /usr/lib64/lustre/tests/cfg/ncli.sh\n"
        test_conf.write(ncli_sh_cmd)


def node_init(node_map, logger):
    total_client = 0
    total_mds = 0
    test_client1 = None
    test_client2 = None
    test_mds1 = None
    test_mds2 = None
    test_ost1 = None

    for key, node_info in node_map.items():
        test_node = Node(node_info[0], node_info[1], node_info[2], node_map, logger)
        if node_info[2] == const.CLIENT:
            if total_client == 0:
                test_client1 = test_node
                total_client += 1
            elif total_client == 1:
                test_client2 = test_node
                total_client += 1
        if node_info[2] == const.MDS:
            if total_mds == 0:
                test_mds1 = test_node
                total_mds += 1
            elif total_mds == 1:
                test_mds2 = test_node
                total_mds += 1
        if node_info[2] == const.OST:
            test_ost1 = test_node

    test_client1.init()
    test_client2.init()
    test_mds1.init()
    test_mds2.init()
    test_ost1.init()

    nodes = [test_client1, test_client2, test_mds1, test_mds2, test_ost1]
    if not reboot_and_check(nodes):
        print("The reboot process is not finished")

    test_client1.ssh_close()
    test_client2.ssh_close()
    test_mds1.ssh_close()
    test_mds2.ssh_close()
    test_ost1.ssh_close()


def reboot_and_check(nodes):
    for node in nodes:
        node.reboot()

    node_status = []
    t1 = datetime.now()
    print("Begin to check the Node Reboot process")
    while (datetime.now() - t1).seconds <= const.REBOOT_TIMEOUT:
        for node in nodes:
            if node.ip in node_status:
                continue
            else:
                try:
                    if node.ssh_connection():
                        node_status.append(node.ip)
                    else:
                        print("The node reboot is not finished: " + node.ip)
                except paramiko.ssh_exception.NoValidConnectionsError:
                    print("can not connect to the node: " + node.ip)

        ready_node = len(node_status)
        print("Ready nodes: " + str(node_status))
        if ready_node == 5:
            break
        time.sleep(5)

    if len(node_status) == 5:
        return True
    else:
        print("The reboot processes of nodes are "
              "not totally ready, only ready: "
              + str(len(node_status)))
        return False


def main():
    node_map = {}
    logging.basicConfig(format='%(asctime)s - %(name)s - '
                               '%(levelname)s - %(message)s',
                        level=logging.INFO)
    logger = logging.getLogger(__name__)
    with open(const.NODE_INFO, 'r') as f2:
        line = f2.readline()
        i = 0
        while line is not None and line != '':
            node_info = line.split()
            node_map[i] = [node_info[0], node_info[1], node_info[2]]
            line = f2.readline()
            i += 1

    node_count = len(node_map)
    if node_count == 4:
        print("Execute the test for 2 clients, 1 MDS and 1 OST")
    elif node_count == 5:
        print("Execute the test for 2 clients, 2 MDS and 1 OST")
    else:
        print("Unsupported Test nodes numbers!")

    multinode_conf_gen(node_map)
    node_init(node_map, logger)


if __name__ == "__main__":
    main()
