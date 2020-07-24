#!/usr/bin/python3
from flask import Flask, render_template, url_for, request, send_file

app = Flask(__name__)

#-------------------
#-- global variables
#-------------------
# dictionary path
dictionary_dir = '/workspace/flask/files/user_dict/'
dictionary_path = dictionary_dir+'dict.csv'
dictionary_path_dic = dictionary_dir+'user.dic'

# debug
debug = False

# new word
class NewWord(object):
    def __init__(self, word='', yomi='', noun_type=''):
        # required for dictionary
        self.word = word
        self.yomi = yomi
        self.noun_type = noun_type

        # dictionary template for sudachi
        self.template_dict = {
            'noun_general': '{word},5146,5146,5000,{word},名詞,普通名詞,一般,*,*,*,{yomi},{word},*,*,*,*,*',
            'noun_sahen': '{word},5133,5133,5000,{word},名詞,普通名詞,サ変可能,*,*,*,{yomi},{word},*,*,*,*,*',
            'propn_general': '{word},4786,4786,5000,{word},名詞,固有名詞,一般,*,*,*,{yomi},{word},*,*,*,*,*',
            'propn_last': '{word},4789,4789,5000,{word},名詞,固有名詞,人名,名,*,*,{yomi},{word},*,*,*,*,*',
            'propn_family': '{word},4790,4790,5000,{word},名詞,固有名詞,人名,姓,*,*,{yomi},{word},*,*,*,*,*',
        }
    
    def convertDictFormat(self):
        # convert word and yomi to sudachi format
        return self.template_dict[self.noun_type].format(word=self.word, yomi=self.yomi)+'\n'

# db config
class DBConfig(object):
    def __init__(self, table, user, database):
        self.table = table
        self.connection_config = {
            'user': user,
            #'password': '',
            'host': 'postgres',
            'port': '5432',
            'database': database
        }

# cache to leave input data after post action
cache = {
    'date_str': '',
    'storyid': '',
    'story': '',
    'transformedData': '',
    'new_word': NewWord()
}

cacheSelectData = {}

#-------------------
#-- functions
#-------------------
def getTransformedData(story, debug=False):
    '''
    入力テキストから名詞を抽出して、ハイライト表示用に<span class=hl>タグを付与する。
    input:  文章
    output: 先頭から順に、名詞に<span class=hl>タグが付与されたリスト
    '''
    import spacy
    nlp = spacy.load('ja_ginza')
    doc = nlp(story)

    story_hl_doc = []
    for sent in doc.sents:
        story_hl_sent = []
        for token in sent:
            if debug:
                print(token.i, token.orth_, token.lemma_, token.pos_, token.tag_, token.dep_, token.head.i)

            if (token.tag_.split('-')[0] == '名詞'):
                token_c = '<span class=hl>{str}</span>'.format(str=token.orth_)
                story_hl_sent.append(token_c)
            else:
                story_hl_sent.append(token.orth_)
        story_hl_doc.append(story_hl_sent)
    
    story_hl_p = [''.join(p) for p in story_hl_doc]
    story_hl_p = '<br>'.join(story_hl_p)
    return story_hl_p

def getDBData(db_config, date_str):
    '''
    PostgreSQLからテキストをselectする。
    input:  db_config: 接続先情報
            date_str:  selectするdatetime情報
    output: selectしたデータ（id: text の辞書形式）
    '''
    import psycopg2

    # set db connection
    connection = psycopg2.connect(**db_config.connection_config)
    connection.set_client_encoding('utf-8') 
    cursor = connection.cursor()

    # select from DB
    select = "select storyid,story from {} where versioncreated::date='{}' order by versioncreated desc;".format(db_config.table, date_str)
    cursor.execute(select)
    selectData = cursor.fetchall()

    # make cacheSelectData dict
    storyid_list = [ _id[0] for _id in selectData ]
    story_list = [ _id[1] for _id in selectData ]
    selectData = dict(zip(storyid_list, story_list))
    return selectData

def readSomeDictionary(dictionary_path=dictionary_path, tail_num=5):
    '''
    辞書のラスト数行を取得する。
    input:  dictionary_path: 辞書のパス
            tail_num: 取得する行数
    output: リスト
    '''
    import subprocess
    command = ['tail', '-n', str(tail_num), dictionary_path]
    dictionaryList = subprocess.run(command, encoding='utf-8', stdout=subprocess.PIPE, text=True).stdout
    return dictionaryList

