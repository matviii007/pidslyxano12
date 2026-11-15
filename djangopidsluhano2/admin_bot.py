import asyncio
import html
import logging
import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "djangopidsluhano2.settings")
django.setup()

from django.conf import settings
from django.contrib.auth.models import User
from django.db import transaction

from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.types import (
    BufferedInputFile,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)
from asgiref.sync import sync_to_async

from main.mentions import notify_mentions
from main.models import Notification, Post, Profile, Reply, Report

logging.basicConfig(level=logging.INFO)
dp = Dispatcher()


def is_admin(user_id: int) -> bool:
    return user_id in settings.TELEGRAM_ADMIN_IDS


@sync_to_async
def get_stats():
    return {
        "users": User.objects.count(),
        "verified": Profile.objects.filter(is_verified=True).count(),
        "posts_approved": Post.objects.filter(is_approved=True).count(),
        "posts_pending": Post.objects.filter(
            is_approved=False,
            is_rejected=False,
        ).count(),
        "replies": Reply.objects.count(),
        "reports": Report.objects.count(),
    }


@sync_to_async
def get_next_pending_post():
    post = (
        Post.objects.filter(is_approved=False, is_rejected=False)
        .select_related("author", "tag")
        .order_by("created_at", "pk")
        .first()
    )
    if post is None:
        return None

    return {
        "id": post.pk,
        "author": post.author.username,
        "is_anon": post.is_anonymous,
        "tag": post.tag.name if post.tag else post.pending_tag_name or "Без тегу",
        "text": post.text,
        "has_image": bool(post.image),
        "created_at": post.created_at.strftime("%d.%m %H:%M"),
    }


@sync_to_async
def get_post_image(post_id: int):
    post = Post.objects.filter(pk=post_id).only("image").first()
    if post is None or not post.image:
        return None
    with post.image.open("rb") as image_file:
        return os.path.basename(post.image.name), image_file.read()


@sync_to_async
def moderate_post(post_id: int, action: str) -> str:
    if action not in {"approve", "reject", "pin"}:
        return "Невідома дія."

    with transaction.atomic():
        post = (
            Post.objects.select_for_update()
            .select_related("author")
            .filter(pk=post_id)
            .first()
        )
        if post is None:
            return "Допис уже видалено."
        if post.is_approved or post.is_rejected:
            return "Цей допис уже опрацьовано."

        if action in {"approve", "pin"}:
            post.is_approved = True
            post.is_rejected = False
            if action == "pin":
                post.is_pinned = True
            post.save()
            Notification.objects.create(
                recipient=post.author,
                post=post,
                kind=Notification.POST_APPROVED,
                message=(
                    "Ваш допис схвалено та закріплено у стрічці!"
                    if action == "pin"
                    else "Ваш допис схвалено модератором!"
                ),
            )
            notify_mentions(post.text, post.author, post, post.is_anonymous)
            if action == "pin":
                return f"📌 Допис #{post.pk} схвалено та закріплено."
            return f"✅ Допис #{post.pk} схвалено та опубліковано."

        post.is_approved = False
        post.is_rejected = True
        post.save(update_fields=["is_approved", "is_rejected"])
        Notification.objects.create(
            recipient=post.author,
            post=post,
            kind=Notification.POST_REJECTED,
            message="Ваш допис відхилено модератором.",
        )
        return f"❌ Допис #{post.pk} відхилено."


@sync_to_async
def get_next_report():
    report = (
        Report.objects.select_related("post", "post__author", "author")
        .order_by("created_at", "pk")
        .first()
    )
    if report is None:
        return None
    return {
        "id": report.pk,
        "reason": report.get_reason_display(),
        "comment": report.comment or "Без коментаря",
        "reporter": report.author.username,
        "post_id": report.post_id,
        "post_author": report.post.author.username,
        "post_text": report.post.text,
    }


@sync_to_async
def resolve_report(report_id: int, delete_post: bool) -> str:
    with transaction.atomic():
        report = (
            Report.objects.select_for_update()
            .select_related("post")
            .filter(pk=report_id)
            .first()
        )
        if report is None:
            return "Скаргу вже опрацьовано."

        post_id = report.post_id
        if delete_post:
            report.post.delete()
            return f"🗑 Допис #{post_id} видалено разом зі скаргами."

        report.delete()
        return f"👌 Скаргу #{report_id} відхилено, допис #{post_id} залишено."


def main_menu_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📝 Модерація дописів"), KeyboardButton(text="🚨 Скарги")],
            [KeyboardButton(text="📊 Статистика ліцею")],
        ],
        resize_keyboard=True,
    )


def post_action_kb(post_id: int):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Схвалити",
                    callback_data=f"post:approve:{post_id}",
                ),
                InlineKeyboardButton(
                    text="❌ Відхилити",
                    callback_data=f"post:reject:{post_id}",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="📌 Схвалити й закріпити",
                    callback_data=f"post:pin:{post_id}",
                ),
            ],
        ]
    )


def report_action_kb(report_id: int):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🗑 Видалити допис",
                    callback_data=f"rep:del:{report_id}",
                ),
                InlineKeyboardButton(
                    text="👌 Відхилити скаргу",
                    callback_data=f"rep:keep:{report_id}",
                ),
            ]
        ]
    )


