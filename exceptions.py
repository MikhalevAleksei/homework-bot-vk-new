"""Исключения бота-ассистента."""


class MissingTokensError(Exception):
    """Не заданы обязательные переменные окружения."""


class EndpointStatusError(Exception):
    """API Практикум Домашки вернул код ответа, отличный от 200."""


class MissingKeyError(KeyError):
    """В ответе API или в данных о домашней работе нет нужного ключа."""


class UnknownStatusError(ValueError):
    """API вернул недокументированный статус домашней работы."""
