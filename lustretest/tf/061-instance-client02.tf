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