async def send_post_card(message, text: str, post_id: int, keyboard):
    image = await get_post_image(post_id)
    if image is None:
        await message.answer(text, parse_mode="HTML", reply_markup=keyboard)
        return

    filename, content = image
    await message.answer_photo(
        photo=BufferedInputFile(content, filename=filename),
        caption=text,
        parse_mode="HTML",
        reply_markup=keyboard,
    )


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    if not message.from_user or not is_admin(message.from_user.id):
        await message.answer("⛔ Доступ заборонено.")
        return
    await message.answer(
        "👋 Адмін-панель «Підслухано у Ліцеї 8».\nОберіть дію:",
        reply_markup=main_menu_kb(),
    )


@dp.message(F.text == "📊 Статистика ліцею")
async def show_stats(message: types.Message):
    if not message.from_user or not is_admin(message.from_user.id):
        await message.answer("⛔ Доступ заборонено.")
        return

    stats = await get_stats()
    await message.answer(
        "📊 <b>Статистика сайту:</b>\n\n"
        f"👥 Користувачів: <b>{stats['users']}</b> "
        f"(верифікованих: {stats['verified']})\n"
        f"✅ Опублікованих дописів: <b>{stats['posts_approved']}</b>\n"
        f"⏳ На модерації: <b>{stats['posts_pending']}</b>\n"
        f"💬 Коментарів: <b>{stats['replies']}</b>\n"
        f"🚨 Скарг: <b>{stats['reports']}</b>",
        parse_mode="HTML",
    )


@dp.message(F.text == "📝 Модерація дописів")
async def check_posts(message: types.Message):
    if not message.from_user or not is_admin(message.from_user.id):
        await message.answer("⛔ Доступ заборонено.")
        return

    post = await get_next_pending_post()
    if post is None:
        await message.answer("🎉 Черга порожня! Усі дописи перевірені.")
        return

    anonymous_label = "Так 🕵️" if post["is_anon"] else "Ні 👤"
    text = (
        f"📝 <b>Допис #{post['id']}</b>\n"
        f"👤 Автор: <code>{html.escape(post['author'])}</code>\n"
        f"🕵️ Анонімно: {anonymous_label}\n"
        f"🏷 Тема: {html.escape(post['tag'])}\n"
        f"🕒 Створено: {post['created_at']}\n\n"
        f"{html.escape(post['text'])}"
    )
    await send_post_card(
        message,
        text,
        post["id"],
        post_action_kb(post["id"]),
    )


@dp.message(F.text == "🚨 Скарги")
async def check_reports(message: types.Message):
    if not message.from_user or not is_admin(message.from_user.id):
        await message.answer("⛔ Доступ заборонено.")
        return

    report = await get_next_report()
    if report is None:
        await message.answer("🎉 Немає відкритих скарг.")
        return

    text = (
        f"🚨 <b>Скарга #{report['id']}</b>\n"
        f"📌 Причина: <b>{html.escape(report['reason'])}</b>\n"
        f"💬 Коментар: <i>{html.escape(report['comment'])}</i>\n"
        f"👤 Скаржник: <code>{html.escape(report['reporter'])}</code>\n"
        "────────────────────\n"
        f"📄 <b>Допис #{report['post_id']}</b> "
        f"(автор: <code>{html.escape(report['post_author'])}</code>):\n"
        f"{html.escape(report['post_text'])}"
    )
    await send_post_card(
        message,
        text,
        report["post_id"],
        report_action_kb(report["id"]),
    )


@dp.callback_query(F.data.startswith("post:"))
async def handle_post_callback(callback: types.CallbackQuery):
    if not callback.from_user or not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ заборонено.", show_alert=True)
        return

    try:
        _, action, post_id_value = callback.data.split(":")
        post_id = int(post_id_value)
    except (AttributeError, ValueError):
        await callback.answer("Некоректна дія.", show_alert=True)
        return

    result = await moderate_post(post_id, action)
    if callback.message:
        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.message.answer(result)
    await callback.answer("Опрацьовано.")


@dp.callback_query(F.data.startswith("rep:"))
async def handle_report_callback(callback: types.CallbackQuery):
    if not callback.from_user or not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ заборонено.", show_alert=True)
        return

    try:
        _, action, report_id_value = callback.data.split(":")
        report_id = int(report_id_value)
    except (AttributeError, ValueError):
        await callback.answer("Некоректна дія.", show_alert=True)
        return
    if action not in {"del", "keep"}:
        await callback.answer("Невідома дія.", show_alert=True)
        return

    result = await resolve_report(report_id, delete_post=action == "del")
    if callback.message:
        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.message.answer(result)
    await callback.answer("Опрацьовано.")


async def main():
    token = settings.TELEGRAM_BOT_TOKEN
    if not token:
        raise RuntimeError(
            "Set TELEGRAM_BOT_TOKEN in the project .env or environment before starting the bot."
        )
    if not settings.TELEGRAM_ADMIN_IDS:
        raise RuntimeError(
            "Set TELEGRAM_ADMIN_IDS to a comma-separated list of trusted Telegram user IDs."
        )

    async with Bot(token=token) as bot:
        logging.info("Telegram admin bot started.")
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
