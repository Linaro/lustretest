# Define required providers
terraform {
required_version = ">= 0.14.0"
  required_providers {
    openstack = {
      source  = "terraform-provider-openstack/openstack"
      version = "~> 1.35.0"
    }
  }
}

# Configure the OpenStack Provider
provider "openstack" {
  user_name   = "lustre-test"
  tenant_name = "lustre-test"
  password    = "g4WAYE5z"
  auth_url    = "https://uk2.linaro.cloud:5000/v3.0"
  region      = "Cambridge"
}