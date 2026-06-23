<#
=====================================================================
 Optimize-WeakPC.ps1
 Самостоятельный скрипт оптимизации слабого ПК на Windows 10/11.

 Скрипт сам определяет железо и сам выбирает твики — ручного ввода нет.
 Безопасен: создаёт точку восстановления, не трогает Windows Update,
 Defender и Microsoft Store, все правки реестра идемпотентны и
 комментируются с исходным значением.

 Запуск (от имени администратора):
   powershell -ExecutionPolicy Bypass -File .\Optimize-WeakPC.ps1
=====================================================================
#>

#region ============ 0. ПОДГОТОВКА: ЛОГ И ОБРАБОТКА ОШИБОК ============

# Жёсткая остановка при необработанной ошибке выполнения команд.
$ErrorActionPreference = 'Stop'

# Каталог и файл лога. Имя файла содержит дату/время запуска.
$LogDir  = 'C:\OptimizeLog'
$LogFile = Join-Path $LogDir ("optimize_{0}.log" -f (Get-Date -Format 'yyyy-MM-dd_HHmmss'))

if (-not (Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
}

# Функция логирования: пишет в файл и в консоль с уровнем важности.
function Write-Log {
    param(
        [Parameter(Mandatory)] [string] $Message,
        [ValidateSet('INFO','WARN','ERROR','OK')] [string] $Level = 'INFO'
    )
    $stamp = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
    $line  = "[{0}] [{1}] {2}" -f $stamp, $Level, $Message
    # Дописываем в лог-файл (UTF-8, чтобы кириллица читалась корректно).
    Add-Content -Path $LogFile -Value $line -Encoding UTF8
    # Цвет в консоли по уровню.
    switch ($Level) {
        'INFO'  { Write-Host $line -ForegroundColor Gray }
        'OK'    { Write-Host $line -ForegroundColor Green }
        'WARN'  { Write-Host $line -ForegroundColor Yellow }
        'ERROR' { Write-Host $line -ForegroundColor Red }
    }
}

Write-Log "=== Запуск Optimize-WeakPC.ps1 ===" 'INFO'
Write-Log "Лог пишется в: $LogFile" 'INFO'

#endregion

#region ============ 1. ПРОВЕРКА ПРАВ АДМИНИСТРАТОРА ============

# Без прав администратора большинство операций (службы, реестр HKLM,
# точка восстановления) недоступны — поэтому проверяем сразу и выходим.
$principal = New-Object Security.Principal.WindowsPrincipal(
    [Security.Principal.WindowsIdentity]::GetCurrent()
)
$isAdmin = $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Log "Скрипт запущен БЕЗ прав администратора. Остановка." 'ERROR'
    Write-Host ""
    Write-Host "Запустите PowerShell от имени администратора и повторите." -ForegroundColor Red
    exit 1
}
Write-Log "Права администратора подтверждены." 'OK'

#endregion

#region ============ 2. АВТОДЕТЕКТ ЖЕЛЕЗА ============

Write-Log "--- Определение конфигурации железа ---" 'INFO'

# --- Оперативная память ---
$cs        = Get-CimInstance Win32_ComputerSystem
$RamBytes  = [double]$cs.TotalPhysicalMemory
$RamGB     = [math]::Round($RamBytes / 1GB, 1)

# Модули памяти: количество и максимальная частота (для информации).
$RamModules = Get-CimInstance Win32_PhysicalMemory
$RamModCount = ($RamModules | Measure-Object).Count
$RamSpeed    = ($RamModules | Measure-Object -Property Speed -Maximum).Maximum

# --- Процессор ---
# Берём первый сокет (для типичного ПК он один).
$cpu        = Get-CimInstance Win32_Processor | Select-Object -First 1
$CpuName    = $cpu.Name.Trim()
$CpuCores   = [int]$cpu.NumberOfCores
$CpuThreads = [int]$cpu.NumberOfLogicalProcessors

