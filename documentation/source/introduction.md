# Introduction

RDFM - Remote Device Fleet Manager - is an open-source ecosystem of tools that enable Over-The-Air (OTA) update delivery and fleet management for systems of embedded devices.

This manual describes the main components of RDFM. It is divided into the following chapters:

- System Architecture - a short overview of the system architecture, and how each component of the system interacts with the other
- RDFM Linux Device Client - build instructions and manual for the Linux RDFM Client, used for installing updates on a device
- RDFM Android Device Client - integration guide and user manual for the RDFM Android Client/app used for providing OTA updates via RDFM on embedded Android devices
- RDFM MCUmgr Device Client - build instructions and manual for the RDFM MCUmgr Client app, used for providing updates via RDFM on embedded devices running ZephyrRTOS
- RDFM Artifact utility - instruction manual for the `rdfm-artifact` utility used for generating update packages for use with the RDFM Linux device client
- RDFM Manager utility - instruction manual for the `rdfm-mgmt` utility, which allows management of devices connected to the RDFM server
- RDFM Management Server - build instructions and deployment manual for the RDFM Management Server
- RDFM Server API Reference - comprehensive reference of the HTTP APIs exposed by the RDFM Management Server
- RDFM OTA Manual - introduces key concepts of the RDFM OTA system and explains it's basic operation principles
