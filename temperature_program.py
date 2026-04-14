"""Программа для учёта измерений температуры с координатами и обязательным знаком."""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from datetime import date
from typing import List
import logging
import sys

# Настройка логирования (сообщения на английском)
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
    """Измерение температуры с координатами места."""

    def __init__(self, date_obj: date, location: str, value: float,
                 latitude: float, longitude: float) -> None:
        self.date = date_obj
        self.location = location
        self.value = value
        self.latitude = latitude
        self.longitude = longitude

    @staticmethod
    def from_string(line: str) -> 'TemperatureMeasurement':
        """
        Создаёт измерение из строки формата:
        TemperatureMeasurement ГГГГ.ММ.ДД "место" значение широта долгота
        """
        # Токенизация с учётом кавычек
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

        if len(tokens) != 6:
            raise ValueError(f"Invalid token count: expected 6, got {len(tokens)}")

        if tokens[0] != "TemperatureMeasurement":
            raise ValueError(f"Unknown type: {tokens[0]}")

        # Дата
        try:
            year, month, day = map(int, tokens[1].split('.'))
            date_obj = date(year, month, day)
        except ValueError as e:
            raise ValueError(f"Invalid date format: {tokens[1]}") from e

        # Место
        location = tokens[2].strip('"')
        if not location:
            raise ValueError("Location cannot be empty")

        # Значение температуры
        try:
            value = float(tokens[3])
        except ValueError as e:
            raise ValueError(f"Invalid numeric value: {tokens[3]}") from e

        # Широта (может быть без знака для совместимости с файлами)
        try:
            latitude = float(tokens[4])
        except ValueError as e:
            raise ValueError(f"Invalid latitude: {tokens[4]}") from e

        # Долгота
        try:
            longitude = float(tokens[5])
        except ValueError as e:
            raise ValueError(f"Invalid longitude: {tokens[5]}") from e

        return TemperatureMeasurement(date_obj, location, value, latitude, longitude)

    def to_string(self) -> str:
        """Преобразует измерение в строку для файла (числа без знака)."""
        date_str = self.date.strftime("%Y.%m.%d")
        return (f'TemperatureMeasurement {date_str} "{self.location}" '
                f'{self.value} {self.latitude} {self.longitude}')


class FileStorage:
    """Чтение/запись измерений в файл с логированием ошибок."""

    def __init__(self, filename: str) -> None:
        self.filename = filename

    def load(self) -> List[TemperatureMeasurement]:
        measurements = []
        try:
            with open(self.filename, 'r', encoding='utf-8') as file:
                for line_num, line in enumerate(file, start=1):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        measurements.append(TemperatureMeasurement.from_string(line))
                    except ValueError as e:
                        logger.error(f"Line {line_num}: {line} -> {e}")
        except FileNotFoundError:
            logger.warning(f"File {self.filename} not found, starting empty.")
        except IOError as e:
            logger.error(f"Failed to read file {self.filename}: {e}")
        return measurements

    def save(self, measurements: List[TemperatureMeasurement]) -> None:
        try:
            with open(self.filename, 'w', encoding='utf-8') as file:
                for m in measurements:
                    file.write(m.to_string() + '\n')
        except IOError as e:
            logger.error(f"Failed to write to file {self.filename}: {e}")
            raise


