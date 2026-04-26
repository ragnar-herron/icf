
Contents:
Version notice:Lab 2 - Create the APM configuration and policy[¶](https://www.google.com/url?sa=E&q=https%3A%2F%2Fclouddocs.f5.com%23lab-2-create-the-apm-configuration-and-policy)
It time to creeate a new APM policy with Network Access resource
## Create the Network Access resources[¶](https://www.google.com/url?sa=E&q=https%3A%2F%2Fclouddocs.f5.com%23create-the-network-access-resources)
### Create a new Lease Pool[¶](https://www.google.com/url?sa=E&q=https%3A%2F%2Fclouddocs.f5.com%23create-a-new-lease-pool)
### Create a new Address Space[¶](https://www.google.com/url?sa=E&q=https%3A%2F%2Fclouddocs.f5.com%23create-a-new-address-space)
In order to keep RDP session up in UDF, we will use split-tunneling. Else we will lose control of the RDP session if we use full-tunnel
Note
10.1.20.0/24 is the back end network. The RDP session is on 10.1.1.0/24 network. Meaning we will keep control of the RDP session when tunnel will be up.
### Create the Network Access profile[¶](https://www.google.com/url?sa=E&q=https%3A%2F%2Fclouddocs.f5.com%23create-the-network-access-profile)
In Network Settings tab
## Create the APM policy and VPE[¶](https://www.google.com/url?sa=E&q=https%3A%2F%2Fclouddocs.f5.com%23create-the-apm-policy-and-vpe)
Create a new policy
## Create the Connectivity profile[¶](https://www.google.com/url?sa=E&q=https%3A%2F%2Fclouddocs.f5.com%23create-the-connectivity-profile)
This is where the OIDC Client mode is set. We will create a custom Connectivity profile so that Edge Client uses OIDC as authentication. Else, Edge client will use the embedded browser (webview)
In Win/Mac Edge Client section, under Oauth settings, set the right OIDC Client values (same as previous use case)
In Win/Mac Edge Client section, under Server List, add en entry
Note
As you can notice, we use the same client settings as previous lab, but instead of using the Client agent in the VPE for APM, we use the Client Agent of the Edge client.
## Create the Virtual Server[¶](https://www.google.com/url?sa=E&q=https%3A%2F%2Fclouddocs.f5.com%23create-the-virtual-server)