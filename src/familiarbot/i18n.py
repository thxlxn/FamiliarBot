import json
import os

translations = {}
locales_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'locales')

def load_translations():
    for filename in os.listdir(locales_dir):
        if filename.endswith('.json'):
            lang_code = filename.split('.')[0]
            with open(os.path.join(locales_dir, filename), 'r', encoding='utf-8') as f:
                translations[lang_code] = json.load(f)

load_translations()

def get_text(lang, key, **kwargs):

    if lang not in translations:
        lang = 'en'
        
    text = translations[lang].get(key, translations['en'].get(key, f"Missing translation: {key}"))
    
    if kwargs:
        return text.format(**kwargs)
    return text