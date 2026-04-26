MY PRODUCTS & PLANSSubscriptionsProduct UsageTrialsRegistration KeysResourcesDownloads
LicensingActivate F5 product registration key
IhealthVerify the proper operation of your BIG-IP system
F5 UniversityGet up to speed with free self-paced courses
DevcentralJoin the community of 300,000+ technical peers
F5 CertificationAdvance your career with F5 Certification
Product ManualsProduct Manuals and Release notes
**Manual Chapter**:   Configuring URL branching for step-up authentication
## Applies To:
Show  Versions
### BIG-IP APMConfiguring URL branching for step-up authentication
Add a URL branching agent to a per-request policy or to a per-request policy subroutine to create simple branching rules based on URLs. You might use URL branching to run different types of step-up authentication for different URLs or to skip step-up authentication altogether for a group of URLs.
If you want to replace the value ( domain.com ) in the default rule: You can use AND and OR operators to configure expressions for your rules. For simplicity of illustration, the examples do not include these operators.
To add a rule, click  Add Branch Rule .
For  Condition Glob Match  in the  URL glob pattern  field, type the globbing pattern that you want to match. URL branching supports these globbing patterns:The per-request policy or subroutine includes URL branching. After the URL branch, you can add step-up authentication if that's what you are trying to do. In a per-request policy, you can insert a call to a subroutine after a URL branch. Or, in a subroutine, you can insert an authentication agent after a URL branch. Make sure to add the per-session and per-request policies to the virtual server.[Contact Support](https://www.google.com/url?sa=E&q=https%3A%2F%2Fwww.f5.com%2Fcompany%2Fcontact%2Fregional-offices%23product-support)Have a Question?[Support and Sales  >](https://www.google.com/url?sa=E&q=https%3A%2F%2Fwww.f5.com%2Fcompany%2Fcontact%2Fregional-offices%23product-support)Follow UsAbout F5EducationF5 SitesSupport Tasks
©2023 F5, Inc. All rights reserved.