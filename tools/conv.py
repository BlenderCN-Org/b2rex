# convert yaml declaration files to json for needing less dependencies since
# json is directly supported by python library.
import json
import yaml

f=open('llsd.yml')
data=f.read()
f.close()

f = open('llsd.json', "w")
f.write(json.dumps(yaml.load(data)))
f.close()

f=open('rex_com.yml')
data=f.read()
f.close()

f = open('rex_com.json', "w")
f.write(json.dumps(yaml.load(data)))
f.close()

