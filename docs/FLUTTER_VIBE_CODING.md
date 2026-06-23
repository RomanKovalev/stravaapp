# Вайбкодинг Flutter-приложения в Cursor

Руководство по итеративной разработке мобильного клиента StravaApp с помощью AI-агента в Cursor.

## Суть подхода

Вайбкодинг — это не «напиши всё приложение одним промптом», а итеративная сборка маленькими кусками с чётким контекстом. Бэкенд и [MOBILE_API.md](./MOBILE_API.md) уже готовы — это основа для мобильного клиента.

## 1. Подготовка проекта

**Отдельная папка Flutter рядом с бэкендом** (или отдельный репозиторий):

```
stravaapp/          ← Django API (уже есть)
stravaapp_mobile/   ← flutter create stravaapp_mobile
```

Создание:

```bash
flutter create stravaapp_mobile
cd stravaapp_mobile
flutter pub get
```

Откройте в Cursor оба проекта (multi-root workspace) или хотя бы Flutter-папку с `@docs/MOBILE_API.md` в контексте.

## 2. Правила для агента

Создайте `.cursor/rules/flutter.mdc` (или User Rule) с фиксированными решениями, чтобы агент не «придумывал» каждый раз:

| Область | Рекомендация |
|---------|--------------|
| State management | `riverpod` или `bloc` — выбрать один |
| HTTP | `dio` + interceptors для JWT |
| Хранение токенов | `flutter_secure_storage` |
| OAuth | `url_launcher` / `app_links` для deep link `stravaapp://auth` |
| Навигация | `go_router` |
| Base URL | `http://13.51.255.182:8080/api/` (см. [MOBILE_API.md](./MOBILE_API.md)) |

Пример первого промпта:

> Создай Flutter-приложение по docs/MOBILE_API.md. Архитектура: feature-first, riverpod, dio. Сначала только auth flow с deep link, без UI-полировки.

## 3. Порядок разработки

Правильный порядок для Strava-проекта:

| Шаг | Что просить у агента |
|-----|----------------------|
| 1 | `flutter create` + структура папок (`lib/features/auth`, `lib/core/api`) |
| 2 | API-клиент: `GET /auth/strava/login/?format=json&mobile=1` |
| 3 | Deep link handler: `stravaapp://auth?code=...` → `POST /auth/strava/token/` |
| 4 | Secure storage для access/refresh |
| 5 | Interceptor: auto-refresh через `POST /auth/token/refresh/` |
| 6 | Экран логина + главный экран с данными атлета |
| 7 | UI/анимации |

**Один промпт = одна фича.** После каждого шага — `flutter run` и проверка.

## 4. Как формулировать промпты

**Плохо:**

> Сделай мобильное приложение для Strava

**Хорошо:**

> Добавь `AuthRepository` с методом `startLogin()` — вызывает `GET /api/auth/strava/login/?format=json&mobile=1`, открывает `authorization_url` через `url_launcher`. Следуй MOBILE_API.md, секция Authentication.

**Ещё лучше** — прикрепляйте файлы через `@`:

- `@docs/MOBILE_API.md`
- `@lib/features/auth/auth_repository.dart`

## 5. Цикл разработки в Cursor

```
Промпт → Агент пишет код → flutter analyze → flutter run
         ↑                                    ↓
    «Исправь ошибку X»  ←  скриншот / лог
```

- **Agent mode** — для написания кода
- **Ask mode** — «объясни, почему deep link не срабатывает»
- **Plan mode** — перед большой фичей (например, офлайн-кэш активностей)

Hot reload (`r` в терминале) — проверка UI. Hot restart (`R`) — после изменений в `initState`, providers, routes.

## 6. Flutter-специфика для AI

Агент часто ошибается в:

| Проблема | Что указать в правилах |
|----------|------------------------|
| Deep links | Настроить `AndroidManifest.xml` и `Info.plist` для `stravaapp://auth` |
| iOS vs Android | Сначала Android, iOS deep link отдельным шагом |
| `pubspec.yaml` | После добавления пакета — `flutter pub get` |
| HTTP на Android | `android:usesCleartextTraffic="true"` для dev (пока HTTP) |
| Generated code | `build_runner` для freezed/json_serializable — просить явно |

## 7. Рекомендуемая структура

```
lib/
  core/
    api/          # dio client, interceptors
    config/       # base URL, constants
    router/       # go_router
  features/
    auth/
      data/       # repository, models
      presentation/  # screens, widgets
      providers/  # riverpod
  main.dart
```

Так проще давать точечные задачи: «добавь в `features/auth`», а не «перепиши всё приложение».

## 8. OAuth-поток (StravaApp)

Целевой flow описан в [DEEP_LINK_OAUTH_PLAN.md](./DEEP_LINK_OAUTH_PLAN.md) и [MOBILE_API.md](./MOBILE_API.md):

```
App → GET login?mobile=1 → браузер → Strava → backend callback
    → deep link stravaapp://auth?code=...
    → POST /auth/strava/token/ → сохранить JWT
```

Промпт для первой рабочей версии:

> Реализуй mobile OAuth по DEEP_LINK_OAUTH_PLAN.md и MOBILE_API.md. Deep link: `stravaapp://auth`. Пакеты: app_links, flutter_secure_storage, dio. Минимальный UI: кнопка «Войти через Strava» и экран «Вы вошли».

## 9. Чего избегать

1. **Не просите всё сразу** — получите тысячи строк, которые сложно отладить
2. **Не пропускайте `flutter analyze`** — агент редко сам гоняет линтер
3. **Не меняйте стек посередине** — riverpod → bloc = переписывание
4. **Коммитьте после каждой рабочей фичи** — легко откатиться
5. **Не доверяйте настройке deep link «на глаз»** — главный источник багов

## 10. Практический старт

1. `flutter create stravaapp_mobile` в корне репозитория (или отдельно)
2. Создать `.cursor/rules/flutter.mdc` с выбранным стеком
3. Первый промпт агенту: **только auth + deep link**, без дизайна

## Итог

Вайбкодинг Flutter в Cursor = **документация API в контексте + фиксированный стек в rules + фичи по одной + постоянный `flutter run`**.
