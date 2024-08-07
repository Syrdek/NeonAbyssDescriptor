import json
import logging
import os.path
import sys
import typing
from operator import itemgetter

import cv2 as cv
import numpy as np
import requests
from PIL import Image

import overlay
from screener import Screener
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


def search_items_via_template_matcher(screen, items: typing.List):
    matches = []
    for item in items:
        tl, br, confidence = find_object_via_template_matcher(item["img"], screen, cv.TM_SQDIFF_NORMED, mask=item["mask"])
        matches.append((confidence, item))

    matches.sort(key=itemgetter(0), reverse=True)
    results = [m[1] for m in matches if m[0] > config["threshold"]]
    if len(results) < 1:
        results = [matches[0][1]]

    return results


def search_items_via_orb(screen, items: typing.List):
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

        logging.info(f"{item['slug']} : {len(good)}")

        item_proximity.append((good, kp1, item))

        # Debug
        #cv.imwrite(f"res/{item['name']}_orb.png", cv.drawMatchesKnn(item["img"], kp1, screen, kp2, good, None, flags=cv.DrawMatchesFlags_NOT_DRAW_SINGLE_POINTS))

    item_proximity.sort(key=lambda i: len(i[0]))
    results = [item[2] for item in item_proximity if len(item[0]) >= 8]
    if len(results) == 0:
        return [item_proximity[-1][2]]
    return results


def make_transparent(img: Image):
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


def load_item_images(item: typing.List[typing.Dict], img_filter: typing.Callable):
    slug = item["slug"]
    img_path = os.path.join("neondb/images", f"{slug}.png")

    if not os.path.exists(img_path):
        logging.info(f"Downloading {slug} image from {item['imgUrl']} to {img_path}")
        r = requests.get(item["imgUrl"], allow_redirects=True)
        with open(img_path, "wb") as f:
            f.write(r.content)

    if "itemSet" in item and item["itemSet"]:
        set_slug = item['itemSet']['slug']
        set_img_path = os.path.join(config["images_path"], f"itemset-{set_slug}.png")
        if not os.path.exists(set_img_path):
            logging.info(f"Downloading {set_slug} set from {item['itemSet']['url']}")
            r = requests.get(item['itemSet']['url'], allow_redirects=True)
            with open(set_img_path, "wb") as f:
                f.write(r.content)
        set_img = Image.open(set_img_path)
        item['itemSet']['img'] = img_convert(set_img, color=cv.COLOR_BGR2RGB)

    img = make_transparent(Image.open(img_path))

    if config["trim_to_alpha"]:
        alpha = img.getchannel('A')
        img = img.crop(alpha.getbbox())

    iw, ih = img.size
    item["small-shape"] = (int(round(iw * config["small_size_ratio"])), int(round(ih * config["small_size_ratio"])))

    item["img"] = img_filter(img)
    item["mask"] = mask(img)

    mini_img = img_convert(img.resize(item["small-shape"]), color=cv.COLOR_BGR2RGB)
    item["small-img"] = mini_img

    return item


def load_item_db(dbpath: str, img_filter: typing.Callable, limit: typing.List = []):
    with open(dbpath, "r", encoding='utf-8') as f:
        items = json.load(f)

        if len(limit) > 0:
            items = [i for i in items if i["slug"] in limit]

        for item in items:
            load_item_images(item, img_filter)

    logging.info(f"{len(items)} images loaded")
    return items


def run_detection(screen: Image,
                  resolution_width: int,
                  resolution_height: int,
                  item_db: typing.List[typing.Dict],
                  window: overlay.OverlayWindow,
                  img_filter: typing.Callable,
                  search_method: typing.Callable = search_items_via_template_matcher):
    window.set_message("Searching...")

    ratio = config["original_width"] / resolution_width
    img_w, img_h = screen.size
    scaled_screen = screen.resize((int(img_w * ratio), int(img_h * ratio)), Image.Resampling.NEAREST)
    logging.info(f"Screen size : {resolution_width}x{resolution_height}. Image ratio: {screen.size} -> {scaled_screen.size}")
    logging.info(f"Item size: {item_db[0]['img'].shape}")

    screen = img_filter(scaled_screen)
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

    img_filter = create_img_filter(gray=not config["use_colors"])
    search_method = search_items_via_orb if config["use_sift"] else search_items_via_template_matcher

    item_db = load_item_db(
        dbpath=config["item_db"],
        img_filter=img_filter,
        limit=config["limit_to_slugs"]
    )

    logging.info("Ready !")

    window = OverlayWindow(
        quit_button=config["quit"],
        clear_button=config["clear"],
        language=config["language"],
        use_llm=config["use_llm_translation"],
    )
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
        for fname in os.listdir("test_img/resolutions"):
            screen = Image.open(f"test_img/resolutions/{fname}")
            run_detection(screen, screen.size[0], screen.size[1], item_db, window, img_filter=img_filter, search_method=search_method)

    thread = threading.Thread(target=thread_run)
    thread.daemon = False
    thread.start()
    #window.run()
    sys.exit(0)
    '''

    screener = Screener(listener=lambda screen, width, height: run_detection(
        screen,
        width,
        height,
        item_db,
        window,
        img_filter=img_filter,
        search_method=search_method))
    screener.start()
    window.set_message("Waiting...")
    window.run()