class EditDialog(simpledialog.Dialog):
    """Диалог редактирования измерения с проверкой знака координат."""

    def __init__(self, parent, title, measurement):
        self.measurement = measurement
        super().__init__(parent, title=title)

    def body(self, master):
        tk.Label(master, text="Дата (ГГГГ.ММ.ДД):").grid(row=0, column=0, padx=5, pady=5, sticky="e")
        self.date_entry = tk.Entry(master, width=15)
        self.date_entry.grid(row=0, column=1, padx=5, pady=5)
        self.date_entry.insert(0, self.measurement.date.strftime("%Y.%m.%d"))

        tk.Label(master, text="Место:").grid(row=1, column=0, padx=5, pady=5, sticky="e")
        self.location_entry = tk.Entry(master, width=30)
        self.location_entry.grid(row=1, column=1, padx=5, pady=5)
        self.location_entry.insert(0, self.measurement.location)

        tk.Label(master, text="Значение:").grid(row=2, column=0, padx=5, pady=5, sticky="e")
        self.value_entry = tk.Entry(master, width=10)
        self.value_entry.grid(row=2, column=1, padx=5, pady=5)
        self.value_entry.insert(0, str(self.measurement.value))

        tk.Label(master, text="Широта (+/-число):").grid(row=3, column=0, padx=5, pady=5, sticky="e")
        self.lat_entry = tk.Entry(master, width=15)
        self.lat_entry.grid(row=3, column=1, padx=5, pady=5)
        lat_val = self.measurement.latitude
        self.lat_entry.insert(0, f"+{lat_val}" if lat_val >= 0 else str(lat_val))

        tk.Label(master, text="Долгота (+/-число):").grid(row=4, column=0, padx=5, pady=5, sticky="e")
        self.lon_entry = tk.Entry(master, width=15)
        self.lon_entry.grid(row=4, column=1, padx=5, pady=5)
        lon_val = self.measurement.longitude
        self.lon_entry.insert(0, f"+{lon_val}" if lon_val >= 0 else str(lon_val))

        return self.date_entry

    def validate_coordinate(self, value_str: str, name: str) -> float:
        """Проверяет, что строка начинается с + или - и затем число."""
        if not value_str:
            raise ValueError(f"{name} не может быть пустым")
        if value_str[0] not in ('+', '-'):
            raise ValueError(f"{name} должна начинаться с '+' или '-'")
        try:
            return float(value_str)
        except ValueError:
            raise ValueError(f"{name} имеет неверный числовой формат")

    def apply(self):
        try:
            date_str = self.date_entry.get().strip()
            year, month, day = map(int, date_str.split('.'))
            new_date = date(year, month, day)
            new_location = self.location_entry.get().strip()
            new_value = float(self.value_entry.get().strip())
            new_lat = self.validate_coordinate(self.lat_entry.get().strip(), "Широта")
            new_lon = self.validate_coordinate(self.lon_entry.get().strip(), "Долгота")

            if not new_location:
                raise ValueError("Место не может быть пустым")

            self.measurement.date = new_date
            self.measurement.location = new_location
            self.measurement.value = new_value
            self.measurement.latitude = new_lat
            self.measurement.longitude = new_lon
            self.result = True
        except Exception as e:
            messagebox.showerror("Ошибка", f"Некорректные данные: {e}")
            self.result = False


