"""Защитные списки: что инструмент НИКОГДА не трогает.

Принцип «максимум скорости при максимуме совместимости»: критичные для
безопасности и работы системы компоненты неприкосновенны независимо от того,
что написано в playbook.
"""
from __future__ import annotations

# Службы, которые нельзя отключать ни при каких условиях.
PROTECTED_SERVICES = {
    # Windows Update
    "wuauserv", "bits", "UsoSvc", "DoSvc", "TrustedInstaller", "msiserver",
    # Defender / безопасность
    "WinDefend", "SecurityHealthService", "Sense", "WdNisSvc", "wscsvc",
    "mpssvc", "SgrmBroker",
    # Store / лицензии
    "InstallService", "AppXSvc", "ClipSVC", "LicenseManager",
    # Ядро ОС
    "RpcSs", "DcomLaunch", "RpcEptMapper", "LSM", "BrokerInfrastructure",
    "SystemEventsBroker", "Power", "ProfSvc", "Themes", "EventLog",
    "PlugPlay", "Dhcp", "Dnscache", "nsi", "CoreMessagingRegistrar",
    "gpsvc", "UserManager", "Schedule",
}

# UWP-пакеты, которые нельзя удалять (совместимость/безопасность).
PROTECTED_APPX = {
    "Microsoft.WindowsStore", "Microsoft.WindowsDefender", "Microsoft.SecHealthUI",
    "Microsoft.Windows.Photos", "Microsoft.WindowsCalculator", "Microsoft.WindowsNotepad",
    "Microsoft.Paint", "Microsoft.ScreenSketch", "Microsoft.WindowsTerminal",
    "Microsoft.PowerShell", "Microsoft.DesktopAppInstaller", "Microsoft.UI.Xaml",
    "Microsoft.VCLibs", "Microsoft.NET",
}

# Компоненты DISM, которые не трогаем (нужны многим программам).
PROTECTED_FEATURES = {
    "NetFx3", "NetFx4-AdvSrvs",
}

# Ветки реестра, в которые запрещено писать (защита от поломки безопасности).
PROTECTED_REGISTRY_PREFIXES = (
    r"HKLM\SOFTWARE\Microsoft\Windows Defender",
    r"HKLM\SOFTWARE\Policies\Microsoft\Windows Defender",
    r"HKLM\SYSTEM\CurrentControlSet\Services\WinDefend",
)


def is_protected_service(name: str) -> bool:
    return name in PROTECTED_SERVICES


def is_protected_appx(name: str) -> bool:
    return any(name.startswith(p) or name == p for p in PROTECTED_APPX)


def is_protected_feature(name: str) -> bool:
    return name in PROTECTED_FEATURES


def is_protected_registry(path: str) -> bool:
    p = path.replace("/", "\\")
    return any(p.lower().startswith(x.lower()) for x in PROTECTED_REGISTRY_PREFIXES)