# --- Диски: тип HDD / SSD ---
# Get-PhysicalDisk.MediaType: 'HDD', 'SSD' или 'Unspecified'.
# Фолбэк: SpindleSpeed = 0 -> SSD, иначе HDD.
$Disks = @()
try {
    $phys = Get-PhysicalDisk -ErrorAction Stop
    foreach ($d in $phys) {
        $type = switch ("$($d.MediaType)") {
            'SSD' { 'SSD' }
            'HDD' { 'HDD' }
            'SCM' { 'SSD' }   # Storage Class Memory — трактуем как твердотельную
            default {
                # MediaType не определён — пробуем по скорости шпинделя.
                if ($null -ne $d.SpindleSpeed -and $d.SpindleSpeed -eq 0) { 'SSD' }
                elseif ($null -ne $d.SpindleSpeed -and $d.SpindleSpeed -gt 0) { 'HDD' }
                else { 'Unknown' }
            }
        }
        $Disks += [pscustomobject]@{
            Number     = $d.DeviceId
            Model      = $d.FriendlyName
            SizeGB     = [math]::Round($d.Size / 1GB, 0)
            MediaType  = $type
        }
    }
}
catch {
    Write-Log "Get-PhysicalDisk недоступен ($($_.Exception.Message)). Тип дисков не определён." 'WARN'
}

$HasHDD = [bool]($Disks | Where-Object MediaType -eq 'HDD')
$HasSSD = [bool]($Disks | Where-Object MediaType -eq 'SSD')
# "Все диски SSD" — только если HDD точно нет и SSD точно есть.
$AllSSD = ($HasSSD -and -not $HasHDD)

# --- Видеокарта ---
$gpus   = Get-CimInstance Win32_VideoController
$Gpu    = ($gpus | Select-Object -First 1)
$GpuName = $Gpu.Name
# AdapterRAM иногда неверен (>4ГБ переполняется), но как ориентир годится.
$GpuVramMB = if ($Gpu.AdapterRAM) { [math]::Round($Gpu.AdapterRAM / 1MB, 0) } else { 0 }

# Признак слабого/интегрированного GPU:
#  - по имени (Intel HD/UHD/Iris, AMD Radeon(TM) Graphics в APU, Microsoft Basic)
#  - либо по объёму видеопамяти < 1 ГБ
$IntegratedPattern = 'Intel.*(HD|UHD|Iris)|AMD Radeon\(TM\) Graphics|Radeon Vega|Microsoft Basic Display'
$WeakGpu = ($GpuName -match $IntegratedPattern) -or ($GpuVramMB -gt 0 -and $GpuVramMB -lt 1024)

# --- Версия и сборка Windows ---
$os         = Get-CimInstance Win32_OperatingSystem
$WinCaption = $os.Caption
$WinVersion = $os.Version
$WinBuild   = $os.BuildNumber
# DisplayVersion (например 22H2) лежит в реестре.
$WinDisplay = (Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion' `
                -Name DisplayVersion -ErrorAction SilentlyContinue).DisplayVersion

# --- Флаги-решения ---
$LowRam     = $RamGB -lt 8
$VeryLowRam = $RamGB -lt 4

# --- Вывод понятным списком ---
Write-Host ""
Write-Host "================ ОБНАРУЖЕННОЕ ЖЕЛЕЗО ================" -ForegroundColor Cyan
$summary = @"
ОЗУ            : $RamGB ГБ ($RamModCount модул., до $RamSpeed МГц)
Процессор      : $CpuName
               : ядер $CpuCores, потоков $CpuThreads
Видеокарта     : $GpuName (видеопамять ~$GpuVramMB МБ)
Windows        : $WinCaption $WinDisplay (вер. $WinVersion, сборка $WinBuild)
"@
Write-Host $summary -ForegroundColor White

