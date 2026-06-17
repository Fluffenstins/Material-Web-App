from flask import Flask, send_from_directory, request, render_template, redirect, jsonify, url_for
import flask_login
from MaterialContainer import ContinuousMaterialManager
from LabelGen import CustomLabel
from MaterialCore import Site, Material, Action, User, CataloguedItem
import os
from dateutil import parser

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


def list_all_sites():
    site_objs = [{'id': key, 'text': val.site_id} for key, val in MATERIAL_APP.sites.items()]
    site_objs = sorted(site_objs, key=lambda x: x['text'])
    return site_objs


def list_all_catalogue_items():
    valid_ids = {val.get_item().id for key, val in MATERIAL_APP.items.items()}
    catalogue_objs = [{'id': key, 'text': MATERIAL_APP.items[key].item_id} for key in valid_ids]
    catalogue_objs = sorted(catalogue_objs, key=lambda x: x['text'])
    return catalogue_objs


def list_action_history_breakdown(obj):
    action_objs = [MATERIAL_APP.lookup(i) for i in obj.action_history[::-1]]
    action_history = [{'id': i.id, 'text': i.display_text()} for i in action_objs]
    return action_history


@app.route("/")
def home_page():
    obj_id = request.args.get('obj_id', default="")
    from_qr = request.args.get('from_qr', default="")
    try:
        obj = MATERIAL_APP.lookup(obj_id)
        print(obj.json())
        if type(obj) is Site:
            if obj.is_intermediate and from_qr != '':
                return redirect(f"/intermediateSite?site_id={obj_id}")
            return redirect(f"/site?site_id={obj_id}")
        if type(obj) is Material:
            return redirect(f"/material?item_id={obj_id}")
        if type(obj) is Action:
            return redirect(f"/action?action_id={obj_id}")
        if type(obj) is User:
            return redirect(f"/user?user_id={obj_id}")
        if type(obj) is CataloguedItem:
            return redirect(f"/catalogue?item_id={obj_id}")
    except KeyError:
        pass
    return redirect("/sites")


@app.route("/material")
@flask_login.login_required
def material_url():
    item_id = request.args.get('item_id', default="")
    material_obj = MATERIAL_APP.lookup(item_id)

    try:
        user_obj = MATERIAL_APP.find_user(flask_login.current_user.id)
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


@app.route("/user")
@flask_login.login_required
def user_url():
    user_id = request.args.get('user_id', default="")
    displayed_user_obj = MATERIAL_APP.lookup(user_id)

    try:
        user_obj = MATERIAL_APP.find_user(flask_login.current_user.id)
        action_history = list_action_history_breakdown(displayed_user_obj)

    except AttributeError:
        user_obj = None
        action_history = 'N/A'

    return render_template(
        "UserPage.html",
        qr_code_url=f"{request.url_root}downloadQRCode?obj_id={displayed_user_obj.id}",
        displayed_user_obj=displayed_user_obj,
        user_obj=user_obj,
        action_history=action_history,
        current_tab="User"
    )


@app.route("/chart")
def user_chart_url():
    return render_template(
        "ChartTemplate.html"
    )


@app.route("/catalogue")
@flask_login.login_required
def catalogue_url():
    item_id = request.args.get('item_id', default="")
    catalogue_item_obj = MATERIAL_APP.lookup(item_id)

    try:
        user_obj = MATERIAL_APP.find_user(flask_login.current_user.id)
        action_history = list_action_history_breakdown(catalogue_item_obj)
    except AttributeError:
        user_obj = None
        action_history = 'N/A'

    aliases = [MATERIAL_APP.lookup(i) for i in catalogue_item_obj.deprecated_items]
    aliases = sorted(aliases, key=lambda x: x.item_id)
    aliases = [{'id': i.id, 'text': i.item_id} for i in aliases]

    deprecated_status = catalogue_item_obj.correct_item is not None
    deprecated_status = True

    return render_template(
        "CataloguePage.html",
        qr_code_url=f"{request.url_root}downloadQRCode?obj_id={catalogue_item_obj.id}",
        catalogue_item_obj=catalogue_item_obj,
        aliases=aliases,
        user_obj=user_obj,
        action_history=action_history,
        deprecated_status=deprecated_status,
        current_tab="Catalogue Item"
    )


