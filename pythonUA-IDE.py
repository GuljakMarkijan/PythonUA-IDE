import sys
import re
import subprocess
import tempfile
import os
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPlainTextEdit,
    QPushButton, QListWidget, QListWidgetItem, QFileDialog, QTextBrowser, QSplitter
)
from PySide6.QtGui import QTextCharFormat, QColor, QFont, QSyntaxHighlighter, QKeyEvent
from PySide6.QtCore import Qt

uk_keywords = [
    "функція", "метод", "повернути", "якщо", "інакше", "інакше_якщо", "для", "доки",
    "вийди", "продовжити", "в", "і", "або", "не", "вивести", "ДонтПушЗеХорсес",
    "Правда", "Брехня", "Ніц", "клас", "спробувати", "лови", "нарешті",
    "з", "як", "лямбда", "глобально", "не_локально", "певне", "видалити",
    "поруч", "викинути", "імпорт", "з_", "ввести", "діапазон",
    "довжина", "сума", "мінімум", "максимум", "від", "круг", "список", "кортеж",
    "словник", "множина", "фільтр", "мапа", "зменшити", "виклик", "існує",
    "відкрити", "рядок", "число", "число_з_плав", "байти", "байт_масив", "декілька",
    "спроба_поділити", "співставити", "відновити", "викликати", "від_рядка",
    "допомога", "тип", "глобальні", "локальні", "ідентифікатор", "приєднати",
    "хеш", "відкрити_файл", "сорт", "повернути_рядок", "дійсне", "ціле", "Слава", "Ісусу", "Христу"
]

translations = {
    "функція": "def", "метод": "def", "повернути": "return", "якщо": "if", "інакше": "else",
    "інакше_якщо": "elif", "для": "for", "доки": "while", "вийди": "break",
    "продовжити": "continue", "в": "in", "і": "and", "або": "or", "не": "not",
    "вивести": "print", "ДонтПушЗеХорсес": "pass", "Правда": "True", "Брехня": "False",
    "Ніц": "None", "клас": "class", "спробувати": "try", "лови": "except",
    "нарешті": "finally", "з": "with", "як": "as", "лямбда": "lambda",
    "глобально": "global", "не_локально": "nonlocal", "певне": "assert",
    "видалити": "del", "поруч": "yield", "викинути": "raise", "імпорт": "import",
    "з_": "from", "ввести": "input", "діапазон": "range",
    "довжина": "len", "сума": "sum", "мінімум": "min", "максимум": "max",
    "від": "abs", "круг": "round", "список": "list", "кортеж": "tuple",
    "словник": "dict", "множина": "set", "фільтр": "filter", "мапа": "map",
    "зменшити": "reduce", "виклик": "callable", "існує": "isinstance",
    "відкрити": "open", "рядок": "str", "число": "int", "число_з_плав": "float",
    "байти": "bytes", "байт_масив": "bytearray", "декілька": "enumerate",
    "спроба_поділити": "divmod", "співставити": "zip", "відновити": "reversed",
    "викликати": "eval", "від_рядка": "exec", "допомога": "help", "тип": "type",
    "глобальні": "globals", "локальні": "locals", "ідентифікатор": "id",
    "приєднати": "dir", "хеш": "hash", "відкрити_файл": "open", "сорт": "sorted",
    "повернути_рядок": "repr", "дійсне": "float", "ціле": "int"
}

class UkrHighlighter(QSyntaxHighlighter):
    def __init__(self, parent):
        super().__init__(parent)
        self.keyword_format = QTextCharFormat()
        self.keyword_format.setForeground(QColor("#0066FF"))
        self.keyword_format.setFontWeight(QFont.Bold)  # type: ignore
        self.string_format = QTextCharFormat()
        self.string_format.setForeground(QColor("#37FF00"))
        self.keywords = uk_keywords

    def highlightBlock(self, text):
        for word in self.keywords:
            for match in re.finditer(rf'\b{word}\b', text):
                start, end = match.start(), match.end()
                self.setFormat(start, end - start, self.keyword_format)
        for match in re.finditer(r'(\".*?\"|\'.*?\')', text):
            start, end = match.start(), match.end()
            self.setFormat(start, end - start, self.string_format)

