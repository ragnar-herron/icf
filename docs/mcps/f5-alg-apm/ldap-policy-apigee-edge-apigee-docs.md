
API MonitoringSenseAPIsTroubleshootingReleasesPricingCommunity/
Sign in
Policies
Caching policies
JWS and JWT policies
JWS policies
JWT policies
OAuthV2 policies
Extensions
Amazon S3 Extension
AWS Lambda Extension
Google Authentication Extension
Google BigQuery Extension
Google Cloud Data Loss Prevention Extension
Google Cloud Firestore Extension
Google Cloud Functions Extension
Google Cloud Natural Language Extension
Google Cloud Pub/Sub Extension
Google Cloud Spanner Database Extension
Google Cloud Storage Extension
Google Cloud Vision Extension
Google Machine Learning Engine Extension
Google Cloud Logging Extension
Informatica Integration Cloud Extension
SalesforceLDAP policy
You're viewing**Apigee Edge**documentation.Go to the**Apigee X**documentation.   info
### What
The LDAP Policy provides:
**Authentication**: User credentials supplied in the request are validated against credentials in the LDAP provider. The LDAP policy gives you a lot of flexibility with authentication, letting you use any DN value along with the password, even if that DN value you want isn't in the request. For example, say you need to use email / password for authentication. The following options are possible:
Use the LDAP Policy when access to protected resources should be limited to users in your LDAP provider—such as your admin users, organization users, and developers—especially when OAuth token access is either unnecessary or too heavyweight. The policy is also designed for retrieving domain name metadata for use in API proxy flows.
For example you can have an API call execute only when a user is successfully authenticated against LDAP; and then optionally retrieve DN (Domain Name) attributes for the user after authentication succeeds.
**NOTE:**This policy is available only in Apigee Edge for Private Cloud.
For additional information, see:
### Samples
### Username/password authentication
<Ldap name="4GLdapPolicy"> <LdapResource>ldap1</LdapResource> <Authentication> <UserName ref="request.header.username"/> <Password ref="request.header.password"/> <Scope>subtree</Scope> <BaseDN ref="apigee.baseDN"></BaseDN> <!-- default is dc=apigee,dc=com --> </Authentication> </Ldap>
This sample provides authentication against an LDAP provider. The policy passes username and password from the request to LDAP for authentication.
### DN attribute authentication
<Ldap name="LdapPolicy"> <LdapResource>ldap1</LdapResource> <Authentication> <Password ref="request.header.password"/> <SearchQuery>mail={request.header.mail}</SearchQuery> <Scope>subtree</Scope> <BaseDN ref="apigee.baseDN"></BaseDN> <!-- default is dc=apigee,dc=com --> </Authentication> </Ldap>
This policy gets the user’s DN with the email in the request header, then authenticates the user against LDAP with the password provided in the request header.
**Note:**Notice that in the Authentication block there is no UserName, which is not allowed when using SearchQuery to retrieve another DN attribute for authentication.
### Searching LDAP
< Ldap   name = "LdapPolicy" >  < ! --   using   a   custom   LDAP   provider   -- >  < LdapConnectorClass>com . custom . ldap . MyProvider < / LdapConnectorClass >  < LdapResource>MyLdap < / LdapResource >  < Search >  < BaseDN   ref = "apigee.baseDN" >< / BaseDN >   < ! --   default   is   dc = apigee , dc = com   -- >  < SearchQuery>mail ={ request . header . mail } < / SearchQuery >  < Attributes >  < Attribute>address < / Attribute >  < Attribute>phone < / Attribute >  < Attribute>title < / Attribute >  < / Attributes >  < Scope >< / Scope >   < ! --   default   is   ‘ subtree ’   -- >  < / Search > < / Ldap >
This policy references a custom LDAP provider. It uses the email address in the request header to identify the user, then retrieves the user’s address, phone, and title from LDAP. The retrieved DN attributes are stored in a variable. See "Policy-specific variables".
To search LDAP and retrieve DN attributes, the request must include administrator credentials.
## Element reference
Following are descriptions of the LDAP Policy elements and attributes.
**Note:**The  name  attribute for this policy is restricted to these characters:  A-Z0-9._\-$ % . However, the Management UI enforces additional restrictions, such as automatically removing characters that are not alphanumeric.
Element
Description
Ldap
Parent element with a name attribute for you to enter the policy name.
LdapConnectorClass
When using the LDAP Policy with a[custom LDAP provider](https://www.google.com/url?sa=E&q=https%3A%2F%2Fdocs.apigee.com%23customldapprovider)(not provided by Apigee), specify the fully qualified LDAP connector class. That's the class in which you implemented Apigee's  ExternalLdapConProvider  interface.
LdapResource
Enter the environment name of the LDAP resource. See[Create an LDAP resource](https://www.google.com/url?sa=E&q=https%3A%2F%2Fdocs.apigee.com%23ldapresource)for more information.
BaseDN
The base level of LDAP under which all of your data exists. For example, in Apigee's LDAP provider, all data are under  dc=apigee,dc=com .
Scope
**Authentication**
Authentication
Parent element for the authentication behavior you implement.
UserName
Empty element that takes one of the following attributes:
If you aren't authenticating with username, or if username isn't included in the request, you don't need to include this element.
If username is in the request, but you want to authenticate a user with a DN attribute other than username, such as email, include a  SearchQuery  to get the user email associated with the password. The LDAP policy uses username to query the LDAP provider for the corresponding email address, which is then used for authentication.
Password
Empty element that takes one of the following attributes:
SearchQuery
If you want to authenticate using a DN attribute other than username, such as email, configure the LDAP policy to get a DN attribute from the request (such as username), which is used to identify the user in LDAP, retrieve the email, and authenticate the user.
For example, assuming LDAP defines a "mail" attribute for storing email address:
<SearchQuery>mail={request.header.mail}</SearchQuery>
**Note:**The  <SearchQuery>  element supports the dynamic string substitution feature called[message templating](https://www.google.com/url?sa=E&q=https%3A%2F%2Fdocs.apigee.com%2Fapi-platform%2Freference%2Fmessage-template-intro).
**Search**
Search
Parent element for the search behavior you implement.
SearchQuery
By identifying the user with metadata in the request or response, you can use this element to retrieve additional DN attributes for the user from LDAP. For example, if the request contains the user email, and your LDAP defines a  mail  attribute for storing user email addresses, you&'d use the following setting:
<SearchQuery>mail={request.header.mail}</SearchQuery>
This query searches LDAP for an email matching the email in the request, and the policy can now retrieve additional DN attributes for that user with the Attributes element.
Attributes
Use one or more  <Attribute>  elements to identify the DN metadata you want to retrieve for the user. At least one attribute is required.
For example, after the  SearchQuery  identifies the user, the policy can now retrieve DN attributes for the user such as address, phone number, and the user's title, as shown in the following example.
Attribute values are the DN attribute names defined in your LDAP.
< Attributes >  < Attribute>address < / Attribute >  < Attribute>phone < / Attribute >  < Attribute>title < / Attribute > < / Attributes >
## Usage notes
Apigee Edge for Private Cloud lets you leverage an LDAP provider in API calls. With the LDAP Policy, applications can authenticate credentials against users stored in LDAP, and you can retrieve distinguished names (DNs) from LDAP—the metadata, or attributes, associated with each user, such as email, address, and phone number. The returned DN is stored in a variable for further use by the API proxy.
### Create an LDAP resource
The LDAP policy leverages an LDAP resource that you create in Apigee Edge. An LDAP resource provides the connection information to your LDAP repository.
To create and manage LDAP resources, use the following API and payload:API
Create ( POST ) an LDAP resource or list ( GET ) all LDAP resources:
/v1/organizations/ org_name /environments/ environment /ldapresources
Get details for ( GET ), Update ( POST ), and Delete ( DELETE ) an LDAP resource:
/v1/organizations/ org_name /environments/ environment /ldapresources/ ldap_resource_namePayload
Following is a sample XML payload with usage comments.
< LdapResource   name = "ldap1" >  < Connection >  < Hosts >  < ! --   port   is   optional :   defaults   to   389   for   ldap : // and 636 for ldaps:// -- >  < Host   port = "636" > foo . com < / Host >  < / Hosts >  < SSLEnabled>false < / SSLEnabled >   < ! --   optional ,   defaults   to   false   -- >  < Version>3 < / Version >   < ! --   optional ,   defaults   to   3 -- >  < Authentication>simple < / Authentication >   < ! --   optional ,   only   simple   supported   -- >  < ConnectionProvider>jndi | unboundid < / ConnectionProvider >   < ! --   required   -- >  < ServerSetType>single | round   robin | failover < / ServerSetType >   < ! --   not   applicable   for   jndi   -- >  < ! --   If   using   a   custom   LDAP   provider ,   the   fully   qualified   class :   -- >[< LdapConnectorClass>com . custom . ldap . MyProvider < / LdapConnectorClass >](https://www.google.com/url?sa=E&q=https%3A%2F%2Fdocs.apigee.com%23customldapprovider)< / Connection >  < ConnectPool   enabled = "true" >   < ! --   enabled   is   optional ,   defaults   to   true   -- >  < Timeout>30000 < / Timeout >   < ! --   optional ,   in   milliseconds ;   if   not   set ,   no   timeout   -- >  < Maxsize>50 < / Maxsize >   < ! --   optional ;   if   not   set ,   no   max   connections   -- >  < Prefsize>30 < / Prefsize >   < ! --   optional ;   if   not   set ,   no   pref   size   -- >  < Initsize >< / Initsize >   < ! --   optional ;   if   not   set ,   defaults   to   1   -- >  < Protocol >< / Protocol >   < ! --   optional ;   if   not   set ,   defaults   to   ' ssl   plain '   -- >  < / ConnectPool >  < Admin >  < DN>cn = manager , dc = apigee , dc = com < / DN >  < Password>secret < / Password >  < / Admin > < / LdapResource >curl example: Create an LDAP resource
The following example creates an LDAP resource named**ldap1**.
curl   - X   POST   - H   "Content-Type: application/xml"   \  https : //api.enterprise.apigee.com/v1/organizations/myorg/environments/test/ldapresources \   - u   apigee_email : password   - d   \  ' < LdapResource   name = "ldap1" >  < Connection >  < Hosts >  < Host>foo . com < / Host >  < / Hosts >  < SSLEnabled>false < / SSLEnabled >  < Version>3 < / Version >  < Authentication>simple < / Authentication >  < ConnectionProvider>unboundid < / ConnectionProvider >  < ServerSetType>round   robin < / ServerSetType >  < / Connection >  < ConnectPool   enabled = "true" >  < Timeout>30000 < / Timeout >  < Maxsize>50 < / Maxsize >  < Prefsize>30 < / Prefsize >  < Initsize >< / Initsize >  < Protocol >< / Protocol >  < / ConnectPool >  < Admin >  < DN>cn = manager , dc = apigee , dc = com < / DN >  < Password>secret < / Password >  < / Admin >  < / LdapResource > '
### Response codes
Following are the HTML response codes the policy returns for success or failure:
## Using a custom LDAP provider in Edge for Private Cloud
**Private Cloud:**Edge for Private Cloud installations only.
### Using a custom LDAP provider
Apigee Edge for Private Cloud comes with an LDAP provider that is already configured to interact with the LDAP Policy. However, if you are using a custom LDAP provider, you must enable the provider to support the LDAP Policy. To do this:
### Using the UnboundID LDAP SDK for Java
You can use the UnboundID LDAP SDK with the LDAP policy, but you must first download version 2.3.1 and add it to each of your Message Processor's classpaths.
To use the UnboundID LDAP SDK with the LDAP policy:
Extract the JAR file from the SDK ZIP file, as the following example shows:  unzip -j -d ~/tmp ~/Downloads/unboundid-ldapsdk-2.3.1-se.zip unboundid-ldapsdk-2.3.1-se/unboundid-ldapsdk-se.jar
This command extracts just the JAR file to the ~/tmp directory. It drops the directory structure with  -j , although this is optional.
Edge adds all thirdparty libraries in the  /opt/apigee/edge-gateway/lib/thirdparty  directory to the classpath.
## Flow variables
Following are the LDAP Policy variables populated by a  SearchQuery .
Variable
Description
ldap. policyName .execution.success
After the policy is executed, this flow variable contains a value of "true" or "false", depending on the result.
ldap. policyName .search.result[ index ]. attribute. attrName [ index ]= value
The flexible format of this variable, the index in particular: accounts for multiple attributes, as well as attributes with multiple values. Index is a number that starts at 1. If no index number is provided, the default index number is 1.
If the policy returns address, phone, and email, you can retrieve the first attribute and value using these variables:
ldap. policyName .search.result.attribute.address ldap. policyName .search.result.attribute.phone ldap. policyName .search.result.attribute.email
If you wanted to retrieve the third address attribute in the search results, you'd use this:
ldap. policyName .search.result[3].attribute.address
If an attribute had multiple values (for example, if a user has multiple email addresses), you'd retrieve the second email address from the results like this:
ldap. policyName .search.result.attribute.mail[2]
## Error codes
Errors returned from Edge policies follow a consistent format as described in the[Error code reference](https://www.google.com/url?sa=E&q=https%3A%2F%2Fdocs.apigee.com%2Fapi-platform%2Freference%2Fpolicies%2Ferror-code-reference).
This policy uses the following error codes:
Error Code   Message   InvalidAttributeName   Invalid attribute name {0}.   InvalidSearchBase   Search base can not be empty.   InvalidValueForPassword   Invalid value for password field. It can not be empty.   InvalidSearchScope   Invalid scope {0}. Allowed scopes are {1}.   InvalidUserCredentials   Invalid user credentials.   InvalidExternalLdapReference   Invalid external ldap reference {0}.   LdapResourceNotFound   Ldap resource {0} not found.   BaseDNRequired   Base DN required.   OnlyReferenceOrValueIsAllowed   Only value or reference is allowed for {0}.   AttributesRequired   At least one attribute required for search action.   UserNameIsNull   User name is null.   SearchQueryAndUserNameCannotBePresent   Both search query and username can not be present in the authentication action. Please specify either one of them.
Except as otherwise noted, the content of this page is licensed under the[Creative Commons Attribution 4.0 License](https://www.google.com/url?sa=E&q=https%3A%2F%2Fcreativecommons.org%2Flicenses%2Fby%2F4.0%2F), and code samples are licensed under the[Apache 2.0 License](https://www.google.com/url?sa=E&q=https%3A%2F%2Fwww.apache.org%2Flicenses%2FLICENSE-2.0). For details, see the[Google Developers Site Policies](https://www.google.com/url?sa=E&q=https%3A%2F%2Fdevelopers.google.com%2Fsite-policies). Java is a registered trademark of Oracle and/or its affiliates.
Last updated 2025-07-02 UTC.
### [[["Easy to understand","easyToUnderstand","thumb-up"],["Solved my problem","solvedMyProblem","thumb-up"],["Other","otherUp","thumb-up"]],[["Missing the information I need","missingTheInformationINeed","thumb-down"],["Too complicated / too many steps","tooComplicatedTooManySteps","thumb-down"],["Out of date","outOfDate","thumb-down"],["Samples / code issue","samplesCodeIssue","thumb-down"],["Other","otherDown","thumb-down"]],["Last updated 2025-07-02 UTC."],[],[]]