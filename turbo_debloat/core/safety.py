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
    # Имена служб Windows регистронезависимы — сравниваем без учёта регистра,
    # чтобы защита не зависела от того, как служба записана в playbook.
    n = (name or "").lower()
    return any(n == s.lower() for s in PROTECTED_SERVICES)


def is_protected_appx(name: str) -> bool:
    # Имя пакета — это либо короткое имя ("Microsoft.WindowsStore"), либо полное
    # ("Microsoft.WindowsStore_8wekyb3d8bbwe"), либо под-namespace
    # (".NET" -> "Microsoft.NET.Native.Framework"). Совпадение проверяем строго
    # по границе (== / "_" / "."), иначе "Microsoft.NET" ошибочно ловит
    # "Microsoft.NetworkSpeedTest".
    n = (name or "").lower()
    for p in PROTECTED_APPX:
        pl = p.lower()
        if n == pl or n.startswith(pl + "_") or n.startswith(pl + "."):
            return True
    return False


def is_protected_feature(name: str) -> bool:
    n = (name or "").lower()
    return any(n == f.lower() for f in PROTECTED_FEATURES)


def is_protected_registry(path: str) -> bool:
    p = (path or "").replace("/", "\\")
    return any(p.lower().startswith(x.lower()) for x in PROTECTED_REGISTRY_PREFIXES)
