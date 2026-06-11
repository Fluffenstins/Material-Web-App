from flask import Flask, send_from_directory, request, render_template, redirect
import flask_login
from MaterialContainer import ContinuousMaterialManager
from LabelGen import CustomLabel
from MaterialCore import ITEM_SPACE, Site, Material, Action
import os

template_dir = os.path.abspath('Templates')
app = Flask(__name__, template_folder=template_dir)
app.secret_key = 'dbnfjGYGygJUGYUFYGUGUIYg7Y87G867G87gh8j89ty75F56fd54D54Ds546t7g'
login_manager = flask_login.LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

MATERIAL_APP = ContinuousMaterialManager()
MATERIAL_APP.load_json()

USERS = {}


class FlaskUser(flask_login.UserMixin):
    pass


@login_manager.user_loader
def user_loader(email):
    internal_user = MATERIAL_APP.find_user(email)
    if internal_user is None:
        return
    user = FlaskUser()
    user.id = internal_user.id
    return user


@login_manager.request_loader
def request_loader(request):
    email = request.form.get('email')
    if email in USERS:
        return USERS[email]

    internal_user = MATERIAL_APP.find_user(email)
    if internal_user is None:
        return

    user = FlaskUser()
    user.id = internal_user.id
    return user


def check_credentials(necessary_credential=None):
    user_id = flask_login.current_user.id


# def fill_json(obj_json):
#     for key, val in obj_json.items():
#         if key in ['id']:
#             continue
#         if type(val) != str:
#             continue
#         try:
#             obj_json[key] = ITEM_SPACE[val].json()
#         except KeyError:
#             pass
#
#     def prune_keys(given_dict, pruned_keys):
#         for key in list(given_dict.keys()):
#             if key not in pruned_keys:
#                 continue
#             given_dict[key] = 'PRUNED'
#             # del given_dict[key]
#
#         for key, val in given_dict.items():
#             if type(val) is dict:
#                 prune_keys(val, pruned_keys)
#         return given_dict
#
#     prune_keys(obj_json, {'action_history'})
#
#     return obj_json

def list_all_sites():
    site_objs = [{'id': key, 'text': val.site_id} for key, val in MATERIAL_APP.sites.items()]
    site_objs = sorted(site_objs, key=lambda x: x['text'])
    return site_objs


def list_action_history_breakdown(obj):
    action_objs = [MATERIAL_APP.lookup(i) for i in obj.action_history[::-1]]
    action_history = [{'id': i.id, 'text': i.display_text()} for i in action_objs]
    return action_history


@app.route("/")
def home_page():
    obj_id = request.args.get('obj_id', default="")
    try:
        obj = ITEM_SPACE[obj_id]
        print(obj.json())
        if type(obj) is Site:
            return redirect(f"/site?site_id={obj_id}")
        if type(obj) is Material:
            return redirect(f"/material?item_id={obj_id}")
        if type(obj) is Action:
            return redirect(f"/action?action_id={obj_id}")
    except KeyError:
        pass
    return redirect("/sites")


@app.route("/material")
@flask_login.login_required
def material_url():
    item_id = request.args.get('item_id', default="")
    material_obj = ITEM_SPACE[item_id]

    try:
        user_obj = MATERIAL_APP.find_user(flask_login.current_user.id)
        # action_history = [{'id': ITEM_SPACE[i].id, 'text': ITEM_SPACE[i].display_text()} for i in material_obj.action_history]
        action_history = list_action_history_breakdown(material_obj)

    except AttributeError:
        user_obj = None
        action_history = 'N/A'

    return render_template(
        "MaterialPage.html",
        qr_code_url=f"{request.url_root}downloadQRCode?obj_id={material_obj.id}",
        material_obj=material_obj,
        user_obj=user_obj,
        action_history=action_history,
        current_tab="Material"
    )


@app.route("/action")
@flask_login.login_required
def action_url():
    action_id = request.args.get('action_id', default="")
    action_obj = ITEM_SPACE[action_id]
    print(action_obj.json())
    try:
        action_user_obj = ITEM_SPACE[action_obj.user]
    except KeyError:
        action_user_obj = None

    try:
        user_obj = MATERIAL_APP.find_user(flask_login.current_user.id)
    except AttributeError:
        user_obj = None

    interpreted_data = {}

    for key, value in action_obj.data.items():
        try:
            interpreted_data[key] = [ITEM_SPACE[value].display_name, f"{request.url_root}?obj_id={value}"]
        except:
            interpreted_data[key] = [value]

    interpreted_output = {}

    for key, value in action_obj.output.items():
        try:
            interpreted_output[key] = [ITEM_SPACE[value].display_name, f"{request.url_root}?obj_id={value}"]
        except:
            interpreted_output[key] = [value]

    return render_template(
        "ActionPage.html",
        qr_code_url=f"{request.url_root}downloadQRCode?obj_id={action_obj.id}",
        action_obj=action_obj,
        user_obj=user_obj,
        action_user_obj=action_user_obj,
        current_tab="Action",
        interpreted_data=interpreted_data,
        interpreted_output=interpreted_output
    )


