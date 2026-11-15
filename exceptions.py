"""Исключения бота-ассистента."""


class EndpointRequestError(Exception):
    """Запрос к API Практикум Домашки не удался."""


class EndpointStatusError(Exception):
    """API Практикум Домашки вернул код ответа, отличный от 200."""


class MissingKeyError(KeyError):
    """В ответе API или в данных о домашней работе нет нужного ключа."""

    def __str__(self):
        """Возвращает текст ошибки без кавычек, которые добавляет KeyError."""
        return str(self.args[0]) if self.args else ''


class UnknownStatusError(ValueError):
    """API вернул недокументированный статус домашней работы."""
