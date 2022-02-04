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
from search_data import user_markup_exit
from with_file import get_list_topic, name_to_src, get_list_ru
from word_start import fill_pattern

cb = CallbackData("call", "group", "id", "name")


class OrderSearch(StatesGroup):
    waiting_for_file_name_pattern = State()
    waiting_for_file_pattern = State()
    waiting_for_text = State()
    waiting_for_acknowledgment_fill = State()


# Выводит на экран Inline клавиатуру с вариантами
async def fill_start(message: types.Message):
    list_pattern = get_list_topic(the_id=message.from_user.id, src='Data/Main_files/table_patterns.txt')
    markup = types.InlineKeyboardMarkup()
    button = []
    list_ru = get_list_ru()
    in_ru = str(message.from_user.id) in list_ru
    for i in range(len(list_pattern)):
        button.append(types.InlineKeyboardButton(text=[f'Fill: {list_pattern[i][: -28]}',
                                                       f'Заполнить: {list_pattern[i][: -28]}'][in_ru],
                                                 callback_data=cb.new(group='pattern',
                                                                      id=message.from_user.id,
                                                                      name=list_pattern[i][-27:])
                                                 ))
        markup.row(button[i])

    button_choice_other = types.InlineKeyboardButton(['Upload a new file', 'Загрузить новый файл'][in_ru],
                                                     callback_data=cb.new(group='pattern',
                                                                          id=message.from_user.id,
                                                                          name='create_new_pattern'))
    markup.row(button_choice_other)
    await message.answer(['Select an option', 'Выберите нужный  вариант'][in_ru], reply_markup=markup)
    await message.answer('..', reply_markup=user_markup_exit)
    await OrderSearch.waiting_for_file_name_pattern.set()


# Обрабатывает коллбеки. Обратите внимание: есть второй аргумент
async def fill_location_chosen(call: types.CallbackQuery, callback_data: dict, state: FSMContext):
    list_ru = get_list_ru()
    in_ru = str(callback_data["id"]) in list_ru
    if callback_data["name"] == 'create_new_pattern':
        await bot.send_message(callback_data["id"],
                               ['Ok. Send me this file',
                                'Хорошо. Пришлите мне этот файл'][in_ru])
        await call.answer()
        await OrderSearch.waiting_for_file_pattern.set()
    else:
        list_pattern = get_list_topic(the_id=callback_data["id"], src='Data/Main_files/table_patterns.txt')
        for pattern in list_pattern:
            print('if callback_data["name"] = ', callback_data['name'], 'in topic= ', pattern)
            if callback_data['name'] in pattern:
                print('!!! callback_data["name"] = ', callback_data['name'], 'in topic= ', pattern)
                list_pattern = [pattern]
                break
        list_src_pattern = name_to_src(lst=list_pattern, src='Data/Main_files/table_patterns.txt')
        await bot.send_message(callback_data["id"],
                               ['Now send me the text to fill in',
                                "Теперь пришлите мне текст для заполнения"][in_ru]
                               )
        await state.update_data(list_src=list_src_pattern)
        await call.answer()
        await OrderSearch.waiting_for_text.set()


# Принимает новый файл .docx
async def fill_set_file(message: types.Message, state: FSMContext):
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
            src_new = f'Data/User_files/Patterns/{chat_id}_{random.randrange(10000)}_{name}'
            src_new = src_new.replace(';', '_')
            src_new = src_new.replace(' ', '_')
            src_new = src_new.replace(',', '_')
            print('src_new= ', src_new)
            urllib.request.urlretrieve(f'https://api.telegram.org/file/bot{TOKEN}/{fi}',
                                       src_new)

            with open('Data/Main_files/table_patterns.txt', 'a', encoding='utf-8') as f:
                name_topic = name + '_' + make_topic_time + '_' + '(cod_' + str(random.randrange(10000)) + ')'
                name_topic = name_topic.replace(';', '_')
                name_topic = name_topic.replace(':', '_')
                print(name_topic, message.from_user.id, src_new, True, sep=';', file=f)

            await message.reply(['File saved\nSend me the text to fill in',
                                 "Файл  успешно сохранён\nПришлите мне, текст для заполнения"][in_ru])
            await asyncio.sleep(2)
            await message.answer(['And by the way, you do not have to type'
                                  ' - i understand voice messages perfectly',
                                  'Да и кстати вам не обязательно печатать '
                                  '- я прекрасно понимаю голосовые сообщения'][in_ru])
            await state.update_data(list_src=[src_new])
            await OrderSearch.waiting_for_text.set()
        except Exception as e:
            print(e)


