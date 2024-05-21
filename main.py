import logging
import telebot
import os
import openai
import json
import boto3
import time
import multiprocessing
import base64
from telebot import types
from telebot.types import InputFile

TG_BOT_TOKEN = os.environ.get("TG_BOT_TOKEN")
PROXY_API_KEY = os.environ.get("PROXY_API_KEY")
YANDEX_KEY_ID = os.environ.get("YANDEX_KEY_ID")
YANDEX_KEY_SECRET = os.environ.get("YANDEX_KEY_SECRET")
YANDEX_BUCKET = os.environ.get("YANDEX_BUCKET")


logger = telebot.logger
telebot.logger.setLevel(logging.INFO)

bot = telebot.TeleBot(TG_BOT_TOKEN, threaded=False)

client = openai.Client(
    api_key=PROXY_API_KEY,
    base_url="https://api.proxyapi.ru/openai/v1",
)


def get_s3_client():
    session = boto3.session.Session(
        aws_access_key_id=YANDEX_KEY_ID, aws_secret_access_key=YANDEX_KEY_SECRET
    )
    return session.client(
        service_name="s3", endpoint_url="https://storage.yandexcloud.net"
    )


def typing(chat_id):
    while True:
        bot.send_chat_action(chat_id, "typing")
        time.sleep(5)


keyboard = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
button1 = types.KeyboardButton(text="Каковы условия доставки?")
button2 = types.KeyboardButton(text="Каковы ваши варианты оплаты?")
button3 = types.KeyboardButton(text="Есть ли гарантия на ваши товары?")
button4 = types.KeyboardButton(text="Могу ли я вернуть или обменять товар, если он мне не подошел?")
button5 = types.KeyboardButton(text="Какая разница между вашими моделями X и Y?")
button6 = types.KeyboardButton(text="Предоставляются ли дополнительные аксессуары к товарам?")
keyboard.add(button1, button2, button3, button4, button5, button6)


@bot.message_handler(commands=["start"])
def send_welcome(message):
    bot.send_message(message.chat.id, "Здравствуйте, я консультант сайта ... .com, тут вы можете получить ответ на часто задаваемы вопросы, а также получить консультацию от ИИ помощника. Для получения полного функционала бота нажмите /help. ", reply_markup=keyboard)
    

@bot.message_handler(commands=["start"])
def send_help(message):
    bot.send_message(message.chat.id, "Я имею набор кнопок  с часто задаваемыми вопросами. Если вы напишите вопрос, который не предоставлен в кнопках, то он будет адресован ИИ-помощнику. ИИ-помощник запоминает историю чата и отвечает в контексте предыдущих сообщений. Его можно спросить о чём угодно. Я умею отвечать на изображения и текстовые сообщения. Также существует команда /new, которая очищает историю сообщений.", reply_markup=keyboard)

@bot.message_handler(commands=["new"])
def clear_history(message):
    clear_history_for_chat(message.chat.id)
    bot.reply_to(message, "История чата очищена!")

