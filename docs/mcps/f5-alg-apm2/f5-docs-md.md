Combined Web Notes
*Generated: 2026-02-20 15:12:34Z*
## Table of Contents
---

## F5 Agility Labs - Index
<a id="page-1"></a>
Source: https://f5-agility-labs-analytics.readthedocs.io/en/latest/
## Welcome
Welcome to the F5 Analytics and Visibility Solutions lab at F5 Agility 2018
The content contained here leverages a full DevOps CI/CD pipeline and is sourced from the GitHub repository at https://github.com/f5devcentral/f5-agility-labs-analytics . Bugs and Requests for enhancements can be made by opening an Issue within the repository.
---

## Welcome
<a id="page-2"></a>
Source: https://f5-agility-labs-iam.readthedocs.io/Welcome
Welcome to the Identity & Access Management lab series at Agility 2018.
The following labs and exercises will instruct you on how to configure and troubleshoot federation use cases based on the experience of field engineers, support engineers and clients. This guide is intended to complement lecture material provided during the course as well as a reference guide that can be referred to after the class as a basis for configuring federation relationships in your own environment.
The content contained here leverages a full DevOps CI/CD pipeline and is sourced from the GitHub repository at https://github.com/f5devcentral/f5-agility-labs-iam . Bugs and Requests for enhancements can be made by opening an Issue within the repository.
---

## Module 1: SAML Identity Provider
<a id="page-3"></a>
Source: https://f5-agility-labs-iam.readthedocs.io/en/latest/class4/module1/module1.htmlModule 1: SAML Identity Provider
In this lab we will learn the basics concepts required to use F5 Access Policy Manager as a SAML Identity Provider (IdP).
---

## Conclusion
<a id="page-4"></a>
Source: https://f5-agility-labs-iam.readthedocs.io/en/latest/class8/conclusion.htmlConclusion
In this lab, you learned how to use various tools including APM logs, ADTest, TCPDump to aid in troubleshooting common Access Policy Manager (APM) issues relating to Access Policy configuration, user authentication, and session variables.
## Learn More
Links & Information
---

## Lab 1: APM Troubleshooting Lab Object Preparation (GUI)
<a id="page-5"></a>
Source: https://f5-agility-labs-iam.readthedocs.io/en/latest/class8/module1/module1.htmlLab 1: APM Troubleshooting Lab Object Preparation (GUI)
Note
You only need to perform EITHER Lab 1 OR Lab 2. They accomplish the same goal, but using different methods. Lab 2 gets the Lab Preparation using TMSH
The purpose of this lab is to preconfigure some objects that will be used throughout the other labs. These objects are as follows:
## Connect to the Lab
## DNS Resolver for System Configuration
## NTP Server for System Configuration
## Access Policy (APM) AAA Server – Active Directory Object Creation
## Access Policy (APM) SSO Configuration – NTLMv1
## Access Policy (APM) Access Profile Creation
## Local Traffic (LTM) Pool and Member Creation
## Local Traffic (LTM) Virtual Server Creation
This lab will walk you through creating the Virtual Server we will use during the course of the lab. This Virtual Server will be used to associate Access Policies which will be evaluated when authenticating users.
---

## Lab 2: APM Troubleshooting Lab Object Preparation (TMSH)
<a id="page-6"></a>
Source: https://f5-agility-labs-iam.readthedocs.io/en/latest/class8/module2/module2.htmlLab 2: APM Troubleshooting Lab Object Preparation (TMSH)
Note: You only need to perform one of Lab 1, 2, or 3. They accomplish the same thing only in different ways. Lab 2 gets the Lab Preparation using TMSH
The purpose of this lab is to preconfigure some objects that will be used throughout the other labs. These objects are as follows:
## Connect to the Lab via SSH
## DNS Resolver for System Configuration (TMSH)
To add a name server to your /etc/resolv.conf file, use the following command syntax, replacing<IP addresses>with your IP addresses:
modify sys dns name-servers add {<IP addresses>}
To add domains to your search list use the following command replacing<domains>with the domain you wish to add:
modify sys dns search add {<domains>}
Configure as follows:
modify sys dns name-servers add { 10.128.20.100 }
modify sys dns search add { agilitylab.com }
save sys config
To verify, use the following command: list sys dns
You should see the following reply:
## NTP Server for System Configuration (TMSH)
To configure one or more NTP servers for the BIG-IP system, use the following command syntax:
modify sys ntp servers add {hostname hostname….}
Configure as follows:
modify sys ntp servers add { 10.128.20.100 }
save sys config
To verify, use the following command:
list sys ntp
You snould see the following reply:
## Access Policy (APM) AAA Server – Active Directory Object Creation (TMSH)
To configure an Active Directory AAA Server object, use the following command syntax:
create apm aaa active-directory<name>domain<domain-name>use-pool<disabled>
Configure as follows:
create apm aaa active-directory LAB_AD_AAA domain agilitylab.com use-pool disabled
save sys config
To verify, use the following command:
list apm aaa
You should see the following reply:
## Access Policy (APM) SSO Configuration – NTLMv1 (TMSH)
To configure an NTLMv1 SSO profile, use the following command syntax:
create apm sso ntlmv1 <profile_name>
Configure as follows:
create apm sso ntlmv1 Agility_Lab_SSO_NTLM
save sys config
To verify, use the command:
list apm sso
## Access Policy (APM) Access Profile Creation (see GUI steps)
## Local Traffic (LTM) Pool and Member Creation (TMSH)
To configure a LTM Pool and Pool members, use the following command syntax:
create ltm pool<pool-name>members add {<IP-addr>:<service-port>}
Configure as follows:
create ltm pool Agility-Lab-Pool members add { 10.128.20.100:80 }
save sys config
To verify, use the following command:
list ltm pool
## Local Traffic (LTM) Virtual Server Creation (TMSH)
To configure a virtual server, use the following command syntax:
create ltm virtual Agility-LTM-VIP { destination 10.128.10.100:443 profiles add { clientssl http Agility-Lab-Access-Profile } vlans default source-address-translation { type automap } }
Configure as follows:
create ltm virtual Agility-LTM-VIP { destination 10.128.10.100:443 profiles add { clientssl http Agility-Lab-Access-Profile } vlans default source-address-translation { type automap } }
save sys config
To verify, use the following command:
list ltm virtual
---

