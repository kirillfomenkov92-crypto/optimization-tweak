﻿<#
=====================================================================
 Optimize-WeakPC.ps1
 Самостоятельный скрипт оптимизации слабого ПК на Windows 10/11.

 Скрипт сам определяет железо и сам выбирает твики — ручного ввода нет.
 Безопасен: создаёт точку восстановления, не трогает Windows Update,
 Defender и Microsoft Store, все правки реестра идемпотентны и
 комментируются с исходным значением.

 Запуск (от имени администратора):
   powershell -ExecutionPolicy Bypass -File .\Optimize-WeakPC.ps1
 Пробный прогон без изменений (рекомендуется первым):
   powershell -ExecutionPolicy Bypass -File .\Optimize-WeakPC.ps1 -DryRun
=====================================================================
#>

#Requires -Version 5.1

[CmdletBinding()]
param(
    # -DryRun: пройти весь скрипт, показать "БЫЛО БЫ ИЗМЕНЕНО: ...",
    # но НИЧЕГО реально не менять (реестр, службы, питание, дефраг,
    # TRIM, перезапуск Explorer). Точка восстановления в dry-run НЕ создаётся.
    [switch]$DryRun
)

#region ============ 0. ПОДГОТОВКА: ЛОГ И ОБРАБОТКА ОШИБОК ============

# Жёсткая остановка при необработанной ошибке выполнения команд.
$ErrorActionPreference = 'Stop'
# Прогресс-бары отдельных командлетов лишь засоряют вывод — отключаем.
$ProgressPreference = 'SilentlyContinue'

# Принудительно переводим вывод консоли в UTF-8, иначе в legacy-консоли
# (Windows PowerShell 5.1 + кодовая страница 866/1251) кириллица в Write-Host
# и Write-Log отображается «квадратами». В некоторых хостах смена кодировки
# недоступна — поэтому мягко, через try/catch.
try {
    $OutputEncoding = [System.Text.Encoding]::UTF8
    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
} catch { }

# Каталог и файл лога. Имя файла содержит дату/время запуска.
# Если прав на C:\ нет (обычный пользователь до повышения) — пишем во временную папку,
# иначе скрипт упал бы здесь раньше, чем сработало бы автоповышение прав.
$LogDir = 'C:\OptimizeLog'
try {
    if (-not (Test-Path $LogDir)) { New-Item -ItemType Directory -Path $LogDir -Force -ErrorAction Stop | Out-Null }
}
catch {
    $LogDir = Join-Path $env:TEMP 'OptimizeLog'
    if (-not (Test-Path $LogDir)) { New-Item -ItemType Directory -Path $LogDir -Force | Out-Null }
}
$LogFile = Join-Path $LogDir ("optimize_{0}.log" -f (Get-Date -Format 'yyyy-MM-dd_HHmmss'))

# Функция логирования: пишет в файл и в консоль с уровнем важности.
# Сбой записи в лог НЕ должен ронять весь скрипт, поэтому пишем мягко.
function Write-Log {
    param(
        [Parameter(Mandatory)] [string] $Message,
        [ValidateSet('INFO','WARN','ERROR','OK','DRY')] [string] $Level = 'INFO'
    )
    $stamp = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
    $line  = "[{0}] [{1}] {2}" -f $stamp, $Level, $Message
    try { Add-Content -Path $LogFile -Value $line -Encoding UTF8 -ErrorAction Stop }
    catch { Write-Host "(не удалось записать в лог: $($_.Exception.Message))" -ForegroundColor DarkYellow }
    switch ($Level) {
        'INFO'  { Write-Host $line -ForegroundColor Gray }
        'OK'    { Write-Host $line -ForegroundColor Green }
        'WARN'  { Write-Host $line -ForegroundColor Yellow }
        'ERROR' { Write-Host $line -ForegroundColor Red }
        'DRY'   { Write-Host $line -ForegroundColor Magenta }
    }
}

Write-Log "=== Запуск Optimize-WeakPC.ps1 ===" 'INFO'
Write-Log "Лог пишется в: $LogFile" 'INFO'
if ($DryRun) {
    Write-Log "РЕЖИМ -DryRun: изменения НЕ применяются, только показываются." 'DRY'
}

#endregion

