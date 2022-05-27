import os
from os import environ as env
from os import listdir
from os.path import isdir, join as path_join
import subprocess

results_top_dir = env['WORKSPACE'] + '/test_logs/log-' + env['BUILD_ID']

for d in listdir(results_top_dir):
    result_dir = path_join(results_top_dir, d)
    if isdir(result_dir):
        cmd = [os.getcwd() + "/maloo_upload.sh", result_dir]
        subprocess.call(cmd)