@app.route("/site")
@flask_login.login_required
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
        material_children = sorted([{'id': ITEM_SPACE[i].id, 'text': ITEM_SPACE[i].item.item_id} for i in site_obj.material_children], key=lambda x: x['text'])
        parent_sites = sorted([{'id': ITEM_SPACE[i].id, 'text': ITEM_SPACE[i].name} for i in site_obj.parent_site_ids], key=lambda x: x['text'])
        site_children = sorted([{'id': ITEM_SPACE[i].id, 'text': ITEM_SPACE[i].name} for i in site_obj.site_children], key=lambda x: x['text'])
        action_history = list_action_history_breakdown(site_obj)
    else:
        site_id = "Not Found"
        address = "N/A"
        material_children = "N/A"
        site_children = "N/A"
        parent_sites = "N/A"
        action_history = "N/A"
        site_type = "N/A"

    try:
        user_obj = MATERIAL_APP.find_user(flask_login.current_user.id)
    except AttributeError:
        user_obj = None

    return render_template(
        "SitePage.html",
        qr_code_url=f"{request.url_root}downloadQRCode?obj_id={site_obj.id}",
        set_parent_url=f"{request.url_root}setSiteParent?site_id={site_obj.id}",
        site_id=site_id,
        address=address,
        site_type=site_type,
        material_children=material_children,
        parent_sites=parent_sites,
        site_children=site_children,
        action_history=action_history,
        user_obj=user_obj,
        current_tab="Site"
    )


@app.route("/setSiteParent", methods=['GET'])
@flask_login.login_required
def set_site_parent_page():
    site_id = request.args.get('site_id', default="")
    parent_site_id = request.args.get('site_parent', default="")

    try:
        user_obj = MATERIAL_APP.find_user(flask_login.current_user.id)
    except AttributeError:
        user_obj = None

    try:
        site_obj = ITEM_SPACE[site_id]
    except KeyError:
        site_obj = MATERIAL_APP.find_site(site_id)

    parent_site_obj = MATERIAL_APP.find_site(parent_site_id)

    print((user_obj, site_obj, parent_site_obj))

    if None not in (user_obj, site_obj, parent_site_obj):
        MATERIAL_APP.set_site_parent(user_obj.id, site_obj.id, parent_site_obj.id)
        MATERIAL_APP.save_json()
        return redirect(f"/site?site_id={parent_site_id}")

    site_objs = list_all_sites()

    return render_template(
        "SetSiteParentPage.html",
        site_url=f"{request.url_root}/?obj_id={site_obj.id}",
        site_obj=site_obj,
        user_obj=user_obj,
        site_objs=site_objs,
        current_tab="Site"
    )


@app.route("/sites")
@flask_login.login_required
def sites_directory_url():

    site_objs = [{'id': key, 'text': val.site_id} for key, val in MATERIAL_APP.sites.items()]
    site_objs = sorted(site_objs, key=lambda x: x['text'])

    try:
        user_obj = MATERIAL_APP.find_user(flask_login.current_user.id)
    except AttributeError:
        user_obj = None

    return render_template(
        "SitesDirectory.html",
        current_tab="Sites",
        site_objs=site_objs,
        user_obj=user_obj,
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


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'GET':
        return render_template(
            "RegisterUser.html"
        )

    email = request.form.get('email')
    password = request.form.get('password')
    first_name = request.form.get('firstName')
    last_name = request.form.get('lastName')
    if None in (email, password, first_name, last_name):
        return

    ret = MATERIAL_APP.create_user(
        email=email,
        password=password,
        first_name=first_name,
        last_name=last_name
    )

    user = user_loader(email)
    flask_login.login_user(user)
    USERS[ret.id] = user

    MATERIAL_APP._save_core_dict_json(MATERIAL_APP.users, "users")

    return redirect("site?site_id=OLT1")


@app.route('/login', methods=['GET', 'POST'])
def login():
    next_url = request.args.get('next', default="")
    if request.method == 'GET':
        if flask_login.current_user.is_authenticated:
            if next_url:
                return redirect(next_url)
            else:
                return redirect("site?site_id=OLT1")
        print("Trying sincerely to log in.")
        print(f"Path: {template_dir}")
        return render_template(
            "Login.html"
        )

    email = request.form.get('email')
    password = request.form.get('password')

    if email is None or password is None:
        return render_template(
            "Login.html"
        )

    user = user_loader(email)
    if user is None:
        return redirect('register')

    user_obj = MATERIAL_APP.find_user(email)

    # need to check password
    if not user_obj.check_password(password):
        print(f"Password didn't match: {user_obj.password}")
        return render_template(
            "Login.html"
        )

    ret = flask_login.login_user(user)
    USERS[user_obj.id] = user
    if not next_url:
        return redirect("site?site_id=OLT1")
    return redirect(next_url)


@app.route('/logout', methods=['GET', 'POST'])
def logout():
    flask_login.logout_user()
    return redirect('/login')


@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():

    return render_template(
        "Login.html"
    )


if __name__ == '__main__':
    print(app.template_folder)
    app.run(host='0.0.0.0', port=5000)
