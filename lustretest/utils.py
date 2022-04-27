import const
import os


def read_node_info(config_path):
    node_map = {}
    test_suites = ""
    with open(config_path, 'r') as f2:
        line = f2.readline()
        test_info = line.split()
        test_suites = test_info[1]
        i = 0
        line = f2.readline()
        while line is not None and line != '':
            node_info = line.split()
            node_map[i] = [node_info[0], node_info[1], node_info[2]]
            line = f2.readline()
            i += 1

    return node_map, get_test_list(test_suites)


def get_test_list(test_suites):
    if test_suites == "1":
        return const.LUSTRE_TEST_SUITE_1
    elif test_suites == "2":
        return const.LUSTRE_TEST_SUITE_2
    elif test_suites == "3":
        return const.LUSTRE_TEST_SUITE_3
    elif test_suites == "4":
        return const.LUSTRE_TEST_SUITE_4
    elif test_suites == "5":
        return const.LUSTRE_TEST_SUITE_5
    elif test_suites == "6":
        return const.LUSTRE_TEST_SUITE_6
    else:
        return


def find_node_conf_dir(test_suites_num):
    node_conf_dir = const.TEST_WORKSPACE + const.TEST_SUITES_PREFIX + test_suites_num
    if not os.path.exists(node_conf_dir):
        os.mkdir(node_conf_dir)
    return node_conf_dir + '/'