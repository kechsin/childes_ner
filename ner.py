import copy
import re
import csv
import json
import os
import subprocess
import sys

from transformers import pipeline
from navec import Navec
from slovnet import NER
import pymorphy3
import spacy
from spacy.util import is_package



def read_file(num):
    fname = f"transcripts/transcript{num}.json"
    with open(fname) as f:
        transcript = json.load(f)
    return transcript


def concat_lists(list1, list2):
    heading = [('Time Stamp', 'Proper Nouns'), ('', '')]
    list1 = list1[2:]
    list2 = list2[2:]
    lists = sorted(set(list1 + list2))
    return heading + lists


def index_timestamp(transcript, start, end):
    """
    По индексу символа в тексте находит слово в транскрипции.
    """
    segments = transcript['segments']
    len_segments = 0
    answer = []
    for segment_number, i in enumerate(segments):
        if not 'text' in i or len_segments + len(i['text']) > start:
            len_words = 0
            for word_number, j in enumerate(i['words']):
                #print(len_words)
                if len_words >= start - len_segments and len_words < end - len_segments:
                    answer.append({'seg_num': segment_number,
                          'word_num': word_number,
                          'text': j['text'],
                          'start': j['start'],
                          'end': j['end']})
                if len_words >= end - len_segments:
                    return answer
                #print('spaces' + str(1 + int(transcript['text'][len_segments + len_words + 1] == ' ')))
                #print('len' + str(len(j['text'].strip())))
                len_words += len(j['text'].strip()) + 1

        if 'text' in i:
            len_segments += len(i['text'])
    return answer


def delete_exceptions(tstamps):
    exceptions = ['алиса', 'алисе', 'алису', 'алисой', 'алисы']
    deleting = []
    for i, line in enumerate(tstamps):
        for j in exceptions:
            if line[1].strip(' .?,"!?\\/-').lower() == j:
                deleting.append(i)
    for i in deleting[::-1]:
        tstamps.pop(i)
    return tstamps


import subprocess
import sys
import spacy
from spacy.util import is_package

