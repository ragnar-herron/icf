MY PRODUCTS & PLANSSubscriptionsProduct UsageTrialsRegistration KeysResourcesDownloads
LicensingActivate F5 product registration key
IhealthVerify the proper operation of your BIG-IP system
F5 UniversityGet up to speed with free self-paced courses
DevcentralJoin the community of 300,000+ technical peers
F5 CertificationAdvance your career with F5 Certification
Product ManualsProduct Manuals and Release notes
**Manual Chapter**:   Specifying how often a user must authenticate
## Applies To:
Show  Versions
### BIG-IP APMSpecifying how often a user must authenticate
You can configure Access Policy Manager (APM) so that step-up authentication runs periodically throughout a session. For example, you might want a user to re-authenticate every eight hours for access to a given application.
For step-up authentication to run periodically, verify that the  Maximum Session Timeout  setting in the access profile is set to a value greater than zero. The default value is 604800 seconds (or 1 week).
To specify how long you want the user to retain access without needing to re-authenticate, update the  Max Subsession Life (sec)  setting:Contact SupportHave a Question?Support and Sales  >Follow UsAbout F5EducationF5 SitesSupport Tasks
©2023 F5, Inc. All rights reserved.