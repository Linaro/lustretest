from distutils.util import strtobool
import logging
from os import listdir
from os.path import basename, isdir, join as path_join
import sys

from filelock import Timeout, FileLock

from auster import Auster
import const
from node_init import multinode_conf_gen, node_init
from provision import Provision
import utils

#
# Provision: get cluster_dir and lock
#


def get_cluster_dir(logger, provision_new, cluster_provision):
    if provision_new:
        cluster_dir = cluster_provision.get_cluster_dir()
        cluster_lock = FileLock(cluster_dir + "/.lock", timeout=0)
        try:
            cluster_lock.acquire()
            return cluster_dir, cluster_lock
        except Timeout:
            msg = basename(cluster_dir) + \
                "is in used, no cluster for test now!!"
            logger.info(msg)
    else:  # find an idle cluster
        clusters_top_dir = const.TEST_WORKSPACE
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
                logger.info(msg)

    return "", None


def main():
    logging.basicConfig(format='%(message)s',
                        level=logging.INFO)
    logger = logging.getLogger(__name__)
    rc = const.TEST_SUCC

    #
    # parse args
    #
    args = sys.argv[1:]
    if len(args) < 2:
        sys.exit("no exact args specified")
    test_group_id = args[0]
    if test_group_id not in const.LUSTRE_TEST_SUITE_NUM_LIST:
        sys.exit("The test group: " + args[0] + " is not support")
    provision_new = bool(strtobool(args[1]))
    if provision_new and len(args) == 3:
        destroy_cluster = bool(strtobool(args[2]))
    else:
        destroy_cluster = False

    #
    # get cluster_dir and lock
    #
    cluster_provision = Provision(logger, provision_new)
    cluster_dir, cluster_lock = get_cluster_dir(
        logger, provision_new, cluster_provision)
    if not cluster_dir:
        sys.exit("get cluster fail!!")

    #
    # do provision, node init and test stages.
    #
    logger.info("cluster dir:'%s'", cluster_dir)
    try:
        #
        # prrovision stage
        #
        logger.info("Provision stage running...")
        result = cluster_provision.provision(cluster_dir)
        if result:
            logger.info("Provision stage is successful")
            # (liuxl)TODO: move below part into Provision class
            for _, client in cluster_provision.ssh_clients.items():
                client.close()
        else:
            sys.exit("The provision process is not successful")

        #
        # node init stage
        # (liuxl)TODO: This should only do reboot for old cluster
        #
        logger.info("Node init stage running...")
        node_map = utils.read_node_info(path_join(cluster_dir,
                                                  const.NODE_INFO))

        if provision_new:
            multinode_conf_gen(node_map, cluster_dir)
        node_init(node_map, cluster_dir, logger)
        logger.info("Node init stage is successful")

        #
        # Run test stage
        #

        logger.info("Test run stage running...")
        # Choose the first node as the test exec node.
        exec_node_ip = ""
        for _, node_info in node_map.items():
            if node_info[2] == const.CLIENT:
                exec_node_ip = node_info[1]
                break
        auster_test = Auster(logger, test_group_id, exec_node_ip)
        rc = auster_test.test()

        if rc != const.TEST_SUCC:
            sys.exit("Test running is not pass")
        logger.info("Test run stage is successful")
    finally:
        cluster_lock.release()
        # Destroy cluster if provision_new for on demand cluster
        # creation.
        if provision_new and destroy_cluster:
            cluster_provision.terraform_destroy()


# Args:                   test_group_id provision_new destroy_cluster
# E.g 2 args:                    1              False
# E.g 2 args:                    1              True
# E.g 3 args if provision new:   1              True    True
if __name__ == "__main__":
    main()
