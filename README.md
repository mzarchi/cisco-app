 <div align="center">

# Cisco App

**A Network Operations Toolkit for Cisco Infrastructure**

Network discovery, switch monitoring, configuration management, and infrastructure visibility — all in one command-line application.

<p>
  <a href="https://github.com/mzarchi/cisco-app">
    <img src="https://img.shields.io/github/repo-size/mzarchi/cisco-app?style=for-the-badge" alt="Repository Size">
  </a>
  <a href="https://github.com/mzarchi/cisco-app">
    <img src="https://img.shields.io/github/last-commit/mzarchi/cisco-app?style=for-the-badge" alt="Last Commit">
  </a>
  <a href="https://github.com/mzarchi/cisco-app">
    <img src="https://img.shields.io/github/stars/mzarchi/cisco-app?style=for-the-badge" alt="GitHub Stars">
  </a>
</p>

[Features](#features) · [Installation](#installation) · [Commands](#command-reference) · [Security](#security) · [Contributing](#contributing)

</div>

---

## Overview

Cisco App is a Windows-based network operations toolkit designed to simplify routine infrastructure administration.

Built with Python and Netmiko, it provides an interactive command-line interface for discovering network devices, collecting switch information, monitoring device health, exploring network connections, and managing operational data through a local SQLite database.

## Features

| Category | Capabilities |
|:--|:--|
| Network Discovery | Subnet scanning and IP address discovery |
| Switch Inventory | Device details, hostname, model, interfaces, and software information |
| Monitoring | Switch temperature, CPU, and memory metrics |
| Network Topology | Switch-link discovery and CDP-related information |
| IP Management | IP inventory collection, storage, and search |
| DNS Lookup | Resolve DNS names associated with IP addresses |
| Configuration | Switch configuration utilities and backups |
| Access Lists | ACL-related management utilities |
| Data Export | Export database records to CSV |
| Database | Local SQLite storage and SQL query utility |
| Automation | Periodic background tasks and concurrent network operations |
| Logging | Execution timing and diagnostic logging |

## Technology Stack

<p align="center">
  <img src="https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/Netmiko-Network_Automation-2C6E49?style=flat-square" alt="Netmiko">
  <img src="https://img.shields.io/badge/SQLite-003B57?style=flat-square&logo=sqlite&logoColor=white" alt="SQLite">
  <img src="https://img.shields.io/badge/PyInstaller-Packaging-4B8BBE?style=flat-square" alt="PyInstaller">
</p>

- **Python** — application logic and automation
- **Netmiko** — SSH-based network device communication
- **SQLite** — persistent local storage
- **Concurrent execution** — parallel network operations
- **PyInstaller** — Windows executable packaging

## Requirements

- Windows
- Python and the dependencies listed in `requirements.txt`
- Network access to the target devices
- SSH credentials with sufficient permissions
- A compatible configuration for your environment

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/mzarchi/cisco-app.git
cd cisco-app
```

### 2. Create a Virtual Environment

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
```

### 3. Install Dependencies

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 4. Configure the Application

Review `config.py` and update the Windows-specific filesystem paths to match your environment.

Ensure the required configuration, device access information, and supporting files are available before launching the application.

### 5. Start Cisco App

```bash
python main.py
```

## Command Reference

| Key | Function |
|:--:|:--|
| `0` | Application settings |
| `1` | IP scanner and subnet discovery |
| `2` | Switch scanning |
| `3` | Switch status information |
| `4` | Switch links and uplinks |
| `5` | Switch IP inventory |
| `6` | DNS lookup by IP |
| `7` | Switch configuration manager |
| `8` | Access-list manager |
| `9` | Configuration and operational backups |
| `s` | Search switch IP records |
| `c` | Export data to CSV |
| `r` | Execute an SQL query |
| `e` | Exit |

## Project Structure

```text
cisco-app/
├── icon/
│   └── cisco-app.ico
├── PeriodicWorker.py
├── config.py
├── core.py
├── database.py
├── decorators.py
├── encrypt.py.example
├── main.py
├── requirements.txt
├── version_info.txt
└── README.md
```

## Security

Cisco App can interact with sensitive network infrastructure and store operational information.

- Use the application only on networks you are authorized to manage.
- Never commit credentials, sensitive configurations, or production database files.
- Use accounts with the minimum permissions necessary.
- Protect local databases, backups, logs, and exported data.

**Important:** The provided `encrypt.py.example` is a placeholder. Its encoding and decoding methods do not perform actual encryption. Do not rely on it to protect credentials or other sensitive data.

## Building a Windows Executable

A starting point for packaging the application with PyInstaller:

```powershell
pyinstaller --onefile --console --icon=icon/cisco-app.ico --version-file=version_info.txt main.py
```

Validate the required dependencies, configuration files, and runtime paths before distributing the executable.

## Contributing

Contributions, bug reports, and feature suggestions are welcome.

When submitting changes, include a clear description of the problem, reproduction steps, and sanitized diagnostic information. Do not share real credentials or sensitive infrastructure data.

## Disclaimer

Cisco App is an independent project and is not affiliated with, endorsed by, or supported by Cisco Systems, Inc.

Test changes in a controlled environment before applying them to production infrastructure.

## Author

**[@mzarchi](https://github.com/mzarchi)**

**Repository:** [github.com/mzarchi/cisco-app](https://github.com/mzarchi/cisco-app)

