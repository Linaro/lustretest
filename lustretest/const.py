import os

CLIENT = 'CLIENT'
MDS = 'MDS'
OST = 'OST'

TEST_WORKSPACE = '/home/centos/workspace/node/'
NODE_INFO = 'lustre-test-node.conf'
SSH_PRIVATE_KEY = TEST_WORKSPACE + 'id_rsa'
TEST_ARGS_CONFIG = os.getcwd() + '/cfg/test-groups.yaml'

TERRAFORM_CONF_TEMPLATE_DIR = os.getcwd() + '/tf'
TERRAFORM_VARIABLES_JSON = "terraform.tfvars.json"
TERRAFORM_BIN = "/home/centos/terraform"
SSH_CONFIG = os.getcwd() + '/cfg/ssh_config'

# Test Node Related
TEST_NODE_ROOT = '/root'
SSH_CFG_DIR = TEST_NODE_ROOT + '/.ssh'
REMOTE_SSH_CONFIG = SSH_CFG_DIR + '/config'
DEFAULT_SSH_USER = 'root'
CLOUD_INIT_CHECK_USER = 'jenkins'
REBOOT_TIMEOUT = 1200
CLOUD_INIT_TIMEOUT = 3600
CLOUD_INIT_FINISH = "/var/lib/cloud/instance/boot-finished"
LUSTER_TEST_CFG = '/usr/lib64/lustre/tests/cfg/'
# Lustre Test
MULTI_NODE_CONFIG = "multinode.sh"
LUSTRE_TEST_CFG_DIR = "/usr/lib64/lustre/tests/cfg"

MDS_DISK1 = "/dev/vdb"
MDS_DISK2 = "/dev/vdc"

OST_DISK1 = "/dev/vdb"
OST_DISK2 = "/dev/vdc"
OST_DISK3 = "/dev/vdd"
OST_DISK4 = "/dev/vde"
OST_DISK5 = "/dev/vdf"
OST_DISK6 = "/dev/vdg"
OST_DISK7 = "/dev/vdh"
OST_DISK8 = "/dev/vdi"

#
# Node Configuration File
# hostname IP TYPE
# TYPE: CLIENT MDS OST
#

# Terraform Resource Name
LUSTRE_CLUSTER_PREFIX = "lustre-"
MAX_NODE_NUM = 5
TF_VAR_NODE_PREFIX = "node"

MAX_CLIENT_NUM = 2
TF_VAR_CLIENT_PORT_PREFIX = "lustre_client"
MAX_MDS_NUM = 2
TF_VAR_MDS_PORT_PREFIX = "lustre_mds"
MAX_OST_NUM = 1
TF_VAR_OST_PORT_PREFIX = "lustre_ost"

TF_VAR_VM_IMAGE = "image"
VM_IMAGES = {
    'el8': 'vm-almalinux-8',
    'oe2203sp1': 'vm-openeuler-minimal-22.03-LTS-SP1'
}

TERRAFORM_CLIENT01_IP = "client01_ip"
TERRAFORM_CLIENT02_IP = "client02_ip"
TERRAFORM_MDS01_IP = "mds01_ip"
TERRAFORM_MDS02_IP = "mds02_ip"
TERRAFORM_OST01_IP = "ost01_ip"

TERRAFORM_CLIENT01_HOSTNAME = "client01_hostname"
TERRAFORM_CLIENT02_HOSTNAME = "client02_hostname"
TERRAFORM_MDS01_HOSTNAME = "mds01_hostname"
TERRAFORM_MDS02_HOSTNAME = "mds02_hostname"
TERRAFORM_OST01_HOSTNAME = "ost01_hostname"

MAX_MDS_VOL_NUM = 4
TF_VAR_MDS_VOL_PREFIX = "mds_volume"
MAX_OST_VOL_NUM = 8
TF_VAR_OST_VOL_PREFIX = "ost_volume"

TEST_FAIL = -1
TEST_SUCC = 0
SHARED_NFS_DIR = "/tmp/test_logs/"
