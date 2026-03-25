/**
 * Eiva i18n Module
 * Standalone internationalization for both index.html and app.html
 */

const TRANSLATIONS = {
  en: {
    // Hero
    "hero.tag": "TON AI Hackathon 2026",
    "hero.title": "Your words. Your voice. Your twin.",
    "hero.subtitle": "Turn your Telegram history into a living AI. Verifiable on TON blockchain.",
    "hero.tryDemo": "🤖 Try Demo in Telegram",
    "hero.openCabinet": "Open Your Cabinet →",

    // Nav
    "nav.howItWorks": "How it works",
    "nav.demo": "Demo",
    "nav.github": "GitHub ↗",
    "nav.cabinet": "Open Cabinet →",

    // How it works
    "how.title": "How It Works",
    "how.step1": "Upload",
    "how.step1desc": "Your Telegram chat export",
    "how.step2": "AI Extracts",
    "how.step2desc": "Your personality & memory",
    "how.step3": "Twin Responds",
    "how.step3desc": "In your authentic voice",
    "how.step4": "Mint NFT",
    "how.step4desc": "Own your identity on TON",

    // Demo
    "demo.title": "🎭 Live Demo — Pavel Durov AI Twin",
    "demo.subtitle": "Built from @durov Telegram channel + Lex Fridman interview",
    "demo.sources": "2 sources",
    "demo.confidence": "87% confidence",
    "demo.messages": "20 posts indexed",
    "demo.network": "Testnet ✓",
    "demo.talkBtn": "💬 Talk to Durov in Telegram",
    "demo.mintBtn": "🎫 Mint Durov Soul Certificate (free)",
    "demo.mintingMsg": "Minting on TON Testnet...",

    // Why TON
    "why.title": "Why TON?",
    "why.point1": "Telegram distribution — zero acquisition cost",
    "why.point2": "TON Wallet built into Telegram — frictionless",
    "why.point3": "Low gas fees — identity operations are cheap",
    "why.point4": "True ownership — no company can revoke your NFT",

    // Cabinet
    "cabinet.connectTitle": "Connect your TON Wallet",
    "cabinet.connectDesc": "To access your personal cabinet, connect your TON wallet.",
    "cabinet.demoMode": "Or explore the demo (no wallet needed)",
    "tabs.twin": "👤 My Twin",
    "tabs.hallucinations": "🤖 Hallucinations",
    "tabs.nft": "🎫 Soul Certificate",
    "tabs.confidence": "📊 Confidence",
    "tabs.privacy": "🔒 Privacy",

    // Twin tab
    "twin.title": "Your Digital Twin",
    "twin.messages": "Messages indexed",
    "twin.sources": "Sources",
    "twin.mode": "Mode",
    "twin.personality": "Personality Traits",

    // Hallucinations tab
    "hall.title": "🤖 AI Hallucination Control",
    "hall.desc": "All AI models hallucinate. Here's how to manage it.",
    "hall.whatItDoes": "Your twin might:",
    "hall.risk1": "⚠️ Invent memories that never happened",
    "hall.risk2": "⚠️ Confuse dates and timelines",
    "hall.risk3": "⚠️ Talk about events not in your messages",
    "hall.risk4": "⚠️ Be overly confident about uncertain things",
    "hall.presets": "Preset Controls:",
    "hall.showUncertainty": "Show uncertainty (\"I think...\" vs \"I remember...\")",
    "hall.refuseLow": "Refuse to answer if low confidence",
    "hall.noInvent": "Never invent memories",
    "hall.customTitle": "Custom Instructions:",
    "hall.customDesc": "Tell your twin what to avoid or emphasize.",
    "hall.customPlaceholder": "Examples:\n- Don't talk about my work\n- Always respond in Russian\n- Don't share opinions about politics",
    "hall.quickPresets": "Quick presets:",
    "hall.preset1": "No fake dates",
    "hall.preset2": "Privacy protection",
    "hall.preset3": "Honest uncertainty",
    "hall.save": "💾 Save Settings",

    // NFT tab
    "nft.title": "🎫 Soul Certificate",
    "nft.type": "Type",
    "nft.network": "Network",
    "nft.sources": "Sources",
    "nft.minted": "Minted",
    "nft.viewTonscan": "View on Tonscan →",
    "nft.mint": "Mint yours →",

    // Confidence tab
    "conf.title": "📊 Personality Confidence",
    "conf.desc": "How well does your twin know you?",
    "conf.style": "Communication style",
    "conf.humor": "Sense of humor",
    "conf.opinions": "Opinions & beliefs",
    "conf.experiences": "Personal experiences",
    "conf.relationships": "Relationships",
    "conf.tip": "Add more sources with /add_source to improve accuracy",

    // Privacy tab
    "priv.title": "🔒 Privacy Protection",
    "priv.desc": "Your twin never shares your sensitive data.",
    "priv.alwaysOn": "🛡️ Always ON — Cannot be disabled",
    "priv.neverShare": "Your twin will NEVER share:",
    "priv.passwords": "Passwords & PINs",
    "priv.emails": "Email addresses",
    "priv.phones": "Phone numbers",
    "priv.address": "Home / work address",
    "priv.cards": "Card / bank numbers",
    "priv.docs": "Passport / ID data",
    "priv.keys": "API keys & tokens",
    "priv.medical": "Medical information",
    "priv.piiFilter": "🛡️ PII Filter",
    "priv.aiLock": "🔒 AI Privacy Lock",
    "priv.localStorage": "💾 Local Storage",
    "priv.noUpload": "☁️ Raw Message Upload",

    // Footer
    "footer.built": "Built for TON AI Hackathon 2026",
    "footer.github": "GitHub",
    "footer.bot": "Telegram Bot",
    "footer.cabinet": "Open Cabinet",

    // How it works subtitle
    "how.subtitle": "Four steps from your Telegram history to a living, blockchain-anchored digital twin",
    "how.eyebrow": "Process",

    // Demo section
    "demo.eyebrow": "Live Demo",
    "demo.titleSection": "See it in action",

    // Why TON headings
    "why.eyebrow": "Technology",
    "why.h1": "Telegram Native",
    "why.h2": "Built-in Wallet",
    "why.h3": "Low Gas Fees",
    "why.h4": "True Ownership",

    // Nav back
    "nav.back": "← Back to Eiva",

    // Cabinet nav & connect screen
    "cabinet.cabinet": "My Cabinet",
    "cabinet.connectBtn": "🔗 Connect Wallet",
    "cabinet.viewDemo": "👁 View Durov Demo Cabinet",
    "cabinet.demoBadge": "Demo Mode — Pavel Durov",

    // Twin tab actions
    "twin.openTelegram": "💬 Open in Telegram →",
    "twin.viewCert": "🎫 View Soul Certificate",
    "twin.modePersonal": "Personal",
    "twin.modeProfessional": "Professional",

    // Status labels
    "status.active": "ACTIVE",
    "status.enabled": "ENABLED",
    "status.never": "NEVER",

    // Demo dialog labels
    "demo.dialogLabel": "Example conversation:",
    "demo.userLabel": "You:",
    "demo.twinLabel": "Durov twin:",

    // Nav extras (cabinet)
    "nav.disconnect": "🔌 Disconnect",

    // Sources tab
    "tabs.sources": "📤 Sources",
    "sources.title": "📤 Upload Sources",
    "sources.desc": "Upload your Telegram chat export (JSON). Max 2 sources · 5 MB per file.",
    "sources.dragDrop": "Drag & drop your Telegram export here",
    "sources.browse": "or click to browse files",
    "sources.limit": "Limit: 2 sources · 5 MB per file · .json only",
    "sources.upload": "🚀 Upload Source",
    "sources.noSources": "No sources yet — upload your first Telegram export below.",
    "sources.maxReached": "⚠️ Maximum 2 sources reached. Remove a source to add a new one.",
    "sources.errJson": "❌ Please select a .json file (Telegram export)",
    "sources.errSize": "❌ File exceeds 5 MB limit. Please export a smaller chat.",
    "sources.errNoWallet": "⚠️ Connect your TON wallet first.",
    "sources.errNoFile": "⚠️ Select a file first.",
    "sources.uploading": "⏳ Uploading and analyzing messages… This may take 30–60 seconds."
  },

  ru: {
    // Hero
    "hero.tag": "TON AI Хакатон 2026",
    "hero.title": "Твои слова. Твой голос. Твой двойник.",
    "hero.subtitle": "Превращаем историю твоих чатов в живой AI. Верифицируется на блокчейне TON.",
    "hero.tryDemo": "🤖 Попробовать демо в Telegram",
    "hero.openCabinet": "Открыть кабинет →",

    // Nav
    "nav.howItWorks": "Как работает",
    "nav.demo": "Демо",
    "nav.github": "GitHub ↗",
    "nav.cabinet": "Открыть кабинет →",

    // How it works
    "how.title": "Как это работает",
    "how.step1": "Загрузи",
    "how.step1desc": "Экспорт чатов из Telegram",
    "how.step2": "AI извлекает",
    "how.step2desc": "Твою личность и память",
    "how.step3": "Двойник отвечает",
    "how.step3desc": "Твоим голосом и стилем",
    "how.step4": "Минтишь NFT",
    "how.step4desc": "Владей своей идентичностью на TON",

    // Demo
    "demo.title": "🎭 Live Demo — AI двойник Павла Дурова",
    "demo.subtitle": "Создан из канала @durov + интервью Лекс Фридмана",
    "demo.sources": "2 источника",
    "demo.confidence": "87% точность",
    "demo.messages": "20 постов",
    "demo.network": "Testnet ✓",
    "demo.talkBtn": "💬 Поговорить с Дуровым",
    "demo.mintBtn": "🎫 Получить NFT Дурова (бесплатно)",
    "demo.mintingMsg": "Минтим на TON Testnet...",

    // Why TON
    "why.title": "Почему TON?",
    "why.point1": "Дистрибуция через Telegram — нулевая стоимость привлечения",
    "why.point2": "TON Кошелёк встроен в Telegram — удобно",
    "why.point3": "Низкие комиссии — операции с идентичностью дёшевы",
    "why.point4": "Настоящее владение — никто не отберёт твой NFT",

    // Cabinet
    "cabinet.connectTitle": "Подключи TON кошелёк",
    "cabinet.connectDesc": "Для доступа к личному кабинету подключи свой TON кошелёк.",
    "cabinet.demoMode": "Или открой демо без кошелька",
    "tabs.twin": "👤 Двойник",
    "tabs.hallucinations": "🤖 Галлюцинации",
    "tabs.nft": "🎫 Soul Certificate",
    "tabs.confidence": "📊 Точность",
    "tabs.privacy": "🔒 Приватность",

    // Twin tab
    "twin.title": "Твой цифровой двойник",
    "twin.messages": "Сообщений",
    "twin.sources": "Источников",
    "twin.mode": "Режим",
    "twin.personality": "Черты личности",

    // Hallucinations tab
    "hall.title": "🤖 Контроль галлюцинаций AI",
    "hall.desc": "Все AI модели галлюцинируют. Вот как это контролировать.",
    "hall.whatItDoes": "Твой двойник может:",
    "hall.risk1": "⚠️ Придумать воспоминания которых не было",
    "hall.risk2": "⚠️ Перепутать даты и временные рамки",
    "hall.risk3": "⚠️ Говорить о событиях не из твоих сообщений",
    "hall.risk4": "⚠️ Быть уверенным в ненадёжных вещах",
    "hall.presets": "Настройки:",
    "hall.showUncertainty": "Показывать неуверенность (\"я думаю...\" vs \"я помню...\")",
    "hall.refuseLow": "Отказываться отвечать при низкой уверенности",
    "hall.noInvent": "Не придумывать воспоминания",
    "hall.customTitle": "Кастомные инструкции:",
    "hall.customDesc": "Скажи двойнику что избегать или выделять.",
    "hall.customPlaceholder": "Примеры:\n- Не говори о моей работе\n- Всегда отвечай на русском\n- Не высказывай мнение о политике",
    "hall.quickPresets": "Быстрые пресеты:",
    "hall.preset1": "Не выдумывай даты",
    "hall.preset2": "Защита приватности",
    "hall.preset3": "Честная неуверенность",
    "hall.save": "💾 Сохранить",

    // NFT tab
    "nft.title": "🎫 Soul Certificate",
    "nft.type": "Тип",
    "nft.network": "Сеть",
    "nft.sources": "Источники",
    "nft.minted": "Создан",
    "nft.viewTonscan": "Tonscan →",
    "nft.mint": "Получить →",

    // Confidence tab
    "conf.title": "📊 Точность личности",
    "conf.desc": "Насколько хорошо двойник тебя знает?",
    "conf.style": "Стиль общения",
    "conf.humor": "Чувство юмора",
    "conf.opinions": "Взгляды и мнения",
    "conf.experiences": "Личный опыт",
    "conf.relationships": "Отношения",
    "conf.tip": "Добавь источники через /add_source для улучшения",

    // Privacy tab
    "priv.title": "🔒 Защита приватности",
    "priv.desc": "Твой двойник никогда не раскроет личные данные.",
    "priv.alwaysOn": "🛡️ Всегда ВКЛЮЧЕНО — нельзя отключить",
    "priv.neverShare": "Двойник НИКОГДА не раскроет:",
    "priv.passwords": "Пароли и PIN-коды",
    "priv.emails": "Email адреса",
    "priv.phones": "Номера телефонов",
    "priv.address": "Домашний / рабочий адрес",
    "priv.cards": "Номера карт и счетов",
    "priv.docs": "Паспортные данные",
    "priv.keys": "API ключи и токены",
    "priv.medical": "Медицинская информация",
    "priv.piiFilter": "🛡️ PII Фильтр",
    "priv.aiLock": "🔒 AI Блокировка",
    "priv.localStorage": "💾 Локальное хранение",
    "priv.noUpload": "☁️ Загрузка сообщений",

    // Footer
    "footer.built": "Создано для TON AI Хакатон 2026",
    "footer.github": "GitHub",
    "footer.bot": "Telegram Бот",
    "footer.cabinet": "Открыть кабинет",

    // How it works subtitle
    "how.subtitle": "Четыре шага от истории чатов до живого цифрового двойника на блокчейне",
    "how.eyebrow": "Процесс",

    // Demo section
    "demo.eyebrow": "Демо",
    "demo.titleSection": "Посмотри как это работает",

    // Why TON headings
    "why.eyebrow": "Технология",
    "why.h1": "Нативно в Telegram",
    "why.h2": "Встроенный кошелёк",
    "why.h3": "Низкие комиссии",
    "why.h4": "Настоящее владение",

    // Nav back
    "nav.back": "← Назад",

    // Cabinet nav & connect screen
    "cabinet.cabinet": "Мой кабинет",
    "cabinet.connectBtn": "🔗 Подключить кошелёк",
    "cabinet.viewDemo": "👁 Демо кабинет Дурова",
    "cabinet.demoBadge": "Демо — Павел Дуров",

    // Twin tab actions
    "twin.openTelegram": "💬 Открыть в Telegram →",
    "twin.viewCert": "🎫 Soul Certificate",
    "twin.modePersonal": "Личный",
    "twin.modeProfessional": "Профессиональный",

    // Status labels
    "status.active": "АКТИВЕН",
    "status.enabled": "ВКЛЮЧЕНО",
    "status.never": "НИКОГДА",

    // Demo dialog labels
    "demo.dialogLabel": "Пример разговора:",
    "demo.userLabel": "Вы:",
    "demo.twinLabel": "Двойник Дурова:",

    // Nav extras (cabinet)
    "nav.disconnect": "🔌 Выйти",

    // Sources tab
    "tabs.sources": "📤 Источники",
    "sources.title": "📤 Загрузить источники",
    "sources.desc": "Загрузи экспорт чатов Telegram (JSON). Максимум 2 источника · 5 МБ на файл.",
    "sources.dragDrop": "Перетащи сюда экспорт Telegram",
    "sources.browse": "или нажми для выбора файла",
    "sources.limit": "Ограничение: 2 источника · 5 МБ на файл · только .json",
    "sources.upload": "🚀 Загрузить источник",
    "sources.noSources": "Источников ещё нет — загрузи первый экспорт ниже.",
    "sources.maxReached": "⚠️ Достигнут лимит в 2 источника.",
    "sources.errJson": "❌ Выбери .json файл (экспорт Telegram)",
    "sources.errSize": "❌ Файл превышает 5 МБ. Выбери меньший чат.",
    "sources.errNoWallet": "⚠️ Сначала подключи TON кошелёк.",
    "sources.errNoFile": "⚠️ Сначала выбери файл.",
    "sources.uploading": "⏳ Загружаем и анализируем сообщения… 30–60 секунд."
  }
};

let currentLang = localStorage.getItem('eiva_lang') || 'en';

function t(key) {
  return TRANSLATIONS[currentLang]?.[key] || TRANSLATIONS.en[key] || key;
}

function setLang(lang) {
  currentLang = lang;
  localStorage.setItem('eiva_lang', lang);
  applyTranslations();
  document.querySelectorAll('.lang-btn').forEach(b => b.classList.remove('active'));
  document.querySelectorAll(`[data-lang="${lang}"]`).forEach(b => b.classList.add('active'));
}

function applyTranslations() {
  document.querySelectorAll('[data-i18n]').forEach(el => {
    const key = el.getAttribute('data-i18n');
    const val = t(key);
    if (val) el.textContent = val;
  });
  document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
    const key = el.getAttribute('data-i18n-placeholder');
    const val = t(key);
    if (val) el.placeholder = val;
  });
}

document.addEventListener('DOMContentLoaded', () => {
  applyTranslations();
  // Set initial language button state
  const langBtn = document.querySelector(`[data-lang="${currentLang}"]`);
  if (langBtn) langBtn.classList.add('activ