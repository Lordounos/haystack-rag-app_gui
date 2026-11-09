"""
GUI для RAG-чата на Flet (полная совместимость с Flet 1.0+).
Запуск: python gui.py
Требуется: pip install flet
"""

import threading
import flet as ft

try:
    from chat_pipeline import run_pipeline
except ImportError:
    import time
    def run_pipeline(query: str) -> str:
        time.sleep(2)  # Имитация работы Haystack
        return f"Ответ из Haystack на запрос: '{query}'\n\nВсё работает отлично! <3"


# ---------- Цвета / стиль ----------
BG = "#0f1117"
PANEL = "#171a22"
ACCENT = "#5b8def"
USER_BG = "#2a3550"
BOT_BG = "#1e222c"
TEXT = "#e6e9ef"
MUTED = "#8b93a7"


def main(page: ft.Page):
    page.title = "RAG-чат: консультант по сотовым телефонам"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = BG
    page.padding = 0
    
    # Настройки окна для Flet 1.0+
    page.window.width = 900
    page.window.height = 750
    page.window.resizable = True

    # ---------- Хранилище сообщений ----------
    chat_column = ft.Column(
        spacing=12,
        scroll=ft.ScrollMode.AUTO,
        auto_scroll=True,
        expand=True,
    )

    # ---------- Индикатор "печатает..." ----------
    typing_indicator = ft.Row(
        controls=[
            ft.ProgressRing(width=16, height=16, stroke_width=2, color=ACCENT),
            ft.Text("Модель думает...", color=MUTED, size=13),
        ],
        spacing=8,
        visible=False,
    )

    def bubble(text: str, is_user: bool) -> ft.Container:
        """Создать пузырь сообщения с переносом текста без использования max_width."""
        return ft.Container(
            # tight=True заставляет контейнер сжиматься под длину короткого текста,
            # а фиксированный width ограничивает максимальный размер и вызывает перенос строк
            content=ft.Row(
                controls=[
                    ft.Text(
                        text,
                        color=TEXT,
                        selectable=True,
                        size=14,
                    )
                ],
                tight=True,
            ),
            bgcolor=USER_BG if is_user else BOT_BG,
            padding=12,
            border_radius=ft.BorderRadius.only(
                top_left=14,
                top_right=14,
                bottom_left=14 if is_user else 4,
                bottom_right=4 if is_user else 14,
            ),
            width=550,  # Задаем базовый размер пузыря для корректного переноса текста
        )

    def add_message(text: str, is_user: bool):
        """Добавляет строку с сообщением в чат и обновляет интерфейс."""
        chat_column.controls.append(
            ft.Row(
                controls=[bubble(text, is_user)],
                alignment=ft.MainAxisAlignment.END if is_user else ft.MainAxisAlignment.START,
            )
        )
        page.update()

    # ---------- Обработка отправки ----------
    def on_send_click(e):
        query = message_input.value.strip()
        if not query:
            return

        add_message(query, is_user=True)
        message_input.value = ""
        
        typing_indicator.visible = True
        page.update()

        def background_worker():
            try:
                reply = run_pipeline(query)
            except Exception as ex:
                reply = f"Ошибка при выполнении запроса: {ex}"
            
            typing_indicator.visible = False
            add_message(reply, is_user=False)

        threading.Thread(target=background_worker, daemon=True).start()

    # ---------- Элементы ввода ----------
    message_input = ft.TextField(
        hint_text="Задайте вопрос о смартфонах...",
        hint_style=ft.TextStyle(color=MUTED),
        fill_color=PANEL,
        filled=True,
        expand=True,
        shift_enter=True,
        on_submit=on_send_click,
        border={
            ft.ControlState.DEFAULT: ft.OutlineInputBorder(
                side=ft.BorderSide(color=PANEL, width=1)
            ),
            ft.ControlState.FOCUSED: ft.OutlineInputBorder(
                side=ft.BorderSide(color=ACCENT, width=1.5)
            ),
        },
    )

    send_button = ft.IconButton(
        icon=ft.Icons.SEND_ROUNDED,
        icon_color=ACCENT,
        on_click=on_send_click,
    )

    # ---------- Сборка интерфейса ----------
    header = ft.Container(
        content=ft.Row(
            [
                ft.Text("Haystack RAG Chat 🤖", size=18, weight=ft.FontWeight.BOLD, color=TEXT),
                ft.Text("v1.0", size=12, color=MUTED)
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN
        ),
        bgcolor=PANEL,
        padding=16,
    )

    chat_area = ft.Container(
        content=ft.Column([chat_column, typing_indicator]),
        expand=True,
        padding=20,
    )

    input_panel = ft.Container(
        content=ft.Row([message_input, send_button], spacing=10),
        bgcolor=PANEL,
        padding=16,
    )

    page.add(
        ft.Column(
            [
                header,
                chat_area,
                input_panel,
            ],
            expand=True,
            spacing=0,
        )
    )


if __name__ == "__main__":
    ft.run(main)
