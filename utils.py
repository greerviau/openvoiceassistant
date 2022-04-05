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

def net_scan(ip):
    arp_req_frame = scapy.ARP(pdst = ip)

    broadcast_ether_frame = scapy.Ether(dst = "ff:ff:ff:ff:ff:ff")
    
    broadcast_ether_arp_req_frame = broadcast_ether_frame / arp_req_frame

    answered_list = scapy.srp(broadcast_ether_arp_req_frame, timeout = 1, verbose = False)[0]
    result = []
    for i in range(0,len(answered_list)):
        client_dict = {"ip" : answered_list[i][1].psrc, "mac" : answered_list[i][1].hwsrc}
        result.append(client_dict)

    return result