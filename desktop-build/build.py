"""
Автоматическая сборка .exe из Python-скрипта через PyInstaller.

ЗАПУСК (на Windows, где установлен Python 3.8+):
    python build.py                  -> соберёт app.py -> dist/App.exe
    python build.py my_script.py     -> соберёт указанный файл
    python build.py my_script.py MyAppName   -> с указанным именем .exe

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


def ensure_pyinstaller() -> None:
    """Устанавливает PyInstaller, если он ещё не установлен."""
    try:
        import PyInstaller  # noqa: F401
        print("PyInstaller уже установлен.")
    except ImportError:
        print("Устанавливаю PyInstaller...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "pyinstaller"])


def build_exe(script_path: str, app_name: str, console: bool) -> Path:
    """Собирает .exe из указанного скрипта и возвращает путь к готовому файлу."""
    script = Path(script_path).resolve()
    if not script.exists():
        raise FileNotFoundError(f"Файл не найден: {script}")

    args = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--name", app_name,
        "--distpath", "dist",
        "--workpath", "build",
        "--specpath", ".",
    ]
    if not console:
        args.append("--windowed")  # без чёрного консольного окна

    args.append(str(script))

    print("Запускаю сборку:", " ".join(args))
    subprocess.check_call(args)

    exe_path = Path("dist") / f"{app_name}.exe"
    return exe_path


def cleanup(app_name: str) -> None:
    """Удаляет временные файлы сборки, оставляя только готовый .exe в dist/."""
    for path in [Path("build"), Path(f"{app_name}.spec")]:
        if path.is_dir():
            shutil.rmtree(path, ignore_errors=True)
        elif path.is_file():
            path.unlink(missing_ok=True)


def main() -> None:
    script_path = sys.argv[1] if len(sys.argv) > 1 else "app.py"
    app_name = sys.argv[2] if len(sys.argv) > 2 else "App"
    # Если нужен видимый терминал (например, для консольных утилит) —
    # запустите: python build.py app.py App console
    console = len(sys.argv) > 3 and sys.argv[3].lower() == "console"

    ensure_pyinstaller()
    exe_path = build_exe(script_path, app_name, console)
    cleanup(app_name)

    if exe_path.exists():
        print(f"\nГотово! Файл создан: {exe_path.resolve()}")
    else:
        print("\nСборка завершилась, но .exe не найден — проверьте вывод выше на ошибки.")


if __name__ == "__main__":
    main()