#region ============ 1. ПРОВЕРКА ПРАВ АДМИНИСТРАТОРА ============

# Без прав администратора большинство операций (службы, реестр HKLM,
# точка восстановления) недоступны — поэтому проверяем сразу и выходим.
$principal = New-Object Security.Principal.WindowsPrincipal(
    [Security.Principal.WindowsIdentity]::GetCurrent()
)
$isAdmin = $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Log "Нет прав администратора — пробую перезапуститься с повышением (UAC)." 'WARN'
    # Без пути к файлу скрипта (например, при запуске из конвейера) перезапуск невозможен.
    if (-not $PSCommandPath) {
        Write-Log "Не удалось определить путь скрипта для перезапуска." 'ERROR'
        Write-Host "Запустите PowerShell от имени администратора и повторите." -ForegroundColor Red
        exit 1
    }
    try {
        # Перезапускаем себя элевированно, сохраняя режим -DryRun.
        $relaunchArgs = @('-NoProfile','-ExecutionPolicy','Bypass','-File', "`"$PSCommandPath`"")
        if ($DryRun) { $relaunchArgs += '-DryRun' }
        Start-Process -FilePath 'powershell.exe' -Verb RunAs -ArgumentList $relaunchArgs | Out-Null
        Write-Log "Запущена копия с повышением прав. Текущий (обычный) процесс завершается." 'INFO'
        exit 0
    }
    catch {
        Write-Log "Повышение прав отклонено или не удалось: $($_.Exception.Message)" 'ERROR'
        Write-Host ""
        Write-Host "Запустите PowerShell от имени администратора и повторите." -ForegroundColor Red
        exit 1
    }
}
Write-Log "Права администратора подтверждены." 'OK'

#endregion

#region ============ 2. АВТОДЕТЕКТ ЖЕЛЕЗА ============

Write-Log "--- Определение конфигурации железа ---" 'INFO'

# Весь детект обёрнут в try/catch: при $ErrorActionPreference='Stop' любой
# сбой CIM иначе уронил бы скрипт без понятного сообщения. Детект идёт ДО
# точки восстановления и ДО любых изменений, поэтому сбой здесь безопасен.
try {
    # --- Оперативная память ---
    # ВАЖНО: Win32_ComputerSystem.TotalPhysicalMemory возвращает память ЗА
    # ВЫЧЕТОМ аппаратно-зарезервированной (на 8 ГБ машине это ~7.8 ГБ), из-за
    # чего честные 8 ГБ ошибочно попадали бы в ветку "<8 ГБ". Поэтому для
    # КЛАССИФИКАЦИИ берём сумму ёмкостей модулей (полный установленный объём).
    $cs           = Get-CimInstance Win32_ComputerSystem
    $RamVisibleGB = [math]::Round([double]$cs.TotalPhysicalMemory / 1GB, 1)

    $RamModules  = @(Get-CimInstance Win32_PhysicalMemory)
    $RamModCount = $RamModules.Count
    $RamSpeed    = ($RamModules | Measure-Object -Property Speed -Maximum).Maximum
    $capSum      = ($RamModules | Measure-Object -Property Capacity -Sum).Sum

    if ($capSum -and $capSum -gt 0) {
        # Полный установленный объём (для порогов).
        $RamGB = [math]::Round([double]$capSum / 1GB, 1)
    } else {
        # Фолбэк: округляем видимую память ВВЕРХ до целого ГБ, чтобы 7.8 -> 8.
        $RamGB = [math]::Ceiling($RamVisibleGB)
        Write-Log "Win32_PhysicalMemory.Capacity недоступен — RAM оценена по видимой памяти (округление вверх)." 'WARN'
    }

    # --- Процессор ---
    # Имя берём с первого сокета, ядра/потоки СУММИРУЕМ по всем сокетам
    # (на серверах их может быть несколько — иначе число занижалось бы).
    $cpus       = @(Get-CimInstance Win32_Processor)
    $cpu        = $cpus | Select-Object -First 1
    $CpuName    = if ($cpu -and $cpu.Name) { $cpu.Name.Trim() } else { 'неизвестно' }
    $CpuCores   = [int](($cpus | Measure-Object -Property NumberOfCores -Sum).Sum)
    $CpuThreads = [int](($cpus | Measure-Object -Property NumberOfLogicalProcessors -Sum).Sum)

    # --- Диски: тип HDD / SSD ---
    # Get-PhysicalDisk.MediaType: 'HDD'(3), 'SSD'(4), 'SCM'(5), 'Unspecified'(0).
    # Фолбэк по SpindleSpeed: 0 -> SSD; >0 и НЕ "неизвестно" -> HDD.
    # КРИТИЧНО: многие SSD/NVMe при неизвестном MediaType отдают
    # SpindleSpeed = 0xFFFFFFFF (4294967295) = "неизвестно" — это НЕ HDD,
    # такой диск помечаем Unknown (а не ошибочно дефрагментируем).
    $UnknownSpindle = [uint32]::MaxValue   # 4294967295 = 0xFFFFFFFF
    $Disks = @()
    try {
        $phys = Get-PhysicalDisk -ErrorAction Stop
        foreach ($d in $phys) {
            $type = switch ("$($d.MediaType)") {
                'SSD' { 'SSD' }
                'HDD' { 'HDD' }
                'SCM' { 'SSD' }   # Storage Class Memory — твердотельная
                default {
                    $ss = $d.SpindleSpeed
                    if     ($null -eq $ss)                 { 'Unknown' }
                    elseif ([uint32]$ss -eq $UnknownSpindle){ 'Unknown' }  # 0xFFFFFFFF
                    elseif ($ss -eq 0)                      { 'SSD' }
                    elseif ($ss -gt 0)                      { 'HDD' }
                    else                                    { 'Unknown' }
                }
            }
            # Съёмные/USB-носители не учитываем при дисковых твиках.
            $bus = "$($d.BusType)"
            if ($bus -in @('USB','SD','MMC')) { $type = 'Removable' }

            $Disks += [pscustomobject]@{
                Number    = $d.DeviceId
                Model     = $d.FriendlyName
                SizeGB    = [math]::Round($d.Size / 1GB, 0)
                MediaType = $type
                BusType   = $bus
            }
        }
    }
    catch {
        Write-Log "Get-PhysicalDisk недоступен ($($_.Exception.Message)). Тип дисков не определён." 'WARN'
    }

    # Учитываем только внутренние диски (не Removable/Unknown).
    $HasHDD = [bool]($Disks | Where-Object { $_.MediaType -eq 'HDD' })
    $HasSSD = [bool]($Disks | Where-Object { $_.MediaType -eq 'SSD' })
    # "Все диски SSD" — только если HDD точно нет и SSD точно есть.
    $AllSSD = ($HasSSD -and -not $HasHDD)

    # --- Видеокарта ---
    $gpus = @(Get-CimInstance Win32_VideoController)
    # Для отображения берём адаптер с максимальной видеопамятью (обычно основной).
    $Gpu = $gpus | Sort-Object -Property @{E={[int64]($_.AdapterRAM)}} -Descending | Select-Object -First 1
    if (-not $Gpu) { $Gpu = $gpus | Select-Object -First 1 }
    $GpuName   = if ($Gpu) { $Gpu.Name } else { 'неизвестно' }
    # AdapterRAM (uint32) переполняется на >4 ГБ — используем лишь как ориентир.
    $GpuVramMB = if ($Gpu -and $Gpu.AdapterRAM) { [math]::Round([int64]$Gpu.AdapterRAM / 1MB, 0) } else { 0 }

    # Дискретные GPU (если есть ХОТЯ БЫ один — система НЕ считается слабой по GPU).
    $DiscretePattern = 'NVIDIA|GeForce|Quadro|\bRTX\b|\bGTX\b|Radeon RX|Radeon Pro|FirePro|Intel\(R\) Arc|Arc\(TM\)'
    # Интегрированные / отсутствующие драйверы.
    $IntegratedPattern = 'Intel.*(HD|UHD|Iris)|Radeon\(TM\)|Radeon Vega|Vega \d|Radeon Graphics|Microsoft Basic Display|Standard VGA'

    $hasDiscrete = [bool]($gpus | Where-Object { $_.Name -match $DiscretePattern })
    $hasWeakName = [bool]($gpus | Where-Object { $_.Name -match $IntegratedPattern })
    # Слабый GPU: нет ни одной дискретной карты И (имя интегрированное ИЛИ мало VRAM).
    $WeakGpu = (-not $hasDiscrete) -and ($hasWeakName -or ($GpuVramMB -gt 0 -and $GpuVramMB -lt 1024))

    # --- Версия и сборка Windows ---
    $os         = Get-CimInstance Win32_OperatingSystem
    $WinCaption = $os.Caption
    $WinVersion = $os.Version
    $WinBuild   = $os.BuildNumber
    $WinDisplay = (Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion' `
                    -Name DisplayVersion -ErrorAction SilentlyContinue).DisplayVersion
}
catch {
    Write-Log "Сбой автодетекта железа: $($_.Exception.Message). Остановка (изменений не вносилось)." 'ERROR'
    exit 1
}

