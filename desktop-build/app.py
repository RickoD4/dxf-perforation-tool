"""
Пример стартового приложения — простое окно на tkinter (входит в стандартную
библиотеку Python, ничего дополнительно ставить не нужно).

Замените содержимое этого файла на свою программу, либо передайте
собственный .py файл первым аргументом в build.py:
    python build.py my_script.py MyApp
"""

import tkinter as tk


def main() -> None:
    root = tk.Tk()
    root.title("My App")
    root.geometry("400x250")

    label = tk.Label(root, text="Привет! Это работающее приложение.", font=("Arial", 12))
    label.pack(pady=40)

    button = tk.Button(root, text="Закрыть", command=root.destroy)
    button.pack()

    root.mainloop()


if __name__ == "__main__":
    main()
