import const
import paramiko
from paramiko import ssh_exception
import logging


class Auster(object):
    def __init__(self, ip, logger):
        self.logger = logger
        self.ssh_user = const.DEFAULT_SSH_USER
        self.ssh_client = None
        self.ip = ip

    def _debug(self, msg, *args):
        self.logger.debug(msg, *args)

    def _info(self, msg, *args):
        self.logger.info(msg, *args)

    def _error(self, msg, *args):
        self.logger.error(msg, *args)

    def ssh_connection(self):
        private_key = \
            paramiko.RSAKey.from_private_key_file(const.SSH_PRIVATE_KEY)
        self.ssh_client = paramiko.SSHClient()
        self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            self.ssh_client.connect(hostname=self.ip,
                                    port=22,
                                    username=self.ssh_user,
                                    pkey=private_key)
        except ssh_exception.NoValidConnectionsError as e:
            self._info("Not yet connected to this node: " + e)
            return

        # # Test SSH connection
        # stdin, stdout, stderr = self.ssh_client.exec_command('ls /')
        # error = stderr.read()
        # if error.strip():
        #     self._error(error)
        #     return

        self._info("SSH client for IP: " + self.ip +
                    " initialization is finished")

    def ssh_close(self):
        self.ssh_client.close()

    def ssh_exec(self, cmd):
        stdin, stdout, stderr = self.ssh_client.exec_command(cmd)
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

    def test(self):
        self.ssh_connection()
        if self.ssh_client:
            cmd = "/usr/lib64/lustre/tests/auster -f multinode -rsv sanity"
            if not self.ssh_exec(cmd):
                self._error("Auster test failed: " + cmd)
        else:
            self._error("No available ssh client for: " + self.ip)


def main():
    node_map = {}
    logging.basicConfig(format='%(message)s',
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

    exec_node_ip = ""
    for key, node_info in node_map.items():
        if node_info[2] == const.CLIENT:
            exec_node_ip = node_info[1]
            break

    auster_test = Auster(exec_node_ip, logger)
    auster_test.test()


if __name__ == "__main__":
    main()
