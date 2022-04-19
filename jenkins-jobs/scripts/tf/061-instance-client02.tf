#### INSTANCE Client01 ####
#
# Create instance
#
resource "openstack_compute_instance_v2" "client02" {
  name        = var.node02
  image_name  = var.image
  flavor_name = var.flavor
  key_pair    = var.jenkinskey
  user_data   = file("cloud-init")
  network {
    port = openstack_networking_port_v2.client02_port.id
  }
}

# Create network port
resource "openstack_networking_port_v2" "client02_port" {
  name           = var.lustre_client02_port
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
resource "openstack_networking_floatingip_v2" "client02_floating" {
  pool = var.ext_net
}

# Attach floating ip to instance
resource "openstack_compute_floatingip_associate_v2" "client02_floating_attach" {
  floating_ip = openstack_networking_floatingip_v2.client02_floating.address
  instance_id = openstack_compute_instance_v2.client02.id
}
