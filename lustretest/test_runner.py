from os import listdir
from os.path import basename, isdir, join as path_join
import sys

from filelock import Timeout, FileLock
import typer
from typing_extensions import Annotated

from auster import Auster
import const
from const import LOG
from node_init import multinode_conf_gen, node_init
from provision import Provision
import utils

#
# Provision: get cluster_dir and lock
#


def get_cluster_dir(provision_new, cluster_provision, dist='el8'):
    if provision_new:
        cluster_dir = cluster_provision.get_cluster_dir()
        cluster_lock = FileLock(cluster_dir + "/.lock", timeout=0)
        try:
            cluster_lock.acquire()
            return cluster_dir, cluster_lock
        except Timeout:
            msg = basename(cluster_dir) + \
                "is in used, no cluster for test now!!"
            LOG.info(msg)
    else:  # find an idle cluster
        clusters_top_dir = path_join(const.TEST_WORKSPACE, dist)
        cluster_dirs = [path_join(clusters_top_dir, f) for f in listdir(
            clusters_top_dir) if isdir(path_join(clusters_top_dir, f))
            and f.startswith(const.LUSTRE_CLUSTER_PREFIX)]
        in_used = 0

        for cluster_dir in cluster_dirs:
            cluster_lock = FileLock(cluster_dir + "/.lock", timeout=0)
            try:
                cluster_lock.acquire()
                return cluster_dir, cluster_lock
            except Timeout:
                in_used += 1
                msg = basename(cluster_dir) + \
                    " is in used, total used: " + str(in_used)
                LOG.info(msg)

    return "", None


def main(
    test_group_id:
        Annotated[int,
                  typer.Option(
                      help="Test group to test, valid value are 1-4.")
                  ] = None,
    test_suites:
        Annotated[str,
                  typer.Option(
                      help="Test suites to test.")
                  ] = None,
    provision_new:
        Annotated[bool,
                  typer.Option(
                      help="Provision a new VM cluster to run test.")
                  ] = False,
    destroy_cluster:
        Annotated[bool,
                  typer.Option(
                      help="Destroy the VM cluster after finish running the test.")
                  ] = False,
    dist:
        Annotated[str,
                  typer.Option(
                      help="Distro to test. E.g.: el8, oe2203sp1")
                  ] = 'el8',
    kernel_version:
        Annotated[str,
                  typer.Option(
                      help="Kernel version to test.")
                  ] = None,
    lustre_branch:
        Annotated[str,
                  typer.Option(
                      help="Lustre branch to test. E.g.: master, b2_15")
                  ] = 'master'
):
    """
    Run a Lustre test group or test suites on a VM cluster.

    At least a test groupt or test suites is given.

    E.g.
    test_runner.py --test-group-id 1

    test_runner.py --test-suites sanity --dist el8

    test_runner.py --test-suites "sanity --only 1-100 sanityn --only 20-30"
    """

    rc = const.TEST_SUCC

    if test_group_id is None and test_suites is None:
        raise typer.Exit(
            "At least a test groupt or test suites is given. Aborted!!!")

    msg = f"options are: [{test_group_id}, {test_suites}, " \
        f"{provision_new}, {destroy_cluster}, {dist}, {lustre_branch}]"
    LOG.info(msg)

    #
    # get cluster_dir and lock
    #
    cluster_provision = Provision(provision_new, dist,
                                  kernel_version=kernel_version,
                                  lustre_branch=lustre_branch)
    cluster_dir, cluster_lock = get_cluster_dir(
        provision_new, cluster_provision, dist)
    if not cluster_dir:
        sys.exit("get cluster fail!!")

    #
    # do provision, node init and test stages.
    #
    LOG.info("cluster dir:'%s'", cluster_dir)
    try:
        #
        # prrovision stage
        #
        LOG.info("Provision stage running...")
        result = cluster_provision.provision(cluster_dir)
        if result:
            LOG.info("Provision stage is successful")
            # (liuxl)TODO: move below part into Provision class
            for _, client in cluster_provision.ssh_clients.items():
                client.close()
        else:
            sys.exit("The provision process is not successful")

        #
        # node init stage
        # (liuxl)TODO: This should only do reboot for old cluster
        #
        LOG.info("Node init stage running...")
        node_map = utils.read_node_info(path_join(cluster_dir,
                                                  const.NODE_INFO))

        multinode_conf_gen(node_map, cluster_dir)
        node_init(node_map, cluster_dir)
        LOG.info("Node init stage is successful")

        #
        # Run test stage
        #

        LOG.info("Test run stage running...")
        # Choose the first node as the test exec node.
        exec_node_ip = ""
        for _, node_info in node_map.items():
            if node_info[2] == const.CLIENT:
                exec_node_ip = node_info[1]
                break
        auster_test = Auster(test_group_id,
                             test_suites, exec_node_ip,
                             const.SHARED_NFS_DIR,
                             dist=dist,
                             lustre_branch=lustre_branch)
        rc = auster_test.run_test()

        if rc != const.TEST_SUCC:
            sys.exit("Test running is not pass")
        LOG.info("Test run stage is successful")
    finally:
        cluster_lock.release()
        # Destroy cluster if provision_new for on demand cluster
        # creation.
        if provision_new and destroy_cluster:
            cluster_provision.terraform_destroy()


if __name__ == "__main__":
    typer.run(main)
