import re


def sanitize(file_data):
    """ Take a file content and sanitize it into a valid yaml """

    output = []

    for line in file_data.splitlines():
        if "error:" in line:
            line = line.replace("\\", "").replace('"', '')
            line = re.sub(r"(error\:)\s*(.*)", r'\1 "\2"', line)

        output.append(line)

    return "\n".join(output)
