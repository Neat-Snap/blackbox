import os
from PIL import Image
from io import BytesIO
import requests
import datetime
import telebot
import time
import csv
from telebot import types
from config import bot_key, admins, request_url

filepath = ''

import fal_client

def close(e):
    print(f'Ошибка в функции: {e}')


# функции по нейронке

def url_to_image(url, retries=3):
    try:
        for _ in range(retries):
            try:
                response = requests.get(url, timeout=60)
                response.raise_for_status()
                img_data = BytesIO(response.content)
                img = Image.open(img_data)
                return img
            except requests.exceptions.RequestException as e:
                print(f"Request failed: {e}")
                time.sleep(2)  # Wait before retrying
            return 'Ошибка'
    except Exception as e:
        close(e)
        return


def request_to_ip(prompt):
    try:
        handler = fal_client.submit(
            request_url,
            arguments={
                "prompt": prompt
            },
        )
        result = handler.get()
        print(f"Request result: {result}")
        image_url = result['images'][0]['url']
        return image_url
    except Exception as e:
        close(e)
        return


def save_image(prompt):
    try:
        global filepath
        image_url = request_to_ip(prompt)
        image = url_to_image(image_url)
        if image == 'Ошибка':
            filepath = 'Ошибка'
        if not os.path.exists('images'):
            os.makedirs('images')
        filepath = f'images/{datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.jpg'
        image.save(filepath)
        print(f"Image saved to {filepath}")
    except Exception as e:
        close(e)
        return


# создание бд или запись бд в локальный список

local_user_list = []
file_exists = os.path.isfile('users.csv')
if not file_exists:
    with open('users.csv', 'a', newline='') as csvfile:
        writer = csv.writer(csvfile, dialect='excel')
        writer.writerow(['user_id', 'time_registred'])

else:
    with open('users.csv') as f:
        csv_reader = csv.reader(f)
        next(csv_reader, None)
        for user in csv_reader:
            if len(user) > 0:
                local_user_list.append(user[0])

# функции по боту

bot = telebot.TeleBot(bot_key)


@bot.message_handler(commands=['start'])
def start_handler(message):
    global local_user_list
    try:
        if str(message.chat.id) not in local_user_list:
            add_user(message.chat.id)

        response_text = (
            '👋 Привет! \n\nЧтобы сгенерировать изображение, напишите свой промпт на английском языке прямо в чат.\n\n'
            'Пример: <i>Extreme close-up of a single tiger eye with detailed texture and the word "BlackLab" painted in white.</i>\n\n'
            'После отправки промпта я сгенерирую изображение и отправлю его вам.'
        )
        bot.send_message(message.chat.id, response_text, parse_mode="HTML")
    except Exception as e:
        close(e)
        return


@bot.message_handler(commands=['help'])
def help_handler(message):
    try:
        response_text = (
            'Команда /help предоставляет инструкции по написанию промптов для генерации изображений. Вот несколько рекомендаций: \n\n'

            '<b>1. Будьте конкретными</b>: Чем более детально вы опишете изображение, тем лучше результат. Например, вместо "тiger", напишите <i>Extreme close-up of a single tiger eye with detailed texture</i>. \n\n'

            '<b>2. Указывайте ключевые детали</b>: Опишите важные элементы, которые должны быть включены, такие как освещение, цвета и текстуры. Например, <i>natural lighting to capture eye shine</i>. \n\n'

            '<b>3. Используйте ясный язык</b>: Пишите простым и понятным языком, избегая многозначных слов. Это поможет системе точнее интерпретировать ваш запрос. \n\n'

            '<b>4. Проверяйте орфографию</b>: Ошибки в тексте могут привести к неверной интерпретации вашего промпта. \n\n'

            'Пример хорошо составленного промпта: <i>Extreme close-up of a single tiger eye, direct frontal view. Detailed iris and pupil with sharp focus on eye texture and color. The word "BlackBox" painted over it in big, white brush strokes with visible texture.</i>'

        )
        bot.send_message(message.chat.id, response_text, parse_mode='HTML')
    except Exception as e:
        close(e)
        return


@bot.callback_query_handler(func=lambda x: True)
def button_handler(call):
    if call.data == 'без сжатия':
        try:
            with open(filepath, 'rb') as f:
                bot.send_document(call.message.chat.id, f)
        except Exception as e:
            bot.send_message(call.message.chat.id, 'Произошла ошибка, повторите запрос')
            print(f'Ошибка при отправке файла без сжатия: {e}')


@bot.message_handler(func=lambda x: True)
def generic_handler(message):
    global filepath
    try:
        if message.text.startswith('/broadcast'):
            if str(message.from_user.id) in admins:
                broadcast_text = message.text[11:].strip()
                if broadcast_text:
                    send_to_all(broadcast_text)
                    bot.send_message(message.chat.id, 'Отправлено всем')
            else:
                bot.send_message(message.chat.id, 'У вас нет доступа к этой команде')
                for admin_id in admins:
                    bot.send_message(admin_id,
                                     f'Кто то пытался использовать команду broadcast. \nid = {message.from_user.id}. Username = @{message.from_user.username}')
        else:
            if filepath != 'Ошибка':
                bot.send_message(message.chat.id,
                                 'Запрос на генерацию принят, ждите. \nИз-за высокой нагрузки примерное время генерации составляет: 2 минуты')
                save_image(message.text)

                # keyboard = types.InlineKeyboardMarkup(row_width=1)
                # request_file_button = types.InlineKeyboardButton('📎 Запросить файл без сжатия', callback_data='без сжатия')
                # keyboard.add(request_file_button)

                with open(filepath, 'rb') as f:
                    bot.send_photo(message.chat.id, f)
                    # f.seek(0)
                    # bot.send_document(message.chat.id, f, caption='Это оригинал фото в высоком качестве')

            else:
                bot.send_message(message.chat.id,
                                 'Не получилось сгенерировать изображение по вашему запросу (\nПопробуйте еще раз через пару минут')
    except Exception as e:
        bot.send_message(message.chat.id, 'Не удалось сгенерировать фото. Повторите свой запрос')
        close(e)
        return


def add_user(user_id):
    global local_user_list
    try:
        with open('users.csv', 'a', newline='') as csvfile:
            writer = csv.writer(csvfile, dialect='excel')
            writer.writerow([user_id, datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")])
            local_user_list.append(user_id)
    except Exception as e:
        close(e)
        return


def send_to_all(message):
    try:
        with open('users.csv') as f:
            csv_reader = csv.reader(f)
            for user in csv_reader:
                try:
                    bot.send_message(user[0], message)
                except Exception as e:
                    print(f'Ошибка при отправке сообщения пользователю {user[0]}: {e}')
    except Exception as e:
        close(e)
        return


bot.polling(none_stop=True)
