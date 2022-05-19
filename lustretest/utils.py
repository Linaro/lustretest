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