# --- Флаги-решения ---
$LowRam     = $RamGB -lt 8
$VeryLowRam = $RamGB -lt 4

# --- Вывод понятным списком ---
Write-Host ""
Write-Host "================ ОБНАРУЖЕННОЕ ЖЕЛЕЗО ================" -ForegroundColor Cyan
$summary = @"
ОЗУ            : $RamGB ГБ установлено (видимо системе $RamVisibleGB ГБ, $RamModCount модул., до $RamSpeed МГц)
Процессор      : $CpuName
               : ядер $CpuCores, потоков $CpuThreads
Видеокарта     : $GpuName (видеопамять ~$GpuVramMB МБ)
Windows        : $WinCaption $WinDisplay (вер. $WinVersion, сборка $WinBuild)
"@
Write-Host $summary -ForegroundColor White

Write-Host "Диски:" -ForegroundColor White
if ($Disks.Count -gt 0) {
    foreach ($d in $Disks) {
        Write-Host ("  - #{0} {1} [{2}, {3} ГБ, шина {4}]" -f $d.Number, $d.Model, $d.MediaType, $d.SizeGB, $d.BusType) -ForegroundColor White
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
Write-Log "RAM=$RamGB ГБ (видимо $RamVisibleGB); CPU='$CpuName' ($CpuCores/$CpuThreads); GPU='$GpuName' (~$GpuVramMB МБ, дискр.=$hasDiscrete); Windows='$WinCaption $WinDisplay' build $WinBuild" 'INFO'
foreach ($d in $Disks) { Write-Log ("Диск #{0} '{1}' тип={2} {3}ГБ шина={4}" -f $d.Number,$d.Model,$d.MediaType,$d.SizeGB,$d.BusType) 'INFO' }
Write-Log "Флаги: LowRam=$LowRam VeryLowRam=$VeryLowRam HasHDD=$HasHDD AllSSD=$AllSSD WeakGpu=$WeakGpu" 'INFO'

#endregion

#region ============ 3. ТОЧКА ВОССТАНОВЛЕНИЯ ============

if ($DryRun) {
    Write-Log "[DryRun] Точка восстановления НЕ создаётся (пробный прогон)." 'DRY'
}
else {
    Write-Log "--- Создание точки восстановления системы ---" 'INFO'
    try {
        # Защита системы должна быть включена на системном диске.
        Enable-ComputerRestore -Drive "$env:SystemDrive\" -ErrorAction SilentlyContinue

        # System Restore по умолчанию ограничивает создание точек чаще, чем раз
        # в 24 часа. Сохраняем исходное значение и временно снимаем лимит,
        # затем возвращаем как было (чтобы не оставлять сайд-эффект).
        $sr = 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\SystemRestore'
        if (-not (Test-Path $sr)) { New-Item -Path $sr -Force | Out-Null }
        $origFreq = (Get-ItemProperty -Path $sr -Name 'SystemRestorePointCreationFrequency' -ErrorAction SilentlyContinue).SystemRestorePointCreationFrequency
        Write-Log "  SystemRestorePointCreationFrequency: было '$origFreq' -> временно '0'  # будет восстановлено" 'INFO'
        New-ItemProperty -Path $sr -Name 'SystemRestorePointCreationFrequency' -PropertyType DWord -Value 0 -Force | Out-Null

        # Запоминаем число существующих точек, чтобы потом убедиться в появлении новой.
        $rpBefore = @(Get-ComputerRestorePoint -ErrorAction SilentlyContinue).Count
        try {
            Checkpoint-Computer -Description "Optimize-WeakPC (до оптимизации)" `
                -RestorePointType 'MODIFY_SETTINGS' -ErrorAction Stop
        }
        finally {
            # Возвращаем исходный лимит частоты (откат сайд-эффекта).
            if ($null -eq $origFreq) {
                Remove-ItemProperty -Path $sr -Name 'SystemRestorePointCreationFrequency' -ErrorAction SilentlyContinue
                Write-Log "  SystemRestorePointCreationFrequency восстановлен: ключ удалён (значения не было)." 'INFO'
            } else {
                New-ItemProperty -Path $sr -Name 'SystemRestorePointCreationFrequency' -PropertyType DWord -Value $origFreq -Force | Out-Null
                Write-Log "  SystemRestorePointCreationFrequency восстановлен в '$origFreq'." 'INFO'
            }
        }

        # КРИТИЧНО: Checkpoint-Computer может вернуть успех, но НЕ создать точку
        # (системный троттлинг/политика). Проверяем фактическое появление точки.
        $rpAfter = @(Get-ComputerRestorePoint -ErrorAction SilentlyContinue).Count
        if ($rpAfter -gt $rpBefore) {
            Write-Log "Точка восстановления создана и проверена (точек: $rpBefore -> $rpAfter)." 'OK'
        } else {
            throw "Checkpoint-Computer не создал новую точку (защита системы отключена или сработал троттлинг)."
        }
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
}

#endregion

#region ============ 4. ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ============

# Список служб, которые НИКОГДА нельзя трогать (Update / Defender / Store).
$ProtectedServices = @(
    'wuauserv','bits','UsoSvc','DoSvc',                    # Windows Update
    'WinDefend','SecurityHealthService','Sense','WdNisSvc','wscsvc', # Defender / безопасность
    'mpssvc',                                              # Брандмауэр
    'InstallService','AppXSvc','ClipSVC'                   # Microsoft Store
)

# Идемпотентная установка значения реестра с логом исходного значения.
# В режиме -DryRun реально ничего не пишет.
function Set-RegistryValue {
    param(
        [Parameter(Mandatory)][string]$Path,
        [Parameter(Mandatory)][string]$Name,
        [Parameter(Mandatory)]$Value,
        [ValidateSet('DWord','String','Binary','ExpandString','QWord')]$Type = 'DWord',
        [string]$Comment = ''
    )
    try {
        $current = $null
        if (Test-Path $Path) {
            try { $current = (Get-ItemProperty -Path $Path -Name $Name -ErrorAction Stop).$Name } catch {}
        }

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

        if ($DryRun) {
            Write-Log "  [DryRun] БЫЛО БЫ ИЗМЕНЕНО: $Path\$Name : '$wasText' -> '$Value'  ($Comment)" 'DRY'
            return
        }

        # Логируем ИСХОДНОЕ значение для возможного отката.
        Write-Log "  [реестр] $Path\$Name : было '$wasText' -> ставим '$Value'  # откат: вернуть '$wasText'  ($Comment)" 'INFO'
        if (-not (Test-Path $Path)) { New-Item -Path $Path -Force | Out-Null }
        New-ItemProperty -Path $Path -Name $Name -Value $Value -PropertyType $Type -Force | Out-Null
    }
    catch {
        Write-Log "  [ОШИБКА реестра] $Path\$Name : $($_.Exception.Message)" 'WARN'
    }
}

# Идемпотентная смена типа запуска службы с защитой "чёрного списка".
# В режиме -DryRun реально ничего не меняет.
function Set-ServiceStartup {
    param(
        [Parameter(Mandatory)][string]$Name,
        [ValidateSet('Automatic','Manual','Disabled')]$StartupType = 'Manual',
        [switch]$StopNow,
        [string]$Reason = ''
    )
    # Защита: служба из чёрного списка пропускается всегда (-contains регистронезависим).
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
        }
        elseif ($DryRun) {
            Write-Log "  [DryRun] БЫЛО БЫ ИЗМЕНЕНО: служба '$Name' : '$current' -> '$StartupType'  ($Reason)" 'DRY'
        }
        else {
            Write-Log "  [служба] '$Name' : было '$current' -> '$StartupType'  # откат: вернуть '$current'  ($Reason)" 'INFO'
            Set-Service -Name $Name -StartupType $StartupType -ErrorAction Stop
        }

        if ($StopNow -and $svc.Status -eq 'Running') {
            if ($DryRun) {
                Write-Log "  [DryRun] БЫЛО БЫ ОСТАНОВЛЕНО: служба '$Name'." 'DRY'
            } else {
                Write-Log "  [служба] Останавливаю '$Name'." 'INFO'
                Stop-Service -Name $Name -Force -ErrorAction SilentlyContinue
            }
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
# Сохраняем исходную схему в лог для возможного отката.
try {
    $highPerf = '8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c'  # GUID схемы High performance
    # Текущая активная схема (для отката).
    $activeLine = (powercfg /getactivescheme) -join ' '
    $origGuid = if ($activeLine -match '([0-9a-fA-F-]{36})') { $Matches[1] } else { '<неизвестно>' }

    $exists = (powercfg /list) -match $highPerf
    if (-not $exists) {
        Write-Log "  Схема 'Высокая производительность' отсутствует — пропуск." 'INFO'
    }
    elseif ($origGuid -eq $highPerf) {
        Write-Log "  [пропуск] План питания уже 'Высокая производительность'." 'INFO'
    }
    elseif ($DryRun) {
        Write-Log "  [DryRun] БЫЛО БЫ ИЗМЕНЕНО: план питания '$origGuid' -> '$highPerf' (High performance)." 'DRY'
    }
    else {
        Write-Log "  [питание] активная схема: было '$origGuid' -> ставим '$highPerf'  # откат: powercfg /setactive $origGuid" 'INFO'
        powercfg /setactive $highPerf | Out-Null
        Write-Log "  План питания переключён на 'Высокая производительность'." 'OK'
    }
}
catch { Write-Log "  Не удалось сменить план питания: $($_.Exception.Message)" 'WARN' }

# 5.2 Визуальные эффекты -> "Наилучшее быстродействие".
# VisualFXSetting: 0=авто, 1=лучший вид, 2=лучшее быстродействие, 3=пользоват.
# ПРИМЕЧАНИЕ: для фактического применения требуется перезапуск explorer.exe
# (выполняется в секции 9). Иначе изменение видно только в окне "Параметры
# быстродействия" и применится после перелогина.
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
        Write-Log "  SysMain не трогаем: есть HDD/неопределённый диск, где он может помогать кэшированию." 'INFO'
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

# ВАЖНО: логика для HDD и SSD ПРОТИВОПОЛОЖНА и взаимоисключающа
# ($AllSSD истинно только когда HDD отсутствует).

# TRIM полезен при наличии ЛЮБОГО SSD (в т.ч. в смешанной конфигурации).
if ($HasSSD) {
    Write-Log "--- Обнаружен SSD: проверяем TRIM (дефраг SSD не выполняем) ---" 'INFO'
    try {
        $trim = (fsutil behavior query DisableDeleteNotify) -join ' '
        # DisableDeleteNotify = 0 -> TRIM ВКЛЮЧЁН.
        if ($trim -match 'DisableDeleteNotify\s*=\s*1') {
            if ($DryRun) {
                Write-Log "  [DryRun] БЫЛО БЫ ИЗМЕНЕНО: TRIM включён (DisableDeleteNotify 1 -> 0)." 'DRY'
            } else {
                fsutil behavior set DisableDeleteNotify 0 | Out-Null
                Write-Log "  TRIM был отключён — включили (DisableDeleteNotify=0)." 'OK'
            }
        } else {
            Write-Log "  TRIM уже включён — ок." 'INFO'
        }
    }
    catch { Write-Log "  Не удалось проверить/включить TRIM: $($_.Exception.Message)" 'WARN' }
}

if ($HasHDD) {
    # На HDD (в т.ч. смешанная конфигурация) включаем штатную задачу оптимизации.
    # Windows сама применяет дефраг к HDD-томам и retrim к SSD-томам — SSD не страдает.
    Write-Log "--- Обнаружен HDD: включаем штатную оптимизацию дисков по расписанию ---" 'INFO'
    try {
        $task = Get-ScheduledTask -TaskName 'ScheduledDefrag' `
                  -TaskPath '\Microsoft\Windows\Defrag\' -ErrorAction Stop
        if ($task.State -ne 'Disabled') {
            Write-Log "  [пропуск] Задача 'ScheduledDefrag' уже активна." 'INFO'
        }
        elseif ($DryRun) {
            Write-Log "  [DryRun] БЫЛО БЫ ИЗМЕНЕНО: включение задачи 'ScheduledDefrag'." 'DRY'
        }
        else {
            Enable-ScheduledTask -InputObject $task | Out-Null
            Write-Log "  Включена штатная задача 'ScheduledDefrag' (еженедельно)." 'OK'
        }
    }
    catch {
        Write-Log "  Не удалось настроить штатную задачу дефрага: $($_.Exception.Message)" 'WARN'
    }
}

if (-not $HasHDD -and -not $HasSSD) {
    Write-Log "--- Тип дисков не определён: дисковые твики пропущены (безопасно) ---" 'WARN'
}

#endregion

#region ============ 8. АДАПТИВНЫЕ ТВИКИ ПО GPU ============

if ($WeakGpu) {
    Write-Log "--- Слабый/интегрированный GPU: отключаем прозрачность и анимации ---" 'INFO'

    # Прозрачность интерфейса (Aero/Acrylic) — нагрузка на GPU.
    Set-RegistryValue -Path 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Themes\Personalize' `
        -Name 'EnableTransparency' -Value 0 -Type DWord -Comment 'Отключить прозрачность интерфейса'

    # (VisualFXSetting=2 уже выставлен в базовой секции 5 — не дублируем.)

    # Анимация при сворачивании/разворачивании окон.
    Set-RegistryValue -Path 'HKCU:\Control Panel\Desktop\WindowMetrics' `
        -Name 'MinAnimate' -Value '0' -Type String -Comment 'Отключить анимацию окон (GPU)'
}
else {
    Write-Log "--- GPU достаточно производителен (есть дискретная карта): эффекты не режем ---" 'INFO'
}

#endregion

#region ============ 9. ПРИМЕНЕНИЕ ВИЗУАЛЬНЫХ НАСТРОЕК И ЗАВЕРШЕНИЕ ============

# Перезапуск explorer.exe нужен, чтобы изменения VisualFX/прозрачности/анимаций
# вступили в силу немедленно (иначе — только после перелогина).
# Делаем это ТОЛЬКО в интерактивной сессии: в фоне (планировщик, SSH) убивать
# оболочку бессмысленно — настройки применятся при следующем входе пользователя.
if (-not [Environment]::UserInteractive) {
    Write-Log "Неинтерактивная сессия — explorer.exe не перезапускаем (применится при входе)." 'INFO'
}
elseif ($DryRun) {
    Write-Log "[DryRun] БЫЛО БЫ ВЫПОЛНЕНО: перезапуск explorer.exe для применения визуальных настроек." 'DRY'
}
else {
    try {
        Write-Log "Перезапуск explorer.exe для применения визуальных настроек..." 'INFO'
        Get-Process -Name explorer -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 1
        # Windows обычно сам поднимает explorer; на всякий случай запускаем явно.
        if (-not (Get-Process -Name explorer -ErrorAction SilentlyContinue)) {
            Start-Process explorer.exe
        }
        Write-Log "explorer.exe перезапущен." 'OK'
    }
    catch { Write-Log "Не удалось перезапустить explorer.exe: $($_.Exception.Message)" 'WARN' }
}

if ($DryRun) {
    Write-Log "=== Пробный прогон (-DryRun) завершён. Изменений не вносилось. ===" 'DRY'
} else {
    Write-Log "=== Оптимизация завершена ===" 'OK'
}
Write-Host ""
Write-Host "Готово. Подробный лог: $LogFile" -ForegroundColor Green
if ($DryRun) {
    Write-Host "Это был ПРОБНЫЙ прогон (-DryRun). Запустите без -DryRun для применения." -ForegroundColor Magenta
} else {
    Write-Host "Рекомендуется перезагрузить компьютер для применения всех изменений." -ForegroundColor Cyan
    Write-Host "Откат: используйте созданную точку восстановления или значения 'было' из лога." -ForegroundColor Cyan
}

#endregion
