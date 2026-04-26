MY PRODUCTS & PLANSSubscriptionsProduct UsageTrialsRegistration KeysResourcesDownloads
LicensingActivate F5 product registration key
IhealthVerify the proper operation of your BIG-IP system
F5 UniversityGet up to speed with free self-paced courses
DevcentralJoin the community of 300,000+ technical peers
F5 CertificationAdvance your career with F5 Certification
Product ManualsProduct Manuals and Release notes
**Manual Chapter**:   LDAP and LDAPS Authentication
## Applies To:
Show  Versions
### BIG-IP APMLDAP and LDAPS Authentication
## About LDAP and LDAPS authentication
You can use LDAPS in place of LDAP when the authentication messages between the Access Policy Manager and the LDAP server must be secured with encryption. However, there are instances where you will not need LDAPS and the security it provides. For example, authentication traffic happens on the internal side of Access Policy Manager, and might not be subject to observation by unauthorized users. Another example of when not to use LDAPS is when authentication is used on separate VLANs to ensure that the traffic cannot be observed by unauthorized users. How LDAP works LDAPS is achieved by directing LDAP traffic over a virtual server that uses server side SSL to communicate with the LDAP server. Essentially, the system creates an LDAP AAA object that has the address of the virtual server. That virtual server (with server SSL) directs its traffic to a pool, which has as a member that has the address of the LDAP server.  How LDAPS works If using LDAP or RADIUS authentication in such a way that requires multiple authentication requests, then One Time Password will not work (because password usage is reached on the second request).
## About how APM handles binary values in LDAP attributes
For LDAP, Access Policy Manager (APM) converts an attribute value to hex only if the value contains unprintable characters. If the session variable contains several values, and one or more of those values is unprintable, then APM converts only those particular values to hex. An attribute with a single unprintable value 9302eb80.session.ldap.last.attr.objectGUID 34 / 0xfef232d3039be9409a72bfc60bf2a6d0 Attribute with multiple values, both printable and unprintable (binary) 29302eb80.session.ldap.last.attr.memberOf 251 | / CN=printable group,OU=groups,OU=someco,DC=smith, / DC=labt,DC=fp,DC=somelabnet,DC=com | / 0x434e3d756e7072696e7461626c6520c2bdc2a12067726f75702c4f553d67726f7570732c4f553d66352c / 44433d73686572776f6f642c44433d6c6162742c44433d66702c44433d66356e65742c44433d636f6d |
## About AAA high availability
Using AAA high availability with Access Policy Manager (APM), you can configure multiple authentication servers to process requests, so that if one authentication server goes down or loses connectivity, the others can resume authentication requests, and new sessions can be established, as usual.  Although new authentications fail if the BIG-IP system loses connectivity to the server, existing sessions are unaffected provided that they do not attempt to re-authenticate.  APM supports the following AAA servers for high availability: RADIUS, Active Directory, LDAP, CRLDP, and TACACS+. APM supports high availability by providing the option to create a pool of server connections when you configure the supported type of AAA server.  If you use AAA with pools, such as RADIUS pools or Active Directory pools, APM assigns each pool member with a different number for the pool member's priority group value. APM must define each pool member with a different priority group because AAA load balancing is not used. The priority group number increases automatically with each created pool member. Alternative AAA pool configurations can be defined manually using the full flexibility of Local Traffic Manager (LTM) if high availability is desired.
## Task summary for configuring for LDAPS authentication
This task list includes all steps required to set up this configuration. If you are adding LDAPS authentication to an existing access policy, you do not need to create another access profile and the access policy might already include a logon page.
### Configuring an LDAPS AAA server in APM
You create an LDAPS AAA server when you need to encrypt authentication messages between Access Policy Manager (APM) and the LDAP server.
The new LDAPS server displays on the LDAP Server list.
### Create an access profile
You create an access profile to provide the access policy configuration for a virtual server that establishes a secured session.
From the  Profile Type  list, select one these options:
From the  Profile Scope  list, select one these options to define user scope:
The access profile displays in the Access Profiles List. Default-log-setting is assigned to the access profile.
### Verify log settings for the access profile
Confirm that the correct log settings are selected for the access profile to ensure that events are logged as you intend.  Log settings are configured in the  Access Overview  Event Log  Settings  area of the product. They enable and disable logging for access system and URL request filtering events. Log settings also specify log publishers that send log messages to specified destinations.
An access profile is in effect when it is assigned to a virtual server.
### Configuring LDAPS authentication
You configure an access policy with an LDAP Auth action to provide LDAP authentication for users.
This creates a basic access policy that collects credentials and uses them to authenticate with an LDAP server over SSL. In practice, an access policy might include additional types of authentication and might also assign ACLS and resources  If you use LDAP Query, Access Policy Manager does not query for the primary group and add it to the  memberOf  attribute. You must manually look up the attribute  memberOf  as well as the primary group.
### Creating a virtual server for LDAPS
You should have an Access Policy Manager LDAP AAA server configured in LDAPS mode. You create a virtual server to handle LDAP traffic and to encrypt authentication messages between Access Policy Manager and the LDAP server.  An AAA server does not load-balance. Do not select a local traffic pool for this virtual server.
### Testing LDAPS authentication
Before starting this procedure, make sure that all the appropriate steps were performed to create an LDAPS authentication.
## Test AAA high availability for supported authentication servers
To effectively test that high availability works for your authentication servers, you should have two servers that are accessible, where you can remove one of them from the network.  High availability is supported for these authentication server types only: RADIUS, Active Directory, LDAP, CRLDP, and TACACS+. If you configured a supported authentication server type to use a pool of connection servers, you can test the configuration using these steps.
## Example of LDAP auth and query default rules
In this example, after successful authentication, the system retrieves a user group using an LDAP query. Resources are assigned to users and users are directed to a webtop if the user group has access to the network access resources. In this figure, the default branch rule for LDAP query was changed to check for a specific user group attribute. Example of an access policy for LDAP auth query
## Importing LDAP user groups
Import user groups from an LDAP server to make them available for assigning resources to an LDAP group. When you configure the LDAP Group Resource Assign access policy item, you can type group names to exactly match those on the LDAP server, or you can select them from the imported list of groups.
### Assigning resources to an LDAP group
You can select groups from a list that you upload from an LDAP server; alternately, or in addition. you can type group names to exactly match LDAP groups. If you plan to select groups and have not updated the list recently, update it from the Groups screen for the AAA LDAP server before you start.  Use an LDAP Group Resource Assign action to assign resources to one or more groups that are configured on the LDAP server. For every group to which a user belongs, the corresponding resources will be assigned to the session.
Repeat these steps for each type of resource that you require. The screen displays one tab for each resource type.
This configures an LDAP group resource assign action and adds it to the access policy.
## LDAP authentication session variables
When the LDAP Auth access policy item runs, it populates session variables which are then available for use in access policy rules. The tables list the session variables for the LDAP Auth access policy items and for a logon access policy item.
## Session variables for LDAP authentication
Session Variable Description   session.ldap.last.authresult Provides the result of the LDAP authentication. The available values are:
session.ldap.last.errmsg Useful for troubleshooting, and contains the last error message generated for LDAP, for example  aad2a221.ldap.last.errmsg .
## Common session variables
Session Variable Description   session.logon.last.username Provides user credentials. The  username  string is stored after encrypting, using the system's client key.  session.logon.last.password Provides user credentials. The  password  string is stored after encrypting, using the system's client key.
## UserDN settings in LDAP
The following is an example of a typical UserDN usage for LDAP.   Access Policy Manager attempts to bind with the LDAP server using the supplied DN and user-entered password. If the bind succeeds, that is, authentication succeeds, the user is validated. If the bind fails, the authentication fails. This value is a fully qualified DN of the user with rights to run the query. Specify this value in lowercase and without spaces to ensure compatibility with some specific LDAP servers. The specific content of this string depends on your directory layout. For example, in an LDAP structure, a typical UserDN for query would be similar to the following string:  cn=%{session.logon.last.username}, cn=users, dc=sales, dc=com. Access Policy Manager supports using session variables in the  SearchFilter ,  SearchDN , and  UserDN  settings. For example, if you want to use the user’s CN from the user’s SSL certificate as input in one of these fields, you can use the session variable  session.ssl.cert.last.cn  in place of  session.logon.last.username .
## LDAP authentication and query troubleshooting tips
You might run into problems with LDAP authentication and query in some instances. Follow these tips to try to resolve any issues you might encounter.
## LDAP auth and query troubleshooting
Possible error messages Possible explanations and corrective actions   LDAP auth failed
LDAP query failed
## Additional troubleshooting tips for LDAP authentication
You should Steps to take   Check that your access policy is attempting to perform authentication
Make sure that your log level is set to the appropriate level. The default log level is  notice   Confirm network connectivity
Confirm network connectivity
Check the LDAP server configuration
A good test is to use full administrative credentials with all rights. If that works, you can use less powerful credentials for verification.   Capture a tcpdump Use the tcpdump utility on the BIG-IP system to record activities between Access Policy Manager and the authentication server when authentication attempts are made.If you decide to escalate the issue to customer support, you must provide a capture of the tcpdump when you encounter authentication issues that you cannot otherwise resolve on your own.[Contact Support](https://www.google.com/url?sa=E&q=https%3A%2F%2Fwww.f5.com%2Fcompany%2Fcontact%2Fregional-offices%23product-support)Have a Question?[Support and Sales  >](https://www.google.com/url?sa=E&q=https%3A%2F%2Fwww.f5.com%2Fcompany%2Fcontact%2Fregional-offices%23product-support)Follow UsAbout F5EducationF5 SitesSupport Tasks
©2023 F5, Inc. All rights reserved.