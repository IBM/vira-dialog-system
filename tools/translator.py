#
# Copyright 2020-2023 IBM Inc. All rights reserved
# SPDX-License-Identifier: Apache2.0
#

import re
import requests
import pandas as pd
import math


ENGLISH_CODE = 'en'


class WatsonTranslator:

	def __init__(self, configuration):
		self.configuration = configuration
		self.api_key = configuration.get_translator_apikey()
		self.url = configuration.get_translator_endpoint()

	def get_translation(self, text, language_code):
		model_id = self.configuration.get_translator_model_id(language_code)
		headers = {'apikey': self.api_key, 'content-type': 'application/json'}
		data = {
			'text': text,
			'model_id': model_id,
			'translations': [],
		}

		resp = requests.post(self.url, json=data, headers=headers, auth=('apikey', self.api_key))
		if resp.status_code != 200:
			print('POST to %s failed: %d: %s' % (self.url, resp.status_code, resp.reason))
			print(resp.text)
			return {}
		return resp.json()

	def get_translation_res(self, res):
		if 'translations' in res.keys():
			return [trans['translation'] for trans in res['translations']]
		return ''

	def translate_file(self, sentences, language_code):
		original = []
		translation = []

		batch_size = 100
		num_batches = math.ceil(len(sentences) / batch_size)

		base_model_id = self.configuration.get_translator_base_model_id(language_code)

		for i, begin in enumerate(range(0, len(sentences), batch_size)):
			print(f'translating batch {i + 1}/{num_batches} ...')
			sent_batch = sentences[begin: begin + batch_size]
			res = self.translate(sent_batch, language_code)
			original += sent_batch
			translation += res

			if i % 100 == 0:
				out_df = pd.DataFrame()
				out_df[f'sentence_{base_model_id.split("-")[0]}'] = original
				out_df[f'sentence_{base_model_id.split("-")[1]}'] = translation

		out_df = pd.DataFrame()
		out_df[f'sentence_{base_model_id.split("-")[0]}'] = original
		out_df[f'sentence_{base_model_id.split("-")[1]}'] = translation
		return out_df[f'sentence_{base_model_id.split("-")[1]}'].tolist()

	def translate(self, text, language_code):
		res = self.get_translation(text, language_code)
		out_res = self.get_translation_res(res)
		return out_res

	def create_model(self, mode, path, language_code):
		base_model_id = self.configuration.get_translator_base_model_id(language_code)
		headers = {'apikey': self.api_key}
		file = {mode: open(path, 'rb')}
		resp = requests.post(self.url.replace("translate", "models") +
							 f"&base_model_id={base_model_id}&name=custom-{base_model_id}",
							 files=file, headers=headers, auth=('apikey', self.api_key))
		return resp.json()['model_id']

	def get_model(self, model_id):
		headers = {'apikey': self.api_key, 'content-type': 'application/json'}
		resp = requests.get(self.url.replace("translate", f"models/{model_id}"),
							headers=headers, auth=('apikey', self.api_key))
		return resp.json()

	def delete_model(self, model_id):
		headers = {'apikey': self.api_key, 'content-type': 'application/json'}
		resp = requests.delete(self.url.replace("translate", f"models/{model_id}"),
							   headers=headers, auth=('apikey', self.api_key))
		return resp.json()

	def get_identification(self, text):
		headers = {'apikey': self.api_key, 'content-type': 'text/plain'}
		resp = requests.post(self.url.replace("translate", "identify"), data=text.encode('utf8'), headers=headers,
							 auth=('apikey', self.api_key))
		return resp.json()

	def identify_language(self, text):
		resp = self.get_identification(text)
		if 'languages' in resp and len(resp['languages']) > 0 and resp['languages'][0]['confidence'] > 0.5:
			return resp['languages'][0]['language']
		return ENGLISH_CODE


def translating_canned_text(language_code):
	from tools.db_manager import DBManager, BotManager
	BotManager().set_name("covid_jhu_en")
	configuration = DBManager().read_configuration()
	configuration.data['watson_translator'][language_code]['model_id'] = f'en-{language_code}'
	configuration.data['watson_translator'][language_code]['base_model_id'] = f'en-{language_code}'
	watson_translator = WatsonTranslator(configuration)
	import pandas as pd
	df = pd.read_csv('bot/covid_jhu_en/resources/canned_text.csv')
	df.dropna(inplace=True, subset=['text'])
	df['text'] = watson_translator.translate_file(df['text'].tolist(), language_code=language_code)
	df.to_csv(f'bot/covid_jhu_en/resources/canned_text_{language_code}.csv', encoding='utf-8-sig')


