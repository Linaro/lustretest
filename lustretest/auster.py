import const
import paramiko
from paramiko import ssh_exception
import logging
import utils
import sys
from distutils.util import strtobool
from os import environ as env


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

        self._info("SSH client for IP: " +
                   self.ip + " initialization is finished")

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

    def test(self, test_suites, num):
        log_dir = env['WORKSPACE'] + '/test_logs/log-' \
                    + env['BUILD_ID'] + '/' + 'group-' + num

        self.ssh_connection()
        if self.ssh_client:
            cmd = "/usr/lib64/lustre/tests/auster -f multinode -rkv -D " \
                    + log_dir + " " + test_suites
            self._info("Exec the test suites on the node: " + self.ip)
            self._info(cmd)
            if not self.ssh_exec(cmd):
                self._error("Auster test failed: " + cmd)
        else:
            self._error("No available ssh client for: " + self.ip)


def main():
    logging.basicConfig(format='%(message)s',
                        level=logging.INFO)
    logger = logging.getLogger(__name__)

    args = sys.argv[1:]
    if len(args) != 2:
        logger.error("no exact args specified")
        return

    test_suites_num = args[0]
    if test_suites_num not in const.LUSTRE_TEST_SUITE_NUM_LIST:
        logger.error("The test suites: " + args[0] + " is not support")
        return

    exec_suites = bool(strtobool(args[1]))

    # We transfer the num for which is > 3 to -3, and use 1-3 clusters already
    # to execute the test
    # test suite 4: 1
    # test suite 5: 2
    # test suite 6: 3
    test_cluster_num = test_suites_num
    if int(test_suites_num) > 3:
        test_cluster_num = str(int(test_suites_num) - 3)
    node_conf_dir = utils.find_node_conf_dir(test_cluster_num)
    node_map, _ = utils.read_node_info(node_conf_dir + const.NODE_INFO)
    test_suites = utils.get_test_list(test_suites_num)

    # Choose the first node as the test exec node.
    exec_node_ip = ""
    for key, node_info in node_map.items():
        if node_info[2] == const.CLIENT:
            exec_node_ip = node_info[1]
            break

    if exec_suites:
        auster_test = Auster(exec_node_ip, logger)
        auster_test.test(test_suites, test_suites_num)
    else:
        logger.info("Skip the test suites: " + test_suites_num + ": " + test_suites)


if __name__ == "__main__":
    main()
