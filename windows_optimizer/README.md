# Windows Optimizer Pro

Десктопное приложение для оптимизации Windows 10/11 на **Python + PyQt6**.
Эта папка самодостаточна — её можно вынести в отдельный репозиторий без изменений.

> Статус: **фундамент + ядро** (этап 1). Реализованы: каркас проекта, утилиты
> (права администратора, реестр, логгер), система бэкапов, сбор системной
> информации, базовые классы оптимизатора, главное окно с навигацией, дашборд
> с метриками в реальном времени и два модуля — **Автозагрузка** и **Реестр**
> (на базе `data/tweaks_database.json`). Остальные 10 модулей — следующими этапами.

## Запуск из исходников
```bash
cd windows_optimizer
python -m venv .venv && . .venv/Scripts/activate   # Windows
pip install -r requirements.txt
python main.py
```

## Сборка .exe
```bash
python build.py        # -> dist/WindowsOptimizerPro.exe (PyInstaller, --uac-admin)
```
Либо скачать готовый `.exe` из Releases (собирается автоматически в CI на `windows-latest`).

## Архитектура
```
main.py                 точка входа (проверка прав, запуск GUI)
app/
  core/                 logger, backup, system_info, optimizer (базовые классы)
  modules/              startup, registry (+ далее: services, disk, network, …)
  ui/                   main_window, dashboard, styles/dark_theme.qss
  utils/                admin, registry_helper
data/tweaks_database.json   декларативная база твиков реестра
resources/icons/        иконка приложения (спидометр)
build.py                сборка PyInstaller
```

## Принципы
- **Безопасность прежде всего**: перед изменениями — бэкап (реестр/точка восстановления).
- **Прозрачность**: каждый твик показывает конкретные изменения реестра и риск.
- **Откат**: каждый твик умеет `apply()` / `revert()` / `status()`.
- **Кроссплатформенный импорт**: Windows-специфика защищена, на Linux модули импортируются (для CI/разработки), но системные операции доступны только на Windows.
