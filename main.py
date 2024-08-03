import json
import logging
import os.path
import re

import cv2 as cv
import numpy as np
import requests
from PIL import Image

from screener import Screener
from translate import Translator
from overlay import OverlayWindow

import threading


def img_convert(img: Image, color=cv.COLOR_BGR2GRAY):
    img2 = np.array(img.convert('RGB'))
    if color is not None:
        return cv.cvtColor(img2, color)
    else:
        return img2


def mask(img: Image):
    _, im_mask = cv.threshold(np.array(img.convert('RGBA'))[:, :, 3], 0, 255, cv.THRESH_BINARY)
    return im_mask


def find_object_via_template_matcher(obj_img, screen_img, method=cv.TM_SQDIFF, mask=None):
    h, w = obj_img.shape[0], obj_img.shape[1]
    sh, sw = screen_img.shape[0], screen_img.shape[1]

    try:
        res = cv.matchTemplate(screen_img, obj_img, method, mask=mask)
        min_val, max_val, min_loc, max_loc = cv.minMaxLoc(res)

        # If the method is TM_SQDIFF or TM_SQDIFF_NORMED, take minimum
        if method in [cv.TM_SQDIFF, cv.TM_SQDIFF_NORMED]:
            top_left = min_loc
            confidence = min_val
            if method == cv.TM_SQDIFF_NORMED:
                confidence = 1.0 - confidence
        else:
            top_left = max_loc
            confidence = max_val

        return top_left, (top_left[0] + w, top_left[1] + h), confidence
    except Exception as e:
        logging.exception(f"Error matching [{w},{h}] template against [{sw}, {sh}] {e}", stack_info=False)
        return (0, 0), (0, 0), 0


def search_items_via_template_matcher(screen, items):
    results = []
    for item in items:
        tl, br, confidence = find_object_via_template_matcher(item["img"], screen, cv.TM_SQDIFF_NORMED, mask=item["mask"])

        logging.info(f"{item['slug']} ({item['shape']}) : {confidence}")
        if confidence > config["threshold"]:
            results.append(item)

    return results

def search_items_via_orb(screen, items):
    item_proximity = []

    sift = cv.SIFT_create()

    kp2, des2 = sift.detectAndCompute(screen, None)
    for item in items:
        kp1, des1 = sift.detectAndCompute(item["img"], item["mask"])

        # BFMatcher with default params
        bf = cv.BFMatcher()
        matches = bf.knnMatch(des1, des2, k=2)

        # Apply ratio test
        good = []
        for m, n in matches:
            if m.distance < 0.75 * n.distance:
                good.append([m])

        logging.info(f"{item['slug']} ({item['shape']}) : {len(good)}")

        item_proximity.append((good, kp1, item))

        # Debug
        #cv.imwrite(f"res/{item['name']}_orb.png", cv.drawMatchesKnn(item["img"], kp1, screen, kp2, good, None, flags=cv.DrawMatchesFlags_NOT_DRAW_SINGLE_POINTS))

    item_proximity.sort(key=lambda i: len(i[0]))
    results = [item[2] for item in item_proximity if len(item[0]) >= 8]
    if len(results) == 0:
        return [item_proximity[-1][2]]
    return results

def make_transparent(img):
    img = img.convert('RGBA')
    data = img.getdata()
    # On considere que le pixel en haut à gauche est transparent
    firstpix = data[0]
    new_data = []
    for pix in data:
        if pix[0] == firstpix[0] and pix[1] == firstpix[1] and pix[2] == firstpix[2]:
            new_data.append((255, 255, 255, 0))
        else:
            new_data.append(pix)
    img.putdata(new_data)
    return img


def json_path(obj, *args):
    if obj is None:
        return None

    if len(args) <= 0:
        return obj

    if args[0] in obj:
        return json_path(obj[args[0]], *args[1:])

    return None


def merge_item(item, merged_name, abyss_item, *abyss_path):
    abyss_value = json_path(abyss_item, *abyss_path)
    if abyss_value:
        item[merged_name] = abyss_value


def load_abyssexplorer_db(dbpath):
    with open(dbpath, "r", encoding='utf-8') as f:
        return json.load(f)


