import datetime


def get_list_ru():
    with open('Data/Main_files/list_ru.txt') as f:
        list_ru = f.read().split('\n')
    return list_ru


def change_language(message, list_ru):
    if str(message.from_user.id) not in list_ru:
        with open('Data/Main_files/list_ru.txt', 'a', encoding='utf-8') as f:
            print(message.from_user.id, file=f)
    else:
        with open('Data/Main_files/list_ru.txt', 'w+', encoding='utf-8') as f:
            cont = f.read().split('\n')
            cont_new = [x for x in cont if x and x != str(message.from_user.id)]
            print(*cont_new, sep='\n', file=f)


#  регистрация новах пользователей в файл
def start_registration(message):
    make_start_time = datetime.datetime.now()
    make_start_time += datetime.timedelta(hours=3)  # Перевод в Московское время
    make_start_time = make_start_time.strftime('%d.%m.%Y-%H:%M')
    with open('Data/Main_files/list_registration.txt', 'a', encoding='utf-8') as f:
        print(message.from_user.id, make_start_time, sep=';', file=f)


def get_list_topic(the_id=None, src='Data/Main_files/table_topics.txt'):
    with open(src, encoding='utf-8') as f:
        cont = f.read().split('\n')
        print('cont=  ', cont)
        cont = list(filter(lambda x: len(x.split(';')) == 4, cont))
        print('cont_f=  ', cont)
        if the_id:
            cont = list(filter(lambda x: str(x.split(';')[1]).strip() == str(the_id) and x.split(';')[3] == 'True',
                               cont))
            print('cont_if= ', cont)
        list_topic = [x.split(';')[0] for x in cont]
        print('list_topic=', list_topic)
    return list_topic


def name_to_src(lst, src='Data/Main_files/table_topics.txt'):
    with open(src, encoding='utf-8') as f:
        cont = f.read().split('\n')
        cont = list(filter(lambda x: len(x.split(';')) == 4, cont))
    return [x.split(';')[2].strip() for x in cont if x.split(';')[0] in lst]


# Удаляет файл
def delete_file(file_name):
    for src in ['Data/Main_files/table_topics.txt', 'Data/Main_files/table_patterns.txt']:  # добавил Патерн !!!!
        result = False
        with open(src, encoding='utf-8') as f:
            cont_new = []
            cont = f.read().split('\n')
            cont = list(filter(lambda x: len(x.split(';')) == 4, cont))
            for row in cont:
                lst = row.split(';')
                if file_name in lst[0]:
                    lst[3] = 'False'
                    result = True
                cont_new.append(';'.join(lst))
        if result:
            with open(src, 'w', encoding='utf-8') as f:
                print(*cont_new, sep='\n', file=f)
            break


