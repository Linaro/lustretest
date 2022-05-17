from distutils.util import strtobool
import logging
from os import environ as env
import sys
import uuid

import paramiko
from paramiko import ssh_exception
import yaml

import const
import myyamlsanitizer
import utils


class Auster():
    def __init__(self, logger, test_group_id):
        self.logger = logger
        self.ssh_user = const.DEFAULT_SSH_USER
        self.ssh_client = None
        self.test_info = {}
        self.test_info['group_id'] = test_group_id
        self.test_info['suites'] = utils.get_test_list(test_group_id)
        logdir = 'log-' + env['BUILD_ID'] + '/group-' + test_group_id
        self.test_info['logdir'] = '/tmp/test_logs/' + logdir
        self.test_info['local_logdir'] = env['WORKSPACE'] + \
            '/test_logs/' + logdir

        # We transfer the num for which is > 3 to -3,
        # and use 1-3 clusters already to execute the test
        # test suite 4: 1
        # test suite 5: 2
        # test suite 6: 3
        test_cluster_num = test_group_id
        if int(test_group_id) > 3:
            test_cluster_num = str(int(test_group_id) - 3)
        node_conf_dir = utils.find_node_conf_dir(test_cluster_num)
        node_map, _ = utils.read_node_info(node_conf_dir + const.NODE_INFO)

        # Choose the first node as the test exec node.
        exec_node_ip = ""
        for _, node_info in node_map.items():
            if node_info[2] == const.CLIENT:
                exec_node_ip = node_info[1]
                break
        self.ip = exec_node_ip

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
            msg = "Not yet connected to this node: " + e
            self._info(msg)
            return

        # # Test SSH connection
        # stdin, stdout, stderr = self.ssh_client.exec_command('ls /')
        # error = stderr.read()
        # if error.strip():
        #     self._error(error)
        #     return

        msg = "SSH client for IP: " + self.ip + " initialization is finished"
        self._info(msg)

    def ssh_close(self):
        self.ssh_client.close()

    def ssh_exec(self, cmd):
        # pty make stderr stream into stdout, so we can
        # print stdout and stderr in realtime
        _, stdout, _ = self.ssh_client.exec_command(cmd, get_pty=True)
        for line in iter(stdout.readline, ""):
            self._info(line.strip())
        return stdout.channel.recv_exit_status()

    def test(self):
        #full_test_args = self.get_test_args()
        self.ssh_connection()
        rc = const.TEST_SUCC
        if self.ssh_client:
            test_env_vars = "LUSTRE_BRANCH=" + env['LUSTRE_BRANCH'] + \
                " TEST_GROUP=group-" + self.test_info['group_id']
            cmd = test_env_vars + \
                " /usr/lib64/lustre/tests/auster -f multinode -rvk -D " \
                + self.test_info['logdir'] + " " + self.test_info['suites']
            self._info("Exec the test suites on the node: " + self.ip)
            self._info(cmd)
            rc = self.ssh_exec(cmd)
            self._info("Auster test finish, rc = %d", rc)

            if rc == const.TEST_SUCC:
                rc = self.parse_test_result()
                self._info("Auster parse result finish, rc = %d", rc)
        else:
            self._error("No available ssh client for: " + self.ip)
            rc = const.TEST_FAIL

        return rc

    def parse_test_result(self):
        """Parse test results.
        Parse test results to check if test running all pass,
        and format test restuls for later uploading to Maloo DB.
        """
        fail = False
        yamlfile = self.test_info['local_logdir'] + '/results.yml'
        with open(yamlfile, 'r+', encoding='utf8') as file:
            filedata = file.read()
            try:
                test_results = yaml.safe_load(
                    myyamlsanitizer.sanitize(filedata))
            except (ImportError, yaml.parser.ParserError, yaml.scanner.ScannerError):
                self._error("yaml file is invalid, file:" + yamlfile)
                raise
            else:
                for test in test_results.get('Tests', {}):
                    failed_subtests = []
                    test_script = test.get('name', '')
                    if test.get('status', '') != 'PASS':
                        fail = True
                        msg = "Test Fail. FAIL: "
                        subtests = test.get('SubTests', {})
                        if subtests is not None:
                            for subtest in subtests:
                                if subtest.get('status', 'FAIL') == 'FAIL':
                                    failed_subtests.append(
                                        subtest['name'].replace('test_', ''))
                    else:
                        msg = "Test Pass."
                    self._info(test_script + ': ' + msg +
                               "'".join(failed_subtests))

                # Add missing required fields to results.yml for Maloo DB
                # upload
                test_results['test_name'] = self.test_info['suites']
                test_results['cumulative_result_id'] = env['CUMULATIVE_RESULT_ID']
                test_results['test_sequence'] = '1'
                test_results['test_index'] = self.test_info['group_id']
                test_results['session_group_id'] = str(uuid.uuid4())
                test_results['enforcing'] = 'false'
                # Only maloo defined names is can be set now, see:
                # https://jira.whamcloud.com/browse/LU-15823
                test_results['triggering_job_name'] = 'linaro-lustre-daily' + \
                    env['LUSTRE_BRANCH']
                test_results['triggering_build_number'] = env['BUILD_ID']
                test_results['total_enforcing_sessions'] = '1'
                file.seek(0)
                yaml.safe_dump(test_results, file)

        if fail:
            return const.TEST_FAIL

        return const.TEST_SUCC

    def get_test_args(self):
        test_suites_full_args = ""
        with open(const.TEST_ARGS_CONFIG, "r") as test_args:
            full_test_args = yaml.load(test_args, Loader=yaml.FullLoader)
            testargs_list = full_test_args['testargs']
            print(testargs_list)
            test_suite_list = self.test_info['suites'].split(" ")
            for test_suite in test_suite_list:
                for _, testargs in enumerate(testargs_list):
                    test_suite_name = testargs.get('test')
                    if test_suite == test_suite_name:
                        args = testargs.get('args')
                        if args is not None:
                            skip_list = args.get('skip')
                            if skip_list and len(skip_list) != 0:
                                skip_cases = ""
                                for _, skip_case in enumerate(skip_list):
                                    skip_cases += str(skip_case) + ","
                                skip_cases = skip_cases[:-1]
                                test_suites_full_args += test_suite \
                                    + " --except \'" + skip_cases + "\' "
                            else:
                                test_suites_full_args += test_suite + " "
                        else:
                            test_suites_full_args += test_suite + " "
        return test_suites_full_args


def main():
    logging.basicConfig(format='%(message)s',
                        level=logging.INFO)
    logger = logging.getLogger(__name__)
    rc = const.TEST_SUCC

    args = sys.argv[1:]
    if len(args) != 2:
        sys.exit("no exact args specified")

    test_group_id = args[0]
    if test_group_id not in const.LUSTRE_TEST_SUITE_NUM_LIST:
        msg = "The test group: " + args[0] + " is not support"
        sys.exit(msg)

    exec_suites = bool(strtobool(args[1]))

    if exec_suites:
        auster_test = Auster(logger, test_group_id)
        rc = auster_test.test()
    else:
        logger.info("Skip the test suites: %d", test_group_id)

    if rc == const.TEST_FAIL:
        sys.exit("Test running is not pass")


if __name__ == "__main__":
    main()
