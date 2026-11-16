import logging
import os
import sys
import time
from http import HTTPStatus

import requests
import vk_api
from dotenv import load_dotenv
from vk_api.utils import get_random_id

from exceptions import (
    EndpointStatusError,
    MissingKeyError,
    MissingTokensError,
    UnknownStatusError,
)

load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
VK_TOKEN = os.getenv('VK_TOKEN')
VK_USER_ID = os.getenv('VK_USER_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logger = logging.getLogger(__name__)


def check_tokens():
    """Проверяет, что заданы все обязательные переменные окружения."""
    tokens = (
        ('PRACTICUM_TOKEN', PRACTICUM_TOKEN),
        ('VK_TOKEN', VK_TOKEN),
        ('VK_USER_ID', VK_USER_ID),
    )
    missing_tokens = []
    for name, token in tokens:
        if not token:
            logger.critical(
                f'Отсутствует обязательная переменная окружения: {name}'
            )
            missing_tokens.append(name)
    if missing_tokens:
        raise MissingTokensError(
            'Отсутствуют обязательные переменные окружения: '
            f'{", ".join(missing_tokens)}. '
            'Программа принудительно остановлена.'
        )


def send_message(vk, message):
    """Отправляет сообщение в VK и сообщает, удалось ли это сделать."""
    try:
        vk.messages.send(
            user_id=VK_USER_ID,
            message=message,
            random_id=get_random_id(),
        )
    except Exception as error:
        # VK может ответить ошибкой API или оборвать соединение:
        # бот не должен падать из-за неудачной отправки.
        logger.error(f'Сбой при отправке сообщения в VK: {error}')
        return False
    logger.debug(f'Бот отправил сообщение "{message}"')
    return True


def get_api_answer(timestamp):
    """Запрашивает статусы домашних работ, изменившиеся после timestamp."""
    request_params = {
        'url': ENDPOINT,
        'headers': HEADERS,
        'params': {'from_date': timestamp},
    }
    logger.debug(
        'Запрос к {url} с параметрами {params}'.format(**request_params)
    )
    try:
        response = requests.get(**request_params)
    except requests.RequestException as error:
        raise ConnectionError(
            'Сбой при запросе к {url} с параметрами {params}: {error}'.format(
                error=error, **request_params
            )
        ) from error
    if response.status_code != HTTPStatus.OK:
        raise EndpointStatusError(
            f'Эндпоинт {ENDPOINT} недоступен. '
            f'Код ответа API: {response.status_code}, '
            f'причина: {response.reason}, текст: {response.text}'
        )
    return response.json()


def check_response(response):
    """Проверяет ответ API и возвращает список домашних работ."""
    if not isinstance(response, dict):
        raise TypeError(
            f'Ответ API должен быть словарём, получен {type(response)}'
        )
    if 'homeworks' not in response:
        raise MissingKeyError('В ответе API нет ключа homeworks')
    homeworks = response['homeworks']
    if not isinstance(homeworks, list):
        raise TypeError(
            'Под ключом homeworks должен быть список, получен '
            f'{type(homeworks)}'
        )
    return homeworks


def parse_status(homework):
    """Готовит сообщение о статусе одной домашней работы."""
    if 'homework_name' not in homework:
        raise MissingKeyError(
            'В данных о домашней работе нет ключа homework_name'
        )
    status = homework.get('status')
    if status not in HOMEWORK_VERDICTS:
        raise UnknownStatusError(
            f'Неожиданный статус домашней работы: {status}'
        )
    homework_name = homework['homework_name']
    verdict = HOMEWORK_VERDICTS[status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    check_tokens()

    vk_session = vk_api.VkApi(token=VK_TOKEN)
    vk = vk_session.get_api()
    timestamp = int(time.time())
    last_message = ''

    while True:
        try:
            response = get_api_answer(timestamp)
            homeworks = check_response(response)
            if not homeworks:
                logger.debug('Новых статусов в ответе API нет')
                continue
            message = parse_status(homeworks[0])
            if message != last_message and send_message(vk, message):
                last_message = message
                timestamp = response.get('current_date', timestamp)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)
            if message != last_message and send_message(vk, message):
                last_message = message
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s [%(levelname)s] %(funcName)s:%(lineno)d '
               '%(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(__file__ + '.log', encoding='utf-8'),
        ],
    )
    main()