@bot.message_handler(func=lambda message: message.text in ["Каковы условия доставки?", "Каковы ваши варианты оплаты?", "Есть ли гарантия на ваши товары?", "Могу ли я вернуть или обменять товар, если он мне не подошел?", "Какая разница между вашими моделями X и Y?", "Предоставляются ли дополнительные аксессуары к товарам?"])
def handle_buttons(message):
    if message.text == "Каковы условия доставки?":
        bot.send_message(message.chat.id, "Мы предлагаем бесплатную доставку на большинство наших товаров. Срок доставки варьируется в зависимости от вашего местоположения. Обычно это занимает от 2 до 7 рабочих дней.", reply_markup=keyboard)
    elif message.text == "Каковы ваши варианты оплаты?":
        bot.send_message(message.chat.id, "Мы принимаем оплату кредитными картами, банковскими переводами и через платежные системы, такие как PayPal. Для вашего удобства мы также предлагаем оплату при получении (наложенным платежом).", reply_markup=keyboard)
    elif message.text == "Есть ли гарантия на ваши товары?":
        bot.send_message(message.chat.id, "Да, все наши товары поставляются с гарантией производителя. Длительность гарантии зависит от конкретного товара и указывается на странице товара. Мы также предлагаем расширенные гарантийные планы для дополнительного покрытия.", reply_markup=keyboard)
    elif message.text == "Могу ли я вернуть или обменять товар, если он мне не подошел?":
        bot.send_message(message.chat.id, "Да, мы предоставляем возможность возврата или обмена товара в течение определенного периода после покупки. Условия возврата и обмена указаны в нашей политике возврата товаров.", reply_markup=keyboard)
    elif message.text == "Какая разница между вашими моделями X и Y?":
        bot.send_message(message.chat.id, "Модели X и Y имеют некоторые различия в функциональности и характеристиках. Мы рекомендуем ознакомиться с подробными спецификациями каждой модели на соответствующих страницах товаров.", reply_markup=keyboard)
    elif message.text == "Предоставляются ли дополнительные аксессуары к товарам?":
        bot.send_message(message.chat.id, "В большинстве случаев наши товары поставляются с основными аксессуарами, необходимыми для работы. Однако некоторые дополнительные аксессуары могут быть приобретены отдельно.", reply_markup=keyboard)

@bot.message_handler(func=lambda message: True, content_types=["text", "photo"])
def echo_message(message):
    typing_process = multiprocessing.Process(target=typing, args=(message.chat.id,))
    typing_process.start()

    try:
        text = message.text
        image_content = None

        photo = message.photo
        if photo is not None:
            photo = photo[0]
            file_info = bot.get_file(photo.file_id)
            image_content = bot.download_file(file_info.file_path)
            text = message.caption
            if text is None or len(text) == 0:
                text = "Что на картинке?"

        ai_response = process_text_message(text, message.chat.id, image_content)
    except Exception as e:
        bot.reply_to(message, f"Произошла ошибка, попробуйте позже! {e}")
        return

    typing_process.terminate()
    bot.reply_to(message, ai_response)


def process_text_message(text, chat_id, image_content=None) -> str:
    model = "gpt-3.5-turbo"
    max_tokens = None

    # read current chat history
    s3client = get_s3_client()
    history = []
    try:
        history_object_response = s3client.get_object(
            Bucket=YANDEX_BUCKET, Key=f"{chat_id}.json"
        )
        history = json.loads(history_object_response["Body"].read())
    except:
        pass

    history_text_only = history.copy()
    history_text_only.append({"role": "user", "content": text})

    if image_content is not None:
        model = "gpt-4-vision-preview"
        max_tokens = 4000
        base64_image_content = base64.b64encode(image_content).decode("utf-8")
        base64_image_content = f"data:image/jpeg;base64,{base64_image_content}"
        history.append(
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": text},
                    {"type": "image_url", "image_url": {"url": base64_image_content}},
                ],
            }
        )
    else:
        history.append({"role": "user", "content": text})

    try:
        chat_completion = client.chat.completions.create(
            model=model, messages=history, max_tokens=max_tokens
        )
    except Exception as e:
        if type(e).__name__ == "InvalidRequestError":
            clear_history_for_chat(chat_id)
            return process_text_message(text, chat_id)
        else:
            raise e

    ai_response = chat_completion.choices[0].message.content
    history_text_only.append({"role": "assistant", "content": ai_response})

    # save current chat history
    s3client.put_object(
        Bucket=YANDEX_BUCKET,
        Key=f"{chat_id}.json",
        Body=json.dumps(history_text_only),
    )

    return ai_response

def clear_history_for_chat(chat_id):
    try:
        s3client = get_s3_client()
        s3client.put_object(
            Bucket=YANDEX_BUCKET,
            Key=f"{chat_id}.json",
            Body=json.dumps([]),
        )
    except:
        pass


def handler(event, context):
    message = json.loads(event["body"])
    update = telebot.types.Update.de_json(message)

    if (
        update.message is not None
    ):
        bot.process_new_updates([update])

    return {
        "statusCode": 200,
        "body": "ok",
    }