def ensure_spacy_model_installed(model_name):
    if is_package(model_name):
        print(f"Модель {model_name} уже установлена.")
        return

    print(f"Модель {model_name} не найдена. Начинаю загрузку...")
    try:
        subprocess.run(
            [sys.executable, "-m", "spacy", "download", model_name],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        print("Модель успешно загружена!")
    except subprocess.CalledProcessError as e:
        print("Ошибка при загрузке модели для spacy:")
        print(e.stderr)
        raise


def save_forms():
    morph = pymorphy3.MorphAnalyzer()

    with open('names.txt') as f:
        names = f.readlines()
        names = [i.strip() for i in names]

    forms = set()
    for i in names:
        if i.find(':') == -1:
            continue
        name, category = i.split(':')
        forms.add(name.lower() + '\n')
        if category == 'nom':
            if name[-1] == 'а':
                forms.add((name[:-1] + '\n').lower())
            elif name[-1] == 'я':
                forms.add((name[:-1] + 'ь' + '\n').lower())
            for option in morph.parse(name):
                if 'Name' in option.tag:
                    for morph_case in ('gent', 'accs', 'datv', 'ablt', 'loct'):
                        form = option.inflect({morph_case})
                        forms.add(form.word + '\n')
        if category == 'poss':
            for option in morph.parse(name):
                if 'ADJF' in option.tag:
                    for morph_case in ('gent', 'accs', 'datv', 'ablt', 'loct'):
                        for gender_number in ('masc', 'femn', 'neut', 'plur'):
                            form = option.inflect({morph_case, gender_number})
                            forms.add(form.word + '\n')
    with open('forms.txt', 'w') as f:
        f.writelines(sorted(forms))


def list_based(transcript):
    if not os.path.exists('forms.txt'):
        if not os.path.exists('names.txt'):
            print('Вам нужно составить список names.txt. Правила будут где-нибудь описаны и будет пример.')
        else:
            save_forms()
    with open('forms.txt') as f:
        forms = {i.strip() for i in f.readlines()}
    tstamps0 = [('Time Stamp', 'Proper Nouns'), ('', '')]
    punctuation = '.,?!":;-—'
    for seg in transcript['segments']:
        for word in seg['words']:
            w_text = word['text'].lower()
            for sign in punctuation:
                w_text = w_text.replace(sign, '')
            if w_text in forms:
                tstamps0.append((word['start'], word['text']))
    return tstamps0


def roberta_single(transcript, ner):
    def join_entities(entities):
        entities2 = copy.deepcopy(entities)
        for n, ent in enumerate(entities[::-1]):
            if ent['entity'][0] == "I":
                index = len(entities) - n - 1
                entities2[index-1]['word'] = entities[index-1]['word'] + entities2[index]['word']
                entities2[index-1]['end'] = entities2[index]['end']
                del entities2[index]
        return entities2
    text = transcript['text']
    entity = ner(text)
    print(entity)
    entities = join_entities(entity)
    tstamps = [('Time Stamp', 'Proper Nouns'), ('', '')]
    for i in entities:
        results = index_timestamp(transcript, i['start'], i['end'])
        for result in results:
            tstamps.append((result['start'], result['text']))
    print(entities)
    return tstamps


def roberta_ner(transcripts):
    ner = pipeline("ner", model="yqelz/xml-roberta-large-ner-russian")
    tstamp_list = []
    file_number = 0
    for transcript in transcripts:
        print(f'Обрабатываем файл номер {file_number}')
        tstamps = roberta_single(transcript, ner)
        tstamp_list.append(tstamps)
        file_number += 1
    return tstamp_list


def spacy_single(transcript, nlp):
    text = transcript['text']
    doc = nlp(text)
    tstamps = [('Time Stamp', 'Proper Nouns'), ('', '')]
    for ent in doc.ents:
        # print(ent.text, ent.start_char, ent.end_char, ent.label_)
        results = index_timestamp(transcript, ent.start_char, ent.end_char)
        for result in results:
            tstamps.append((result['start'], result['text']))
    return tstamps


def spacy_ner(transcripts):
    ensure_spacy_model_installed("ru_core_news_md")
    nlp = spacy.load("ru_core_news_md")
    tstamp_list = []
    file_number = 0
    for transcript in transcripts:
        print(f'Обрабатываем файл номер {file_number}')
        tstamps = spacy_single(transcript, nlp)
        tstamp_list.append(tstamps)
        file_number += 1
    return tstamp_list


def natasha_single(transcript, ner):
    text = transcript['text']
    markup = ner(text)
    tstamps = [('Time Stamp', 'Proper Nouns'), ('', '')]
    for ent in markup.spans:
        # print(ent.text, ent.start_char, ent.end_char, ent.label_)
        results = index_timestamp(transcript, ent.start, ent.stop)
        for result in results:
            tstamps.append((result['start'], result['text']))
        # print(ent.start, ent.stop)
    return tstamps


def natasha_ner(transcripts):
    navec = Navec.load('navec_news_v1_1B_250K_300d_100q.tar')
    ner = NER.load('slovnet_ner_news_v1.tar')
    ner.navec(navec)
    tstamp_list = []
    file_number = 0
    for transcript in transcripts:
        print(f'Обрабатываем файл номер {file_number}')
        tstamps = natasha_single(transcript, ner)
        tstamp_list.append(tstamps)
        file_number += 1
    return tstamp_list


def process_transcripts(names, ner_function, testing=True):
    transcripts = []
    for name in names:
        transcripts.append(read_file('_' + name))
    for i in range(len(transcripts)):
        transcripts[i]['text'] = re.sub(r'\s+', ' ', transcripts[i]['text']).strip()
    timestamps1 = ner_function(transcripts)
    timestamps0 = [list_based(transcript) for transcript in transcripts]

    if testing:
        funname = '_' + str(ner_function).split()[1]
    else:
        funname = ""
    for i in range(len(names)):
        all_timestamps = concat_lists(timestamps0[i], timestamps1[i])
        all_timestamps = delete_exceptions(all_timestamps)
        with open(f'ner/{names[i]}{funname}.csv', 'w') as f:
            writer = csv.writer(f)
            writer.writerows(all_timestamps)


def main():
    print('Если всё правильно, то на данный момент у вас должны быть файлы с транскрипциями.\n'
          'Они называются в формате transcript_<номер>_<способ транскрипции>.json.\n'
          'Скрипт GigaAM.ipynb записывает способ транскрипции = "e2e_ctc".\n'
          'Если вы это меняли, и в названии файлов указан другой способ, введите его.\n'
          '(Например, если хотите обработать файл transcript_001_whisper, введите whisper).\n'
          'Если вы это не меняли, нажмите Enter.')
    transcript_option = input().lower()
    if transcript_option == '':
        transcript_option = 'e2e_ctc'
    print('Введите номера файлов с транскрипциями (каждый в новой строке).\n'
          'Когда закончите, нажмите Enter.\n'
          'Транскрипции для обработки должны лежать в папке transcripts.\n'
          'И быть в формате, который выдаёт скрипт GigaAM.ipynb.')
    numbers = []
    num = input()
    while num != '':
        if os.path.exists(f'transcripts/transcript_{num}_{transcript_option}.json'):
            numbers.append(num)
        else:
            print(
                f'Ошибка: не найден файл transcripts/transcript_{num}_{transcript_option}.json'
                f'\n(Вы можете продолжать вводить, но последняя строка не засчитана)')
        num = input()
    print('Введите вариант извлечения именованных сущностей.\n'
          'Варианты: roberta (не рекомендуется), spacy, natasha.')
    ner_option = input().lower()
    chosen_ner = False
    names = list([f'{i}_{transcript_option}' for i in numbers])
    while not chosen_ner:
        chosen_ner = True
        if ner_option == 'roberta':
            process_transcripts(names, roberta_ner)
        elif ner_option == 'spacy':
            process_transcripts(names, spacy_ner)
        elif ner_option == 'natasha':
            process_transcripts(names, natasha_ner)
        else:
            print('Некорректный ввод. Варианты: roberta (не рекомендуется), spacy, natasha.')
            chosen_ner = False


if __name__ == '__main__':
    main()
