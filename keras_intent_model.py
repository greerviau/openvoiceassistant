import os
import json 
from utils import clean_text, encode_word_vec, pad_sequence
import numpy as np

def load_data(data_path):
    json_file = json.load(open('intentions.json'))
    intentions = json_file['intentions']
    compiled_data = []
    for intention in intentions:
        tag = intention['tag']
        patterns = intention['patterns']
        compiled_data.extend([[tag, clean_text(pattern)] for pattern in patterns])
    compiled_data = np.array(compiled_data)
    return compiled_data[:,1], compiled_data[:,0]

from keras.datasets import imdb
import pandas as pd
from keras.datasets import imdb
from keras.models import Sequential, load_model
from keras.layers import Dense, LSTM, Dropout
from keras.layers.embeddings import Embedding
from keras.preprocessing import sequence
from sklearn.preprocessing import OneHotEncoder
import pickle

# fix random seed for reproducibility
np.random.seed(7)
max_length = 10
embedding_dim = 100

X, y = load_data('intentions.json')

labels = list(set(y))
label_to_int = dict((l, i) for i, l in enumerate(labels))
int_to_label = dict((i, l) for i, l in enumerate(labels))

raw_text = ' '.join(X)
words = sorted(list(set(raw_text.split())))
word_to_int = dict((c, i+1) for i, c in enumerate(words))
int_to_word = dict((i+1, c) for i, c in enumerate(words))
word_to_int['bigpaddingbig'] = 0
int_to_word[0] = 'bigpaddingbig'

n_vocab = len(word_to_int)
n_labels = len(labels)

print('Word vocab size: ', n_vocab)
print('Word to int: ', word_to_int)
print('Number of total labels: ', n_labels)
print('Labels: ', labels)

data_X = []
data_y = []
for text, label in zip(X, y):
    encoded = encode_word_vec(text, word_to_int)
    padded = pad_sequence(encoded, max_length)
    data_X.append(padded)
    data_y.append([label_to_int[label]])

X = np.array(data_X)
onehot_encoder = OneHotEncoder(sparse=False)
y = onehot_encoder.fit_transform(data_y)
y = np.array(y)

print(X[0], y[0])

model = Sequential()
'''
model.add(Dense(16, input_dim=n_vocab, activation='relu'))
model.add(Dense(8, input_dim=n_vocab, activation='relu'))
'''
model.add(Embedding(n_vocab, embedding_dim, input_length=max_length))
model.add(LSTM(32))
model.add(Dropout(0.2))
model.add(Dense(n_labels, activation='softmax'))
model.compile(loss='categorical_crossentropy', optimizer='adam', metrics=['accuracy'])
print(model.summary())
model.fit(X, y, epochs=30, batch_size=8)

scores = model.evaluate(X, y, verbose=0)
print("Accuracy: %.2f%%" % (scores[1]*100))

model.save('intent_model.h5')
pickle.dump([word_to_int, int_to_label, max_length], open('vocab.p', 'wb'))

model = load_model('intent_model.h5')
word_to_int, int_to_label, max_length = pickle.load(open('vocab.p', 'rb'))

while True:
    test = input('you: ')
    cleaned = clean_text(test)
    encoded = encode_word_vec(cleaned, word_to_int)
    padded = pad_sequence(encoded, max_length)
    prediction = model.predict(np.array([padded]))[0]
    argmax = np.argmax(prediction)
    print(f'intent: {int_to_label[argmax]} - conf: {round(float(prediction[argmax])*100, 3)}%\n')