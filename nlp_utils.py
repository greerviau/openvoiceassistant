import datetime
from rake_nltk import Rake
from word2number import w2n
from nltk.corpus import stopwords
import spacy

sp = spacy.load('en_core_web_sm')
rake = Rake()

STOPWORDS = list(set(stopwords.words('english')))
STOPWORDS.extend(['some', 'what'])
MONTHS = ['january', 'february', 'march', 'april', 'may', 'june','july', 'august', 'september','october', 'november', 'december']
DAYS = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
DAY_OF_MONTH = {
    'first':1, 
    'second':2, 
    'third':3, 
    'fourth':4, 
    'fifth':5, 
    'sixth':6, 
    'seventh':7, 
    'eighth':8, 
    'ninth':9, 
    'tenth':10, 
    'eleventh':11, 
    'twelfth':12, 
    'thirteenth':13, 
    'fourteenth':14, 
    'fifteenth':15, 
    'sixteenth':16, 
    'seventeenth':17, 
    'eighteenth':18, 
    'nineteenth':19, 
    'twentieth':20, 
    'twenty first':21,
    'twenty second':22,
    'twenty third':23,
    'twenty fourth':24,
    'twenty fifth':25,
    'twenty sixth':26,
    'twenty seventh':27,
    'twenty eighth':28,
    'twenty ninth':29,
    'thirtieth':30,
    'thirty first':31
}
DAY_EXTENTIONS = ['rd', 'th', 'st', 'nd']

def try_parse_word_number(word):
    try:
        return w2n.word_to_num(word)
    except:
        return None

def parse_time(text):
    text = text.lower()
    time = None
    time_str = ''
    try:
        time = datetime.strptime(text, '%H:%M %p')
        return (int(time.strftime('%I%M')), time, text, True)
    except:
        pass

    try:
        time = datetime.strptime(text, '%H %p')
        return (int(time.strftime('%I')), time, text, True)
    except:
        pass

    try:
        time = datetime.strptime(text, '%H:%M')
        return (int(time.strftime('%I%M')), time, text, True)
    except:
        pass

    try:
        time = datetime.strptime(text, '%H')
        return (int(time.strftime('%I')), time, text, True)
    except:
        pass

    numbers = []
    pm = False
    am = False
    tod = False
    for word in text.split():
        if word.isdigit():
            numbers.append(int(word))
        else:
            try:
                numbers.append(w2n.word_to_num(word))
            except:
                pass
        if 'pm' in word:
            pm = True
            tod = True
        elif 'am' in word:
            am = True
            tod = True

    if len(numbers) > 0:
        try:
            if pm:
                numbers[0] += 12
            time = datetime.time(*numbers)
            time_str = time.strftime('%I:%M %p')
        except:
            pass
    if time:
        return (int(time.strftime('%I%M')), time, time_str, tod)
    return (None, None, '', False)

def parse_date(text):
    text = text.lower()
    today = datetime.date.today()

    if text.count('today') > 0:
        return today, 'today'
    
    if text.count('tomorrow') > 0:
        return today + datetime.timedelta(days=1), 'tomorrow'

    day = -1
    day_str = ''
    day_of_week = -1
    day_of_week_str = ''
    month = -1
    month_str = ''
    year = today.year

    for word in text.split():
        if word in MONTHS:
            month = MONTHS.index(word) + 1
            month_str = MONTHS[month-1]
        elif word in DAYS:
            day_of_week = DAYS.index(word)
            day_of_week_str = DAYS[day_of_week]
        elif word.isdigit():
            day = int(word)
            day_str = word
        else:
            for ext in DAY_EXTENTIONS:
                found = word.find(ext)
                if found > 0:
                    try:
                        day = int(word[:found])
                        day_str = word
                    except:
                        pass

    for word, number in DAY_OF_MONTH.items():
        if word in text:
            day = DAY_OF_MONTH[word]
            day_str = word
            break

    # THE NEW PART STARTS HERE
    if month < today.month and month != -1:  # if the month mentioned is before the current month set the year to the next
        year = year+1

    # This is slighlty different from the video but the correct version
    if month == -1 and day != -1:  # if we didn't find a month, but we have a day
        if day < today.day:
            month = today.month + 1
        else:
            month = today.month

    # if we only found a dta of the week
    if month == -1 and day == -1 and day_of_week != -1:
        current_day_of_week = today.weekday()
        dif = day_of_week - current_day_of_week

        if dif < 0:
            dif += 7
            if text.count('next') >= 1:
                dif += 7
                day_of_week_str = 'next '+day_of_week_str
        return today + datetime.timedelta(dif), day_of_week_str

    if day != -1:  # FIXED FROM VIDEO
        return datetime.date(month=month, day=day, year=year), f'{month_str} {day_str}'

    return None, None

def extract_subject(text):
    kw = rake.extract_keywords_from_text(text)
    ranked_phrases = rake.get_ranked_phrases()
    #filter(lambda w: not w in STOPWORDS, ranked_phrases)
    print(ranked_phrases)
    return ranked_phrases

def extract_keywords(text):
    kw = rake.extract_keywords_from_text(text)
    ranked_phrases = rake.get_ranked_phrases()
    return ranked_phrases

def tokenize(text):
    doc = sp(text)
    return [token.text for token in doc]

def extract_verbs(text):
    doc = sp(text)
    return [token.text for token in doc if token.pos_ == "VERB"]
    
def extract_entities(text):
    doc = sp(text)
    return doc.ents

def extract_noun_chunks(text):
    doc = sp(text)
    return [chunk.text for chunk in doc.noun_chunks]

if __name__ == '__main__':
    while True:
        text = input('input: ')
        print(tokenize(text))
        print(extract_noun_chunks(text))
        print(extract_verbs(text))
        print(extract_entities(text))
        print(extract_keywords(text))