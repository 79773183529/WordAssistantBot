import asyncio
import datetime
import subprocess
import random
import urllib.request

import emoji
import speech_recognition as sr

from aiogram import Dispatcher, types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import ContentType
from aiogram.utils.callback_data import CallbackData

from bot import bot, TOKEN
from with_file import get_list_topic, name_to_src, get_list_ru
from word_start import search_object_in_src

cb = CallbackData("call", "group", "id", "name")


class OrderSearch(StatesGroup):
    waiting_for_file_name = State()
    waiting_for_file = State()
    waiting_for_object = State()
    waiting_for_acknowledgment = State()


# Выводит на экран Inline клавиатуру с вариантами
async def search_start(message: types.Message):
    list_topic = get_list_topic(the_id=message.from_user.id)
    print('list_topic= ', list_topic)
    markup = types.InlineKeyboardMarkup()
    button = []
    list_ru = get_list_ru()
    in_ru = str(message.from_user.id) in list_ru
    for i in range(len(list_topic)):
        button.append(types.InlineKeyboardButton(text=[f'Search in {list_topic[i][: -28]}',
                                                       f'Искать в: {list_topic[i][: -28]}'][in_ru],
                                                 callback_data=cb.new(group='topic',
                                                                      id=message.from_user.id,
                                                                      name=list_topic[i][-27:])
                                                 ))
        print('list_topic[i][-27:]= ', list_topic[i][-27:])
        markup.row(button[i])
    if len(list_topic) > 1:
        button_choice_all = types.InlineKeyboardButton(['Search everywhere', 'Искать везде'][in_ru],
                                                       callback_data=cb.new(group='topic',
                                                                            id=message.from_user.id,
                                                                            name='search_everywhere'))
        markup.row(button_choice_all)

    button_choice_other = types.InlineKeyboardButton(['Upload a new file', 'Загрузить новый файл'][in_ru],
                                                     callback_data=cb.new(group='topic',
                                                                          id=message.from_user.id,
                                                                          name='create_new_topic'))
    markup.row(button_choice_other)
    await message.answer(['Select an option', f'Выберите нужный  вариант '][in_ru], reply_markup=markup)
    await message.answer('..', reply_markup=user_markup_exit)
    await OrderSearch.waiting_for_file_name.set()


# Обрабатывает коллбеки. Обратите внимание: есть второй аргумент
async def search_location_chosen(call: types.CallbackQuery, callback_data: dict, state: FSMContext):
    list_ru = get_list_ru()
    in_ru = str(callback_data["id"]) in list_ru
    if callback_data["name"] == 'create_new_topic':
        await bot.send_message(callback_data["id"],
                               ['Ok. Send me this file',
                                'Хорошо. Пришлите мне этот файл'][in_ru])
        await call.answer()
        await OrderSearch.waiting_for_file.set()
    else:
        list_topic = get_list_topic(the_id=callback_data["id"])
        for topic in list_topic:
            print('if callback_data["name"] = ', callback_data['name'], 'in topic= ', topic)
            if callback_data['name'] in topic:
                print('!!! callback_data["name"] = ', callback_data['name'], 'in topic= ', topic)
                list_topic = [topic]
                print("Я в ife. list_topic=", list_topic)
                break
        list_src_topic = name_to_src(lst=list_topic)
        print('list_src_topic = ', list_src_topic)
        await bot.send_message(callback_data["id"],
                               ['Ok. Now send me what we need to find',
                                'Хорошо. Теперь пришлите мне, что нам нужно найти'][in_ru])
        await state.update_data(list_src=list_src_topic)
        await call.answer()
        await OrderSearch.waiting_for_object.set()


