import telebot
# Запуск запланированных задач
import schedule
# Создание потоков
from threading import Thread
# Токен для бота
from TgToken import TOKEN
# Работа с sqlite и курсором
from Gibbon_sqlite import timers, create_connection, execute_query, execute_read_query
# Доп утилиты для расписания, тг панели, отправки файлов и прав доступа
from utils.sched import *
from utils.kb import *
from utils.send_file import *
from utils.check import *

import re


bot = telebot.TeleBot(TOKEN)
count_sched = 1
answCommand = ["📄 Документ", "⏱ Таймер", "🗓 Список расписаний", "⌛ Стоп"]


@bot.message_handler(commands=['sendGroup'],func=check_admin)
def stepSendMsg(message):
    msg = bot.send_message(message.chat.id, "Напишите id группы")
    bot.register_next_step_handler(msg, idMsg)

def idMsg(message):
    msg = bot.send_message(message.chat.id, "Напишите сообщение")
    bot.register_next_step_handler(msg, sendMsg, message.text)

def sendMsg(message, id):
    bot.send_message(id, message.text)


@bot.message_handler(content_types=["text"],func=check_user)
def start(message):
    bot.send_message(message.chat.id, message.text)


@bot.message_handler(commands=['start'],func=check_admin)
def welcome(message):
    for tm in timers:
        if f"Расписание {tm[2]}" not in answCommand:
            timer_sched(tm[1], tm[2], send_f, bot, message.chat.id)
            answCommand.append(f"Расписание {tm[2]}")

    mark = keyboard(answCommand[:3])

    bot.send_message(message.chat.id, "Choose one letter:", reply_markup=mark)


@bot.message_handler(content_types=["text"],func=check_admin)
def start(message):
    if message.text == answCommand[0]:
        doc = open('Files/CW14.pdf', 'rb')

        wait = bot.send_message(message.chat.id, 'Ожидайте...')

        bot.send_document(message.chat.id, doc)
        bot.delete_message(message.chat.id, wait.message_id)

    elif message.text == answCommand[1]:
        mesg = bot.send_message(message.chat.id,'Придумайте название для расписания')
        bot.register_next_step_handler(mesg, nameTimer)

    elif message.text == answCommand[2]:
        mark = keyboard(answCommand[1:2] + answCommand[3:])
        bot.send_message(message.chat.id, "Ваш список", reply_markup=mark)

    elif message.text == answCommand[3]:
        if answCommand[4:]:
            for i in answCommand[4:]:
                answCommand.remove(i)

        mark = keyboard(answCommand[:3])
        schedule.clear()
        bot.send_message(message.chat.id, "Таймер выключился", reply_markup=mark)

    elif re.search(r"^Расписание", message.text):
        selectSched = f'''
        SELECT
            schedule
        FROM
            Timer
         WHERE
            name='{message.text.split()[1]}'
        '''

        timer = execute_read_query(selectSched)

        markup = keyboard([f"❌ Расписание {message.text[11:]}", f"Поменять имя Расписание {message.text[11:]}", f"Поменять дату Расписание {message.text[11:]}"])
        bot.send_message(message.chat.id, f"Дата: {timer[0][0]}")
        bot.send_message(message.chat.id, "Выбирите команду:", reply_markup=markup)

    elif re.search(r"^❌ Расписание", message.text):
        deleteSched =f'''
        DELETE FROM
            Timer
        WHERE
            name='{message.text[13:]}'
        '''

        try:
            if not len(schedule.get_jobs()):
                markup = keyboard(answCommand[:3])
            elif len(schedule.get_jobs()) == 1:
                markup = keyboard(answCommand[:3])
                answCommand.remove(f"Расписание {message.text[13:]}")

                execute_query(deleteSched)

                schedule.clear(f"timer{message.text[13:]}")
            else:
                answCommand.remove(f"Расписание {message.text[13:]}")
                markup = keyboard(answCommand[1:2] + answCommand[3:])

                execute_query(deleteSched)

                schedule.clear(f"timer{message.text[13:]}")

            bot.send_message(message.chat.id, f"Расписание {message.text[13:]} удалили", reply_markup=markup)

        except Exception:
            bot.send_message(message.chat.id, f"Расписание {message.text[13:]} не существует")


    elif re.search(r"^Поменять имя Расписание", message.text):
        msg = bot.send_message(message.chat.id, "Придумайте новое имя")
        bot.register_next_step_handler(msg, changeSched, message.text[24:], "name")


    elif re.search(r"^Поменять дату Расписание", message.text):
        msg = bot.send_message(message.chat.id, "Придумайте новую дату")
        bot.register_next_step_handler(msg, changeSched, message.text[25:], "schedule")


    else:
        bot.send_message(message.chat.id, "🙈")
        bot.send_message(message.from_user.id, 'Команды: /start')
        bot.send_message(message.from_user.id, 'Sms в группу: /sendGroup')


def changeSched(message, name, field):
    schedule.clear(f"timer{name}")

    if field == 'name':
        answCommand[answCommand.index(f'Расписание {name}')] = f'Расписание {message.text}'

        selectSched = f'''
        SELECT
            *
        FROM
            Timer
         WHERE
            name='{name}'
        '''

        sched = execute_read_query(selectSched)

        timer_sched(sched[0][1], message.text, send_f, bot, message.chat.id)
    else:
        timer_sched(message.text, name, send_f, bot, message.chat.id)

    markup = keyboard(answCommand[1:2] + answCommand[3:])

    changeNameSched = f'''
         UPDATE
            Timer
         SET
            {field}='{message.text}'
         WHERE
            name='{name}'
        '''

    execute_query(changeNameSched)

    bot.send_message(message.chat.id, f"Записали", reply_markup=markup)


def nameTimer(message):
        mesg = bot.send_message(message.chat.id,'Напишите расписание format: ДН/ДН ЧЧ:MM/ЧЧ:MM exmp. вт/пт 02:05/05:00')
        bot.register_next_step_handler(mesg, stepTimer, message.text)


def stepTimer(message, name):
    markup = keyboard(answCommand[1:2] + answCommand[3:])

    createSched = f'''
    INSERT INTO
        Timer (schedule, name)
    VALUES
        ('{message.text}', '{name}')'''

    if re.search(r"^([а-яА-Я]{2}/?)+\s(\d{2}:\d{2}/?)+$", message.text):
        answCommand.insert(4, f"Расписание {name}")
        execute_query(createSched)

        timer_sched(message.text, name, send_f, bot, message.chat.id)

        bot.send_message(message.chat.id, f"Записали новое расписание", reply_markup=markup)
    else:
        bot.send_message(message.chat.id, f"🚫 Неверная дата", reply_markup=markup)


if __name__ == "__main__":
    test = Thread(target=schedule_checker)
    test.daemon = True
    test.start()

    print("TgBot started")

    bot.polling(none_stop=True, interval=0)