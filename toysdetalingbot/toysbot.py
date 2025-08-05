import logging
import io
import os
from datetime import datetime, timedelta

from telegram import Update, InputFile
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ContextTypes, ConversationHandler, filters
)

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# === Настройка логирования ===
logging.basicConfig(level=logging.INFO)

# === Регистрация шрифтов ===
pdfmetrics.registerFont(TTFont('Arial', '/System/Library/Fonts/Supplemental/Arial.ttf'))
pdfmetrics.registerFont(TTFont('Arial-Bold', '/System/Library/Fonts/Supplemental/Arial Bold.ttf'))

# === Telegram Bot Token ===
BOT_TOKEN = "8369046593:AAETwJVlMwOyNIX7AM05FqFt5cN1kCif_o8"

# === Состояния для ConversationHandler ===
WAITING_FOR_ORDER = 1

# === Команда /bahtiyar ===
async def bahtiyar_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Насильника, готов собрать для вас заказ-наряд.\n\n"
        "Пожалуйста, пришлите данные в формате:\n\n"
        "Марка авто: Toyota\nМодель: Camry\nVIN: JTMCV02J304194780\n"
        "Гос. номер: Н063ТА777\nПробег: 62190\n"
        "Список выполняемых работ:\n- Химчистка\n- Полировка"
    )
    return WAITING_FOR_ORDER

# === Получение текста с заказом ===
async def receive_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    data = parse_text(text)

    try:
        pdf = generate_pdf(data)
        file = io.BytesIO(pdf)
        file.name = "zakaz_naryad.pdf"
        await update.message.reply_document(InputFile(file))
    except Exception as e:
        await update.message.reply_text(f"Ошибка при генерации PDF: {str(e)}")

    return ConversationHandler.END

# === Отмена команды ===
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Операция отменена.")
    return ConversationHandler.END

# === Генерация PDF ===
def generate_pdf(data: dict) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=20, leftMargin=20, topMargin=30, bottomMargin=30)
    elements = []

    styles = getSampleStyleSheet()
    header_style = ParagraphStyle(name="Header", fontName="Arial-Bold", fontSize=12, leading=14)
    custom_normal = ParagraphStyle(name="CustomNormal", fontName="Arial", fontSize=10, leading=12)

    # Логотип (если есть)
    logo_path = "images.png"
    if os.path.exists(logo_path):
        logo = Image(logo_path, width=50, height=50)
        elements.append(logo)
        elements.append(Spacer(1, 8))

    elements.append(Paragraph('<b>ООО "Детейлинг Тойз"</b>', header_style))
    elements.append(Paragraph('г. Москва, ул. Мельникова д. 5', custom_normal))
    elements.append(Paragraph('тел.: +7 (967) 089-62-51', custom_normal))
    elements.append(Paragraph('Пн-Сб с 10:00 до 20:00', custom_normal))
    elements.append(Spacer(1, 10))

    elements.append(Paragraph('<b>Заказ-наряд № __________</b>', header_style))
    elements.append(Spacer(1, 10))

    now = datetime.now()

    auto_table_data = [
        ["Марка авто:", data.get("марка", "не указано"), "Пробег:", data.get("пробег", "не указан")],
        ["Модель авто:", data.get("модель", "не указано"), "Дата приема заказа:", now.strftime("%d.%m.%Y")],
        ["VIN-код:", data.get("VIN", "не указан"), "Срок окончания работ:", ""],
        ["Гос. номер:", data.get("гос_номер", "не указан"), "", ""]
    ]
    auto_table = Table(auto_table_data, colWidths=[80, 150, 120, 120])
    auto_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "Arial"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    elements.append(auto_table)
    elements.append(Spacer(1, 16))

    # Работы
    elements.append(Paragraph("Список выполняемых работ:", custom_normal))
    work_data = [["№", "Наименование работ", "Кол-во", "Сумма"]]
    for i, item in enumerate(data.get("работы", []), 1):
        clean_item = item.lstrip(f"{i}.").strip()
        work_data.append([str(i), clean_item, "", ""])

    work_table = Table(work_data, colWidths=[25, 300, 60, 60])
    work_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
        ("FONTNAME", (0, 0), (-1, 0), "Arial-Bold"),
        ("FONTNAME", (0, 1), (-1, -1), "Arial"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (0, 0), (0, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
    ]))
    elements.append(work_table)
    elements.append(Spacer(1, 16))

    # Запчасти
    elements.append(Paragraph("Список запчастей и услуг:", custom_normal))
    part_data = [["№", "Наименование запчастей и услуг", "Кол-во", "Сумма"]]
    for i, item in enumerate(data.get("запчасти", []), 1):
        part_data.append([str(i), item, "", ""])

    part_table = Table(part_data, colWidths=[25, 300, 60, 60])
    part_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
        ("FONTNAME", (0, 0), (-1, 0), "Arial-Bold"),
        ("FONTNAME", (0, 1), (-1, -1), "Arial"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (0, 0), (0, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
    ]))
    elements.append(part_table)
    elements.append(Spacer(1, 16))

    summary_data = [["Оплачено:", "______", "К оплате:", "______"], ["Итого:", "______", "", ""]]
    summary_table = Table(summary_data, colWidths=[70, 100, 70, 100])
    summary_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "Arial-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 12))

    doc.build(elements)
    return buffer.getvalue()

# === Парсинг текста ===
def parse_text(text: str) -> dict:
    result = {
        "марка": "не указано",
        "модель": "не указано",
        "VIN": "не указан",
        "гос_номер": "не указан",
        "пробег": "не указан",
        "работы": [],
        "запчасти": []
    }

    lines = text.strip().splitlines()
    section = None

    for line in lines:
        line = line.strip()
        l = line.lower()
        if l.startswith("марка"):
            result["марка"] = line.split(":", 1)[1].strip()
        elif l.startswith("модель"):
            result["модель"] = line.split(":", 1)[1].strip()
        elif l.startswith("vin"):
            result["VIN"] = line.split(":", 1)[1].strip()
        elif any(l.startswith(x) for x in ["гос. номер:", "номер:", "госномер:"]):
            result["гос_номер"] = line.split(":", 1)[1].strip()
        elif l.startswith("пробег"):
            result["пробег"] = line.split(":", 1)[1].strip()
        elif "работ" in l:
            section = "работы"
        elif "запчаст" in l:
            section = "запчасти"
        else:
            if section:
                result[section].append(line)

    return result

# === Запуск ===
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("bahtiyar", bahtiyar_command)],
        states={WAITING_FOR_ORDER: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_order)]},
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(conv_handler)
    app.run_polling()

if __name__ == '__main__':
    main()





