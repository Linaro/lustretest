from os import environ as env
import uuid

import paramiko
from paramiko import ssh_exception
import yaml

import const
import myyamlsanitizer


class Auster():
    def __init__(self, logger, test_group_id, exec_node_ip, nfs_dir):
        self.logger = logger
        self.ssh_user = const.DEFAULT_SSH_USER
        self.ssh_client = None
        self.ip = exec_node_ip
        self.test_info = {}
        self.test_info['env_vars'] = ""
        self.test_info['group_id'] = test_group_id
        self.test_info['suites'] = self.get_test_suites(test_group_id)
        logdir = 'log-' + env['BUILD_ID'] + '/' + self.test_info['group_name']
        self.test_info['logdir'] = nfs_dir + '/' + logdir
        self.test_info['local_logdir'] = env['WORKSPACE'] + \
            '/test_logs/' + logdir
        self.test_info['shared_dir'] = nfs_dir

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

    def ssh_exec(self, cmd, timeout=None):
        if timeout == -1:
            timeout = None
        try:
            # pty make stderr stream into stdout, so we can
            # print stdout and stderr in realtime
            _, stdout, _ = self.ssh_client.exec_command(cmd, get_pty=True,
                                                        timeout=timeout)
            for line in iter(stdout.readline, ""):
                self._info(line.strip())
            return stdout.channel.recv_exit_status()
        except TimeoutError:
            self._info("Cmd running timeout, cmd: " + cmd)
            return const.TEST_FAIL

    def run_test(self):
        self.ssh_connection()
        rc = const.TEST_SUCC
        if self.ssh_client:
            self.test_info['env_vars'] += \
                "TEST_GROUP=" + self.test_info['group_name'] + " "
            self.test_info['env_vars'] += \
                "SHARED_DIRECTORY=" + self.test_info['shared_dir'] + " "
            cmd = self.test_info['env_vars'] + \
                "/usr/lib64/lustre/tests/auster -f multinode -rvs -D " \
                + self.test_info['logdir'] + " " + self.test_info['suites']

            self._info("Exec the test suites on the node: " + self.ip)
            self._info("Timeout: " + str(self.test_info['timeout']))
            self._info("Cmd: " + cmd)
            rc = self.ssh_exec(cmd, self.test_info['timeout'])
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
        total_sum = 0
        fail_sum = 0
        skip_sum = 0
        duration_sum = 0
        with open(yamlfile, 'r', encoding='utf8') as file:
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
                    skipped_subtests = []
                    test_script = test.get('name', '')
                    test_duration = test.get('duration', -1)
                    duration_sum += test_duration
                    test_status = test.get('status', '')
                    subtests = test.get('SubTests', {})
                    if subtests is not None:
                        test_count = len(subtests)
                    else:
                        test_count = 0
                    total_sum += test_count

                    if test_status not in ['PASS', 'SKIP']:
                        fail = True
                        msg = "Test fail"
                        if subtests is not None:
                            for subtest in subtests:
                                subtest_num = subtest['name'].replace(
                                    'test_', '')
                                subtest_status = subtest.get('status', '')
                                if subtest_status not in ['PASS', 'SKIP']:
                                    failed_subtests.append(subtest_num)
                                if subtest_status == 'SKIP':
                                    skipped_subtests.append(subtest_num)
                    else:
                        if test_status == 'SKIP':
                            msg = "Test skip"
                        else:
                            msg = "Test pass"

                    msg = test_script + ': ' + msg + \
                        ", total tests: " + str(test_count) + \
                        ", take " + str(test_duration) + " s."
                    self._info(msg)
                    test['total'] = test_count
                    if failed_subtests:
                        failed_count = len(failed_subtests)
                        fail_sum += failed_count
                        percent = f"{failed_count/test_count:.1%}"
                        test['failed_total'] = failed_count
                        test['failed_percent'] = percent
                        msg = "    Failed total: " + str(failed_count) + \
                            "/" + str(test_count) + ", " + percent + \
                            ". Failed tests: " + ",".join(failed_subtests)
                        self._info(msg)
                    if skipped_subtests:
                        skipped_count = len(skipped_subtests)
                        skip_sum += skipped_count
                        percent = f"{skipped_count/test_count:.1%}"
                        test['skipped_total'] = skipped_count
                        test['skipped_percent'] = percent
                        msg = "    Skipped total: " + str(skipped_count) + \
                            "/" + str(test_count) + ", " + percent + \
                            ". Skipped tests: " + ",".join(skipped_subtests)
                        self._info(msg)

        duration_sum = f'{duration_sum/60/60:.1f}'  # hours
        test_results['duration_hours'] = duration_sum
        msg = self.test_info['group_name'] + " total tests: " + \
            str(total_sum) + ", take " + str(duration_sum) + " hours."
        self._info(msg)
        if fail_sum > 0:
            percent = f"{fail_sum/total_sum:.1%}"
            test_results['failed_total'] = total_sum
            test_results['failed_percent'] = percent
            msg = "    Failed total: " + str(fail_sum) + \
                "/" + str(total_sum) + ", " + percent + "."
            self._info(msg)
        if skip_sum > 0:
            percent = f"{skip_sum/total_sum:.1%}"
            test_results['skipped_total'] = skip_sum
            test_results['skipped_percent'] = percent
            msg = "    Skipped total: " + str(skip_sum) + \
                "/" + str(total_sum) + ", " + percent + "."
            self._info(msg)
        # Add missing required fields to results.yml for Maloo DB upload
        with open(yamlfile, 'w', encoding='utf8') as file:
            test_results['cumulative_result_id'] = env['CUMULATIVE_RESULT_ID']
            test_results['test_sequence'] = '1'
            test_results['test_index'] = str(self.test_info['group_id'])
            test_results['session_group_id'] = str(uuid.uuid4())
            test_results['enforcing'] = 'false'
            # Only maloo defined names is can be set now, see:
            # https://jira.whamcloud.com/browse/LU-15823
            test_results['triggering_job_name'] = 'custom'
            test_results['triggering_build_number'] = env['BUILD_ID']
            test_results['total_enforcing_sessions'] = '1'
            # lustre-master-el8.5-x86_64--linaro-full-part-1--1.10
            test_results['test_name'] = 'lustre-' + env['LUSTRE_BRANCH'] + \
                "-el8.5-aarch64--" + self.test_info['group_name'] + "--" + \
                test_results['test_sequence'] + \
                "." + test_results['test_index']
            test_results['test_suites'] = self.test_info['suites'].strip()
            yaml.safe_dump(test_results, file)

        if fail:
            return const.TEST_FAIL

        return const.TEST_SUCC

    def get_test_suites(self, test_group_id):
        test_suites_with_args = ""
        with open(const.TEST_ARGS_CONFIG, "r") as test_args:
            test_groups = yaml.load(test_args, Loader=yaml.FullLoader)
            for group in test_groups:
                if group['id'] == test_group_id:
                    self.test_info['group_name'] = group['name']
                    self.test_info['timeout'] = group.get('timeout', -1)
                    for test_suite in group['test_suite']:
                        name = test_suite['name']
                        args = test_suite.get('args', "")
                        test_suites_with_args += " " + name + " " + args
                    break
        return test_suites_with_args