def compileDictionary(dictionary_path=dictionary_path):
    '''
    辞書をコンパイルする。
    input:  dictionary_path: 辞書のパス
    output: なし
    '''
    import subprocess
    # compile dictionary
    command = ["sudachipy", "ubuild", "-s", "/usr/local/lib/python3.8/site-packages/ja_ginza_dict/sudachidict/system.dic", "-o", dictionary_path_dic ,dictionary_path]
    subprocess.run(command)
    return

def addDictionary(new_word, dictionary_path=dictionary_path):
    '''
    現在の辞書をバックアップして、新単語を追加した辞書を適用する。
    input:  new_word: 登録する単語
            dictionary_path: 辞書のパス
    output: なし
    '''
    import shutil

    # format
    new_dictionary = new_word.convertDictFormat()

    # backup dictionary
    backup_dictionary_path = dictionary_path + '.backup'
    shutil.copy(dictionary_path, backup_dictionary_path)

    # write dictionary
    with open(dictionary_path, 'a') as f:
        f.write(new_dictionary)

    # compile dictionary
    compileDictionary(dictionary_path)
    return

def restoreDictionary(dictionary_path=dictionary_path):
    '''
    バックアップした辞書を復旧させる。
    input:  dictionary_path: 辞書のパス
    output: なし
    '''
    import shutil

    # restore dictionary
    backup_dictionary_path = dictionary_path + '.backup'
    shutil.copy(backup_dictionary_path, dictionary_path)

    # compile dictionary
    compileDictionary(dictionary_path)
    return

#-------------------
#-- routing
#-------------------
@app.route('/')
def index():
    # read dictionary
    dictionaryData = readSomeDictionary()

    # compile dictionary
    compileDictionary()

    return render_template('index.html', dictionaryData=dictionaryData)

@app.route('/transformed', methods=["GET", "POST"])
def transformed():
    # global variables
    global cache
    global cacheSelectData
    global dictionary_path

    # read dictionary
    dictionaryData = readSomeDictionary(dictionary_path)

    # debug
    if debug:
        print(request.form)

    if request.method == "GET":
        pass

    if request.method == 'POST':
        if 'date' in request.form.keys():
            # get date
            date_str = request.form['date']

            # get news from DB
            db_config = DBConfig(table='news01', user='readonly_user', database='news')
            cacheSelectData = getDBData(db_config, date_str)

            # to cache
            cache['date_str'] = date_str

        if 'select' in request.form.keys():
            # get story
            storyid = request.form['select']
            story = cacheSelectData[storyid]

            # transform by nlp and highlight text
            transformedData = getTransformedData(story)

            # to cache
            cache['storyid'] = storyid
            cache['story'] = story
            cache['transformedData'] = transformedData

        if 'retransform' in request.form.keys():
            # from cache
            story = cache['story']

            # get textarea
            new_word = NewWord(
                word = request.form['word'],
                yomi = request.form['yomi'],
                noun_type = request.form['dictionary'],
            )

            # backup and add dictionary
            addDictionary(new_word)

            # transform by nlp and highlight text
            transformedData = getTransformedData(story)

            # restore dictionary
            restoreDictionary()

            # to cache
            cache['transformedData'] = transformedData
            cache['new_word'] = new_word

        if 'entry' in request.form.keys():
            # get textarea
            ## read from form, not from cache
            new_word = NewWord(
                word = request.form['word'],
                yomi = request.form['yomi'],
                noun_type = request.form['dictionary'],
            )

            # backup and add dictionary
            addDictionary(new_word)

            # read dictionary to comfirm new entry
            dictionaryData = readSomeDictionary()

            # clear cache
            cache['new_word'] = NewWord()

    return render_template('index.html',
                           date_str=cache['date_str'],
                           storyid=cache['storyid'],
                           storyid_list=cacheSelectData.keys(),
                           transformedData=cache['transformedData'],
                           new_word=cache['new_word'],
                           dictionaryData=dictionaryData
                           )

@app.route('/download', methods=['GET'])
def download_file():
    return send_file('./user_dict/dict.csv', as_attachment=True)

#-------------------
#-- main
#-------------------
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)