Write-Host "Диски:" -ForegroundColor White
if ($Disks.Count -gt 0) {
    foreach ($d in $Disks) {
        Write-Host ("  - #{0} {1} [{2}, {3} ГБ]" -f $d.Number, $d.Model, $d.MediaType, $d.SizeGB) -ForegroundColor White
    }
} else {
    Write-Host "  (не удалось определить)" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Выводы для оптимизации:" -ForegroundColor Cyan
Write-Host ("  Мало RAM (<8 ГБ)      : {0}" -f $LowRam)  -ForegroundColor White
Write-Host ("  Очень мало RAM (<4 ГБ): {0}" -f $VeryLowRam) -ForegroundColor White
Write-Host ("  Есть HDD              : {0}" -f $HasHDD)  -ForegroundColor White
Write-Host ("  Только SSD            : {0}" -f $AllSSD)  -ForegroundColor White
Write-Host ("  Слабый/инт. GPU       : {0}" -f $WeakGpu) -ForegroundColor White
Write-Host "====================================================" -ForegroundColor Cyan
Write-Host ""

# Дублируем всё в лог.
Write-Log "RAM=$RamGB ГБ; CPU='$CpuName' ($CpuCores/$CpuThreads); GPU='$GpuName' (~$GpuVramMB МБ); Windows='$WinCaption $WinDisplay' build $WinBuild" 'INFO'
foreach ($d in $Disks) { Write-Log ("Диск #{0} '{1}' тип={2} {3}ГБ" -f $d.Number,$d.Model,$d.MediaType,$d.SizeGB) 'INFO' }
Write-Log "Флаги: LowRam=$LowRam VeryLowRam=$VeryLowRam HasHDD=$HasHDD AllSSD=$AllSSD WeakGpu=$WeakGpu" 'INFO'

#endregion

#region ============ 3. ТОЧКА ВОССТАНОВЛЕНИЯ ============

Write-Log "--- Создание точки восстановления системы ---" 'INFO'
try {
    # Защита системы должна быть включена на системном диске.
    Enable-ComputerRestore -Drive "$env:SystemDrive\" -ErrorAction SilentlyContinue

    # System Restore по умолчанию ограничивает создание точек чаще, чем раз
    # в 24 часа. Снимаем ограничение частоты на время работы скрипта.
    $sr = 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\SystemRestore'
    if (-not (Test-Path $sr)) { New-Item -Path $sr -Force | Out-Null }
    New-ItemProperty -Path $sr -Name 'SystemRestorePointCreationFrequency' `
        -PropertyType DWord -Value 0 -Force | Out-Null

    Checkpoint-Computer -Description "Optimize-WeakPC (до оптимизации)" `
        -RestorePointType 'MODIFY_SETTINGS' -ErrorAction Stop

    Write-Log "Точка восстановления успешно создана." 'OK'
}
catch {
    Write-Log "НЕ удалось создать точку восстановления: $($_.Exception.Message)" 'ERROR'
    Write-Host ""
    Write-Host "Возможные причины:" -ForegroundColor Yellow
    Write-Host "  - Защита системы отключена (System Protection)." -ForegroundColor Yellow
    Write-Host "  - Недостаточно места на системном диске." -ForegroundColor Yellow
    Write-Host "Оптимизация остановлена ради безопасности." -ForegroundColor Red
    exit 1
}

#endregion

#region ============ 4. ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ============

# Список служб, которые НИКОГДА нельзя трогать (Update / Defender / Store).
$ProtectedServices = @(
    'wuauserv','bits','usosvc','UsoSvc','DoSvc',          # Windows Update
    'WinDefend','SecurityHealthService','Sense','WdNisSvc','wscsvc', # Defender / безопасность
    'mpssvc',                                              # Брандмауэр
    'InstallService','AppXSvc','ClipSVC'                   # Microsoft Store
)

# Идемпотентная установка значения реестра с логом исходного значения.
function Set-RegistryValue {
    param(
        [Parameter(Mandatory)][string]$Path,
        [Parameter(Mandatory)][string]$Name,
        [Parameter(Mandatory)]$Value,
        [ValidateSet('DWord','String','Binary','ExpandString','QWord')]$Type = 'DWord',
        [string]$Comment = ''
    )
    try {
        if (-not (Test-Path $Path)) { New-Item -Path $Path -Force | Out-Null }

        $current = $null
        try { $current = (Get-ItemProperty -Path $Path -Name $Name -ErrorAction Stop).$Name } catch {}

        # Для бинарных значений сравниваем как строки.
        $same = if ($Type -eq 'Binary') {
            ($null -ne $current) -and (($current -join ',') -eq ($Value -join ','))
        } else {
            ($null -ne $current) -and ($current -eq $Value)
        }

        if ($same) {
            Write-Log "  [пропуск] $Path\$Name уже = '$Value' ($Comment)" 'INFO'
            return
        }

        $wasText = if ($null -eq $current) { '<не задано>' } else { "$current" }
        # Логируем ИСХОДНОЕ значение для возможного отката.
        Write-Log "  [реестр] $Path\$Name : было '$wasText' -> ставим '$Value'  # откат: вернуть '$wasText'  ($Comment)" 'INFO'

        New-ItemProperty -Path $Path -Name $Name -Value $Value -PropertyType $Type -Force | Out-Null
    }
    catch {
        Write-Log "  [ОШИБКА реестра] $Path\$Name : $($_.Exception.Message)" 'WARN'
    }
}

# Идемпотентная смена типа запуска службы с защитой "чёрного списка".
function Set-ServiceStartup {
    param(
        [Parameter(Mandatory)][string]$Name,
        [ValidateSet('Automatic','Manual','Disabled')]$StartupType = 'Manual',
        [switch]$StopNow,
        [string]$Reason = ''
    )
    # Защита: служба из чёрного списка пропускается всегда.
    if ($ProtectedServices -contains $Name) {
        Write-Log "  [ЗАЩИТА] Служба '$Name' в списке неприкосновенных — пропуск." 'WARN'
        return
    }
    try {
        $svc = Get-Service -Name $Name -ErrorAction Stop
        $current = (Get-CimInstance Win32_Service -Filter "Name='$Name'").StartMode
        if ($current -eq 'Auto') { $current = 'Automatic' }

        if ($current -eq $StartupType) {
            Write-Log "  [пропуск] Служба '$Name' уже '$StartupType' ($Reason)" 'INFO'
        } else {
            Write-Log "  [служба] '$Name' : было '$current' -> '$StartupType'  # откт: вернуть '$current'  ($Reason)" 'INFO'
            Set-Service -Name $Name -StartupType $StartupType -ErrorAction Stop
        }

        if ($StopNow -and $svc.Status -eq 'Running') {
            Write-Log "  [служба] Останавливаю '$Name'." 'INFO'
            Stop-Service -Name $Name -Force -ErrorAction SilentlyContinue
        }
    }
    catch {
        Write-Log "  [служба] '$Name' недоступна/не найдена — пропуск. ($($_.Exception.Message))" 'INFO'
    }
}

#endregion

#region ============ 5. БАЗОВЫЕ ТВИКИ (применяются всегда) ============

Write-Log "--- Базовая оптимизация (для любого железа) ---" 'INFO'

# 5.1 План электропитания -> "Высокая производительность".
# На слабом ноутбуке это ускоряет отклик (минус — расход батареи).
try {
    $highPerf = '8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c'  # GUID схемы High performance
    $exists = (powercfg /list) -match $highPerf
    if ($exists) {
        powercfg /setactive $highPerf | Out-Null
        Write-Log "  План питания переключён на 'Высокая производительность'." 'OK'
    } else {
        Write-Log "  Схема 'Высокая производительность' отсутствует — пропуск." 'INFO'
    }
}
catch { Write-Log "  Не удалось сменить план питания: $($_.Exception.Message)" 'WARN' }

# 5.2 Визуальные эффекты -> "Наилучшее быстродействие".
# VisualFXSetting: 0=авто, 1=лучший вид, 2=лучшее быстродействие, 3=пользоват.
Set-RegistryValue -Path 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\VisualEffects' `
    -Name 'VisualFXSetting' -Value 2 -Type DWord `
    -Comment 'Наилучшее быстродействие интерфейса'

#endregion

#region ============ 6. АДАПТИВНЫЕ ТВИКИ ПО RAM ============

if ($LowRam) {
    Write-Log "--- Мало RAM (<8 ГБ): режем фон и эффекты ---" 'INFO'

    # Отключаем анимацию окон и панели задач (экономия на отрисовке).
    Set-RegistryValue -Path 'HKCU:\Control Panel\Desktop\WindowMetrics' `
        -Name 'MinAnimate' -Value '0' -Type String -Comment 'Отключить анимацию свёртывания окон'
    Set-RegistryValue -Path 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced' `
        -Name 'TaskbarAnimations' -Value 0 -Type DWord -Comment 'Отключить анимации панели задач'

    # Телеметрия и второстепенные службы — безопасный набор.
    Set-ServiceStartup -Name 'DiagTrack'   -StartupType Disabled -StopNow -Reason 'Телеметрия (Connected User Experiences)'
    Set-ServiceStartup -Name 'dmwappushservice' -StartupType Disabled -StopNow -Reason 'WAP Push маршрутизация (телеметрия)'
    Set-ServiceStartup -Name 'Fax'         -StartupType Disabled -Reason 'Факс — на ПК обычно не нужен'
    Set-ServiceStartup -Name 'RetailDemo'  -StartupType Disabled -Reason 'Демо-режим магазина'
    Set-ServiceStartup -Name 'MapsBroker'  -StartupType Manual   -Reason 'Загрузка офлайн-карт'
    Set-ServiceStartup -Name 'RemoteRegistry' -StartupType Disabled -Reason 'Удалённый реестр (риск/не нужен дома)'

    # SysMain (Superfetch): на SSD пользы мало, на HDD может быть полезен.
    # Поэтому трогаем ТОЛЬКО если все диски SSD.
    if ($AllSSD) {
        Set-ServiceStartup -Name 'SysMain' -StartupType Manual -Reason 'Superfetch малополезен на SSD'
    } else {
        Write-Log "  SysMain не трогаем: есть HDD, где он может помогать кэшированию." 'INFO'
    }

    # Windows Search отключаем только при ОЧЕНЬ малой памяти (<4 ГБ),
    # т.к. индексатор заметно расходует RAM и диск.
    if ($VeryLowRam) {
        Set-ServiceStartup -Name 'WSearch' -StartupType Disabled -StopNow -Reason 'Индексатор поиска (RAM<4ГБ)'
    } else {
        Write-Log "  WSearch оставляем: RAM >= 4 ГБ." 'INFO'
    }
}
else {
    Write-Log "--- RAM >= 8 ГБ: агрессивная чистка служб не требуется ---" 'INFO'
}

