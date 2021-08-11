import string
import numpy as np

def get_after(text, token):
    return text.split(token)[-1]

def clean_text(text):
    table = str.maketrans('', '', string.punctuation)
    text = text.lower()
    text = ' '.join([w.translate(table) for w in text.split()])
    text = text.strip()
    return text

def encode_bow(text, vocab):
    encoded = np.zeros(len(vocab))
    for word in text.split():
        if word in vocab.keys():
            encoded[vocab[word]] += 1
    return np.array(encoded)

def encode_word_vec(text, vocab):
    encoded = np.zeros(len(text.split()))
    for i, word in enumerate(text.split()):
        if word in vocab.keys():
            encoded[i] = vocab[word]
    return np.array(encoded)

def pad_sequence(encoded, seq_length):
    padding = np.zeros(seq_length)
    if len(encoded) > seq_length:
        padding = encoded[:seq_length]
    else:
        padding[:len(encoded)] = encoded
    return padding