@app.route("/action")
@flask_login.login_required
def action_url():
    action_id = request.args.get('action_id', default="")
    action_obj = MATERIAL_APP.lookup(action_id)
    print(action_obj.json())
    try:
        action_user_obj = MATERIAL_APP.lookup(action_obj.user)
    except KeyError:
        action_user_obj = None

    try:
        user_obj = MATERIAL_APP.find_user(flask_login.current_user.id)
    except AttributeError:
        user_obj = None

    # interpreted_data = {}
    #
    # for key, value in action_obj.data.items():
    #     try:
    #         interpreted_data[key] = [MATERIAL_APP.lookup(value).display_name, f"{request.url_root}?obj_id={value}"]
    #     except:
    #         interpreted_data[key] = [value]
    interpreted_data = {}

    for key, value in action_obj.data.items():
        interpreted_data[key] = [value]

    interpreted_output = {}

    for key, value in action_obj.output.items():
        try:
            interpreted_output[key] = [MATERIAL_APP.lookup(value).display_name, f"{request.url_root}?obj_id={value}"]
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
        site_obj = MATERIAL_APP.lookup(site_id)
    except KeyError:
        site_obj = MATERIAL_APP.find_site(site_id)
    if site_obj is not None:
        site_id = site_obj.site_id
        site_type = site_obj.site_type
        address = site_obj.address
        material_children = sorted([{'id': MATERIAL_APP.lookup(i).id, 'text': MATERIAL_APP.lookup(i).item.item_id} for i in site_obj.material_children], key=lambda x: x['text'])
        parent_sites = sorted([{'id': MATERIAL_APP.lookup(i).id, 'text': MATERIAL_APP.lookup(i).name} for i in site_obj.parent_site_ids], key=lambda x: x['text'])
        site_children = sorted([{'id': MATERIAL_APP.lookup(i).id, 'text': MATERIAL_APP.lookup(i).name} for i in site_obj.site_children], key=lambda x: x['text'])
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
        site_obj=site_obj,
        material_children=material_children,
        parent_sites=parent_sites,
        site_children=site_children,
        action_history=action_history,
        user_obj=user_obj,
        current_tab="Site"
    )


@app.route("/intermediateSite")
@flask_login.login_required
def intermediate_site_url():
    site_id = request.args.get('site_id', default="")
    try:
        site_obj = MATERIAL_APP.lookup(site_id)
    except KeyError:
        site_obj = MATERIAL_APP.find_site(site_id)

    if site_obj is not None:
        site_id = site_obj.site_id
        site_type = site_obj.site_type
        address = site_obj.address
        material_children = sorted([{'id': MATERIAL_APP.lookup(i).id, 'text': MATERIAL_APP.lookup(i).item.item_id} for i in site_obj.material_children], key=lambda x: x['text'])
        parent_sites = sorted([{'id': MATERIAL_APP.lookup(i).id, 'text': MATERIAL_APP.lookup(i).name} for i in site_obj.parent_site_ids], key=lambda x: x['text'])
        site_children = sorted([{'id': MATERIAL_APP.lookup(i).id, 'text': MATERIAL_APP.lookup(i).name} for i in site_obj.site_children], key=lambda x: x['text'])
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
        "IntermediateSite.html",
        qr_code_url=f"{request.url_root}downloadQRCode?obj_id={site_obj.id}",
        set_parent_url=f"{request.url_root}setSiteParent?site_id={site_obj.id}",
        site_obj=site_obj,
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


@app.route("/receive", methods=['GET'])
@flask_login.login_required
def receive_material_page():
    location_id = request.args.get('location_id', default="")
    project_id = request.args.get('project_id', default="")
    catalogue_id = request.args.get('item_id', default="")
    site_id = request.args.get('site_id', default="")
    if site_id is not None:
        site_obj = MATERIAL_APP.find_site(site_id)
        if site_obj.site_type == 'project':
            project_id = site_obj.id
        elif site_obj.site_type == 'location':
            location_id = site_obj.id

    try:
        user_obj = MATERIAL_APP.find_user(flask_login.current_user.id)
    except AttributeError:
        user_obj = None

    location_obj = MATERIAL_APP.find_site(location_id)
    project_obj = MATERIAL_APP.find_site(project_id)
    catalogue_obj = MATERIAL_APP.find_item(catalogue_id)

    site_objs = list_all_sites()
    catalogue_objs = list_all_catalogue_items()

    return render_template(
        "ReceiveMaterialPage.html",
        location_obj=location_obj,
        project_obj=project_obj,
        catalogue_obj=catalogue_obj,
        user_obj=user_obj,
        site_objs=site_objs,
        catalogue_objs=catalogue_objs,
        current_tab="Receive"
    )


