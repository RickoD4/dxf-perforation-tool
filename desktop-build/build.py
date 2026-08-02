"""
Автоматическая сборка .exe из Python-скрипта через PyInstaller.

ЗАПУСК (на Windows, где установлен Python 3.8+):
    python build.py                  -> соберёт app.py -> dist/App.exe
    python build.py my_script.py     -> соберёт указанный файл
    python build.py my_script.py MyAppName   -> с указанным именем .exe

Проще всего: дважды кликните на СОБРАТЬ.bat — он сам найдёт Python и запустит сборку.

Что делает скрипт:
    1. Проверяет, установлен ли PyInstaller — если нет, ставит через pip.
    2. Запускает сборку в режиме "один файл" (--onefile), без консольного окна.
    3. Кладёт временные файлы в build/, готовый .exe — в dist/.
    4. Убирает после себя временные файлы (build/, .spec), оставляя только dist/.

Требования: Windows + Python, доступ в интернет для установки зависимостей.
"""

import subprocess
import sys
import shutil
from pathlib import Path

# На старых консолях Windows (cp866/cp1251) вывод кириллицы через print()
# может падать с UnicodeEncodeError. Переключаем stdout/stderr на UTF-8,
# если интерпретатор это поддерживает (Python 3.7+).
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        try:
            _stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

# Все пути (app.py, requirements.txt, dist/, build/) считаем ОТНОСИТЕЛЬНО
# папки, где лежит сам build.py — а не текущей рабочей директории терминала.
# Иначе запуск не из этой папки (например "python desktop-build\build.py"
# из корня проекта) не найдёт нужные файлы и сборка завершится с ошибкой.
BASE_DIR = Path(__file__).resolve().parent


def _pip_install(args: list) -> None:
    """Устанавливает пакет через pip; при ошибке доступа (PermissionError /
    "Access is denied" / "Errno 13") повторяет попытку с флагом --user,
    который не требует прав администратора."""
    full_args = [sys.executable, "-m", "pip", "install", "--upgrade", "--no-input", *args]
    try:
        subprocess.check_call(full_args)
    except subprocess.CalledProcessError:
        print("Не удалось установить пакет с правами по умолчанию.")
        print("Повторяю попытку установки в профиль пользователя (--user)...")
        subprocess.check_call(full_args + ["--user"])


def ensure_pip() -> None:
    """Проверяет, что pip доступен, и при необходимости устанавливает его."""
    try:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "--version"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
    except subprocess.CalledProcessError:
        print("pip не найден, устанавливаю через ensurepip...")
        subprocess.check_call([sys.executable, "-m", "ensurepip", "--upgrade"])


def ensure_pyinstaller() -> None:
    """Устанавливает PyInstaller, если он ещё не установлен."""
    try:
        import PyInstaller  # noqa: F401
        print("PyInstaller уже установлен.")
    except ImportError:
        print("Устанавливаю PyInstaller (это может занять 1-2 минуты)...")
        _pip_install(["pyinstaller"])


def ensure_requirements() -> None:
    """Устанавливает зависимости проекта из requirements.txt, если файл есть."""
    req = BASE_DIR / "requirements.txt"
    if not req.exists():
        return
    print("Устанавливаю зависимости из requirements.txt...")
    _pip_install(["-r", str(req)])


def build_exe(script_path: str, app_name: str, console: bool) -> Path:
    """Собирает .exe из указанного скрипта и возвращает путь к готовому файлу."""
    script = Path(script_path)
    if not script.is_absolute():
        script = BASE_DIR / script
    script = script.resolve()
    if not script.exists():
        raise FileNotFoundError(
            f"Файл не найден: {script}\n"
            f"Убедитесь, что .py файл лежит рядом с build.py, "
            f"либо укажите правильный путь: python build.py путь\\к\\файлу.py"
        )

    dist_dir = BASE_DIR / "dist"
    work_dir = BASE_DIR / "build"

    args = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--noconfirm",
        "--name", app_name,
        "--distpath", str(dist_dir),
        "--workpath", str(work_dir),
        "--specpath", str(BASE_DIR),
    ]
    if not console:
        args.append("--windowed")  # без чёрного консольного окна

    args.append(str(script))

    print("Запускаю сборку:", " ".join(args))
    subprocess.check_call(args)

    # На Windows PyInstaller сам добавляет расширение .exe к имени.
    exe_path = dist_dir / f"{app_name}.exe"
    if not exe_path.exists():
        # На случай иной платформы/конфигурации — файл без расширения.
        alt = dist_dir / app_name
        if alt.exists():
            exe_path = alt
    return exe_path


def cleanup(app_name: str) -> None:
    """Удаляет временные файлы сборки, оставляя только готовый .exe в dist/."""
    for path in [BASE_DIR / "build", BASE_DIR / f"{app_name}.spec"]:
        if path.is_dir():
            shutil.rmtree(path, ignore_errors=True)
        elif path.is_file():
            path.unlink(missing_ok=True)


def run() -> int:
    script_path = sys.argv[1] if len(sys.argv) > 1 else "app.py"
    app_name = sys.argv[2] if len(sys.argv) > 2 else "App"
    # Если нужен видимый терминал (например, для консольных утилит) —
    # запустите: python build.py app.py App console
    console = len(sys.argv) > 3 and sys.argv[3].lower() == "console"

    ensure_pip()
    ensure_pyinstaller()
    ensure_requirements()
    exe_path = build_exe(script_path, app_name, console)
    cleanup(app_name)

    if exe_path.exists():
        print(f"\nГотово! Файл создан: {exe_path.resolve()}")
        return 0
    else:
        print("\nСборка завершилась, но .exe не найден — проверьте вывод выше на ошибки.")
        return 1


def main() -> None:
    try:
        code = run()
    except subprocess.CalledProcessError as e:
        print(f"\nОШИБКА: команда завершилась с кодом {e.returncode}.")
        print("Проверьте сообщения выше — обычно там указана точная причина.")
        code = 1
    except FileNotFoundError as e:
        print(f"\nОШИБКА: {e}")
        code = 1
    except Exception as e:  # неожиданная ошибка — не даём окну закрыться молча
        print(f"\nНЕОЖИДАННАЯ ОШИБКА: {e}")
        code = 1

    # Если скрипт запущен двойным кликом (не из консоли), окно закроется
    # мгновенно и результат будет не виден — держим его открытым.
    if sys.stdin.isatty():
        try:
            input("\nНажмите Enter, чтобы закрыть окно...")
        except EOFError:
            pass

    sys.exit(code)


if __name__ == "__main__":
    main()