from os import environ as env
import re
import uuid

import paramiko
from paramiko import ssh_exception
import yaml

import const
from const import LOG
import myyamlsanitizer


class Auster():
    def __init__(self, test_group_id, test_suites,
                 exec_node_ip, nfs_dir, lustre_branch='master',
                 build_id=env['BUILD_ID'], dist='el8', arch='aarch64',
                 run_uuid=env['CUMULATIVE_RESULT_ID'],
                 workspace=env['WORKSPACE']
                 ):
        self.ssh_user = const.DEFAULT_SSH_USER
        self.ssh_client = None
        self.ip = exec_node_ip
        self.test_info = {}
        self.test_info['suites'] = []
        self.test_info['lustre_branch'] = lustre_branch
        self.test_info['build_id'] = build_id
        self.test_info['dist'] = dist
        self.test_info['dist_main'] = re.sub(r'sp\d+', '', dist)
        self.test_info['arch'] = arch
        self.test_info['run_uuid'] = run_uuid
        self.test_info['workspace'] = workspace
        if test_group_id is not None:
            self.test_info['group_id'] = test_group_id
            self.test_info['suites'] = self.get_test_suites(test_group_id)
        else:
            self.test_info['group_id'] = 0
            self.test_info['suites'].append(test_suites)
            self.test_info['group_name'] = 'custom-' + str(uuid.uuid4())[:8]
            self.test_info['timeout'] = -1
        logdir = f"{lustre_branch}/{dist}/log-{self.test_info['build_id']}/" \
            f"{self.test_info['group_name']}"
        self.test_info['logdir'] = f"{nfs_dir}/{logdir}"
        self.test_info['local_logdir'] = f"{self.test_info['workspace']}/test_logs/{logdir}"
        self.test_info['shared_dir'] = nfs_dir

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
            msg = f"Not yet connected to this node: {e}"
            LOG.info(msg)
            return

        # # Test SSH connection
        # stdin, stdout, stderr = self.ssh_client.exec_command('ls /')
        # error = stderr.read()
        # if error.strip():
        #     LOG.error(error)
        #     return

        msg = f"SSH client for IP: {self.ip} initialization is finished"
        LOG.info(msg)

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
            stdout._set_mode('b')
            for line in iter(stdout.readline, b""):
                line = line.decode('utf-8', 'ignore')
                LOG.info(line.strip())
            return stdout.channel.recv_exit_status()
        except TimeoutError:
            msg = f"Cmd running timeout, cmd: {cmd}"
            LOG.info(msg)
            return const.TEST_FAIL

    def run_test(self):
        self.ssh_connection()
        rc = const.TEST_SUCC
        if self.ssh_client:
            env_vars = f"TEST_GROUP={self.test_info['group_name']} " \
                f"SHARED_DIRECTORY={self.test_info['shared_dir']} " \
                f"PJDFSTEST_DIR=/home/{const.CLOUD_INIT_CHECK_USER}/pjdfstest "
            for suite in self.test_info['suites']:
                cmd = f"module load mpi/openmpi-{self.test_info['arch']} &&" \
                    f"{env_vars} " \
                    "/usr/lib64/lustre/tests/auster -f multinode -rvsk " \
                    f"-D {self.test_info['logdir']} {suite}"

                msg = \
                    f"Exec the test suite on the node: {self.ip}\n" \
                    f"Timeout: {self.test_info['timeout']}\n" \
                    f"Cmd: {cmd}\n..."

                LOG.info(msg)
                rc = self.ssh_exec(cmd, self.test_info['timeout'])
                msg = f"Auster test finish, test suite: {suite}, rc = {rc}"
                LOG.info(msg)
            msg = f"Auster test finish, test suites: {self.test_info['suites']}"
            LOG.info(msg)

            rc = self.parse_test_result()
            LOG.info("Auster parse result finish, rc = %d", rc)
        else:
            msg = f"No available ssh client for: {self.ip}"
            LOG.error(msg)
            rc = const.TEST_FAIL

        return rc

    def parse_test_result(self):
        """Parse test results.
        Parse test results to check if test running all pass,
        and format test restuls for later uploading to Maloo DB.
        """
        fail = False
        yamlfile = f"{self.test_info['local_logdir']}/results.yml"
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
                msg = f"yaml file is invalid, file: {yamlfile}"
                LOG.error(msg)
                raise

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

                msg = f"{test_script}: {msg}, total tests: " \
                    f"{test_count}, take {test_duration}  s."
                LOG.info(msg)
                test['total'] = test_count
                if failed_subtests:
                    failed_count = len(failed_subtests)
                    fail_sum += failed_count
                    percent = f"{failed_count/test_count:.1%}"
                    test['failed_total'] = failed_count
                    test['failed_percent'] = percent
                    msg = f"    Failed total: {failed_count}/{test_count}," \
                        f" {percent}. Failed tests: "
                    msg += ",".join(failed_subtests)
                    LOG.info(msg)
                if skipped_subtests:
                    skipped_count = len(skipped_subtests)
                    skip_sum += skipped_count
                    percent = f"{skipped_count/test_count:.1%}"
                    test['skipped_total'] = skipped_count
                    test['skipped_percent'] = percent
                    msg = f"    Skipped total: {skipped_count}/{test_count}," \
                        f" {percent} . Skipped tests: "
                    msg += ",".join(skipped_subtests)
                    LOG.info(msg)

        duration_sum = f'{duration_sum/60/60:.1f}'  # hours
        test_results['duration_hours'] = duration_sum
        msg = f"\n====>{self.test_info['group_name']} total tests: "\
            f"{total_sum}, take {duration_sum} hours.<===="
        LOG.info(msg)
        if fail_sum > 0:
            percent = f"{fail_sum/total_sum:.1%}"
            test_results['failed_total'] = total_sum
            test_results['failed_percent'] = percent
            msg = f"    Failed total: {fail_sum}/{total_sum}, {percent}."
            LOG.info(msg)
        if skip_sum > 0:
            percent = f"{skip_sum/total_sum:.1%}"
            test_results['skipped_total'] = skip_sum
            test_results['skipped_percent'] = percent
            msg = f"    Skipped total: {skip_sum}/{total_sum}, {percent}."
            LOG.info(msg)
        # Add missing required fields to results.yml for Maloo DB upload
        with open(yamlfile, 'w', encoding='utf8') as file:
            test_results['cumulative_result_id'] = self.test_info['run_uuid']
            test_results['test_sequence'] = '1'
            test_results['test_index'] = str(self.test_info['group_id'])
            test_results['session_group_id'] = str(uuid.uuid4())
            test_results['enforcing'] = 'false'
            # Only maloo defined names is can be set now, see:
            # https://jira.whamcloud.com/browse/LU-15823
            test_results['triggering_job_name'] = 'custom'
            test_results['triggering_build_number'] = self.test_info['build_id']
            test_results['total_enforcing_sessions'] = '1'
            # lustre-master-el8.5-x86_64--linaro-full-part-1--1.10
            test_name = f"lustre-{self.test_info['lustre_branch']}-" \
                f"{self.test_info['dist']}-{self.test_info['arch']}--" \
                f"{self.test_info['group_name']}--" \
                f"{test_results['test_sequence']}.{test_results['test_index']}"
            test_results['test_name'] = test_name
            test_results['test_suites'] = ', '.join(self.test_info['suites'])
            yaml.safe_dump(test_results, file)

        if fail:
            return const.TEST_FAIL

        return const.TEST_SUCC

    def get_test_suites(self, test_group_id):
        test_suites_with_args = []
        with open(const.TEST_ARGS_CONFIG, "r") as test_args:
            test_groups = yaml.load(test_args, Loader=yaml.FullLoader)
            for group in test_groups:
                if group['id'] == test_group_id:
                    self.test_info['group_name'] = group['name']
                    self.test_info['timeout'] = group.get('timeout', -1)
                    for test_suite in group['test_suite']:
                        name = test_suite['name']
                        args = test_suite.get('args', "")
                        if isinstance(args, dict):
                            key = self.test_info['dist_main']
                            value = args.get(key, "")
                            if value == "":
                                key = f"{self.test_info['dist_main']}_" \
                                    f"{self.test_info['lustre_branch']}"
                                value = args.get(key, "")
                        else:
                            value = args

                        # check if value is '--except all'
                        if "all" not in value:
                            suite = f"{name} {value}"
                            test_suites_with_args.append(suite)
                    break
        return test_suites_with_args
