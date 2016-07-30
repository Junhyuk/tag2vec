import os
import re
import logging
import tensorflow as tf
from flask import Flask, request, render_template, jsonify, send_from_directory
from werkzeug.contrib.cache import SimpleCache
from word2vec_optimized import Tag2vec
from instagram import Instagram

app = Flask(__name__)
model = Tag2vec().model
instagram = Instagram()
NEARBY_COUNT = 12
cache = SimpleCache()

@app.route("/", methods=['GET'])
def main():
  q = request.args.get('q') or ''
  q = q.strip()

  if not q:
    data = {'vocab_size': model.get_vocab_size(), 'emb_dim': model.get_emb_dim() }
    return render_template('index.html', query='', data=data)
  return query(q)

def query(q):
  data = {}
  if q.startswith('!'):
    words = q[1:].strip().split()
    data['doesnt_match'] = model.get_doesnt_match(*words)
  else:
    words = q.split()
    count = len(words)
    m = re.search('([^\-]+)\-([^\+]+)\+(.+)', q)
    if m:
      words = map(lambda x: x.strip(), m.groups())
      data['analogy'] = model.get_analogy(*words)
    elif count == 1 and not q.startswith('-'):
      data['no_words'] = model.get_no_words(words)
      if not data['no_words']:
        data['nearby'] = model.get_nearby([q], [], num=NEARBY_COUNT + count)
        data['tag'] = q
    else:
      negative_words = [word[1:] for word in words if word.startswith('-')]
      positive_words = [word for word in words if not word.startswith('-')]
      data['no_words'] = model.get_no_words(negative_words + positive_words)
      if not data['no_words']:
        data['nearby'] = model.get_nearby(positive_words, negative_words, num=NEARBY_COUNT + count)
        data['tag'] = data['nearby'][0][0]
  data['words'] = words
  return render_template('query.html', query=q, data=data)

@app.route("/tags/<string:tag_name>/media.js", methods=['GET'])
def tag_media(tag_name):
  key = '/tags/%s/media.js' % tag_name
  json = cache.get(key)
  if not json:
    media = instagram.media(tag_name)
    json = jsonify(media=media)
    cache.set(key, json, timeout=60*60)
  return json

@app.route("/tsne.js", methods=['GET'])
def tsne_js():
  return send_from_directory('train', 'tsne.js')


if __name__ == "__main__":
  app.debug = True
  app.run(host=os.getenv('IP', '0.0.0.0'),port=int(os.getenv('PORT', 8080)))
