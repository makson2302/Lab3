"""Программа для учёта измерений температуры с графическим интерфейсом и логированием ошибок."""

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date
from typing import List, Optional
import logging
import sys

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("errors.log", encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class TemperatureMeasurement:
    """Представляет одно измерение температуры."""

    def __init__(self, date_obj: date, location: str, value: float) -> None:
        """Инициализирует измерение.

        Args:
            date_obj: Дата измерения.
            location: Место измерения.
            value: Значение температуры.
        """
        self.date = date_obj
        self.location = location
        self.value = value

    @staticmethod
    def from_string(line: str) -> 'TemperatureMeasurement':
        """Создаёт измерение из форматированной строки.

        Ожидаемый формат:
            TemperatureMeasurement ГГГГ.ММ.ДД "место" значение

        Args:
            line: Входная строка.

        Returns:
            Объект TemperatureMeasurement.

        Raises:
            ValueError: Если формат строки неверен.
        """
        # Разбор строки на токены с учётом кавычек
        tokens = []
        current = []
        in_quotes = False

        for ch in line:
            if ch == '"':
                in_quotes = not in_quotes
                current.append(ch)
            elif ch.isspace() and not in_quotes:
                if current:
                    tokens.append(''.join(current))
                    current = []
            else:
                current.append(ch)
        if current:
            tokens.append(''.join(current))

        if len(tokens) != 4:
            raise ValueError(f"Неверное количество токенов: ожидалось 4, получено {len(tokens)}")

        if tokens[0] != "TemperatureMeasurement":
            raise ValueError(f"Неизвестный тип объекта: {tokens[0]}")

        try:
            date_str = tokens[1]
            year, month, day = map(int, date_str.split('.'))
            date_obj = date(year, month, day)
        except ValueError as e:
            raise ValueError(f"Неверный формат даты: {tokens[1]}") from e

        location = tokens[2].strip('"')
        if not location:
            raise ValueError("Место измерения не может быть пустым")

        try:
            value = float(tokens[3])
        except ValueError as e:
            raise ValueError(f"Неверное числовое значение: {tokens[3]}") from e

        return TemperatureMeasurement(date_obj, location, value)

    def to_string(self) -> str:
        """Преобразует измерение в строку для сохранения в файл.

        Returns:
            Строка формата: TemperatureMeasurement ГГГГ.ММ.ДД "место" значение
        """
        date_str = self.date.strftime("%Y.%m.%d")
        return f'TemperatureMeasurement {date_str} "{self.location}" {self.value}'


class FileStorage:
    """Обеспечивает чтение/запись измерений в файл с логированием ошибок."""

    def __init__(self, filename: str) -> None:
        """Инициализирует хранилище с именем файла.

        Args:
            filename: Путь к файлу данных.
        """
        self.filename = filename

    def load(self) -> List[TemperatureMeasurement]:
        """Читает из файла все корректные измерения.

        Некорректные строки пропускаются и логируются.

        Returns:
            Список объектов TemperatureMeasurement.
        """
        measurements = []
        try:
            with open(self.filename, 'r', encoding='utf-8') as file:
                for line_num, line in enumerate(file, start=1):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        measurement = TemperatureMeasurement.from_string(line)
                        measurements.append(measurement)
                    except ValueError as e:
                        logger.error(f"Строка {line_num}: {line} -> {e}")
        except FileNotFoundError:
            logger.warning(f"Файл {self.filename} не найден, начинаем с пустого списка.")
        except IOError as e:
            logger.error(f"Не удалось прочитать файл {self.filename}: {e}")
        return measurements

    def save(self, measurements: List[TemperatureMeasurement]) -> None:
        """Сохраняет измерения в файл.

        Args:
            measurements: Список измерений для сохранения.
        """
        try:
            with open(self.filename, 'w', encoding='utf-8') as file:
                for m in measurements:
                    file.write(m.to_string() + '\n')
        except IOError as e:
            logger.error(f"Не удалось записать в файл {self.filename}: {e}")
            raise


class Application:
    """Главный класс графического интерфейса (Представление)."""

    def __init__(self, storage: FileStorage) -> None:
        """Инициализирует окно и виджеты.

        Args:
            storage: Экземпляр FileStorage.
        """
        self.storage = storage
        self.measurements = storage.load()

        self.root = tk.Tk()
        self.root.title("Измерения температуры")
        self.root.geometry("700x400")

        # Создание таблицы (Treeview)
        self.tree = ttk.Treeview(
            self.root,
            columns=("date", "location", "value"),
            show="headings"
        )
        self.tree.heading("date", text="Дата")
        self.tree.heading("location", text="Место")
        self.tree.heading("value", text="Значение (°C)")
        self.tree.column("date", width=100)
        self.tree.column("location", width=300)
        self.tree.column("value", width=100)
        self.tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Панель ввода
        input_frame = ttk.Frame(self.root)
        input_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(input_frame, text="Дата (ГГГГ.ММ.ДД):").grid(row=0, column=0, padx=5, pady=2)
        self.date_entry = ttk.Entry(input_frame, width=12)
        self.date_entry.grid(row=0, column=1, padx=5, pady=2)

        ttk.Label(input_frame, text="Место:").grid(row=0, column=2, padx=5, pady=2)
        self.location_entry = ttk.Entry(input_frame, width=25)
        self.location_entry.grid(row=0, column=3, padx=5, pady=2)

        ttk.Label(input_frame, text="Значение:").grid(row=0, column=4, padx=5, pady=2)
        self.value_entry = ttk.Entry(input_frame, width=8)
        self.value_entry.grid(row=0, column=5, padx=5, pady=2)

        # Панель кнопок
        btn_frame = ttk.Frame(self.root)
        btn_frame.pack(fill=tk.X, padx=10, pady=5)

        add_btn = ttk.Button(btn_frame, text="Добавить", command=self.add_measurement)
        add_btn.pack(side=tk.LEFT, padx=5)

        delete_btn = ttk.Button(btn_frame, text="Удалить выделенное", command=self.delete_measurement)
        delete_btn.pack(side=tk.LEFT, padx=5)

        self.refresh_table()

    def refresh_table(self) -> None:
        """Обновляет таблицу текущими измерениями."""
        for row in self.tree.get_children():
            self.tree.delete(row)

        for m in self.measurements:
            self.tree.insert(
                "",
                tk.END,
                values=(
                    m.date.strftime("%Y.%m.%d"),
                    m.location,
                    f"{m.value:.2f}"
                )
            )

    def add_measurement(self) -> None:
        """Добавляет новое измерение из полей ввода."""
        date_str = self.date_entry.get().strip()
        location = self.location_entry.get().strip()
        value_str = self.value_entry.get().strip()

        if not date_str or not location or not value_str:
            messagebox.showerror("Ошибка", "Все поля должны быть заполнены")
            return

        try:
            year, month, day = map(int, date_str.split('.'))
            date_obj = date(year, month, day)
            value = float(value_str)

            new_meas = TemperatureMeasurement(date_obj, location, value)
            self.measurements.append(new_meas)
            self.storage.save(self.measurements)
            self.refresh_table()
            self.clear_entries()
        except Exception as e:
            messagebox.showerror("Ошибка ввода", f"Неверные данные: {e}")

    def delete_measurement(self) -> None:
        """Удаляет выделенное измерение из списка."""
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Предупреждение", "Ничего не выбрано")
            return

        index = self.tree.index(selected[0])
        if 0 <= index < len(self.measurements):
            del self.measurements[index]
            self.storage.save(self.measurements)
            self.refresh_table()

    def clear_entries(self) -> None:
        """Очищает поля ввода."""
        self.date_entry.delete(0, tk.END)
        self.location_entry.delete(0, tk.END)
        self.value_entry.delete(0, tk.END)

    def run(self) -> None:
        """Запускает главный цикл GUI."""
        self.root.mainloop()


def main() -> None:
    """Точка входа в программу."""
    storage = FileStorage("data.txt")
    app = Application(storage)
    app.run()


if __name__ == "__main__":
    main()