## Lab 5: Command Line Tools
<a id="page-7"></a>
Source: https://f5-agility-labs-iam.readthedocs.io/en/latest/class8/module5/module5.htmlLab 5: Command Line Tools
This lab will show you how to make use of some of the Command Line Utilities for troubleshooting Access Policy Manager when dealing with Authentication issues that you could experience.
## Questions to ask yourself (LAB5)
## What’s Not Covered but we will discuss
## Checking APM Logs
APM Logs by default show the same information you can get from the Manage Sessions menu, as well as APM module-specific information.
Access Policy Manager uses syslog-ng to log events. The syslog-ng utility is an enhanced version of the standard logging utility syslog.
The type of event messages available on the APM are:
When setting up logging you can customize the logs by designating the minimum severity level or log level, that you want the system to report when a type of event occurs. The minimum log level indicates the minimum severity level at which the system logs that type of event.
Note
Files are rotated daily if their file size exceeds 10MB. Additionally, weekly rotations are enforced if the rotated log file is a week old, regardless whether or not the file exceeds the 10MB threshold.
The default log level for the BIG-IP APM access policy log is Notice , which does*not*log Session Variables. Setting the access policy log level to Informational or Debug will cause the BIG-IP APM system to log Session Variables, but it will also add additional system overhead. If you need to log Session Variables on a production system, F5 recommends setting the access policy log level to Informational temporarily while performing troubleshooting or debugging.
We need to add some more actions to the APM Profile in the VPE we have been working with to go along with the next few lab tests.
STEP 1
Hint: A Message Box can be added by clicking the + sign, navigating to the General Purpose tab and selecting Message Box
Hint: An AD Auth action can be added by clicking the + sign, navigating to the Authentication tab and selecting AD Auth
Notice that one the top branch to the AD Query object the line reads User Primary Group ID is 100 (See graphic in Step 8 above, just after AD Query). Maybe you do not want to query for that information and would prefer to delete that branch. You must be*careful*in what you select or do when deleting that branch when you have other actions following it in the policy or they could be deleted when you do not want them to be deleted. Here is a trick you can use to preserve the actions that follow the ad query when you need to delete a branch.
Now let’s see what can be seen in the logs when set at the default logging level of Notice.
TEST 1
With the SSH console logging, open a browser and access the APM as the user student .
With the*default logging*level, there are no session variables being logged.
In the Next test we will turn up logging to Informational and restart the user session and then in the last test change logging level to Debug and notice the differences from Informational and Notice logging levels.
## Turning up the heat on Logging
Now let’s test more verbose logging. You can step up from Notice to Informational and then to Debug if you want to see the differences yourself. For the purpose of this test though I will jump straight to Debug. You can use the GUI to make the log level changes to Debug or you could use the Traffic Management Shell (TMSH) command from the CLI to adjust the logging.
STEP 1
TIP: Make sure you change setting back to Notice when not troubleshooting. High levels of logging not only consume more disk space, but also consume other resources, such as CPU, when enabled.
TEST 2
For sake of saving space in this document we will not include the screen shots showing the Informational and Debug logging messages and allow you to experience that yourself during your tests.
## SessionDump Command
SessionDump is a command line utility that shows sessions and their associated session variables (like GUI Reports)
The sessiondump command has sever switches that can be used and you can further enhance your troubleshooting by additionally using other CLI utilities like grep to help filter the results to certain information. As you can see from the examples below, the first command simple provides all keys to be dumped for any/all user sessions while the second using grep allows you to filter the output to those associated with a given username. Refer to the screen shots below if you need additional detail.
This first example uses just the –allkeys switch.
sessiondump –allkeys
This second example also uses the –allkeys switch. However, it also adds the |grep command to search for the “username”
sessiondump -allkeys | grep ‘student’
STEP 1
Remember back in previous labs we learned that Session Variables cannot be displayed in the Reports screens if the User Session is not in an*Active*state. Well that is the same with the CLI sessiondump utility. There must be active sessions through APM in order to dump details.
Compare that with running: sessiondump –allkeys | grep student You should then only see the lines that had the username you specified in the command to be returned
Now let us have some fun with using this utility to help with SSO troubleshooting/validation.
STEP 2
TEST 2
If you see the two lines with session.sso.token.last, then we know the credential mapping is happening and the username should be displayed accordingly. So what’s missing?
STEP 3
TEST 3
If necessary, you can kill your existing session by navigating to Access Policy  Manage Sessions, then select the user/session and Click Kill Selected Sessions
## iRules Logging Assistance
As many know one of the most useful features of F5 BIGIP TMOS is the flexibility provided by iRules.
With APM and iRules you can accomplish many things, in fact you can now use iRules to create APM sessions. We are not going to go over that here however for the purpose of how iRules can be used for troubleshooting we will provide some highlights.
Often you can run into problems wherein an application single sign-on is not being processed and completing as it should. What happens as a result of the initial setup not working im/_static/class4tely is that many people start second guessing what is happening as traffic passes from the clients browser, to the front client side of the BIGIP VIP, then what F5 VIP is actually able to SEE, next What does LTM see, APM see, what is being passed along the way at each stage of the transaction through the BIGIP, and of course what does the BIGIP APM then forward to the Backend Server Application and How does that Backend Server Application respond? Fortunately, iRules can be very beneficial in this process to collect and subsequently log specific data at each stage which greatly enhances the troubleshooting capabilities.
We all know that TCPDump can be your friend in capturing data to analyze however at times the application workflows between client f5 and server and encryption along the way can hamper what TCPDump could capture for analysis. Another issue with TCPDump is that is captures a lot of data that then needs to be analyzed. Granted TCPDump provides a filtering capability to weed through that extra data however when you compare it to using some targeted iRules to collect APM session variables and data to be output to logs it makes it easier to review the application flow more specific to the steps you are trying to validate.
By default, APM in the current code release automatically secures that variables that are entered into the logon page on APM. Furthermore, the password is hidden from the reports screen session variable view and hidden from the database. Yet there are times when the Admin of the APM may need to have access to the decrypted password to either verify that the correct information is being keyed by user, received by APM and sent from APM to servers. Fortunately, there is a way using an iRule to do just this for our troubleshooting purpose.
TEST 1
Next, we will implement an iRule to assist the Admin in verifying what password is being entered by the user.
An iRule has been created already and supplied for you so you won’t need to create it yourself you only need to apply it to the Virtual Server under the Resources Tab.
STEP 2
TEST 2
## TCPDump Troubleshooting Assistance
Beginning in BIG-IP 11.2.0, you can use the “ p ” interface modifier with the “ p ” modifier to capture traffic with TMM information for a specific flow, and its related peer flow. The “ p ” modifier allows you to capture a specific traffic flow through the BIG-IP system from end to end, even when the configuration uses a Secure Network Address Translation (SNAT) or OneConnect. For example, the following command searches for traffic to or from client 10.128.10.100 on interface 0.0 :
tcpdump -ni 0.0:nnnp -s0 -c 100000 -w /var/tmp/capture.dmp host 10.128.10.100
Once tcpdump identifies a related flow, the flow is marked in TMM, and every subsequent packet in the flow (on both sides of the BIG-IP system) is written to the capture file.
---

## Lab 1: Create a basic APM Policy
<a id="page-8"></a>
Source: https://f5-agility-labs-iam.readthedocs.io/en/latest/class9/module2/module2.htmlLab 1: Create a basic APM Policy
In this module you will learn how to configure a basic APM Policy
---

## F5 Agility Labs - Index
<a id="page-9"></a>
Source: https://f5-asm-advanced-protection.readthedocs.io/
## Welcome
Welcome to the ASM Advanced Mitigation Techniques lab at F5 Agility 2018
The content contained here leverages a full DevOps CI/CD pipeline and is sourced from the GitHub repository at https://github.com/pmscheffler/f5-asm-advanced-protection . Bugs and Requests for enhancements can be made using by opening an Issue within the repository.
---
