
Documentation>[Connectors](https://www.google.com/url?sa=E&q=https%3A%2F%2Fwww.logintc.com%2Fdocs%2Fconnectors%2F)>Two factor authentication for F5 BIG-IP APM
Last Updated: March 21, 2025
**Overview**The LoginTC RADIUS Connector is a complete[two-factor authentication](https://www.google.com/url?sa=E&q=https%3A%2F%2Fwww.logintc.com%2Ftwo-factor-authentication%2F)virtual machine packaged to run within your corporate network. The LoginTC RADIUS Connector enables F5 BIG-IP APM to use[LoginTC](https://www.google.com/url?sa=E&q=https%3A%2F%2Fwww.logintc.com%2F)for the most secure two-factor authentication. 
  Explore how LoginTC can add MFA to your F5 BIG-IP APM below.
**Subscription Requirement**Your organization requires the**Business**or**Enterprise**plan to use the Iframe mode of the LoginTC RADIUS Connector.Explore Pricing Plans
**User Experience**There are a wide variety of authentication mechanism users can use to perform MFA with the F5 BIG-IP APM product suite.**Video Instructions****Architecture**Authentication Flow
**Prefer Reading a PDF?**Download a PDF file with configuration instructions:
**Prerequisites**Before proceeding, please ensure you have the following:
Virtual Machine requirements:
**Create Application**Start by creating a LoginTC Application for your deployment. An Application represents a service (e.g. An application is a service (e.g., VPN or web application) that you want to protect. e) that you want to protect with LoginTC.
Create a LoginTC Application in[LoginTC Admin Panel](https://www.google.com/url?sa=E&q=https%3A%2F%2Fcloud.logintc.com%2F), follow[Create Application Steps](https://www.google.com/url?sa=E&q=https%3A%2F%2Fwww.logintc.com%2Fdocs%2Fguides%2Fapplications%23creating).
If you have already created a LoginTC Application for your deployment, then you may skip this section and proceed to[Installation](https://www.google.com/url?sa=E&q=https%3A%2F%2Fwww.logintc.com%2Fdocs%2Fconnectors%2Ff5%23installation).
**Installation**Download the latest LoginTC RADIUS Connector:
Import the virtual appliance your computer virtualization software
If you have an existing LoginTC RADIUS Connector your wish to import configurations then click**Yes, import configurations from an existing LoginTC RADIUS Connector**, otherwise click**No, continue to the adminsitration panel**:
**NOTE**These instructions assume a new environment. For a complete 2.X / 3.X to 4.X upgrade guide:[LoginTC RADIUS Connector Upgrade Guide](https://www.google.com/url?sa=E&q=https%3A%2F%2Fwww.logintc.com%2Fdocs%2Fguides%2Fconnector-upgrade.html)
The LoginTC RADIUS Connector runs a firewall with the following open ports:  Port   Protocol   Purpose   1812   UDP   RADIUS authentication   443   TCP   API traffic   8443   TCP   Web interface**Note: Username and Password**logintc-user  is used for SSH and web access. The default password is  logintcradius . You will be asked to change the default password on first boot of the appliance.**Configuration for F5 MFA**Endpoints describe how the appliance will authenticate your[RADIUS](https://www.google.com/url?sa=E&q=http%3A%2F%2Fen.wikipedia.org%2Fwiki%2FRADIUS)-speaking device with an optional first factor and LoginTC as a second factor. Each endpoint has**4 Sections**:
**1. LoginTC Settings**This section describes how the appliance itself authenticates against[LoginTC Admin Panel](https://www.google.com/url?sa=E&q=https%3A%2F%2Fcloud.logintc.com%2F)with your LoginTC[Application](https://www.google.com/url?sa=E&q=https%3A%2F%2Fwww.logintc.com%2Fdocs%2Fguides%2Fapplications). Only users that are part of your organization and added to the domain configured will be able to authenticate.
**2. User Directory**This section describes how the appliance will conduct an optional first factor. Either against an existing LDAP, Active Directory or RADIUS server. If no first factor is selected, then only LoginTC will be used for authentication.
**3. Challenge Strategy / Passthrough**This section describes whether the appliance will perform a LoginTC challenge for an authenticating user. The default is to challenge all users. However with either a static list or Active Directory / LDAP Group you can control whom gets challenged to facilitate seamless testing and rollout.
**4. Client Settings**This section describes which[RADIUS](https://www.google.com/url?sa=E&q=http%3A%2F%2Fen.wikipedia.org%2Fwiki%2FRADIUS)-speaking device will be connecting to the appliance and whether to encrypt API Key, password and secret parameters.
The**web interface**makes setting up an endpoint simple and straightforward. Each section has a**Test**feature, which validates each input value and reports all potential errors. Section specific validation simplifies troubleshooting and gets your infrastructure protected correctly faster.First Endpoint
Close the console and navigate to your appliance**web interface**URL. Use username  logintc-user  and the password you set upon initial launch of the appliance. You will now configure the LoginTC RADIUS Connector.
Create a new endpoint file by clicking**+ Create your first endpoint**:LoginTC Settings
A list of available Applications will be displayed from your LoginTC organization. Select which LoginTC**Application**to use:
Configure the application:
Configuration values:
Property   Explanation   Application ID   The 40-character Application ID,[retrieve Application ID](https://www.google.com/url?sa=E&q=https%3A%2F%2Fwww.logintc.com%2Fdocs%2Fguides%2Fapplications%23retrieve-application-id)Application API Key   The 64-character Application API Key,[retrieve Application API Key](https://www.google.com/url?sa=E&q=https%3A%2F%2Fwww.logintc.com%2Fdocs%2Fguides%2Fapplications%23retrieve-application-api-key)Request Timeout   Number of seconds that the RADIUS connector will wait for
The Application ID and Application API Key are found on the[LoginTC Admin Panel](https://www.google.com/url?sa=E&q=https%3A%2F%2Fcloud.logintc.com%2F).Request Timeout
Make a note of what you set the Request Timeout to as you will need to use a larger timeout value in your RADIUS client. We recommend setting the Request Timeout value to 60 seconds in the LoginTC RADIUS Connector and setting the RADIUS authentication server timeout to 70 seconds in RADIUS Client. For more information see:[Recommended settings for an optimal user experience for VPN access](https://www.google.com/url?sa=E&q=https%3A%2F%2Flogintc.tawk.help%2Farticle%2Frecommended-settings-for-an-optimal-user-experience-for-vpn-access)
Click**Test**to validate the values and then click**Next**:User Directory
Configure the user directory to be used for first authentication factor in conjunction with LoginTC. You may use Active Directory / LDAP or an existing RADIUS server. You may also opt not to use a first factor, in which case LoginTC will be the only authentication factor.
**Active Directory / Generic LDAP Option**
Select**Active Directory**if you have an AD Server. For all other LDAP-speaking directory services, such as OpenDJ or OpenLDAP, select**Generic LDAP**:
Configuration values:
Property   Explanation   Examples   host   Host or IP address of the LDAP server   ldap.example.com  or  192.168.1.42   port  (optional)   Port if LDAP server uses non-standard (i.e.,  389 / 636 )   4000   bind_dn   DN of a user with read access to the directory   cn=admin,dc=example,dc=com   bind_password   The password for the above bind_dn account   password   base_dn   The top-level DN that you wish to query from   dc=example,dc=com   attr_username   The attribute containing the user’s username   sAMAccountName  or  uid   attr_name   The attribute containing the user’s real name   displayName  or  cn   attr_email   The attribute containing the user’s email address   mail  or  email   LDAP Group  (optional)   The name of the LDAP group to be sent back to the authenticating server.   SSLVPN-Users   encryption  (optional)   Encryption mechanism   ssl  or  startTLS   cacert  (optional)   CA certificate file (PEM format)   /opt/logintc/cacert.pem
Click**Test**to validate the values and then click**Next**.
**Existing RADIUS Server Option**
If you want to use your existing RADIUS server, select**RADIUS**:
Configuration values:
Property   Explanation   Examples   IP Address or Host Name   Host or IP address of the RADIUS server   radius.example.com  or  192.168.1.43   Authentication Port  (optional)   Port if the RADIUS server uses non-standard (i.e.,  1812 )   1812   Shared Secret   The secret shared between the RADIUS server and the LoginTC RADIUS Connector   testing123RADIUS Vendor-Specific Attributes
Common Vendor-Specific Attributes (VSAs) returned by the RADIUS server will be relayed.
Click**Test**to validate the values and then click**Next**.Challenge Strategy / Passthrough
Configure which users will be challenged with LoginTC. This allows you to control how LoginTC will be phased in for your users. This flexibility allows for seamless testing and roll out.
For example, with smaller or proof of concept deployments select the[Static List](https://www.google.com/url?sa=E&q=https%3A%2F%2Fwww.logintc.com%23static-list)option. Users on the static list will be challenged with LoginTC, while those not on the list will only be challenged with the configured[First Authentication Factor](https://www.google.com/url?sa=E&q=https%3A%2F%2Fwww.logintc.com%23first-authentication-factor). That means you will be able to test LoginTC without affecting existing users accessing your VPN.
For larger deployments you can elect to use the[Active Directory or LDAP Group](https://www.google.com/url?sa=E&q=https%3A%2F%2Fwww.logintc.com%23active-directory-ldap-group)option. Only users part of a particular LDAP or Active Directory Group will be challenged with LoginTC. As your users are migrating to LoginTC your LDAP and Active Directory group policy will ensure that they will be challenged with LoginTC. Users not part of the group will only be challenged with the configured[First Authentication Factor](https://www.google.com/url?sa=E&q=https%3A%2F%2Fwww.logintc.com%23first-authentication-factor).
**Challenge All Users**
Select this option if you wish every user to be challenged with LoginTC.
**Challenge Users Based on Static Username List**
Select this option if you wish to have a static list of users that will be challenged with LoginTC. Good for small number of users.
LoginTC challenge users: a new line separated list of usernames. For example:
jane.doe jane.smith john.doe john.smith
**Challenge Users Based on Group Membership**
Select this option if you wish to have only users part of a particular Active Directory or LDAP group to be challenged with LoginTC. Good for medium and large number of users.
Configuration values:
Property   Explanation   Examples   Challenge Groups (Optional)   Comma separated list of groups for which users will be challenged with LoginTC   SSLVPN-Users  or  two-factor-users   Challenge Groups (Optional)   Comma separated list of groups for which users will always bypass LoginTC   NOMFA-Users
Click**Test**to validate the values and then click**Next**.Client Settings
Configure RADIUS client (e.g. your RADIUS-speaking VPN):
Client configuration values:
Property   Explanation   Examples   name   A unique identifier of your RADIUS client   CorporateVPN   IP Addresss   The IP address of your RADIUS client (e.g. your RADIUS-speaking VPN). Add additional IP Addresses by clicking**plus**.   192.168.1.44   Shared Secret   The secret shared between the LoginTC RADIUS Connector and its client   bigsecret
Under Authentication Mode select**Iframe**
The user will be prompted on how they wish to proceed with second-factor authentication (e.g. LoginTC Push, OTP, bypass code). Your RADIUS client must support RADIUS challenges to use this. Challenging the user will often result in a better user experience. See[User Experience](https://www.google.com/url?sa=E&q=https%3A%2F%2Fwww.logintc.com%23user-experience)for more information.
Click**Test**to validate the values and then click**Save**.
**Testing**When you are ready to test your configuration, create a LoginTC user (if you haven’t already done so). The username should match your existing user. Provision a token by following the steps:
When you have loaded a token for your new user and domain, navigate to your appliance**web interface**URL:
Click**Test Configuration**:
Enter a valid username and password; if there is no password leave it blank. A simulated authentication request will be sent to the mobile or desktop device with the user token loaded. Approve the request to continue:
Congratulations! Your appliance can successfully broker first and second factor authentication. The only remaining step is to configure your RADIUS device!
If there was an error during testing, the following will appear:
In this case, click**See logs**(or click the**Logs**section):
**F5 MFA Configuration**Once you are satisfied with your setup, configure your F5 Big-IP APM to use the LoginTC RADIUS Connector.
For your reference, the appliance**web interface****Settings**page displays the appliance IP address and RADIUS ports:
The following are quick steps to setup F5 Big-IP APM with LoginTC.
<!-- Start of LoginTC F5 Integration --> <style type="text/css">.logintc #main_table_info_cell { visibility: hidden; }</style> <script type="text/javascript"> var logintc_host = 'cloud.logintc.com'; var logintc_application_id = 'YOUR_APPLICATION_ID'; document.documentElement.className="logintc";var domReady=function(e,n,t){n=document,t="addEventListener",n[t]?n[t]("DOMContentLoaded",e):window.attachEvent("onload",e)};domReady(function(){if(-1!=document.getElementById("credentials_table_header").innerHTML.indexOf("LoginTC-Request-Token")){var e=document.createElement("script");e.src="https://" + logintc_host + "/static/iframe/f5-iframe-injector-v2.js",document.getElementsByTagName("head")[0].appendChild(e)}else document.documentElement.className=""}); </script> <!-- End of LoginTC F5 Integration -->
**Note: Add your Application ID**Replace  YOUR_APPLICATION_ID  with the actual LoginTC Application ID you wish to use,[retrieve Application ID](https://www.google.com/url?sa=E&q=https%3A%2F%2Fwww.logintc.com%2Fdocs%2Fguides%2Fapplications.html%23retrieve-application-id).
There are a variety of ways to add the LoginTC RADIUS Connector to your F5 Access Policy. You can for example replace your existing First Factor authentication, like LDAP / Active Directory with the LoginTC RADIUS Connector. You can also perform First Factor from your existing LDAP / Active Directory and then leverage the LoginTC RADIUS Connector. Here are some end state examples:
Replacing an existing First Factor, like LDAP / Active Directory with the LoginTC RADIUS Connector:
Chaining the LoginTC RADIUS Connector:
To find the way which works best for your environment review the F5 Configuration Guide for BIG-IP Access Policy Manager or contact your F5 vendor or F5 support directly.
**F5 Testing**To test, navigate to the logon page using the access policy just configured and attempt to login. You should be prompted with a LoginTC login form:
Select the method you wish to use to authenticate and continue.
**Loading Balancing and Health Monitoring**F5 allows for multiple LoginTC RADIUS Connectors to be load balanced for high availability. For more information on how to configure AAA high availability see:[Setting up Access Policy Manager for AAA high availability](https://www.google.com/url?sa=E&q=https%3A%2F%2Fsupport.f5.com%2Fcsp%2Fknowledge-center%2Fsoftware%2FBIG-IP%3Fmodule%3DBIG-IP%2520APM).
Steps to configure a health check monitoring user on the LoginTC RADIUS Connector:
When health checks requests are received for the monitoring user, the configured First Factor authentication will be checked and LoginTC verification will automatically passthrough. If First Factor authentication passes  ACCESS-ACCEPT  will be returned.
**LoginTC application dedicated for monitoring**Recommend creating a new LoginTC application and domain only for monitoring. No users need to be part of the application / domain.
**(Optional) Active Directory check for monitoring user**Recommend leveraging a dedicated service account for First Factor authentication.
**User Management**There are several options for managing your users within LoginTC:
**Logging**Logs can be found on the**Logs**tab:**Troubleshooting**Not Authenticating
If you are unable to authenticate, navigate to your appliance**web interface**URL and click**Status**:
Ensure that all the status checks pass. For additional troubleshooting, click**Logs**:
**Email Support**For any additional help please email support@cyphercor.com. Expect a speedy reply.**Upgrading**From 4.X
**NOTE: Upgrade time**Upgrade can take 10-15 minutes, please be patient.From 3.X
**Important: LoginTC RADIUS Connector 3.X End-of-life**The LoginTC RADIUS Connector 3.X virtual appliance is built with CentOS 7.9. CentOS 7.X is End of Lifetime (EOL) June 30th, 2024. Although the appliance will still function it will no longer receive updates and nor will it be officially supported.
**New LoginTC RADIUS Connector 4.X**A new LoginTC RADIUS Connector 4.X virtual appliance has been created. The Operating System will be supported for many years. Inline upgrade is not supported. As a result upgrade is deploying a new appliance. The appliance has been significantly revamped and although the underlying functionality is identical, it has many new features to take advantage of.
Complete 3.X to 4.X upgrade guide:[LoginTC RADIUS Connector Upgrade Guide](https://www.google.com/url?sa=E&q=https%3A%2F%2Fwww.logintc.com%2Fdocs%2Fguides%2Fconnector-upgrade.html)
Start your free trial today. No credit card required.
[Sign up and Go](https://www.google.com/url?sa=E&q=https%3A%2F%2Fwww.logintc.com%2Fdocs%2Fguides%2Fconnector-upgrade.html)
[sales@cyphercor.com](https://www.google.com/url?sa=E&q=https%3A%2F%2Fwww.logintc.com%2Fdocs%2Fguides%2Fconnector-upgrade.html)
[T: 1-877-564-4682](https://www.google.com/url?sa=E&q=https%3A%2F%2Fwww.logintc.com%2Fdocs%2Fguides%2Fconnector-upgrade.html)
[Contact Us](https://www.google.com/url?sa=E&q=https%3A%2F%2Fwww.logintc.com%2Fdocs%2Fguides%2Fconnector-upgrade.html)
© 2025 Cyphercor Inc • Made in Canada
By continuing to use our website, you acknowledge the use of cookies.[Privacy Policy](https://www.google.com/url?sa=E&q=https%3A%2F%2Fwww.logintc.com%2Fprivacy-policy%2F)[Close](https://www.google.com/url?sa=E&q=https%3A%2F%2Fwww.logintc.com%2Fprivacy-policy%2F)