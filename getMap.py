#!/bin/python3
# Grabs and returns the latest high res map from MiHoYo
#
# Some useful API locations are:
#
# For map layers: https://sg-public-api-static.hoyolab.com/common/map_user/ys_obc/v2/map/point_group?map_id=2&app_sn=ys_obc&lang=en-us
# For map slices: https://sg-public-api-static.hoyolab.com/common/map_user/ys_obc/v1/map/info?map_id=2&app_sn=ys_obc&lang=en-us

import requests
import json
import PIL
from PIL import Image, ImageEnhance
from io import BytesIO
import sys
import math

# Because the image is massive
PIL.Image.MAX_IMAGE_PIXELS = 933120000

map_number = 2
overlay_ids = []
if len(sys.argv) > 1:
    map_number = sys.argv[1]
if len(sys.argv) > 2:
    overlay_ids = sys.argv[2].split(",")

map_link = "https://sg-public-api-static.hoyolab.com/common/map_user/ys_obc/v1/map/info?map_id=" + str(map_number) + "&app_sn=ys_obc&lang=en-us"

returned_json = json.loads(requests.get(map_link).text)
if returned_json['message'] != 'OK':
    print("ERROR: \"" + returned_json['message'] + "\"")
    exit(1)

details = returned_json['data']['info']['detail']
if details == "":
    print("ERROR: Details key empty")
    exit(1)

details = json.loads(details)

name = returned_json['data']['info']['name']

print("Downloading map of \"" + name + "\", ID is " + str(map_number))

ori_x, ori_y = details['origin']
x, y = details['total_size']
pad_x, pad_y = details['padding']
slices = details['slices']

grid = Image.new('RGBA', size=(x, y))

print(f"Origin:     [{ori_x}, {ori_y}]")
print(f"Resolution: [{x}, {y}]")

# Download the map slices
numslices = len(slices[0]) * len(slices)
print("Downloading " + str(numslices) + " slices...")
wrapper = "["
wrapper += ' ' * numslices
wrapper += "]"
print(wrapper)
print('\033[1A\033[1C', end='', flush=True)
w = 0
for slice in slices:
    img_x = int(x / len(slice))
    img_y = int(y / len(slices))

    h = 0
    for img in slice:
        url = img['url']

        print('#', end='', flush=True)

        response = requests.get(url)
        file_img = BytesIO(response.content)
        decoded_img = Image.open(file_img)
        grid.paste(decoded_img,
                   box=(img_x * h,
                        img_y * w,
                        (img_x * h) + img_x,
                        (img_y * w) + img_y
                        )
                   )

        h += 1
    w += 1
print("")
print("Finished downloading!")

if len(overlay_ids) > 0:
    overlay_link = " https://sg-public-api-static.hoyolab.com/common/map_user/ys_obc/v2/map/point_group?map_id=" + str(map_number) + "&app_sn=ys_obc&lang=en-us"

    returned_json = json.loads(requests.get(overlay_link).text)
    if returned_json['message'] != 'OK':
        print("ERROR: \"" + returned_json['message'] + "\"")
        exit(1)

    details = returned_json['data']['list']
    if details == []:
        print("ERROR: Details key empty")
        exit(1)

    print("Downloading " + str(len(overlay_ids)) + " overlays...")
    # Download the overlay images
    for num, layer in enumerate(overlay_ids):
        percent = round((num / len(overlay_ids)) * 100)
        print(str(percent) + "%", end='\r', flush=True)

        floors = details[int(layer)]['floors']
        floors.reverse()
        for i, floor in enumerate(floors):
            url = floor['overlay']['url']
            l_x = floor['overlay']['l_x']
            l_y = floor['overlay']['l_y']

            r_x = floor['overlay']['r_x']
            r_y = floor['overlay']['r_y']

            size_x = round(r_x - l_x)
            size_y = round(r_y - l_y)

            try:
                response = requests.get(url)
            except:
                continue
            file_img = BytesIO(response.content)
            decoded_img = Image.open(file_img)
            decoded_img = decoded_img.convert('RGBA')
            decoded_img = decoded_img.resize((size_x, size_y))
            enhancer = ImageEnhance.Brightness(decoded_img)
            decoded_img = enhancer.enhance(0.9 - (len(floors) - i) * 0.1)

            grid.paste(decoded_img,
                       box=(ori_x + math.floor(l_x),
                            ori_y + math.floor(l_y)),
                       mask=decoded_img.split()[3])
    print()
    print("Finished downloading overlays!")

print("Cropping...")
grid = grid.crop((pad_x, pad_y, (x - pad_x), (y - pad_y)))

grid = grid.convert('RGB')

print("Saving jpg...")
grid.save(name + ".jpg")

print("Saving png...")
grid.save(name + ".png")
