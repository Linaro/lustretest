import const


def read_node_info(config_path):
    node_map = {}
    with open(config_path, 'r') as f2:
        i = 0
        line = f2.readline()
        while line is not None and line != '':
            node_info = line.split()
            node_map[i] = [node_info[0], node_info[1], node_info[2]]
            line = f2.readline()
            i += 1

    return node_map


def get_test_list(test_suites):
    if test_suites == "1":
        return const.LUSTRE_TEST_SUITE_1
    if test_suites == "2":
        return const.LUSTRE_TEST_SUITE_2
    if test_suites == "3":
        return const.LUSTRE_TEST_SUITE_3
    if test_suites == "4":
        return const.LUSTRE_TEST_SUITE_4
    if test_suites == "5":
        return const.LUSTRE_TEST_SUITE_5
    if test_suites == "6":
        return const.LUSTRE_TEST_SUITE_6
    return ""
