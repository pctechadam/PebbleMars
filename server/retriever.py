import requests
from pprint import pprint
import os
import json
from PIL import Image 
from os import path
import time
import math
import struct
import base64

IMAGE_DIR_RAW = path.join(path.dirname(__file__), 'images_raw')
IMAGE_DIR_PROCESSED = path.join(path.dirname(__file__), 'images_processed')

WORD_SIZE = 4
IMAGE_WIDTH = 144
IMAGE_HEIGHT = 168
IMAGE_COLS = float(IMAGE_WIDTH) / (8 * WORD_SIZE)
IMAGE_ROWS = IMAGE_HEIGHT
IMAGE_PADDING_BYTES = int(IMAGE_COLS % 1 * WORD_SIZE);

print IMAGE_DIR_PROCESSED

def getLatestUrl():
	response = requests.get('http://mars.jpl.nasa.gov/msl-raw-images/image/image_manifest.json')
	data = response.json()

	latest_sol = data['sols'][-1]
	sol_url = latest_sol['catalog_url']
	return sol_url
	
	
	
def getLatestImages(image_count):
	
	response = requests.get(getLatestUrl())
	data = response.json()
	
	images = data['images']
	# Filter
	filtered = [i for i in images
		if 'NAV_' in i['instrument'] and i["sampleType"] == "full"]
	
	print 'filtered length: ', len(filtered)
	if len(filtered) == 0:
		print 'warning, filtered image len == 0.  Adding all images back in'
		filtered = [i for i in images if i["sampleType"] == "full"]
		print 'new filtered len: ', len(filtered)

	metadata = []
	for i in filtered:
		metadata.append({'instrument' : i['instrument'],
			'url' : i['urlList'],
			'utc' : i['utc'],
			'id' : i['itemName'],
			'site' : i['site'],
			'sol' : i['sol']
			})
	return metadata
	
def saveRawImages(images):
	# Remove old images
	print 'removing old images'
	for name in os.listdir(IMAGE_DIR_RAW):
		os.remove(path.join(IMAGE_DIR_RAW, name))
	for i in images:
		i['filename'] = i['id'] + '.jpg'
		outFile = open(path.join(IMAGE_DIR_RAW, i['filename']), 'w')
		request = requests.get(i['url'], stream=True)
		for block in request.iter_content(1024):
			if not block:
				break
		 	outFile.write(block)
		outFile.close()
		print 'saving: ', i['id'], '.png'
	outManifest = open(path.join(IMAGE_DIR_RAW, 'manifest.json'), 'w')
	outManifest.write(json.dumps(images))
	outManifest.close()
	#TODO: Save JSON manifest

def getImageData(filename):
	#Load
	img = Image.open(filename) # open colour image
	
	#Scale
	dims = (IMAGE_WIDTH, IMAGE_HEIGHT)
	img.thumbnail(dims, Image.ANTIALIAS)
	
	#Black and white
	img = img.convert('1') # convert image to black and white

	#Save Temp
	img.save(path.join(IMAGE_DIR_PROCESSED, filename.split('/')[-1].split('.')[0] + ".png"))

	# Convert to bytestream
	bytes = []
	for i in range(img.size[0]):
		for j in range(img.size[1]):
			bytes.append(int(bool(img.getpixel((j,i)))))
		if IMAGE_PADDING_BYTES > 0:
			for k in range(IMAGE_PADDING_BYTES * 8):
				bytes.append(0)
	return bytes

def processImages():
	image_files = os.listdir(IMAGE_DIR_RAW)
	f = open(path.join(IMAGE_DIR_RAW, 'manifest.json'), 'r')
	manifest = json.loads(f.read())
	f.close()

	response = []
	for obj in manifest:
		data = getImageData(path.join(IMAGE_DIR_RAW, obj['filename']))
		data_bytes = []
		data_str = [str(d) for d in data]
		word_bits = 8 * WORD_SIZE
		pos = 0
		chunk_id = 0
		for k in range(0, IMAGE_HEIGHT, 2):
			chunk_bytes = [struct.pack('B', chunk_id)]
			chunk_id += 1
			for j in range(k, k+4):
				for i in range(int(math.ceil(IMAGE_COLS))):
					nums = data_str[word_bits*pos:word_bits*(pos+1)][::-1]
					pos += 1
					if len(nums) == 0:
						break
					chunk_bytes.append(struct.pack('I', int(''.join(nums), 2)))
			if len(chunk_bytes) == 0:
				break
			data_bytes.append(base64.b64encode(''.join(chunk_bytes)))
		secs = time.mktime(time.localtime()) - time.mktime(time.strptime("2013-08-30T15:07:12Z", "%Y-%m-%dT%H:%M:%SZ"))
		hours = int(secs/3600)
		if hours == 0:
			rel_time = str(int(secs/61)) + ' mins '
		else:
			rel_time = str(hours) + ' hours '
		rel_time += 'ago'
		response.append({
			#'data' : data,
			'word_size' : WORD_SIZE,
			'data_bytes' : data_bytes,
			'width' : IMAGE_WIDTH,
			'height' : IMAGE_HEIGHT,
			'rel_time' : rel_time,
			'filename' : obj['filename'].replace('jpg', 'png'),
			'instrument' : obj['instrument'],
			'utc' : obj['utc'],
			'site': obj['site'],
			'sol': obj['sol']
		})
	print 'Writing output file...'
	f = open(path.join(IMAGE_DIR_PROCESSED, 'manifest.json'), 'w')
	f.write(json.dumps(response))
	f.close()
	return response

def main(image_count):
	images = getLatestImages(image_count)
	pprint(images)
	saveRawImages(images)
	data = processImages()
	
	
if __name__ == '__main__':
	main(5)
	
	
	
	


