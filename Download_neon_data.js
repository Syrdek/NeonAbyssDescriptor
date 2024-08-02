// Snippet to use in developer console on https://neonabyss.fandom.com/wiki/Items and https://neonabyss.fandom.com/wiki/Weapons pages to dump the data as json config.

function get_img_slug(url) {
    if (url == null) return null;
    return get_img_name(url).replace(/\.[^.]*$/, '');
}

function get_img_name(url) {
    if (url == null) return null;
    return get_img_url(url).replace(/^.*\//, '');
}

function get_img_url(url) {
    if (url == null) return null;
    return url.replace(/\/revision\/.*$/, '');
}

function direct_text_content(node) {
    const cNodes = node.childNodes;
    let text = ""
    for (const cNode of cNodes) {
        if (cNode.nodeValue != null) {
            text = text + cNode.nodeValue;
        }
    }
    return text;
}

function download_img(url, name) {
    if (name == null) name = url.replace(/^.*\//, '');

    let dlAnchor = document.querySelector("a#downloadAnchor");
    if (dlAnchor == undefined) {
        dlAnchor = document.createElement('a');
        dlAnchor.setAttribute('download', true);
        dlAnchor.setAttribute('target', '_blank');
        dlAnchor.id="downloadAnchor";
        document.body.appendChild(dlAnchor);
    }

    dlAnchor.setAttribute("href", url);
    dlAnchor.setAttribute("download", name);
    dlAnchor.click();
}

function process_line(tr) {
    let imgLink = tr.querySelector("td:nth-child(1) a.image");
    let imgUrl = null;
    if (imgLink != null) {
        imgUrl = imgLink.href;
    } else {
        imgLink = tr.querySelector("td:nth-child(1) img");
        if (imgLink == null) {
            return;
        }
        imgUrl = imgLink.src;
    }
    if (imgUrl == null) {
        return;
    }

    let itemName = tr.querySelector("td:nth-child(2)")
    if (itemName == null) {
        console.log("Item ", imgUrl, " has no name !")
        return;
    }

    let itemSetNode = itemName.querySelector("img")
    let itemSet = null;
    if (itemSetNode != null) {
        itemSetNode = itemSetNode.getAttribute("data-src");
        itemSet = {
            "name": get_img_name(itemSetNode),
            "url": get_img_url(itemSetNode),
            "slug": get_img_slug(itemSetNode)
        }
    }

    let itemDesc = tr.querySelector("td:nth-child(3)")
    if (itemDesc == null) {
        console.log("Item ", imgUrl, " has no desc !")
        return;
    }

    let lineData = {
        "imgUrl": get_img_url(imgUrl),
        "imgName": get_img_name(imgUrl),
        "slug": get_img_slug(imgUrl),
        "name": itemName.textContent.trim(),
        "desc": itemDesc.textContent.trim(),
        "itemSet": itemSet
    }

    let itemMode = tr.querySelector("td:nth-child(4)")
    if (itemMode != null) {
        lineData["type"] = "weapon";
        lineData["fire-mode"] = itemMode.textContent;
    } else {
        lineData["type"] = "item";
    }

    let itemAtkType = tr.querySelector("td:nth-child(5)")
    if (itemAtkType != null) {
        lineData["atk"] = itemAtkType.textContent;
    }

    let itemAbility = tr.querySelector("td:nth-child(6)")
    if (itemAbility != null) {
        lineData["passive"] = direct_text_content(itemAbility).trim();
        let activeAbilities = [];
        for (const itemActive of itemAbility.querySelectorAll("a")) {
            console.log("active", itemActive)
            let abilityName = itemActive.textContent;
            if (abilityName != null && abilityName.trim().length > 0) {
                activeAbilities.push({"url":itemActive.href, "name":abilityName.trim()});
            }
        }
        lineData["active"] = activeAbilities;
    }

    return lineData;
}

let jsonData = [];
for (const line of document.querySelectorAll("table.wikitable.mw-collapsible tr")) {
    let lineData = process_line(line);
    if (lineData != null) {
        jsonData.push(lineData);
    }
}

console.log(jsonData);
