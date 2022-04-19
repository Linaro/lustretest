# Params file for variables

#### GLANCE
variable "image" {
  type    = string
  default = "vm-centos-8-stream"
}

#### NEUTRON
variable "ext_net" {
  type    = string
  default = "ext-net"
}

variable "lustre_net" {
  type    = string
  default = "8621fad4-f90d-4d3e-b239-ac94c677c3f0"
}

variable "lustre_subnet" {
  type    = string
  default = "b1b32e6c-64a4-468c-9c1c-e31a2a06ccd5"
}

variable "lustre_sg" {
  type    = string
  default = "e81a5d9f-cd16-434d-8c47-340d067cda3a"
}

variable "lustre_client01_port" {
  type    = string
  default = "lustre_client01_port"
}

variable "lustre_client02_port" {
  type    = string
  default = "lustre_client02_port"
}

variable "lustre_mds01_port" {
  type    = string
  default = "lustre_mds01_port"
}

variable "lustre_mds02_port" {
  type    = string
  default = "lustre_mds02_port"
}

variable "lustre_ost01_port" {
  type    = string
  default = "lustre_ost01_port"
}

#### VM parameters
variable "flavor" {
  type    = string
  default = "vm.large"
}

variable "jenkinskey" {
  type    = string
  default = "jenkins"
}

variable "network" {
  type = map(string)
  default = {
    subnet_name = "lustre-test-network"
  }
}

variable "node01" {
  type    = string
  default = "lustre-node-01"
}

variable "node02" {
  type    = string
  default = "lustre-node-02"
}

variable "node03" {
  type    = string
  default = "lustre-node-03"
}

variable "node04" {
  type    = string
  default = "lustre-node-04"
}

variable "node05" {
  type    = string
  default = "lustre-node-05"
}

# Volume info
variable "mds_volume01" {
  type    = string
  default = "mds_volume01"
}

variable "mds_volume02" {
  type    = string
  default = "mds_volume02"
}

variable "mds_volume03" {
  type    = string
  default = "mds_volume03"
}

variable "mds_volume04" {
  type    = string
  default = "mds_volume04"
}

variable "ost_volume01" {
  type    = string
  default = "ost_volume01"
}

variable "ost_volume02" {
  type    = string
  default = "ost_volume02"
}

variable "ost_volume03" {
  type    = string
  default = "ost_volume03"
}

variable "ost_volume04" {
  type    = string
  default = "ost_volume04"
}

variable "ost_volume05" {
  type    = string
  default = "ost_volume05"
}

variable "ost_volume06" {
  type    = string
  default = "ost_volume06"
}

variable "ost_volume07" {
  type    = string
  default = "ost_volume07"
}

variable "ost_volume08" {
  type    = string
  default = "ost_volume08"
}

variable "mds_size" {
  type    = number
  default = 50
}

variable "ost_size" {
  type    = number
  default = 60
}
