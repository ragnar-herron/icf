
Topic
You should consider using this procedure under the following conditions:
Your BIG-IP is licensed and provisioned with the BIG-IP APM module.
You want to restrict access to a virtual server using Lightweight Directory Access Protocol (LDAP) authentication.
Description
You can configure the BIG-IP APM system to prompt users for their LDAP authentication credentials when accessing a
virtual server.
Prerequisites
You must meet the following prerequisites to use this procedure:
The BIG-IP is configured with the virtual server to which you want to apply LDAP authentication.
You have previously deployed LDAP server(s) in your environment, and the BIG-IP system can access them.
Procedures
Creating a custom LDAP monitor
Creating the LDAP authentication profile
Creating the access profile
Creating the access policy
Applying the access profile to the virtual server
Creating a custom LDAP monitor
The following procedure outlines the steps to create a new BIG-IP APM LDAP authentication profile that references
existing LDAP servers of your environment.
Performing the following procedure should not have a negative impact on your system.Impact of procedure:
For example:
cn=Admin,cn=Users,dc=example,dc=com
K52354366: Creating a LDAP authentication profile and policy for virtual server authentication
https://my.f5.com/manage/s/article/K52354366
Published Date: Oct 05, 2020 UTC Updated Date: Feb 21, 2023 UTC
Applies to
BIG-IP APM : [16.1.3, 16.1.2, 16.1.1, 16.1.0, 16.1.X, 16.0.1, 16.0.0, 16.0.X, 16.X.X, 15.1.8, 15.1.7, 15.1.6, 15.1.5, 15.1.4,
15.1.3, 15.1.2, 15.1.1, 15.1.0, 15.1.X, 15.0.1, 15.0.0, 15.0.X, 15.X.X, 14.1.5, 14.1.4, 14.1.3, 14.1.2, 14.1.0, 14.1.X, 14.0.1,
14.0.0, 14.0.X, 14.X.X, 13.1.5, 13.1.4, 13.1.3, 13.1.1, 13.1.0, 13.1.X, 13.0.1, 13.0.0, 13.0.X, 13.X.X, 12.1.6, 12.1.5, 12.1.4,
12.1.3, 12.1.2, 12.1.1, 12.1.0, 12.1.X, 12.0.0, 12.0.X, 12.X.X]
1.
2.
3.
4.
5.
6.
7.
8.
9.
10.
11.
12.
13.
1.
2.
3.
4.
5.
6.
7.
8.
9.
10.
11.
Log in to the BIG-IP APM Configuration utility.
Go to  > .Local Traffic Monitors
Select .Create
Enter a name for the monitor.
Select .Type LDAP
Leave  at the default setting of .Parent Monitor ldap
For , enter a user name DN that can authenticate to the LDAP servers.User Name
For , enter the user's LDAP password.Password
For , enter the base search DN.Base
For example:
cn=Users,dc=example,dc=com
For , enter the LDAP filter.Filter
For example:
objectclass=*
Set  to the secure protocol encryption type the LDAP servers use or leave the setting at the default, Security
, if the LDAP server does not use it.None
For , select .Chase Referrals Yes
Select .Finished
Creating the LDAP authentication profile
The following procedure outlines the steps to create a new BIG-IP APM LDAP authentication profile that references
existing LDAP servers of your environment.
Performing the following procedure should not have a negative impact on your system.Impact of procedure:
Log in to the BIG-IP APM Configuration utility.
Go to  >  > .Access Authentication LDAP
: For BIG-IP 11.6.x through 12.x, go to  >  > .Note Access Policy AAA Servers LDAP
Select .Create
Enter a name for the LDAP authentication profile.
For , select .Server Connection Use Pool
: For a  LDAP server you can also select .Note singular Direct
For , enter a  and IP address of the LDAP server.Server Pool name
Select . Add
Repeat steps 6 and 7 to add the rest of the LDAP pool members.
For , select the custom LDAP monitor you created in the first procedure.Server Pool Monitor
Select the protocol used by the LDAP servers.Mode
: Ensure that you select a server pool monitor that is compatible with the protocol.Note
For , enter the LDAP server specific configuration details and the admin password.Admin DN
For example:
cn=Administrator,CN=Users,DC=example,DC=com
12.
1.
2.
3.
4.
5.
6.
7.
8.
1.
2.
3.
4.
5.
6.
7.
8.
9.
10.
11.
12.
13.
14.
15.
Select .Finished
Creating the access profile
The following procedure outlines the steps to create a new BIG-IP APM access profile and configure the associated
access policy to present a logon page and authenticate users to existing LDAP server or servers in your environment.
: Performing the following procedure should not have a negative impact on your system.Impact of procedure
Go to  > .Access Profiles/Policies
Select .Create
Enter a name for the access profile.
For , select .Profile Type LTM-APM
For , select  or .Profile Scope Virtual Server Profile
For , leave at the default of .Customization Type Modern
Important: If you are configuring an application access control scenario where you are using an HTTPS
virtual server to authenticate and then sending the user to an existing HTTP virtual server to use an
application, clear the check box for the  > setting.SSO Across Authentication Domains Secure
For , for , select the languages you want to use and move themLanguage Settings Factory BuiltIn Languages
to .Accepted Languages
Select .Finished
Creating the access policy
The following procedure outlines the steps to create a new BIG-IP APM access profile and configure the associated
access policy to present a logon page and authenticate users to existing LDAP server or servers in your environment.
Performing the following procedure should not have a negative impact on your system.Impact of procedure:
Go to  > .Access Profiles/Policies
Next to your access profile, select to open the Virtual Policy Editor (VPE).Edit
In VPE, select the Add icon ( ).+
Select .Logon Page
Select .Add Item
Modify the .Form Header Text
Select .Save
After the  agent, select the Add icon ( ).Logon Page +
Select the  tab.Authentication
Select .LDAP Auth
Select .Add Item
For , select the LDAP server profile created in the previous procedure.Server
Complete the  and  to match the configuration of the LDAP servers.SearchDN SearchFilter
For example:
cn=Users,dc=example,dc=com
Example SearchFilter:
(sAmAccountName=%{session.logon.last.username})
Select .Save
Select the  ending of the  branch.Deny Successful
F5 support engineers who work directly with customers write Support Solution and Knowledge articles, which give you
immediate access to mitigation, workaround, or troubleshooting suggestions.
Related Content
K41837805: Creating a RADIUS authentication profile and policy for virtual server authentication
K34150119: Creating a TACACS+ authentication profile and policy for virtual server authentication
K17472: Overview of LDAP Monitoring (11.x - 15.x)
16.
17.
18.
19.
1.
2.
3.
4.
Select .Allow
Select .Save
Select .Apply Access Policy
Select  to exit VPE.Close
Applying the access profile to the virtual server
The following procedure outlines the steps to apply the newly create access profile and the associated access policy to
an existing virtual server.
: Performing the following procedure requires users to present their LDAP credentials whenImpact of procedure
accessing a virtual server that is configured with the BIG-IP APM access profile/policy.
Go to  >  > .Local Traffic Virtual Servers Virtual Server List
Select the name of the virtual server to which you want to apply the LDAP authentication access profile.
For , select the recently created access profile.Access Policy
Select .Update