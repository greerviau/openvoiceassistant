from subject_verb_object_extract import findSVOs, nlp
tokens = nlp("Remind me to call Bank Gloucester at 3pm tomorrow")
svos = findSVOs(tokens)
print(svos)