# childes_ner
Repository for bachelor thesis about NER in oral childen speech

In this project we created an automatic Named Entity Recognition (NER) system for processing audio-recordings of conversations with a child based on the CHILDES corpus, for anonimisation purposes. Our system consists of two components: automatic speech recognition and named entity recognition. For each component we have compared some of-the-shelf models and have chosen the one which showed the best results on our texts. In NER together with the models we used a search of name forms from premade list. Metrics of our system are: recall = 0.79, precision = 0.48, F1 = 0.6. Besides that, we analysed models' errors and found some patterns in what causes those errors.
This project can be useful for those who work with child speech, because anonimisation is important not only for a corpus, but, for example, for voice assistants' training.

For using the system you need:
0) Get WAV file of yout recording. If you have a video, you can use
`ffmpeg -i <адрес видео> <адрес аудио>`
If you have a non-WAV audio file, use any converter.
1) Put WAV file into audio directory
2) Run GigaAM.ipynb (all cells, there are some instructions in text blocks)
3) You may add names of people in the recording to names.txt
4) Run ner.py