@app.route("/transfer", methods=['GET'])
@flask_login.login_required
def transfer_material_page():
    source_site_id = request.args.get('source_id', default="")
    target_site_id = request.args.get('target_id', default="")
    catalogue_id = request.args.get('item_id', default="")

    try:
        user_obj = MATERIAL_APP.find_user(flask_login.current_user.id)
    except AttributeError:
        user_obj = None

    source_obj = MATERIAL_APP.find_site(source_site_id)
    target_obj = MATERIAL_APP.find_site(target_site_id)
    catalogue_obj = MATERIAL_APP.find_item(catalogue_id)

    print(source_obj, target_obj, catalogue_obj)

    site_objs = list_all_sites()
    catalogue_objs = list_all_catalogue_items()

    return render_template(
        "TransferMaterialPage.html",
        source_obj=source_obj,
        target_obj=target_obj,
        catalogue_obj=catalogue_obj,
        user_obj=user_obj,
        site_objs=site_objs,
        catalogue_objs=catalogue_objs,
        current_tab="Transfer Material"
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


@app.route("/locations")
@flask_login.login_required
def locations_directory_url():

    site_objs = [{'id': key, 'text': val.site_id} for key, val in MATERIAL_APP.sites.items() if val.site_type == 'location']
    site_objs = sorted(site_objs, key=lambda x: x['text'])

    try:
        user_obj = MATERIAL_APP.find_user(flask_login.current_user.id)
    except AttributeError:
        user_obj = None

    return render_template(
        "SitesDirectory.html",
        current_tab="Locations",
        site_objs=site_objs,
        user_obj=user_obj,
    )


@app.route("/projects")
@flask_login.login_required
def projects_directory_url():

    site_objs = [{'id': key, 'text': val.site_id} for key, val in MATERIAL_APP.sites.items() if val.site_type == 'project']
    site_objs = sorted(site_objs, key=lambda x: x['text'])

    try:
        user_obj = MATERIAL_APP.find_user(flask_login.current_user.id)
    except AttributeError:
        user_obj = None

    return render_template(
        "SitesDirectory.html",
        current_tab="Projects",
        site_objs=site_objs,
        user_obj=user_obj,
    )


@app.route("/stages")
@flask_login.login_required
def stages_directory_url():

    site_objs = [{'id': key, 'text': val.site_id} for key, val in MATERIAL_APP.sites.items() if val.site_type == 'intermediate']
    site_objs = sorted(site_objs, key=lambda x: x['text'])

    try:
        user_obj = MATERIAL_APP.find_user(flask_login.current_user.id)
    except AttributeError:
        user_obj = None

    return render_template(
        "SitesDirectory.html",
        current_tab="Stages",
        site_objs=site_objs,
        user_obj=user_obj,
    )


@app.route("/stage")
@flask_login.login_required
def stage_url():
    source_site_id = request.args.get('source_id', default="")
    target_site_id = request.args.get('target_id', default="")
    catalogue_id = request.args.get('item_id', default="")

    user_obj = MATERIAL_APP.find_user(flask_login.current_user.id)

    if not target_site_id:
        # find most recent intermediate site for user
        active_staging_sites = []
        for site_id, site_obj in MATERIAL_APP.sites.items():
            owner = site_obj.owner
            if owner is None:
                continue
            if site_obj.status != 'stage':
                continue
            if owner.id != user_obj.id:
                continue
            active_staging_sites.append(site_obj)

        if len(active_staging_sites) == 0:
            created_new_stage = True
            counter = 0
            stage_name = f"Stage {counter}"
            while MATERIAL_APP.find_site(stage_name) is not None:
                counter += 1
                stage_name = f"Stage {counter}"
            stage_obj = MATERIAL_APP.create_site(
                site_id=stage_name,
                site_type='intermediate',
                status='stage',
                user_id=user_obj.id
            )
            print(f"Creating Stage: {stage_obj.id} : {stage_obj.display_name}")
        else:
            stage_obj = sorted(active_staging_sites, key=lambda x: parser.parse(x.creation_date))[-1]
            print(f"Found Stage: {stage_obj.id} : {stage_obj.display_name}")
    else:
        stage_obj = MATERIAL_APP.find_site(target_site_id)
        print(f"Defaulting to Stage: {stage_obj.id} : {stage_obj.display_name}")

    source_obj = MATERIAL_APP.find_site(source_site_id)

    catalogue_obj = MATERIAL_APP.find_item(catalogue_id)

    args = "&".join([f"{key}={val.id}" for key, val in {'source_id': source_obj, 'target_id': stage_obj, 'item_id': catalogue_obj}.items() if val is not None])

    return redirect(
        f'/transfer?{args}')


@app.route("/downloadQRCode")
def download_qr_code():
    obj_id = request.args.get('obj_id', default=None)
    obj = MATERIAL_APP.lookup(obj_id)
    label = CustomLabel(obj.display_name, f"{request.root_url}?obj_id={obj_id}&from_qr=true")
    label.save()
    return send_from_directory(
        directory="",
        path="label.pdf",
        as_attachment=True
    )


@app.route('/updatePassword', methods=['GET', 'POST'])
def update_password():
    if request.method == 'GET':
        return render_template(
            "UpdatePassword.html"
        )

    email = request.form.get('email')
    password = request.form.get('password')
    if None in (email, password):
        return render_template(
            "UpdatePassword.html"
        )

    user_obj = MATERIAL_APP.find_user(email=email)
    user_obj.password = user_obj.hash_password(password)

    return redirect("login")


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
        print(f"error registering {(email, password, first_name, last_name)}")
        return

    try:
        ret = MATERIAL_APP.create_user(
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name
        )
    except KeyError:
        return redirect('/login')

    user = user_loader(email)
    flask_login.login_user(user)
    USERS[ret.id] = user

    MATERIAL_APP.save_json()

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
        return redirect("sites")
    return redirect(next_url)


@app.route('/logout', methods=['GET', 'POST'])
def logout():
    flask_login.logout_user()
    return redirect('/login')


@app.route('/api/site', methods=['GET', 'POST', 'PATCH'])
def api_site():
    # get
    # return site json

    # post
    # create site, return json

    # patch
    # adjust specific site obj attributes
    # allow to note whether appending to a list or popping when relevant.
    # assume that if append/pop is not provided, that we are adding.
    if request.method == 'GET':
        # return a site
        raise NotImplementedError
    if request.method == 'POST':
        # create a site
        data = request.get_json()
        site_id = data.get('site_id')
        site_type = data.get('site_type')

        user_obj = MATERIAL_APP.find_user(flask_login.current_user.id)

        existing_site_obj = MATERIAL_APP.find_site(site_id)
        if existing_site_obj is not None:
            return jsonify({"error": f"Site {site_id} already exists."}), 409

        ret = MATERIAL_APP.create_site(site_id=site_id, site_type=site_type, user_id=user_obj.id)

        if type(ret) is not Site:
            return jsonify({"error": f"Error when creating site."}), 409

        return jsonify({"message": f"Site created successfully.", "data": {"id": ret.id}}), 201
    if request.method == 'PATCH':
        # update a site
        data = request.get_json()
        site_id = data.get('site_id')
        site_obj = MATERIAL_APP.find_site(site_id)

        user_obj = MATERIAL_APP.find_user(flask_login.current_user.id)

        if site_obj is None:
            return jsonify({"error": f"Site {site_id} was not found."}), 404

        ret = {"message": f"Site updated successfully.", "data": {"id": site_obj.id}}

        site_type = data.get('site_type')
        status = data.get('status')
        address = data.get('address')
        raise NotImplementedError


@app.route('/api/user', methods=['GET', 'POST', 'PATCH'])
def api_user():
    # get
    # return user json

    # post
    # create user, return json

    # patch
    # adjust specific user obj attributes
    # allow to note whether appending to a list or popping when relevant.
    # assume that if append/pop is not provided, that we are adding.
    pass


@app.route('/api/catalogueItem', methods=['GET', 'POST', 'PATCH'])
def api_catalogue_item():
    # get
    # return item json

    # post
    # create item, return json

    # patch
    # adjust specific item obj attributes
    # allow to note whether appending to a list or popping when relevant.
    # assume that if append/pop is not provided, that we are adding.
    pass


@app.route('/api/receiveMaterial', methods=['POST'])
def api_receive_material():
    data = request.get_json()

    location = data.get('location')
    project = data.get('project')
    item = data.get('item')
    qty = data.get('qty')

    location_obj = MATERIAL_APP.find_site(location)
    project_obj = MATERIAL_APP.find_site(project)
    item_obj = MATERIAL_APP.find_item(item)

    user_obj = MATERIAL_APP.find_user(flask_login.current_user.id)

    if location is None or location_obj is None:
        return jsonify({"error": f"Location \"{location}\" not found."}), 404
    if project is not None and project_obj is None:
        return jsonify({"error": f"Project \"{project}\" not found."}), 404
    if item is None or (not item):
        return jsonify({"error": f"No item provided."}), 404
    if item_obj is None:
        return jsonify({"error": f"Item \"{item}\" not found."}), 404
    if qty is None:
        return jsonify({"error": f"Qty not provided."}), 400

    ret = MATERIAL_APP.receive(
        user_id=user_obj.id,
        project_id=project_obj.id,
        location=location_obj.id,
        qty=qty,
        item_id=item_obj.id
    )

    return jsonify({"message": f"Item received created successfully.", "data": {"id": ret.id}}), 202


@app.route('/api/transferMaterial', methods=['POST'])
def api_transfer_material():
    data = request.get_json()

    source = data.get('source')
    target = data.get('target')
    item = data.get('item')
    qty = data.get('qty')

    source_obj = MATERIAL_APP.find_site(source)
    target_obj = MATERIAL_APP.find_site(target)
    item_obj = MATERIAL_APP.find_item(item)

    user_obj = MATERIAL_APP.find_user(flask_login.current_user.id)

    if source is None or source_obj is None:
        return jsonify({"error": f"Source site \"{source}\" not found."}), 404
    if target is not None and target_obj is None:
        return jsonify({"error": f"Project \"{target}\" not found."}), 404
    if item is None or (not item):
        return jsonify({"error": f"No item provided."}), 404
    if item_obj is None:
        return jsonify({"error": f"Item \"{item}\" not found."}), 404
    if qty is None:
        return jsonify({"error": f"Qty not provided."}), 400

    ret = MATERIAL_APP.transfer_material(
        user_id=user_obj.id,
        target_id=target_obj.id,
        source_id=source_obj.id,
        qty=qty,
        item_id=item_obj.id
    )

    return jsonify({"message": f"Item received created successfully!", "data": {"id": ret.id}}), 202


@app.route('/api/setInventory', methods=['POST'])
def api_set_inventory():
    data = request.get_json()
    site_id = data.get('site_id')
    item = data.get('item')
    qty = data.get('qty')

    site_obj = MATERIAL_APP.find_site(site_id)
    item_obj = MATERIAL_APP.find_item(item)

    user_obj = MATERIAL_APP.find_user(flask_login.current_user.id)

    if site_obj is None:
        return jsonify({"error": f"Site \"{site_id}\" not found."}), 404
    if user_obj is None:
        return jsonify({"error": f"User \"{user_obj}\" not found."}), 404
    if item_obj is None:
        return jsonify({"error": f"Item \"{item}\" not found."}), 404

    ret = MATERIAL_APP.set_inventory(
        user_id=user_obj.id,
        site_id=site_obj.id,
        qty=qty,
        item_id=item_obj.id
    )

    return jsonify({"message": f"Material QOH updated successfully!", "data": {"id": ret.id}}), 202


@app.route('/api/inventoryReport', methods=['GET'])
def api_inventory_report():
    # allow tags so we can filter material
    pass


@app.route('/api/pickUpMaterial', methods=['POST'])
def api_pick_up_material():
    data = request.get_json()
    site_id = data.get('site_id')

    user_obj = MATERIAL_APP.find_user(flask_login.current_user.id)

    try:
        ret = MATERIAL_APP.patch_site(user_id=user_obj.id, site_id=site_id, data={'status': 'in_transit'})
    except AttributeError:
        return jsonify({"error": f"Value is unchanged in {site_id}."}), 422
    except PermissionError:
        return jsonify({"error": f"Invalid attribute requested for {site_id}."}), 403

    if type(ret) is Site:
        return jsonify({"message": f"Material QOH updated successfully!", "data": {"id": ret.id}}), 202
    return jsonify({"error": f"Unable to edit site {site_id}."}), 404


@app.route('/api/completeIntermediateTransfer', methods=['POST'])
def api_complete_intermediate_material():
    data = request.get_json()
    source_id = data.get('source_id')

    source_obj = MATERIAL_APP.find_site(source_id)
    print(source_id, source_obj)


    target_id = MATERIAL_APP.find_site(source_obj.destination_site).id

    user_obj = MATERIAL_APP.find_user(flask_login.current_user.id)

    MATERIAL_APP.transfer_all_material(user_id=user_obj.id, source_id=source_obj.id, target_id=target_id)
    MATERIAL_APP.patch_site(user_id=user_obj.id, site_id=source_obj.id, data={'status': 'delivered'})


if __name__ == '__main__':
    print(app.template_folder)
    app.run(host='0.0.0.0', port=5000)