#endregion

#region ============ 7. АДАПТИВНЫЕ ТВИКИ ПО ДИСКАМ ============

# ВАЖНО: логика для HDD и SSD ПРОТИВОПОЛОЖНА.
if ($HasHDD) {
    Write-Log "--- Обнаружен HDD: настраиваем дефрагментацию по расписанию ---" 'INFO'
    try {
        # Штатная задача оптимизации дисков Windows.
        $task = Get-ScheduledTask -TaskName 'ScheduledDefrag' `
                  -TaskPath '\Microsoft\Windows\Defrag\' -ErrorAction Stop
        if ($task.State -eq 'Disabled') {
            Enable-ScheduledTask -InputObject $task | Out-Null
            Write-Log "  Включена штатная задача 'ScheduledDefrag'." 'OK'
        } else {
            Write-Log "  Задача 'ScheduledDefrag' уже активна — ок." 'INFO'
        }
        Write-Log "  Дефрагментация HDD будет идти по штатному расписанию (еженедельно)." 'INFO'
    }
    catch {
        Write-Log "  Не удалось настроить штатную задачу дефрага: $($_.Exception.Message)" 'WARN'
    }
}

if ($AllSSD) {
    Write-Log "--- Только SSD: дефрагментацию НЕ выполняем (вредно для SSD) ---" 'INFO'
    # Для SSD важен TRIM. Проверяем и при необходимости включаем.
    try {
        $trim = (fsutil behavior query DisableDeleteNotify) -join ' '
        # DisableDeleteNotify = 0  -> TRIM ВКЛЮЧЁН.
        if ($trim -match 'DisableDeleteNotify\s*=\s*1') {
            fsutil behavior set DisableDeleteNotify 0 | Out-Null
            Write-Log "  TRIM был отключён — включили (DisableDeleteNotify=0)." 'OK'
        } else {
            Write-Log "  TRIM уже включён — ок." 'INFO'
        }
    }
    catch { Write-Log "  Не удалось проверить/включить TRIM: $($_.Exception.Message)" 'WARN' }
}

if (-not $HasHDD -and -not $AllSSD) {
    Write-Log "--- Тип дисков не определён: дисковые твики пропущены ---" 'WARN'
}

#endregion

#region ============ 8. АДАПТИВНЫЕ ТВИКИ ПО GPU ============

if ($WeakGpu) {
    Write-Log "--- Слабый/интегрированный GPU: отключаем прозрачность и анимации ---" 'INFO'

    # Прозрачность интерфейса (Aero/Acrylic) — нагрузка на GPU.
    Set-RegistryValue -Path 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Themes\Personalize' `
        -Name 'EnableTransparency' -Value 0 -Type DWord -Comment 'Отключить прозрачность интерфейса'

    # Глобальное отключение анимаций интерфейса для слабого GPU.
    Set-RegistryValue -Path 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\VisualEffects' `
        -Name 'VisualFXSetting' -Value 2 -Type DWord -Comment 'Быстродействие вместо красоты (GPU)'

    # Анимация при сворачивании/разворачивании окон.
    Set-RegistryValue -Path 'HKCU:\Control Panel\Desktop\WindowMetrics' `
        -Name 'MinAnimate' -Value '0' -Type String -Comment 'Отключить анимацию окон (GPU)'
}
else {
    Write-Log "--- GPU достаточно производителен: визуальные эффекты не режем дополнительно ---" 'INFO'
}

#endregion

#region ============ 9. ЗАВЕРШЕНИЕ ============

Write-Log "=== Оптимизация завершена ===" 'OK'
Write-Host ""
Write-Host "Готово. Подробный лог: $LogFile" -ForegroundColor Green
Write-Host "Рекомендуется перезагрузить компьютер для применения всех изменений." -ForegroundColor Cyan
Write-Host "Откат: используйте созданную точку восстановления или значения 'было' из лога." -ForegroundColor Cyan

#endregion
