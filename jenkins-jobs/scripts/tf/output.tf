output "client01_ip" {
  value = "${openstack_networking_floatingip_v2.client01_floating.address}"
}

output "client02_ip" {
  value = "${openstack_networking_floatingip_v2.client02_floating.address}"
}

output "mds01_ip" {
  value = "${openstack_networking_floatingip_v2.mds01_floating.address}"
}

output "mds02_ip" {
  value = "${openstack_networking_floatingip_v2.mds02_floating.address}"
}

output "ost01_ip" {
  value = "${openstack_networking_floatingip_v2.ost01_floating.address}"
}

output "client01_hostname" {
  value = "${openstack_compute_instance_v2.client01.name}"
}

output "client02_hostname" {
  value = "${openstack_compute_instance_v2.client02.name}"
}

output "mds01_hostname" {
  value = "${openstack_compute_instance_v2.mds01.name}"
}

output "mds02_hostname" {
  value = "${openstack_compute_instance_v2.mds02.name}"
}

output "ost01_hostname" {
  value = "${openstack_compute_instance_v2.ost01.name}"
}