# Принимает новый файл .docx
async def search_set_file(message: types.Message, state: FSMContext):
    list_ru = get_list_ru()
    in_ru = str(message.from_user.id) in list_ru
    if not message.document or '.docx' not in message.document.file_name:
        await message.reply(["The file must be Word.\nTry again",
                             "Файл должен быть Вордовским )..\nПопробуйте ещё раз"][in_ru])
        return
    else:
        try:
            chat_id = message.chat.id
            make_topic_time = datetime.datetime.now() + datetime.timedelta(hours=3)  # Перевод в Московское время
            make_topic_time = make_topic_time.strftime('%Y.%m.%d-%H.%M')

            document_id = message.document.file_id
            file_info = await bot.get_file(document_id)

            fi = file_info.file_path
            name = message.document.file_name
            name = name.replace('.docx.docx', '.docx')
            name = name.replace('._docx', '.docx')
            name = name.replace('. docx.docx', '.docx')
            print('name= ', name)
            src_new = f'Data/User_files/Topics/{chat_id}_{random.randrange(10000)}_{name}'
            src_new = src_new.replace(';', '_')
            src_new = src_new.replace(' ', '_')
            src_new = src_new.replace(',', '_')
            print('src_new= ', src_new)
            urllib.request.urlretrieve(f'https://api.telegram.org/file/bot{TOKEN}/{fi}',
                                       src_new)

            with open('Data/Main_files/table_topics.txt', 'a', encoding='utf-8') as f:
                name_topic = name + '_' + make_topic_time + '_' + '(cod_' + str(random.randrange(10000)) + ')'
                name_topic = name_topic.replace(';', '_')
                name_topic = name_topic.replace(':', '_')
                print(name_topic, message.from_user.id, src_new, True, sep=';', file=f)

            await message.reply(['File saved\nSend me what you want to find in it',
                                 "Файл  успешно сохранён\nПришлите мне, что вы хотите в нём найти"][in_ru])
            await asyncio.sleep(2)
            await message.answer(['And by the way, you do not have to type'
                                  ' - i understand voice messages perfectly',
                                  'Да и кстати вам не обязательно печатать '
                                  '- я прекрасно понимаю голосовые сообщения'][in_ru])
            await state.update_data(list_src=[src_new])
            await OrderSearch.waiting_for_object.set()
        except Exception as e:
            print(e)


# Принимает объект для поиска
async def search_set_object(message: types.voice, state: FSMContext):
    list_ru = get_list_ru()
    in_ru = str(message.from_user.id) in list_ru
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    buttons = [["/menu", "/меню"][in_ru],
               ["/help", "/помощь"][in_ru]]
    keyboard.add(*buttons)
    try:
        document_id = message.voice.file_id
        file_info = await bot.get_file(document_id)
        fi = file_info.file_path

        await message.answer(emoji.emojize(":deaf_woman:"))

        file_name = 'audio.ogg'
        urllib.request.urlretrieve(f'https://api.telegram.org/file/bot{TOKEN}/{fi}',
                                   file_name)

        process = subprocess.run(['ffmpeg', '-i', 'audio.ogg', 'audio.wav', '-y'])
        file = sr.AudioFile('audio.wav')
        with file as source:
            audio = r.record(source)
            text = r.recognize_google(audio, language=['en-US', 'ru-RU'][in_ru])
            print('voice_to_text return: ', text)

        markup = types.InlineKeyboardMarkup()
        button_yes = types.InlineKeyboardButton(['That is right. Continue', 'Всё верно. Продолжить'][in_ru],
                                                callback_data=cb.new(group='acknowledgment',
                                                                     id=message.from_user.id,
                                                                     name='yes'))
        markup.row(button_yes)
        button_no = types.InlineKeyboardButton(['No. Repeat input', 'Нет. Повторить ввод'][in_ru],
                                               callback_data=cb.new(group='acknowledgment',
                                                                    id=message.from_user.id,
                                                                    name='no'))
        markup.row(button_no)
        await message.answer([f'Did I understand you correctly?\n We are looking for: "{text}"',
                              f'Я вас правильно поняла?\n Мы ищем: "{text}"'][in_ru],
                             reply_markup=markup)

        await message.answer('..', reply_markup=user_markup_exit)
        await state.update_data(the_object=text)
        await OrderSearch.waiting_for_acknowledgment.set()
    except Exception as e:
        print(e)
        print('message.text= ', message.text)
        await state.update_data(the_object=message.text)
        user_data = await state.get_data()
        the_object = user_data['the_object']
        list_src = user_data['list_src']
        result = False
        for src in list_src:
            list_data = search_object_in_src(the_object, src)
            await message.answer(emoji.emojize(":woman_technologist:"))
            if list_data:
                result = True
            counter, counter2 = 0, 0
            for data in list_data:
                await message.answer(data, parse_mode=types.ParseMode.HTML)
                counter += 1
                counter2 += 1
                if counter == 10:
                    counter = 0
                    await message.answer(emoji.emojize(":woman_technologist:"))
                    await asyncio.sleep(3)
                if counter2 == 100:
                    await message.answer(emoji.emojize(":old_woman:"))
                    counter2 = 0
                    await asyncio.sleep(8)
        await message.answer('..', reply_markup=keyboard)
        if not result:
            await message.answer(emoji.emojize(":woman_shrugging:"))
            await message.answer(['Nothing found', 'Ничего не найдено'][in_ru])
        await message.answer(emoji.emojize(":woman_office_worker:"))
        await message.answer(
                               ['You can try again or press  <b>/cancel</b>  to exit',
                                'Вы можете повторить попытку или нажать  <b>/cancel</b>  для выхода'][in_ru],
                               parse_mode=types.ParseMode.HTML,
                               reply_markup=user_markup_exit
        )
        await OrderSearch.waiting_for_object.set()


