MY PRODUCTS & PLANSSubscriptionsProduct UsageTrialsRegistration KeysResourcesDownloads
LicensingActivate F5 product registration key
IhealthVerify the proper operation of your BIG-IP system
F5 UniversityGet up to speed with free self-paced courses
DevcentralJoin the community of 300,000+ technical peers
F5 CertificationAdvance your career with F5 Certification
Product ManualsProduct Manuals and Release notes
**Manual Chapter**:   Configuring Remote LDAP Authentication
## Applies To:
Show  Versions
### BIG-IP LTMConfiguring Remote LDAP Authentication
## Overview of remote LDAP authentication for application traffic
As an administrator in a large computing environment, you can set up the BIG-IP system to use this server to authenticate any network traffic passing through the BIG-IP system. This type of traffic passes through a virtual server and through Traffic Management Microkernel (TMM) interfaces. Remote authentication servers typically use one of these protocols:
To configure remote authentication for this type of traffic, you must create a configuration object and a profile that correspond to the type of authentication server you are using to store your user accounts. For example, if your remote authentication server is an LDAP server, you create an LDAP configuration object and an LDAP profile. When implementing a RADIUS, SSL OCSP, or CRLDP authentication module, you must also create a third type of object. For RADIUS and CRLDP authentication, this object is referred to as a server object. For SSL OCSP authentication, this object is referred to as an OCSP responder.  For remote LDAP authentication, the BIG-IP system provides two different LDAP modules, one of which includes support for SSL. For security reasons, F5 strongly recommends that you use the SSL Client Certificate LDAP authentication module instead of the less-secure LDAP module. This ensures that: certain data sent between the BIG-IP system and the LDAP server is protected, the bind password is stored securely, and the BIG-IP system verifies the identity of the LDAP server.
## Task summary for configuring remote LDAP authentication
To configure remote authentication for LDAP traffic, you must create a configuration object and a profile that correspond to the LDAP authentication server you are using to store your user accounts. You must also modify the relevant virtual server.  Use of this non-SSL LDAP authentication module is not secure. For security reasons, F5 strongly recommends that you use the SSL Client Certificate LDAP authentication module instead. This ensures that: certain data sent between the BIG-IP system and the LDAP server is protected, the bind password is stored securely, and the BIG-IP system verifies the identity of the LDAP server.
### Creating an LDAP configuration object for authenticating application traffic remotely
An  LDAP configuration object  specifies information that the BIG-IP system needs to perform the remote authentication. For example, the configuration object specifies the remote LDAP tree that the system uses as the source location for the authentication data.  Use of this non-SSL LDAP authentication module is not secure. For security reasons, F5 strongly recommends that you use the SSL Client Certificate LDAP authentication module instead. This ensures that: certain data sent between the BIG-IP system and the LDAP server is protected, the bind password is stored securely, and the BIG-IP system verifies the identity of the LDAP server.
You now have an LDAP configuration object that the LDAP authentication profile can reference.
### Creating a custom LDAP profile
The next task in configuring LDAP-based or Active Directory-based remote authentication on the BIG-IP system is to create a custom LDAP profile.
The custom LDAP profile appears in the  Profiles  list.
### Modifying a virtual server for LDAP authentication
The final task in the process of implementing authentication using a remote LDAP server is to assign the custom LDAP profile and a default LDAP authentication iRule to a virtual server that is configured to process HTTP traffic (that is, a virtual server to which an HTTP profile is assigned).The virtual server is assigned the custom LDAP profile.[Contact Support](https://www.google.com/url?sa=E&q=https%3A%2F%2Fwww.f5.com%2Fcompany%2Fcontact%2Fregional-offices%23product-support)Have a Question?[Support and Sales  >](https://www.google.com/url?sa=E&q=https%3A%2F%2Fwww.f5.com%2Fcompany%2Fcontact%2Fregional-offices%23product-support)Follow UsAbout F5EducationF5 SitesSupport Tasks
©2023 F5, Inc. All rights reserved.