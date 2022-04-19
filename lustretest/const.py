
CLIENT = 'CLIENT'
MDS = 'MDS'
OST = 'OST'

TEST_WORKSPACE = '/home/centos/workspace/'
SSH_PRIVATE_KEY = '/home/centos/workspace/node/id_rsa'
SSH_PRIKEY_EXEC = '/home/centos/.ssh/'
NODE_INFO = TEST_WORKSPACE + 'lustre-test-node.conf'
TERRAFORM_CONF_TEMPLATE_DIR = '/home/centos/tf/devbox/lustre/builder/tf'
TERRAFORM_CONF_DIR = '/home/centos/tf/'

TERRAFORM_EXIST_CONF = "lustre-NJQWIdPR/"

TERRAFORM_VARIABLES_JSON = "terraform.tfvars.json"
TERRAFORM_BIN = "/home/centos/terraform"

# test_type
TEST_SERVER = "TEST_SERVER"
TEST_CLIENT = "TEST_CLIENT"

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
