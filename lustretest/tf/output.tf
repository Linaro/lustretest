output "client01_ip" {
  value = "${openstack_compute_instance_v2.client01.network[0].fixed_ip_v4}"
}

output "client02_ip" {
  value = "${openstack_compute_instance_v2.client02.network[0].fixed_ip_v4}"
}

output "mds01_ip" {
  value = "${openstack_compute_instance_v2.mds01.network[0].fixed_ip_v4}"
}

output "mds02_ip" {
  value = "${openstack_compute_instance_v2.mds02.network[0].fixed_ip_v4}"
}

output "ost01_ip" {
  value = "${openstack_compute_instance_v2.ost01.network[0].fixed_ip_v4}"
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
