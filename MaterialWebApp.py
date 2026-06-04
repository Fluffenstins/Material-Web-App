from flask import Flask, send_from_directory, request, render_template, redirect
from MaterialContainer import ContinuousMaterialManager
from LabelGen import CustomLabel
from MaterialCore import ITEM_SPACE, Site, Material
import os

app = Flask(__name__)


MATERIAL_APP = ContinuousMaterialManager()
MATERIAL_APP.load_json()


def load_webpage(path):
    with open(path, 'r', encoding='utf8') as file:
        ret = file.read()
    return ret


@app.route("/")
def hello_world():
    obj_id = request.args.get('obj_id', default="")
    try:
        obj = ITEM_SPACE[obj_id]
        if type(obj) is Site:
            return redirect(f"/site?site_id={obj_id}")
        if type(obj) is Material:
            return redirect(f"/material?item_id={obj_id}")
    except KeyError:
        pass
    return redirect("/site?site_id=24-176")


@app.route("/material")
def material_url():
    item_id = request.args.get('item_id', default="")
    material_obj = ITEM_SPACE[item_id]
    print(material_obj)
    return render_template(
        "MaterialPage.html",
        qr_code_url=f"{request.url_root}downloadQRCode?obj_id={material_obj.id}",
        material_obj=material_obj
    )


@app.route("/site")
def site_url():
    site_id = request.args.get('site_id', default="")
    try:
        site_obj = ITEM_SPACE[site_id]
    except KeyError:
        site_obj = MATERIAL_APP.find_site(site_id)
    if site_obj is not None:
        site_id = site_obj.site_id
        site_type = site_obj.site_type
        address = site_obj.address
        material_children = sorted([ITEM_SPACE[i] for i in site_obj.material_children], key=lambda x: x.item_id)
    else:
        site_id = "Not Found"
        address = "N/A"
        material_children = "N/A"
        site_type = "N/A"

    return render_template(
        "SitePage.html",
        qr_code_url=f"{request.url_root}downloadQRCode?obj_id={site_obj.id}",
        site_id=site_id,
        address=address,
        site_type=site_type,
        material_children=material_children
    )


@app.route("/downloadQRCode")
def download_qr_code():
    obj_id = request.args.get('obj_id', default=None)
    obj = ITEM_SPACE[obj_id]
    label = CustomLabel(obj.id, f"{request.root_url}?obj_id={obj_id}")
    label.save()
    return send_from_directory(
        directory="",
        path="label.pdf",
        as_attachment=True
    )


@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