# Принимает объект для поиска
async def fill_set_text(message: types.voice, state: FSMContext):
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
        await message.answer([f'Did I understand you correctly?\n You said: "{text}"',
                              f'Я вас правильно поняла?\n Вы сказали: "{text}"'][in_ru],
                             reply_markup=markup)

        await message.answer('..', reply_markup=user_markup_exit)
        await state.update_data(the_object=text)
        await OrderSearch.waiting_for_acknowledgment_fill.set()
    except Exception as e:
        await message.answer(emoji.emojize(":woman_technologist:"))
        await state.update_data(the_object=message.text)
        user_data = await state.get_data()
        the_object = user_data['the_object']
        list_src = user_data['list_src']
        src_filled_pattern = fill_pattern(list_src, the_object)
        the_doc = open(src_filled_pattern, 'rb')
        await message.answer(['Done\nHere is your file',
                              'Готово\nВот ваш файл'][in_ru])
        await bot.send_document(message.from_user.id, the_doc, reply_markup=keyboard)


# Обрабатывает коллбеки - подтверждения после обработки голосового сообщения
async def set_acknowledgment(call: types.CallbackQuery, callback_data: dict, state: FSMContext):
    list_ru = get_list_ru()
    in_ru = str(callback_data["id"]) in list_ru
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    buttons = [["/menu", "/меню"][in_ru],
               ["/help", "/помощь"][in_ru]]
    keyboard.add(*buttons)
    if callback_data["name"] == 'no':
        await bot.send_message(callback_data["id"], emoji.emojize(":woman_shrugging:"))
        await bot.send_message(callback_data["id"],
                               ['Well, it happens. Send me your text again',
                                'Что ж такое бывает. Пришлите мне ваш текст для поиска ещё раз'][in_ru])
        await call.answer()
        await bot.send_message(callback_data["id"], '..', reply_markup=user_markup_exit)
        await OrderSearch.waiting_for_text.set()
    elif callback_data["name"] == 'yes':
        await bot.send_message(callback_data["id"], emoji.emojize(":woman_technologist:"))
        user_data = await state.get_data()
        the_object = user_data['the_object']
        list_src = user_data['list_src']
        src_filled_pattern = fill_pattern(list_src, the_object)
        the_doc = open(src_filled_pattern, 'rb')
        await bot.send_message(callback_data["id"], ['Done\nHere is your file',
                                                     'Готово\nВот ваш файл'][in_ru])
        await bot.send_document(callback_data["id"], the_doc)
        await bot.send_message(callback_data['id'], '..', reply_markup=keyboard)
        await call.answer()


def register_handlers_fill(dp: Dispatcher):
    dp.register_message_handler(fill_start, commands="fillpattern", state="*")
    dp.register_callback_query_handler(fill_location_chosen,
                                       cb.filter(group=['pattern']),
                                       state=OrderSearch.waiting_for_file_name_pattern)
    dp.register_message_handler(fill_set_file,
                                content_types=['document'],
                                state=OrderSearch.waiting_for_file_pattern)
    dp.register_message_handler(fill_set_text,
                                content_types=[ContentType.VOICE, ContentType.TEXT],
                                state=OrderSearch.waiting_for_text)
    dp.register_callback_query_handler(set_acknowledgment,
                                       cb.filter(group=['acknowledgment']),
                                       state=OrderSearch.waiting_for_acknowledgment_fill)


r = sr.Recognizer()
