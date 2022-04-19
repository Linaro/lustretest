# The Lustre Builder

This repo include all the script we needs for Lustre Arm64 external Builder and Tester CI

## Lustre CI pipeline

```mermaid
graph TD
A[Terraform OpenStack]-->B[Node Init]
B-->C[Cluster Reboot]
C-->D[Auster Run Test]
D-->E[Upload Maloo DB]
E-->F[Keep/Destroy Cluster]
```

The terraform Provisioner module has several steps

```mermaid
graph TD
A[Prepare tf conf]
A-->|Provision New| B[Prepare tf configuration]
A-->|Use existing cluster| C[Use existing tf config]
B-->D[Generate tfvars and dir]
D-->E[Terraform Init]
E-->F[Terraform Apply]
C-->D
F-->G[Node Check]
G-->|Provision New| I[Wait Cloud-init Finished Flags]
G-->|Use existing cluster| J[Install new Lustre RPMS]
I-->K[Write node-info config]
J-->K
```

The node init module has several steps

```mermaid
graph TD
A[Abstract the node-info config]
A-->B[Write to node_map]
B-->C[Begin Init all nodes]
C-->E[Scp private key to all nodes]
E-->F[Write /etc/hosts]
F-->G[Generate Lustre test file]
```