class Application:
    """Главное окно программы."""

    def __init__(self, storage: FileStorage) -> None:
        self.storage = storage
        self.measurements = storage.load()

        self.root = tk.Tk()
        self.root.title("Измерения температуры с координатами")
        self.root.geometry("950x500")

        # Таблица с 5 столбцами
        self.tree = ttk.Treeview(
            self.root,
            columns=("date", "location", "value", "latitude", "longitude"),
            show="headings"
        )
        self.tree.heading("date", text="Дата")
        self.tree.heading("location", text="Место")
        self.tree.heading("value", text="Значение (°C)")
        self.tree.heading("latitude", text="Широта")
        self.tree.heading("longitude", text="Долгота")
        self.tree.column("date", width=100)
        self.tree.column("location", width=250)
        self.tree.column("value", width=100)
        self.tree.column("latitude", width=150)
        self.tree.column("longitude", width=150)
        self.tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Панель ввода
        input_frame = ttk.Frame(self.root)
        input_frame.pack(fill=tk.X, padx=10, pady=5)

        # Первая строка: Дата, Место, Значение
        ttk.Label(input_frame, text="Дата (ГГГГ.ММ.ДД):").grid(row=0, column=0, padx=5, pady=2)
        self.date_entry = ttk.Entry(input_frame, width=12)
        self.date_entry.grid(row=0, column=1, padx=5, pady=2)

        ttk.Label(input_frame, text="Место:").grid(row=0, column=2, padx=5, pady=2)
        self.location_entry = ttk.Entry(input_frame, width=25)
        self.location_entry.grid(row=0, column=3, padx=5, pady=2)

        ttk.Label(input_frame, text="Значение:").grid(row=0, column=4, padx=5, pady=2)
        self.value_entry = ttk.Entry(input_frame, width=8)
        self.value_entry.grid(row=0, column=5, padx=5, pady=2)

        # Вторая строка: Широта, Долгота с подсказкой о знаке
        ttk.Label(input_frame, text="Широта:").grid(row=1, column=0, padx=5, pady=2)
        self.latitude_entry = ttk.Entry(input_frame, width=15)
        self.latitude_entry.grid(row=1, column=1, padx=5, pady=2)

        ttk.Label(input_frame, text="Долгота:").grid(row=1, column=2, padx=5, pady=2)
        self.longitude_entry = ttk.Entry(input_frame, width=15)
        self.longitude_entry.grid(row=1, column=3, padx=5, pady=2)

        # Кнопки
        btn_frame = ttk.Frame(self.root)
        btn_frame.pack(fill=tk.X, padx=10, pady=5)

        add_btn = ttk.Button(btn_frame, text="Добавить", command=self.add_measurement)
        add_btn.pack(side=tk.LEFT, padx=5)

        edit_btn = ttk.Button(btn_frame, text="Изменить", command=self.edit_measurement)
        edit_btn.pack(side=tk.LEFT, padx=5)

        delete_btn = ttk.Button(btn_frame, text="Удалить выделенное", command=self.delete_measurement)
        delete_btn.pack(side=tk.LEFT, padx=5)

        self.refresh_table()

    def format_coordinate(self, value: float, is_latitude: bool) -> str:
        sign = '+' if value >= 0 else ''
        number_str = f"{sign}{value:.6f}"
        if is_latitude:
            direction = "с.ш." if value >= 0 else "ю.ш."
        else:
            direction = "в.д." if value >= 0 else "з.д."
        return f"{number_str} {direction}"

    def refresh_table(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        for m in self.measurements:
            self.tree.insert("", tk.END, values=(
                m.date.strftime("%Y.%m.%d"),
                m.location,
                f"{m.value:.2f}",
                self.format_coordinate(m.latitude, is_latitude=True),
                self.format_coordinate(m.longitude, is_latitude=False)
            ))

    def validate_coordinate_input(self, value_str: str, name: str) -> float:
        if not value_str:
            raise ValueError(f"{name} не может быть пустым")
        if value_str[0] not in ('+', '-'):
            raise ValueError(f"{name} должна начинаться с '+' или '-'")
        try:
            return float(value_str)
        except ValueError:
            raise ValueError(f"{name} имеет неверный числовой формат")

    def add_measurement(self):
        date_str = self.date_entry.get().strip()
        location = self.location_entry.get().strip()
        value_str = self.value_entry.get().strip()
        lat_str = self.latitude_entry.get().strip()
        lon_str = self.longitude_entry.get().strip()

        if not all([date_str, location, value_str, lat_str, lon_str]):
            messagebox.showerror("Ошибка", "Все поля должны быть заполнены")
            return

        try:
            year, month, day = map(int, date_str.split('.'))
            date_obj = date(year, month, day)
            value = float(value_str)
            latitude = self.validate_coordinate_input(lat_str, "Широта")
            longitude = self.validate_coordinate_input(lon_str, "Долгота")

            new_meas = TemperatureMeasurement(date_obj, location, value, latitude, longitude)
            self.measurements.append(new_meas)
            self.storage.save(self.measurements)
            self.refresh_table()
            self.clear_entries()
        except Exception as e:
            messagebox.showerror("Ошибка ввода", f"Неверные данные: {e}")

    def edit_measurement(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Предупреждение", "Ничего не выбрано")
            return
        index = self.tree.index(selected[0])
        meas = self.measurements[index]
        dialog = EditDialog(self.root, "Редактирование измерения", meas)
        if dialog.result:
            self.storage.save(self.measurements)
            self.refresh_table()

    def delete_measurement(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Предупреждение", "Ничего не выбрано")
            return
        index = self.tree.index(selected[0])
        del self.measurements[index]
        self.storage.save(self.measurements)
        self.refresh_table()

    def clear_entries(self):
        self.date_entry.delete(0, tk.END)
        self.location_entry.delete(0, tk.END)
        self.value_entry.delete(0, tk.END)
        self.latitude_entry.delete(0, tk.END)
        self.longitude_entry.delete(0, tk.END)

    def run(self):
        self.root.mainloop()


def main():
    storage = FileStorage("data.txt")
    app = Application(storage)
    app.run()


if __name__ == "__main__":
    main()