def load_item_images(item, img_filter):
    slug = item["slug"]
    img_path = os.path.join("neondb/wiki/images", f"{slug}.png")

    if not os.path.exists(img_path):
        logging.info(f"Downloading {slug} from {item['imgUrl']}")
        r = requests.get(item["imgUrl"], allow_redirects=True)
        with open(img_path, "wb") as f:
            f.write(r.content)

    if "itemSet" in item and item["itemSet"]:
        set_slug = item['itemSet']['slug']
        set_img_path = os.path.join("neondb/wiki/images", f"itemset-{set_slug}.png")
        if not os.path.exists(set_img_path):
            logging.info(f"Downloading {set_slug} set from {item['itemSet']['url']}")
            r = requests.get(item['itemSet']['url'], allow_redirects=True)
            with open(set_img_path, "wb") as f:
                f.write(r.content)
        set_img = Image.open(set_img_path)
        d = set_img.getdata()
        item['itemSet']['img'] = img_convert(set_img, color=cv.COLOR_BGR2RGB)

    if "ratio" not in item:
        item["ratio"] = config["size_ratio"]

    img = make_transparent(Image.open(img_path))

    if config["trim_to_alpha"]:
        alpha = img.getchannel('A')
        img = img.crop(alpha.getbbox())

    iw, ih = img.size
    item["shape"] = (int(round(iw * item["ratio"])), int(round(ih * item["ratio"])))
    item["small-shape"] = (int(round(item["shape"][0] * config["small_size_ratio"])), int(round(item["shape"][1] * config["small_size_ratio"])))

    img = img.resize(item["shape"], Image.NEAREST)
    game_img = img_filter(img)
    item["img"] = game_img
    item["mask"] = mask(img)

    mini_img = img_convert(img.resize(item["small-shape"]), color=cv.COLOR_BGR2RGB)
    item["small-img"] = mini_img

    return item

def load_item_db(dbpath, img_filter, translator=None, save_translation=None):
    items = []
    for db in dbpath:
        with open(db, "r", encoding='utf-8') as f:
            items.extend(json.load(f))

    abyss_db = load_abyssexplorer_db(config["abyss_db"])

    for item in items:
        slug = item["slug"]

        abyss_slug = re.sub("[^a-z0-9]", "-", slug.lower()).strip('-')
        abyss_items = [i for i in abyss_db if i["slug"].lower() == abyss_slug]

        if len(abyss_items) > 0:
            abyss_item = abyss_items[0]
            logging.info(f"Merging abyss-db information about {abyss_item['slug']} into item {slug}")
            merge_item(item, "name", abyss_item, "name", config["language"])
            merge_item(item, "desc", abyss_item, "desc", config["language"])
        elif translator is not None:
            logging.info(f"Translating information about item {slug}")
            item["desc"] = translator.translate(item["desc"])

    if translator is not None and save_translation is not None:
        with open(save_translation, "w") as f:
            json.dump(items, f, indent=2)

    for item in items:
        load_item_images(item, img_filter)

    logging.info(f"{len(items)} images loaded")
    return items


def run_detection(screen, item_db, window, img_filter, search_method=search_items_via_template_matcher):
    window.set_message("Recherche en cours...")
    screen = img_filter(screen)
    found_items = search_method(screen, item_db)
    logging.info(f"Matched items are {[i['name'] for i in found_items]}")
    window.set_items(found_items)
    return found_items


def create_img_filter(gray=False, canny=False):
    if canny:
        return lambda img: cv.Canny(img_convert(img, cv.COLOR_BGR2GRAY), 50, 200)
    if gray:
        return lambda img: img_convert(img, cv.COLOR_BGR2GRAY)
    return lambda img: img_convert(img, cv.COLOR_BGR2RGB)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    logging.info("Reading BD...")
    with open("neondb/conf.js", "r", encoding="utf8") as config_fp:
        config = json.load(config_fp)

    translator = None
    if config["translate"]:
        translator = Translator(
            model_name=config["translator_model"],
            src_lang="eng_Latn",
            dst_lang=config["translator_lang"]
        )

    img_filter = create_img_filter(gray=not config["use_colors"])
    search_method = search_items_via_orb if config["use_sift"] else search_items_via_template_matcher

    item_db = load_item_db(
        dbpath=config["item_db"],
        img_filter=img_filter,
        translator=translator,
        save_translation=config["save_translated_path"]
    )

    logging.info("Ready !")

    window = OverlayWindow(
        quit_button=config["quit"],
        clear_button=config["clear"])
    window.column_size = config["column_size"]
    window.bgcolor = config["bgcolor"]
    window.fgcolor = config["fgcolor"]
    window.small_font = config["small_font"]
    window.large_font = config["large_font"]
    window.geometry(config["position"])
    window.overrideredirect(not config["decorated"])
    window.wm_attributes("-topmost", config["topmost"])
    window.set_message("Ready !")

    '''
    window.set_message("Waiting...")
    def thread_run():
        screen = Image.open(r"test_img/capture.png")
        run_detection(screen, item_db, window, img_filter=img_filter, search_method=search_method)

    thread = threading.Thread(target=thread_run)
    thread.daemon = True
    thread.start()
    window.run()
    '''

    screener = Screener(listener=lambda screen: run_detection(
        screen,
        item_db,
        window,
        img_filter=img_filter,
        search_method=search_method))
    screener.start()
    window.set_message("Waiting...")
    window.run()
