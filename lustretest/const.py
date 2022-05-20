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
CLOUD_INIT_CHECK_USER = 'centos'
REBOOT_TIMEOUT = 300
CLOUD_INIT_TIMEOUT = 900
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
LUSTRE_NODE_NUM_01 = "-01"
LUSTRE_NODE_NUM_02 = "-02"
LUSTRE_NODE_NUM_03 = "-03"
LUSTRE_NODE_NUM_04 = "-04"
LUSTRE_NODE_NUM_05 = "-05"

LUSTRE_NODE_01 = "node01"
LUSTRE_NODE_02 = "node02"
LUSTRE_NODE_03 = "node03"
LUSTRE_NODE_04 = "node04"
LUSTRE_NODE_05 = "node05"

LUSTRE_CLIENT01_PORT = "lustre_client01_port"
LUSTRE_CLIENT02_PORT = "lustre_client02_port"
LUSTRE_MDS01_PORT = "lustre_client01_port"
LUSTRE_MDS02_PORT = "lustre_client01_port"
LUSTRE_OST01_PORT = "lustre_client01_port"

LUSTRE_CLIENT01_PORT_PREFIX = "_client01_port"
LUSTRE_CLIENT02_PORT_PREFIX = "_client02_port"
LUSTRE_MDS01_PORT_PREFIX = "_mds01_port"
LUSTRE_MDS02_PORT_PREFIX = "_mds02_port"
LUSTRE_OST01_PORT_PREFIX = "_ost01_port"

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

TEST_FAIL = -1
TEST_SUCC = 0
SHARED_NFS_DIR = "/tmp/test_logs/"