# Обрабатывает коллбеки - подтверждения после обработки голосового сообщения
async def set_acknowledgment(call: types.CallbackQuery, callback_data: dict, state: FSMContext):
    list_ru = get_list_ru()
    in_ru = str(callback_data["id"]) in list_ru
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    buttons = [["/menu", "/меню"][in_ru],
               ["/help", "/помощь"][in_ru]]
    keyboard.add(*buttons)
    if callback_data["name"] == 'no':
        await bot.send_message(callback_data["id"],
                               [f'{emoji.emojize(":woman_shrugging:")}  Well, it happens. '
                                f'Send me your search text again',
                                emoji.emojize(":woman_shrugging:") + '  Что ж такое бывает. '
                                                                     'Пришлите мне ваш текст для'
                                                                     ' поиска ещё раз'][in_ru])
        await call.answer()
        await bot.send_message(callback_data["id"], '..', reply_markup=user_markup_exit)
        await OrderSearch.waiting_for_object.set()
    elif callback_data["name"] == 'yes':
        user_data = await state.get_data()
        the_object = user_data['the_object']
        list_src = user_data['list_src']
        result = False
        for src in list_src:
            list_data = search_object_in_src(the_object, src)
            if list_data:
                await bot.send_message(callback_data["id"], emoji.emojize(":woman_technologist:"))
                result = True
            counter, counter2 = 0, 0
            for data in list_data:
                await bot.send_message(callback_data["id"], data, parse_mode=types.ParseMode.HTML)
                counter += 1
                counter2 += 1
                if counter == 10:
                    counter = 0
                    await asyncio.sleep(3)
                if counter2 == 100:
                    counter2 = 0
                    await asyncio.sleep(8)
        await bot.send_message(callback_data["id"], '..', reply_markup=keyboard)
        await call.answer()
        if not result:
            await bot.send_message(callback_data["id"], emoji.emojize(":woman_shrugging:"))
            await bot.send_message(callback_data["id"], ['Nothing found', 'Ничего не найдено'][in_ru])
        await bot.send_message(callback_data["id"], emoji.emojize(":woman_office_worker:"))
        await bot.send_message(callback_data["id"],
                               ['You can try again or press  <b>/cancel</b>  to exit',
                                'Вы можете повторить попытку или нажать  <b>/cancel</b>  для выхода'][in_ru],
                               parse_mode=types.ParseMode.HTML,
                               reply_markup=user_markup_exit)
        await call.answer()
        await OrderSearch.waiting_for_object.set()


def register_handlers_search(dp: Dispatcher):
    dp.register_message_handler(search_start, commands="searchdata", state="*")
    dp.register_callback_query_handler(search_location_chosen,
                                       cb.filter(group=['topic']),
                                       state=OrderSearch.waiting_for_file_name)
    dp.register_message_handler(search_set_file,
                                content_types=['document'],
                                state=OrderSearch.waiting_for_file)
    dp.register_message_handler(search_set_object,
                                content_types=[ContentType.VOICE, ContentType.TEXT],
                                state=OrderSearch.waiting_for_object)
    dp.register_callback_query_handler(set_acknowledgment,
                                       cb.filter(group=['acknowledgment']),
                                       state=OrderSearch.waiting_for_acknowledgment)


user_markup_exit = types.ReplyKeyboardMarkup(resize_keyboard=True)
user_markup_exit.row('/cancel')

r = sr.Recognizer()
