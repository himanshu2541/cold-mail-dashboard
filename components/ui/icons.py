ICON_FALLBACKS = {
    ":rocket:": "🚀",
    ":outbox_tray:": "📤",
    ":memo:": "📝",
    ":paperclip:": "📎",
    ":triangular_ruler:": "📐",
    ":file_folder:": "🗂️",
    ":satellite_antenna:": "📡",
    ":bar_chart:": "📊",
    ":white_check_mark:": "✅",
    ":warning:": "⚠️",
    ":x:": "❌",
    ":sparkles:": "✨",
    ":link:": "🧵",
}

try:
    import emoji as emoji_package
except Exception:  # pragma: no cover - fallback only
    emoji_package = None


def icon(alias, fallback=None):
    fallback = fallback or ICON_FALLBACKS.get(alias, alias)
    if emoji_package is None:
        return fallback
    try:
        return emoji_package.emojize(alias, language="alias")
    except Exception:
        return fallback
