import os

CLIENT = 'CLIENT'
MDS = 'MDS'
OST = 'OST'

PROVISION_NEW_CLUSTER = False
TEST_WORKSPACE = '/home/centos/workspace/node/'
NODE_INFO = TEST_WORKSPACE + 'lustre-test-node.conf'
SSH_PRIVATE_KEY = '/home/centos/workspace/node/id_rsa'
SSH_PRIKEY_EXEC = '/home/jenkins/.ssh'


TERRAFORM_CONF_TEMPLATE_DIR = os.getcwd() + '/tf'
TERRAFORM_CONF_DIR = '/home/centos/tf/'

TERRAFORM_EXIST_CONF = "lustre-NJQWIdPR/"

TERRAFORM_VARIABLES_JSON = "terraform.tfvars.json"
TERRAFORM_BIN = "/home/centos/terraform"

# test_type
TEST_SERVER = "TEST_SERVER"
TEST_CLIENT = "TEST_CLIENT"



TERRAFORM_CLIENT01_HOSTNAME = "client01_hostname"
TERRAFORM_CLIENT02_HOSTNAME = "client02_hostname"
TERRAFORM_MDS01_HOSTNAME = "mds01_hostname"
TERRAFORM_MDS02_HOSTNAME = "mds02_hostname"
TERRAFORM_OST01_HOSTNAME = "ost01_hostname"

DEFAULT_SSH_USER = 'jenkins'
CLOUD_INIT_TIMEOUT = 900
CLOUD_INIT_FINISH = "/var/lib/cloud/instance/boot-finished"

LUSTER_TEST_CFG = '/usr/lib64/lustre/tests/cfg/'

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
LUSTRE_CLUSTER_PREFIX = "lustre_"
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

# Lustre Test
MULTI_NODE_CONFIG = "multinode.sh"
LUSTRE_TEST_CFG_DIR = "/usr/lib64/lustre/tests/cfg"
