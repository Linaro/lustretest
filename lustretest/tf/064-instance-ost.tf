#### INSTANCE Client01 ####
#
# Create instance
#
resource "openstack_compute_instance_v2" "ost01" {
  name        = var.node05
  image_name  = var.image
  flavor_name = var.flavor
  key_pair    = var.jenkinskey
  user_data   = file("cloud-init")
  network {
    port = openstack_networking_port_v2.ost01_port.id
  }
}

# Create network port
resource "openstack_networking_port_v2" "ost01_port" {
  name           = var.lustre_ost01_port
  network_id     = var.lustre_net
  admin_state_up = true
  security_group_ids = [
    var.lustre_sg,
  ]
  fixed_ip {
    subnet_id = var.lustre_subnet
  }
}

# Create floating ip
resource "openstack_networking_floatingip_v2" "ost01_floating" {
  pool = var.ext_net
}

# Attach floating ip to instance
resource "openstack_compute_floatingip_associate_v2" "ost01_floating_attach" {
  floating_ip = openstack_networking_floatingip_v2.ost01_floating.address
  instance_id = openstack_compute_instance_v2.ost01.id
}

# Create volume
resource "openstack_blockstorage_volume_v2" "ost01_volume01" {
  name = var.ost_volume01
  size = var.ost_size
}

resource "openstack_blockstorage_volume_v2" "ost01_volume02" {
  name = var.ost_volume02
  size = var.ost_size
}

resource "openstack_blockstorage_volume_v2" "ost01_volume03" {
  name = var.ost_volume03
  size = var.ost_size
}

resource "openstack_blockstorage_volume_v2" "ost01_volume04" {
  name = var.ost_volume04
  size = var.ost_size
}

resource "openstack_blockstorage_volume_v2" "ost01_volume05" {
  name = var.ost_volume05
  size = var.ost_size
}

resource "openstack_blockstorage_volume_v2" "ost01_volume06" {
  name = var.ost_volume06
  size = var.ost_size
}

resource "openstack_blockstorage_volume_v2" "ost01_volume07" {
  name = var.ost_volume07
  size = var.ost_size
}

resource "openstack_blockstorage_volume_v2" "ost01_volume08" {
  name = var.ost_volume08
  size = var.ost_size
}

# Attach volume to instance instance db
resource "openstack_compute_volume_attach_v2" "ost01_volume01_attach" {
  instance_id = openstack_compute_instance_v2.ost01.id
  volume_id   = openstack_blockstorage_volume_v2.ost01_volume01.id
}

resource "openstack_compute_volume_attach_v2" "ost01_volume02_attach" {
  instance_id = openstack_compute_instance_v2.ost01.id
  volume_id   = openstack_blockstorage_volume_v2.ost01_volume02.id
}

resource "openstack_compute_volume_attach_v2" "ost01_volume03_attach" {
  instance_id = openstack_compute_instance_v2.ost01.id
  volume_id   = openstack_blockstorage_volume_v2.ost01_volume03.id
}

resource "openstack_compute_volume_attach_v2" "ost01_volume04_attach" {
  instance_id = openstack_compute_instance_v2.ost01.id
  volume_id   = openstack_blockstorage_volume_v2.ost01_volume04.id
}

resource "openstack_compute_volume_attach_v2" "ost01_volume05_attach" {
  instance_id = openstack_compute_instance_v2.ost01.id
  volume_id   = openstack_blockstorage_volume_v2.ost01_volume05.id
}

resource "openstack_compute_volume_attach_v2" "ost01_volume06_attach" {
  instance_id = openstack_compute_instance_v2.ost01.id
  volume_id   = openstack_blockstorage_volume_v2.ost01_volume06.id
}

resource "openstack_compute_volume_attach_v2" "ost01_volume07_attach" {
  instance_id = openstack_compute_instance_v2.ost01.id
  volume_id   = openstack_blockstorage_volume_v2.ost01_volume07.id
}

resource "openstack_compute_volume_attach_v2" "ost01_volume08_attach" {
  instance_id = openstack_compute_instance_v2.ost01.id
  volume_id   = openstack_blockstorage_volume_v2.ost01_volume08.id
}
