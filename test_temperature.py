"""Модульные тесты для модели TemperatureMeasurement (с координатами)."""

import unittest
import tempfile
import os
from datetime import date
from temperature_program import TemperatureMeasurement, FileStorage


class TestTemperatureMeasurement(unittest.TestCase):
    """Тесты для класса TemperatureMeasurement (парсинг и сериализация)."""

    def test_from_string_valid(self):
        """Корректная строка с координатами."""
        line = 'TemperatureMeasurement 2023.10.05 "Laboratory" 23.5 55.751244 37.618423'
        m = TemperatureMeasurement.from_string(line)
        self.assertEqual(m.date, date(2023, 10, 5))
        self.assertEqual(m.location, "Laboratory")
        self.assertAlmostEqual(m.value, 23.5)
        self.assertAlmostEqual(m.latitude, 55.751244)
        self.assertAlmostEqual(m.longitude, 37.618423)

    def test_from_string_location_with_spaces(self):
        """Место с пробелами внутри кавычек."""
        line = 'TemperatureMeasurement 2024.01.15 "Moscow, Red Square" -5.2 55.751244 37.618423'
        m = TemperatureMeasurement.from_string(line)
        self.assertEqual(m.location, "Moscow, Red Square")
        self.assertAlmostEqual(m.latitude, 55.751244)

    def test_from_string_extra_spaces(self):
        """Лишние пробелы между токенами."""
        line = 'TemperatureMeasurement   2022.07.01   "Home"   22.0   59.9343   30.3351'
        m = TemperatureMeasurement.from_string(line)
        self.assertAlmostEqual(m.value, 22.0)
        self.assertAlmostEqual(m.latitude, 59.9343)

    def test_from_string_invalid_token_count(self):
        """Неверное количество токенов (меньше 6)."""
        with self.assertRaises(ValueError) as ctx:
            TemperatureMeasurement.from_string('TemperatureMeasurement 2023.10.05 "Office" 23.5')
        self.assertIn("Invalid token count", str(ctx.exception))

    def test_from_string_wrong_type(self):
        """Неизвестный тип объекта."""
        with self.assertRaises(ValueError) as ctx:
            TemperatureMeasurement.from_string('WrongType 2023.10.05 "Office" 23.5 0 0')
        self.assertIn("Unknown type", str(ctx.exception))

    def test_from_string_invalid_date(self):
        """Неверный формат даты."""
        with self.assertRaises(ValueError) as ctx:
            TemperatureMeasurement.from_string('TemperatureMeasurement 2023/10/05 "Office" 23.5 0 0')
        self.assertIn("Invalid date format", str(ctx.exception))

    def test_from_string_empty_location(self):
        """Пустое место (пустые кавычки)."""
        with self.assertRaises(ValueError) as ctx:
            TemperatureMeasurement.from_string('TemperatureMeasurement 2023.10.05 "" 23.5 0 0')
        self.assertIn("Location cannot be empty", str(ctx.exception))

    def test_from_string_invalid_value(self):
        """Нечисловое значение температуры."""
        with self.assertRaises(ValueError) as ctx:
            TemperatureMeasurement.from_string('TemperatureMeasurement 2023.10.05 "Office" hot 0 0')
        self.assertIn("Invalid numeric value", str(ctx.exception))

    def test_from_string_invalid_latitude(self):
        """Нечисловая широта."""
        with self.assertRaises(ValueError) as ctx:
            TemperatureMeasurement.from_string('TemperatureMeasurement 2023.10.05 "Office" 23.5 abc 37.618423')
        self.assertIn("Invalid latitude", str(ctx.exception))

    def test_from_string_invalid_longitude(self):
        """Нечисловая долгота."""
        with self.assertRaises(ValueError) as ctx:
            TemperatureMeasurement.from_string('TemperatureMeasurement 2023.10.05 "Office" 23.5 55.751244 xyz')
        self.assertIn("Invalid longitude", str(ctx.exception))

    def test_to_string(self):
        """Сериализация в строку."""
        m = TemperatureMeasurement(date(2023, 10, 5), "Laboratory", 23.5, 55.751244, 37.618423)
        expected = 'TemperatureMeasurement 2023.10.05 "Laboratory" 23.5 55.751244 37.618423'
        self.assertEqual(m.to_string(), expected)


class TestFileStorage(unittest.TestCase):
    """Тесты для FileStorage (чтение/запись файла с пропуском ошибочных строк)."""

    def setUp(self):
        """Создаёт временный файл для тестов."""
        self.temp_file = tempfile.NamedTemporaryFile(mode='w+', delete=False, encoding='utf-8')
        self.filename = self.temp_file.name
        self.temp_file.close()

    def tearDown(self):
        """Удаляет временный файл после теста."""
        if os.path.exists(self.filename):
            os.unlink(self.filename)

    def write_lines(self, lines):
        """Записывает строки во временный файл."""
        with open(self.filename, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))

    def test_load_valid_lines(self):
        """Загружаются только корректные строки, некорректные пропускаются."""
        lines = [
            'TemperatureMeasurement 2023.10.05 "Lab" 23.5 55.75 37.61',
            'garbage line that is invalid',
            'TemperatureMeasurement 2024.01.01 "Home" 18.0 59.93 30.33',
            'Invalid 2024.02.02 "Bad" 99 0 0'
        ]
        self.write_lines(lines)
        storage = FileStorage(self.filename)
        measurements = storage.load()
        self.assertEqual(len(measurements), 2)
        self.assertEqual(measurements[0].location, "Lab")
        self.assertEqual(measurements[1].location, "Home")

    def test_load_empty_file(self):
        """Пустой файл -> пустой список."""
        self.write_lines([])
        storage = FileStorage(self.filename)
        measurements = storage.load()
        self.assertEqual(measurements, [])

    def test_load_file_not_found(self):
        """Файл не существует -> пустой список и предупреждение в лог."""
        os.unlink(self.filename)
        storage = FileStorage(self.filename)
        measurements = storage.load()
        self.assertEqual(measurements, [])

    def test_save_and_load(self):
        """Сохранение и последующая загрузка списка измерений."""
        measurements = [
            TemperatureMeasurement(date(2023, 10, 5), "Lab", 23.5, 55.751244, 37.618423),
            TemperatureMeasurement(date(2024, 1, 1), "Home", 18.0, 59.9343, 30.3351)
        ]
        storage = FileStorage(self.filename)
        storage.save(measurements)
        loaded = storage.load()
        self.assertEqual(len(loaded), 2)
        self.assertEqual(loaded[0].to_string(), measurements[0].to_string())
        self.assertEqual(loaded[1].to_string(), measurements[1].to_string())


if __name__ == '__main__':
    unittest.main()
