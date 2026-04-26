MY PRODUCTS & PLANSSubscriptionsProduct UsageTrialsRegistration KeysResourcesDownloads
LicensingActivate F5 product registration key
IhealthVerify the proper operation of your BIG-IP system
F5 UniversityGet up to speed with free self-paced courses
DevcentralJoin the community of 300,000+ technical peers
F5 CertificationAdvance your career with F5 Certification
Product ManualsProduct Manuals and Release notes
**Manual Chapter**:   Setting gating criteria to run step-up authentication more than once per session
## Applies To:
Show  Versions
### BIG-IP APMSetting gating criteria to run step-up authentication more than once per session
A subroutine creates a subsession for each distinct gating criteria value. By default, gating criteria for a subroutine is set to blank and the subroutine runs once. To base step-up authentication on distinct values dynamically set in a variable, you configure a perflow variable as the gating criteria.  If you set the gating criteria to a perflow variable that is populated by an agent, you must place that agent before the subroutine call in the per-request policy. Otherwise, the gating criteria does not contain a valid value, the subroutine returns an error, and step-up authentication does not run.
Put your cursor in the  Gating Criteria  field and select one entry from the list.  If you type in the  Gating Criteria  field, variables display that match the string you type. You can base step-up authentication on custom values or on values provided by specific agents. Some examples follow. Use these perflow variables for application data from Application Lookup:
These are custom values that you must populate with Variable Assign:
These values are automatically populated:
These values contain URL data, available with an SWG subscription, that you must populate with Category Lookup:
This value contains URL data, available with or without an SWG subscription, that you must populate with Category Lookup:
This value contains a pool name that you must populate with Pool Assign:
This value contains a protocol type (HTTP or HTTPS) that you must populate with Protocol Lookup:
This value defaults to False; can be set to True with SSL Bypass Set (or set to False with SSL Intercept Set):
This value defaults to False; can be set to True with SSL Bypass Set (or set to False with SSL Intercept Set):
This value is automatically populated and does not change. When this variable is selected, step-up authentication will run once:Contact SupportHave a Question?Support and Sales  >Follow UsAbout F5EducationF5 SitesSupport Tasks
©2023 F5, Inc. All rights reserved.