def translating_response_db(language_code):
	from tools.db_manager import DBManager, BotManager
	BotManager().set_name("covid_jhu_en")
	configuration = DBManager().read_configuration()
	configuration.data['watson_translator'][language_code]['model_id'] = f'en-{language_code}'
	configuration.data['watson_translator'][language_code]['base_model_id'] = f'en-{language_code}'
	watson_translator = WatsonTranslator(configuration)
	link_pattern = re.compile(r'<[ ]*LINK[ ]*[|]([^|]+)[|]([^>]+)>')

	def translating_response(response):
		new_response = ''
		match = link_pattern.search(response)
		while match:
			span = match.span()
			prefix = response[0:span[0]]
			suffix = response[span[1]:]
			link_caption = match.group(1)
			link_url = match.group(2)
			if link_suspected(prefix):
				print("Suspicious character in %s" % new_response)
			texts = watson_translator.translate_file([prefix, link_caption], language_code=language_code)
			new_response += texts[0] + '<LINK | ' + texts[1] + '|' + link_url + '>'
			response = suffix
			match = link_pattern.search(response) if len(response.strip()) > 0 else None
		if len(response.strip()) > 0:
			if link_suspected(response):
				print("Suspicious character in %s" % response)
			new_response += watson_translator.translate(response)[0]
		return new_response

	def link_suspected(text):
		return "LINK" in text or '<' in text or '|' in text or 'http' in text

	import pandas as pd
	df = pd.read_csv('bot/covid_jhu_en/resources/response_db.csv')
	df.dropna(inplace=True, subset=['system_response'])
	df['system_response'] = df['system_response'].apply(translating_response)
	df.to_csv(f'bot/covid_jhu_en/resources/response_db_{language_code}.csv', index=False, encoding='utf-8-sig')


def translating_free_texts(language_code):
	from tools.db_manager import DBManager, BotManager
	BotManager().set_name("covid_jhu_en")
	configuration = DBManager().read_configuration()
	configuration.data['watson_translator'][language_code]['model_id'] = f'en-{language_code}'
	configuration.data['watson_translator'][language_code]['base_model_id'] = f'en-{language_code}'
	watson_translator = WatsonTranslator(configuration)
	texts = [
		"WELCOME TO VIRA, FROM JOHNS HOPKINS INTERNATIONAL VACCINE ACCESS CENTER. ",
		"Get answers to your questions about COVID-19 vaccines from VIRA (Vaccine Information Resource Assistant). 🌞 ",
		"VIRA is not a substitute for medical advice."]
	print(watson_translator.translate_file(texts, language_code=language_code))


# mode can be "forced_glossary" or "parallel_corpus"
def create_custom_model(mode, language_code):
	from tools.db_manager import DBManager, BotManager
	BotManager().set_name("covid_jhu_en")
	configuration = DBManager().read_configuration()
	watson_translator = WatsonTranslator(configuration)
	old_model_id = configuration.get_translator_model_id(language_code=language_code)
	print(f'after new model is created and tested, please delete {old_model_id} using delete_model')
	# creating model and new model id, should be saved in configuration.json under "model_id"
	new_model_id = watson_translator.create_model(mode=mode,
												  path=f'bot/covid_jhu_en/resources/translation_{mode}_{language_code}.csv',
												  language_code=language_code)
	print(f'created new model id {new_model_id}')
	# checking model status of the new model id, after a few minutes/hours it should be "available"
	print(watson_translator.get_model(model_id=new_model_id))
	# after testing of new model id, delete old model id
	# print(watson_translator.delete_model(id=old_model_id))


def get_model(model_id):
	from tools.db_manager import DBManager, BotManager
	BotManager().set_name("covid_jhu_en")
	configuration = DBManager().read_configuration()
	# to get a list of all models, put in model_id an empty_string
	model_id = model_id if model_id is not None else ""
	watson_translator = WatsonTranslator(configuration)
	print(watson_translator.get_model(model_id))


def delete_model(model_id):
	from tools.db_manager import DBManager, BotManager
	BotManager().set_name("covid_jhu_en")
	configuration = DBManager().read_configuration()
	watson_translator = WatsonTranslator(configuration)
	print(watson_translator.delete_model(model_id))


def test_identify_language():
	from tools.db_manager import DBManager, BotManager
	BotManager().set_name("covid_jhu_en")
	configuration = DBManager().read_configuration()
	watson_translator = WatsonTranslator(configuration)
	texts = ['hi', 'good morning', 'how are you', 'I have a question', 'hello', 'side effects', 'Buen día', 'Buenas tardes',
			 'Buenas noches', 'tengo una pregunta', 'hola', 'Buenos días', 'Tengo miedo de los efectos secundarios',
			 'adiós', 'Bienvenido', 'efectos secundarios']
	for text in texts:
		print(text, watson_translator.identify_language(text))


if __name__ == '__main__':
	# translating_response_db("es")
	# create_custom_model( mode='forced_glossary',language_code='he')
	# get_model(model_id="d50ec172-3dcc-462d-813f-474bd95441d7")
	test_identify_language()