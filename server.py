import csv
from datetime import datetime
import json
import os
from random import randrange

from flask import Flask, request

app = Flask(__name__)


def main(testing=False, injected_questions=None, injected_write_answer=None,
         injected_write_audio=None):
    global questions, write_answer, write_audio

    # dependency injection for testing
    if testing:
        questions = injected_questions
        write_answer = injected_write_answer
        write_audio = injected_write_audio
        return

    with open('questions.json') as f:
        questions = json.load(f)

        for question in questions:
            for key in ('english', 'german'):
                assert key in question

    # not using "with", keep the file open as long as the server is running
    # newline='' is recommended for csv, buffering=1 means line buffering
    answers_file = open('answers.csv', 'a', newline='', buffering=1)
    answers_csv_writer = csv.DictWriter(
            answers_file, (
                'user_id',
                'date',
                'app_name',
                'question',
                'answer_text',
                'answer_audio_uuid',
                ))

    # only write header if file is empty
    if os.stat(answers_file.name).st_size == 0:
        answers_csv_writer.writeheader()

    def write_answer(row):
        answers_csv_writer.writerow(row)

    def write_audio(file_name, data):
        with open(file_name, 'wb') as f:
            f.write(data)


def key_is_invalid(key):
    return key != 'hef3TF^Vg90546bvgFVL>Zzxskfou;aswperwrsf,c/x'


@app.route('/browser/question')
def send_question():
    if key_is_invalid(request.args.get('key', '')):
        return ''

    app_name = request.args.get('app_name', 'this app')
    question_type = request.args.get('question_type', 'normal')
    suitable_questions = \
        [question for question in questions
         if ('whitelist' not in question or app_name in question['whitelist'])
         and question.get('question_type', 'normal') == question_type]

    language = request.args.get('language', 'english')
    question_id = request.args.get('question_id',
                                   randrange(len(suitable_questions)))

    question_template = suitable_questions[int(question_id)][language]
    return question_template.replace('<app_name>', app_name)


@app.route('/browser/answer', methods=('POST',))
def receive_answer():
    if key_is_invalid(request.args.get('key', '')):
        return ''

    data = request.get_json(force=True)
    write_answer({
        'date': datetime.utcnow().isoformat(),
        'user_id': data.get('user_id', 'NULL'),
        'app_name': data.get('app_name', 'NULL'),
        'question': data.get('question', 'NULL'),
        'answer_text': data.get('answer_text', 'NULL'),
        'answer_audio_uuid': data.get('answer_audio_uuid', 'NULL'),
    })
    # if answer_audio_uuid is set the data should be sent to /audio
    return 'Thanks for your answer!'


@app.route('/browser/audio', methods=('POST',))
def receive_audio():
    if key_is_invalid(request.args.get('key', '')):
        return ''

    if 'uuid' not in request.args.keys():
        return 'UUID is required.'

    if not request.content_length:
        return 'Audio data is required.'

    if request.content_length > 5 * 10**6:
        return 'File is too big: ' + request.content_length + ' byte.'

    write_audio('audio/' + request.args["uuid"] + '.aac', request.get_data())

    return 'Thanks for your audio answer!'


main()

if __name__ == '__main__':
    app.run(
        # ssl_context='adhoc',
        host='0.0.0.0')