class Editor(QPlainTextEdit):
    pairs = {"(": ")", "[": "]", "{": "}", '"': '"', "'": "'"}

    def __init__(self):
        super().__init__()
        self.setStyleSheet("background-color:#2B2B2B; color:#F8F8F2;")
        self.setFont(QFont("Consolas", 12))
        self.completer_popup = QListWidget()
        self.completer_popup.setWindowFlags(Qt.Popup) # type: ignore
        self.completer_popup.setFocusPolicy(Qt.NoFocus) # type: ignore
        self.completer_popup.itemClicked.connect(self.insert_completion)
        self.textChanged.connect(self.on_text_changed)

    def keyPressEvent(self, event: QKeyEvent):
        cursor = self.textCursor()
        key = event.text()
        if key in self.pairs:
            closing = self.pairs[key]
            super().keyPressEvent(event)
            cursor = self.textCursor()
            cursor.insertText(closing)
            cursor.movePosition(cursor.Left)  # type: ignore
            self.setTextCursor(cursor)
            return
        elif key in self.pairs.values():
            next_char = self.textCursor().document().characterAt(self.textCursor().position())
            if next_char == key:
                cursor.movePosition(cursor.Right)  # type: ignore
                self.setTextCursor(cursor)
                return
        super().keyPressEvent(event)
        if event.text().isalnum() or event.text() == "_":
            self.show_completer()
        else:
            self.completer_popup.hide()

    def on_text_changed(self):
        self.show_completer()

    def show_completer(self):
        cursor = self.textCursor()
        cursor.select(cursor.WordUnderCursor)  # type: ignore
        word = cursor.selectedText()
        if not word:
            self.completer_popup.hide()
            return
        matches = [k for k in uk_keywords if k.startswith(word)]
        if not matches:
            self.completer_popup.hide()
            return
        self.completer_popup.clear()
        for m in matches:
            QListWidgetItem(m, self.completer_popup)
        rect = self.cursorRect()
        pos = self.mapToGlobal(rect.bottomRight())
        self.completer_popup.move(pos)
        self.completer_popup.setCurrentRow(0)
        self.completer_popup.show()

    def insert_completion(self, item):
        cursor = self.textCursor()
        cursor.select(cursor.WordUnderCursor)  # type: ignore
        cursor.removeSelectedText()
        cursor.insertText(item.text())
        self.setTextCursor(cursor)
        self.completer_popup.hide()

class UkrInterpreter:
    def __init__(self, output_widget: QTextBrowser):
        self.output = output_widget
        self.runner_cmd = "PythonUA"

    def exec(self, code: str):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".ua", delete=False, encoding="utf-8") as tmp:
            tmp.write(code)
            tmp_path = tmp.name

        try:
            result = subprocess.run(
                [self.runner_cmd, tmp_path],
                capture_output=True,
                text=True
            )
            if result.stdout:
                self.output.append(result.stdout)
            if result.stderr:
                self.output.append(f"<span style='color:red'>{result.stderr}</span>")
        except FileNotFoundError:
            self.output.append("<span style='color:red'>Помилка: інтерпретатор PythonUA не знайдено в PATH, щоб додати в PATH відкрийте config-pythonua.exe</span>")
        except Exception as e:
            self.output.append(f"<span style='color:red'>Помилка запуску: {e}</span>")
        finally:
            os.remove(tmp_path)

class UkrIDE(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Українська Python IDE")
        self.resize(900, 700)
        layout = QVBoxLayout(self)

        splitter = QSplitter(Qt.Vertical)  # type: ignore

        self.editor = Editor()
        self.highlighter = UkrHighlighter(self.editor.document())
        splitter.addWidget(self.editor)

        self.console = QTextBrowser()
        self.console.setStyleSheet("background-color:#1E1E1E; color:#F8F8F2; font-family: Consolas;")
        self.interpreter = UkrInterpreter(self.console)
        splitter.addWidget(self.console)

        splitter.setSizes([500, 200])
        layout.addWidget(splitter)

        btn_layout = QHBoxLayout()
        self.run_btn = QPushButton("Запуск")
        self.run_btn.clicked.connect(self.run_code)
        self.save_btn = QPushButton("Зберегти як...")
        self.save_btn.clicked.connect(self.save_file)
        btn_layout.addWidget(self.run_btn)
        btn_layout.addWidget(self.save_btn)

        layout.addLayout(btn_layout)

    def run_code(self):
        code = self.editor.toPlainText()
        self.console.append("<span style='color:cyan'>=== Виконання програми ===</span>")
        self.interpreter.exec(code)
        self.console.append("<span style='color:cyan'>=== Кінець виконання ===</span>")

    def save_file(self):
        file_name, _ = QFileDialog.getSaveFileName(self, "Зберегти файл", "", "Українські python-скрипти (*.ua)")
        if file_name:
            if not file_name.endswith(".ua"):
                file_name += ".ua"
            with open(file_name, "w", encoding="utf-8") as f:
                f.write(self.editor.toPlainText())
            self.console.append(f"<span style='color:green'>Файл збережено: {file_name}</span>")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    ide = UkrIDE()
    ide.show()
    sys.exit(app.exec())