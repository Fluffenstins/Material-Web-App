import os
from dateutil import parser
from flask import Flask, request, render_template, redirect, jsonify, send_file
import flask_login
from MaterialContainer import ContinuousMaterialManager
from LabelGen import CustomLabel
from MaterialCore import Site, Material, Action, User, CataloguedItem, Role
from functools import wraps

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
    def __init__(self):
        super().__init__()
        self.id = None


@login_manager.user_loader
def user_loader(email):
    internal_user = MATERIAL_APP.find_user(email)
    if internal_user is None:
        return None
    user = FlaskUser()
    user.id = internal_user.id
    return user


@login_manager.request_loader
def request_loader(request_obj):
    email = request_obj.form.get('email')
    if email in USERS:
        return USERS[email]

    internal_user = MATERIAL_APP.find_user(email)
    if internal_user is None:
        return None

    user = FlaskUser()
    user.id = internal_user.id
    return user


def list_all_sites():
    site_objs = [{'id': key, 'text': val.path} for key, val in MATERIAL_APP.sites.items()]
    site_objs = sorted(site_objs, key=lambda x: x['text'])
    return site_objs


def list_all_catalogue_items():
    valid_ids = {val.get_item().id for key, val in MATERIAL_APP.items.items()}
    catalogue_objs = [{'id': key, 'text': MATERIAL_APP.items[key].item_id} for key in valid_ids]
    catalogue_objs = sorted(catalogue_objs, key=lambda x: x['text'])
    return catalogue_objs


def list_action_history_breakdown(obj):
    action_objs = []
    for i in obj.action_history[::-1]:
        try:
            action_objs.append(MATERIAL_APP.lookup(i))
        except KeyError:
            continue
    action_history = [{'id': i.id, 'text': i.display_text()} for i in action_objs]
    return action_history


def list_header_options(user_id):
    header_permission_pairs = {
        'Locations':    (['view_locations', 'edit_all'],                    "window.location.href='/locations'"),
        'Projects':     (['view_projects', 'edit_all'],                     "window.location.href='/locations'"),
        'Stages':       (['view_stages', 'edit_all'],                       "window.location.href='/locations'"),
        'Items':        (['view_items', 'edit_catalogue_item', 'edit_all'], "window.location.href='/locations'"),
        'Users':        (['view_users', 'edit_user', 'edit_all'],           "window.location.href='/locations'"),
        'Roles':        (['view_roles', 'edit_role', 'edit_all'],           "window.location.href='/locations'"),
        'Create Site':  (['create_site', 'edit_all'],                       "window.location.href='/locations'"),
        'Create Item':  (['create_item', 'edit_all'],                       "window.location.href='/locations'")
    }
    header_permission_pairs = {
        key: val for key, val in header_permission_pairs
        if MATERIAL_APP.check_permission(user_id=user_id, permission_ids=val[0])
    }
    return header_permission_pairs


@app.before_request
def check_maintenance_mode():

    if os.environ.get('MAINTENANCE_MODE') == '1':
        # You can bypass specific routes (like an admin dashboard) here
        if request.path in ['/api/setMaintenanceMode', '/setMaintenance', '/api/dbBackup']:
            return None
        return render_template(
            "MaintenancePage.html"
        )
    return None


def permission_required(permission_ids):
    app.app_context()
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user_obj = MATERIAL_APP.find_user(flask_login.current_user.id)
            user_id = user_obj.id
            if not MATERIAL_APP.check_permission(user_id, permission_ids=permission_ids):
                return jsonify({"error": "Permission denied"}), 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator


@app.route("/")
def home_page():
    obj_id = request.args.get('obj_id', default="")
    from_qr = request.args.get('from_qr', default="")

    try:
        obj = MATERIAL_APP.lookup(obj_id)
    except KeyError:
        return redirect("/sites")

    if isinstance(obj, Site):
        if obj.is_intermediate and from_qr != '':
            return redirect(f"/intermediateSite?site_id={obj_id}")
        return redirect(f"/site?site_id={obj_id}")

    redirects = [
        [Material, f"/material?item_id={obj_id}"],
        [Action, f"/action?action_id={obj_id}"],
        [User, f"/user?user_id={obj_id}"],
        [CataloguedItem, f"/catalogue?item_id={obj_id}"],
        [Role, f"/role?role_id={obj_id}"]
    ]

    for data_type, redirect_link in redirects:
        if isinstance(obj, data_type):
            return redirect(redirect_link)

    return redirect("/sites")


@app.route("/material")
@flask_login.login_required
@permission_required(['edit_material', 'edit_all'])
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
        current_tab="Material",
        header_options=list_header_options(user_obj.id)
    )


@app.route("/createSite")
@flask_login.login_required
@permission_required(['create_site', 'edit_site', 'edit_all'])
def create_site_url():
    parent_id = request.args.get('parent_id', default="")
    try:
        parent_site_name = MATERIAL_APP.find_site(parent_id).path
    except AttributeError:
        parent_site_name = ""

    site_type_options = [
        {'id': 'location', 'text': 'Location'},
        {'id': 'project', 'text': 'Project'}
    ]

    site_objs = list_all_sites()
    try:
        user_obj = MATERIAL_APP.find_user(flask_login.current_user.id)
    except AttributeError:
        user_obj = None

    return render_template(
        "CreateSitePage.html",
        user_obj=user_obj,
        current_tab="Create Site",
        parent_sites=site_objs,
        site_type_options=site_type_options,
        parent_site_name=parent_site_name
    )


@app.route("/createItem")
@flask_login.login_required
@permission_required(['create_catalogue_item', 'edit_catalogue_item', 'edit_all'])
def create_item_url():

    item_type_options = [
        {'id': '1', 'text': 'Misc'},
        {'id': '2', 'text': 'Consumables'},
        {'id': '3', 'text': 'Duct'},
        {'id': '4', 'text': 'Vaults'},
        {'id': '5', 'text': 'Endcaps'},
        {'id': '6', 'text': 'Connectors'},
        {'id': '7', 'text': 'Buried Microcable'},
        {'id': '8', 'text': 'Aerial Microcable'},
        {'id': '9', 'text': 'Drop Cable'},
        {'id': '10', 'text': 'Splicing Tray'},
        {'id': '11', 'text': 'Splitters'},
        {'id': '12', 'text': 'Tie wraps'},
        {'id': '13', 'text': 'Tape'},
        {'id': '14', 'text': 'OLT'}
        ]

    supplier_options = [
        {'id': 'HA', 'text': 'Hall'},
        {'id': 'HX', 'text': 'Hexatronic'},
        {'id': 'NR', 'text': 'Noramco'},
        {'id': 'TW', 'text': 'TVC/Wesco'},
        {'id': 'NK', 'text': 'Nokia'},
        {'id': 'CN', 'text': 'Connect'},
        {'id': 'TC', 'text': 'Technity'},
        {'id': 'MC', 'text': 'CT&M'}
        ]

    # site_objs = list_all_sites()
    try:
        user_obj = MATERIAL_APP.find_user(flask_login.current_user.id)
    except AttributeError:
        user_obj = None

    return render_template(
        "CreateCatalogueItem.html",
        user_obj=user_obj,
        current_tab="Create Item",
        item_type_options=item_type_options,
        supplier_options=supplier_options,
    )


@app.route("/editItem")
@flask_login.login_required
@permission_required(['edit_catalogue_item', 'edit_all'])
def edit_item_url():
    item_id = request.args.get('item_id', default="")
    try:
        item_obj = MATERIAL_APP.find_item(item_id)
    except AttributeError:
        return redirect(f"/createItem")

    try:
        user_obj = MATERIAL_APP.find_user(flask_login.current_user.id)
    except AttributeError:
        user_obj = None

    return render_template(
        "EditCatalogueItem.html",
        user_obj=user_obj,
        item_obj=item_obj,
        current_tab="Edit Item",
    )


@app.route("/user")
@flask_login.login_required
@permission_required(['read_user', 'read_all', 'edit_all'])
def user_url():
    user_id = request.args.get('user_id', default="")
    displayed_user_obj = MATERIAL_APP.lookup(user_id)

    is_viewing_self = False

    try:
        user_obj = MATERIAL_APP.find_user(flask_login.current_user.id)
        action_history = list_action_history_breakdown(displayed_user_obj)
        role_objs = [{'id': role_id, 'text': role_obj.display_name} for role_id, role_obj in MATERIAL_APP.roles.items()]
        if user_obj.id == displayed_user_obj.id:
            is_viewing_self = True
    except AttributeError:
        user_obj = None
        action_history = 'N/A'
        role_objs = 'N/A'

    return render_template(
        "UserPage.html",
        qr_code_url=f"{request.url_root}downloadQRCode?obj_id={displayed_user_obj.id}",
        displayed_user_obj=displayed_user_obj,
        user_obj=user_obj,
        action_history=action_history,
        role_objs=role_objs,
        current_tab="User",
        is_viewing_self=is_viewing_self
    )


@app.route("/chart")
def user_chart_url():
    return render_template(
        "ChartTemplate.html"
    )


@app.route("/catalogue")
@flask_login.login_required
@permission_required(['read_catalogue_item', 'edit_catalogue_item', 'edit_all'])
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
@permission_required(['read_action', 'edit_action', 'edit_all'])
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

    interpreted_data = {}

    for key, value in action_obj.data.items():
        interpreted_data[key] = [value]

    interpreted_output = {}

    for key, value in action_obj.output.items():
        try:
            interpreted_output[key] = [
                MATERIAL_APP.lookup(value).display_name,
                f"{request.url_root}?obj_id={value}"
            ]
        except AttributeError:
            interpreted_output[key] = [value]
        except KeyError:
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
@permission_required(['read_site', 'edit_site', 'edit_all'])
def site_url():
    site_id = request.args.get('site_id', default="")
    try:
        site_obj = MATERIAL_APP.lookup(site_id)
    except KeyError:
        site_obj = MATERIAL_APP.find_site(site_id)
    if site_obj is not None:
        # site_id = site_obj.site_id
        # site_type = site_obj.site_type
        # address = site_obj.address
        material_children = sorted([
            {'id': MATERIAL_APP.lookup(i).id, 'text': MATERIAL_APP.lookup(i).item.display_name}
            for i in site_obj.material_children
        ], key=lambda x: x['text'])
        parent_sites = sorted([
            {'id': MATERIAL_APP.lookup(i).id, 'text': MATERIAL_APP.lookup(i).name}
            for i in site_obj.parent_site_ids
        ], key=lambda x: x['text'])
        site_children = sorted([
            {'id': MATERIAL_APP.lookup(i).id, 'text': MATERIAL_APP.lookup(i).name}
            for i in site_obj.site_children
        ], key=lambda x: x['text'])
        action_history = list_action_history_breakdown(site_obj)
    else:
        # site_id = "Not Found"
        # address = "N/A"
        material_children = "N/A"
        site_children = "N/A"
        parent_sites = "N/A"
        action_history = "N/A"
        # site_type = "N/A"

    try:
        user_obj = MATERIAL_APP.find_user(flask_login.current_user.id)
    except AttributeError:
        user_obj = None

    if site_obj.is_intermediate:
        return render_template(
            "StagePage.html",
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
    return render_template(
        "SitePage.html",
        qr_code_url=f"{request.url_root}downloadQRCode?obj_id={site_obj.id}",
        set_parent_url=f"{request.url_root}setSiteParent?site_id={site_obj.id}",
        create_sub_site_url=f"{request.url_root}createSite?parent_id={site_obj.id}",
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
@permission_required(['read_stage', 'read_site', 'edit_stage', 'edit_site', 'edit_all'])
def intermediate_site_url():
    site_id = request.args.get('site_id', default="")
    try:
        site_obj = MATERIAL_APP.lookup(site_id)
    except KeyError:
        site_obj = MATERIAL_APP.find_site(site_id)

    if site_obj is not None:
        material_children = sorted([{'id': MATERIAL_APP.lookup(i).id, 'text': MATERIAL_APP.lookup(i).item.item_id} for i in site_obj.material_children], key=lambda x: x['text'])
        parent_sites = sorted([{'id': MATERIAL_APP.lookup(i).id, 'text': MATERIAL_APP.lookup(i).name} for i in site_obj.parent_site_ids], key=lambda x: x['text'])
        site_children = sorted([{'id': MATERIAL_APP.lookup(i).id, 'text': MATERIAL_APP.lookup(i).name} for i in site_obj.site_children], key=lambda x: x['text'])
        action_history = list_action_history_breakdown(site_obj)
    else:
        material_children = "N/A"
        site_children = "N/A"
        parent_sites = "N/A"
        action_history = "N/A"

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
@permission_required(['edit_site', 'edit_site_parent', 'edit_all'])
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


@app.route("/setSiteDestination", methods=['GET'])
@flask_login.login_required
@permission_required(['edit_site', 'edit_stage', 'edit_all'])
def set_site_destination_page():
    site_id = request.args.get('site_id', default="")
    destination_site_id = request.args.get('destination_id', default="")

    try:
        user_obj = MATERIAL_APP.find_user(flask_login.current_user.id)
    except AttributeError:
        user_obj = None

    site_obj = MATERIAL_APP.find_site(site_id)
    destination_obj = MATERIAL_APP.find_site(destination_site_id)

    print(f"destination {(user_obj, site_obj, destination_obj, destination_site_id)}")

    if None not in (user_obj, site_obj, destination_obj):
        MATERIAL_APP.patch_site(user_id=user_obj.id, site_id=site_obj.id, data={'destination_site': destination_obj.id})
        return redirect(f"/site?site_id={site_obj.id}")

    site_objs = list_all_sites()

    return render_template(
        "SetSiteDestinationPage.html",
        site_url=f"{request.url_root}/?obj_id={site_obj.id}",
        site_obj=site_obj,
        destination_obj=destination_obj,
        user_obj=user_obj,
        site_objs=site_objs,
        current_tab="Site"
    )


@app.route("/receive", methods=['GET'])
@flask_login.login_required
@permission_required(['edit_material', 'edit_all'])
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
@permission_required(['edit_material', 'edit_all'])
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
@permission_required(['read_site', 'read_all', 'edit_site', 'edit_all'])
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
@permission_required(['read_location', 'read_site', 'edit_site', 'read_all', 'edit_all'])
def locations_directory_url():

    site_objs = [{'id': key, 'text': val.path} for key, val in MATERIAL_APP.sites.items() if val.site_type == 'location' and len(val.parent_site_ids) == 0]
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
@permission_required(['read_project', 'read_site', 'edit_site', 'read_all', 'edit_all'])
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


@app.route("/users")
@flask_login.login_required
@permission_required(['read_user', 'edit_user', 'read_all', 'edit_all'])
def users_directory_url():

    site_objs = [{'id': key, 'text': val.display_name} for key, val in MATERIAL_APP.users.items()]
    site_objs = sorted(site_objs, key=lambda x: x['text'])

    try:
        user_obj = MATERIAL_APP.find_user(flask_login.current_user.id)
    except AttributeError:
        user_obj = None

    return render_template(
        "UserDirectory.html",
        current_tab="Users",
        user_objs=site_objs,
        user_obj=user_obj,
    )


@app.route("/items")
@flask_login.login_required
@permission_required(['read_catalogue_item', 'edit_catalogue_item', 'read_all', 'edit_all'])
def items_directory_url():

    catalogue_item_objs = [{'id': key, 'text': val.display_name} for key, val in MATERIAL_APP.items.items()]
    catalogue_item_objs = sorted(catalogue_item_objs, key=lambda x: x['text'])

    try:
        user_obj = MATERIAL_APP.find_user(flask_login.current_user.id)
    except AttributeError:
        user_obj = None

    return render_template(
        "CatalogueItemDirectory.html",
        current_tab="Items",
        catalogue_item_objs=catalogue_item_objs,
        user_obj=user_obj,
    )


@app.route("/roles")
@flask_login.login_required
@permission_required(['read_role', 'edit_role', 'read_all', 'edit_all'])
def roles_directory_url():
    role_objs = [{'id': key, 'text': val.display_name} for key, val in MATERIAL_APP.roles.items()]
    role_objs = sorted(role_objs, key=lambda x: x['text'])

    try:
        user_obj = MATERIAL_APP.find_user(flask_login.current_user.id)
    except AttributeError:
        user_obj = None

    return render_template(
        "RoleDirectory.html",
        current_tab="Roles",
        role_objs=role_objs,
        user_obj=user_obj,
    )


@app.route("/role")
@flask_login.login_required
@permission_required(['read_role', 'edit_role', 'read_all', 'edit_all'])
def role_url():
    role_id = request.args.get('role_id', default="")
    role_obj = MATERIAL_APP.lookup(role_id)

    try:
        user_obj = MATERIAL_APP.find_user(flask_login.current_user.id)
        action_history = list_action_history_breakdown(role_obj)
    except AttributeError:
        user_obj = None
        action_history = 'N/A'

    return render_template(
        "RolePage.html",
        # qr_code_url=f"{request.url_root}downloadQRCode?obj_id={role_obj.id}",
        role_obj=role_obj,
        user_obj=user_obj,
        action_history=action_history,
        current_tab="Role"
    )


@app.route("/setMaintenance")
@flask_login.login_required
@permission_required(['set_maintenance'])
def set_maintenance_url():

    try:
        user_obj = MATERIAL_APP.find_user(flask_login.current_user.id)
    except AttributeError:
        user_obj = None

    return render_template(
        "SetMaintenanceModePage.html",
        user_obj=user_obj,
    )


@app.route("/stages")
@flask_login.login_required
@permission_required(['read_stage', 'read_site', 'edit_site', 'edit_all', 'read_all'])
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
@permission_required(['read_stage', 'read_site', 'edit_site', 'edit_all', 'read_all'])
def stage_url():
    source_site_id = request.args.get('source_id', default="")
    target_site_id = request.args.get('target_id', default="")
    catalogue_id = request.args.get('item_id', default="")

    user_obj = MATERIAL_APP.find_user(flask_login.current_user.id)

    if not target_site_id:
        # find most recent intermediate site for user
        active_staging_sites = []
        for _, site_obj in MATERIAL_APP.sites.items():
            owner = site_obj.owner
            if owner is None:
                continue
            if site_obj.status != 'stage':
                continue
            if owner.id != user_obj.id:
                continue
            active_staging_sites.append(site_obj)

        if len(active_staging_sites) == 0:
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
    label = CustomLabel(obj.display_name, f"{request.root_url}?obj_id={obj.id}&from_qr=true")
    label.save(path='label')
    return send_file(
        'label.pdf',
        as_attachment=True,
        download_name=f"Label {obj.id}.pdf"
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
        return redirect("/register")

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

    MATERIAL_APP.async_save()

    return redirect("site?site_id=OLT1")


@app.route('/login', methods=['GET'])
def login():
    next_url = request.args.get('next', default="")
    if flask_login.current_user.is_authenticated:
        if next_url:
            return redirect(next_url)
        return redirect("site?site_id=OLT1")
    print("Trying sincerely to log in.")
    print(f"Path: {template_dir}")
    return render_template(
        "Login.html"
    )


@app.route('/logout', methods=['GET', 'POST'])
def logout():
    flask_login.logout_user()
    return redirect('/login')


@app.route('/barcode', methods=['GET'])
def barcode_test():
    return render_template(
        "BarCodeScannerTest.html"
    )


@app.route('/api/site', methods=['GET', 'POST', 'PATCH'])
@permission_required(['edit_site', 'edit_all'])
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
        raise NotImplementedError()
    if request.method == 'POST':
        # create a site
        data = request.get_json()
        site_id = data.get('site_id')
        site_type = data.get('site_type')

        user_obj = MATERIAL_APP.find_user(flask_login.current_user.id)

        existing_site_obj = MATERIAL_APP.find_site(site_id)
        if existing_site_obj is not None:
            return jsonify({
                "error": f"Site {site_id} already exists."
            }), 409

        ret = MATERIAL_APP.create_site(site_id=site_id, site_type=site_type, user_id=user_obj.id)

        if isinstance(ret, Site):
            return jsonify({
                "error": "Error when creating site."
            }), 409

        return jsonify({
            "message": "Site created successfully.",
            "data": {"id": ret.id}
        }), 201
    if request.method == 'PATCH':
        # update a site
        data = request.get_json()
        site_id = data.get('site_id')
        site_obj = MATERIAL_APP.find_site(site_id)

        user_obj = MATERIAL_APP.find_user(flask_login.current_user.id)

        if site_obj is None:
            return jsonify({
                "error": f"Site {site_id} was not found."
            }), 404

        # site_type = data.get('site_type')
        # status = data.get('status')
        # address = data.get('address')
        # ret = {"message": f"Site updated successfully.", "data": {"id": site_obj.id}}
        raise NotImplementedError()

    return NotImplementedError()


@app.route('/api/catalogueItems', methods=['GET'])
@permission_required(['read_catalogue_item', 'edit_all'])
def api_items():
    # get
    # return user json

    # post
    # create user, return json

    # patch
    # adjust specific user obj attributes
    # allow to note whether appending to a list or popping when relevant.
    # assume that if append/pop is not provided, that we are adding.
    ret = {'data': {}}
    for item_id, item in MATERIAL_APP.items.items():
        ret['data'][item_id] = item.json()

    print(len(ret['data']))

    return jsonify({
        "message": "Catalogue item list retrieved successfully.",
        "data": ret
    }), 200


@app.route('/api/catalogueItem', methods=['GET', 'POST', 'PATCH'])
@permission_required(['edit_catalogue_item', 'edit_all'])
def api_catalogue_item():
    # get
    # return item json

    # post
    # create item, return json

    # patch
    # adjust specific item obj attributes
    # allow to note whether appending to a list or popping when relevant.
    # assume that if append/pop is not provided, that we are adding.

    data = request.get_json()
    if request.method == 'GET':
        item_id = data.get('item_id')
        item_obj = MATERIAL_APP.lookup(item_id)
        if item_obj is None:
            return jsonify({
                "error": f"Item \"{item_id}\" not found."
            }), 404
        return jsonify({
            "message": f"Item {item_obj.item_id} found.",
            "data": item_obj.json()
        }), 200
    if request.method == 'POST':
        pass
    if request.method == 'PATCH':
        pass

    return jsonify({
        "error": "Requested feature is not implemented."
    }), 501


@app.route('/api/receiveMaterial', methods=['POST'])
@permission_required(['edit_material', 'edit_all'])
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
        return jsonify({
            "error": f"Location \"{location}\" not found."
        }), 404
    if project and project_obj is None:
        return jsonify({
            "error": f"Project \"{project}\" not found."
        }), 404
    if item is None or (not item):
        return jsonify({
            "error": "No item provided."
        }), 404
    if item_obj is None:
        return jsonify({
            "error": f"Item \"{item}\" not found."
        }), 404
    if qty is None:
        return jsonify({
            "error": "Qty not provided."
        }), 400

    if project_obj is None:
        project_id = None
    else:
        project_id = project_obj.id

    ret = MATERIAL_APP.receive(
        user_id=user_obj.id,
        project_id=project_id,
        location=location_obj.id,
        qty=qty,
        item_id=item_obj.id
    )

    return jsonify({
        "message": "Item received created successfully.",
        "data": {"id": ret.id}
    }), 200


@app.route('/api/setSiteParent', methods=['POST'])
@permission_required(['edit_site', 'edit_all'])
def api_set_site_parent():
    data = request.get_json()

    site_id = data.get('site_id')
    parent_site_id = data.get('parent_site_id')

    site_obj = MATERIAL_APP.find_site(site_id)
    parent_site_obj = MATERIAL_APP.find_site(parent_site_id)

    user_obj = MATERIAL_APP.find_user(flask_login.current_user.id)

    if user_obj is None:
        return jsonify({
            "error": "User not found."
        }), 404
    if site_obj is None:
        return jsonify({
            "error": f"Site {site_id} not found."
        }), 404
    if parent_site_obj is None:
        return jsonify({
            "error": f"Site {parent_site_id} not found."
        }), 404

    ret = MATERIAL_APP.set_site_parent(user_obj.id, site_obj.id, parent_site_obj.id)

    return jsonify({
        "message": f"Site {site_obj.site_id}'s parent set to {parent_site_obj.site_id}.",
        "data": {"id": ret.id}
    }), 200


@app.route('/api/transferMaterial', methods=['POST'])
@permission_required(['edit_material', 'edit_all'])
def api_transfer_material():
    data = request.get_json()

    source = data.get('source')
    target = data.get('target')
    item = data.get('item')
    qty = data.get('qty')

    print(source, target, item, qty)

    source_obj = MATERIAL_APP.find_site(source)
    target_obj = MATERIAL_APP.find_site(target)
    item_obj = MATERIAL_APP.find_item(item)

    print([i.display_name for i in [source_obj, target_obj, item_obj]])

    user_obj = MATERIAL_APP.find_user(flask_login.current_user.id)

    if source is None or source_obj is None:
        return jsonify({
            "error": f"Source site \"{source}\" not found."
        }), 404
    if target is not None and target_obj is None:
        return jsonify({
            "error": f"Project \"{target}\" not found."
        }), 404
    if item is None or (not item):
        return jsonify({
            "error": "No item provided."
        }), 404
    if item_obj is None:
        return jsonify({
            "error": f"Item \"{item}\" not found."
        }), 404
    if qty is None:
        return jsonify({
            "error": "Qty not provided."
        }), 400

    ret = MATERIAL_APP.transfer_material(
        user_id=user_obj.id,
        target_id=target_obj.id,
        source_id=source_obj.id,
        qty=qty,
        item_id=item_obj.id
    )

    return jsonify({
        "message": "Item received created successfully!",
        "data": {"id": ret.id}
    }), 200


@app.route('/api/setInventory', methods=['POST'])
@permission_required(['edit_material', 'perform_inventory', 'edit_all'])
def api_set_inventory():
    data = request.get_json()
    site_id = data.get('site_id')
    item = data.get('item')
    qty = data.get('qty')

    site_obj = MATERIAL_APP.find_site(site_id)
    item_obj = MATERIAL_APP.find_item(item)

    user_obj = MATERIAL_APP.find_user(flask_login.current_user.id)

    if site_obj is None:
        return jsonify({
            "error": f"Site \"{site_id}\" not found."
        }), 404
    if user_obj is None:
        return jsonify({
            "error": f"User \"{user_obj}\" not found."
        }), 404
    if item_obj is None:
        return jsonify({
            "error": f"Item \"{item}\" not found."
        }), 404

    ret = MATERIAL_APP.set_inventory(
        user_id=user_obj.id,
        site_id=site_obj.id,
        qty=qty,
        item_id=item_obj.id
    )

    return jsonify({
        "message": "Material QOH updated successfully!",
        "data": {"id": ret.id}
    }), 200


@app.route('/api/createSite', methods=['POST'])
@permission_required(['edit_site', 'edit_all'])
def api_create_site():
    data = request.get_json()
    site_name = data.get('site_name')
    shorthand = data.get('shorthand')
    site_type = data.get('site_type')
    parent_site_name = data.get('parent_site_name')

    parent_site_obj = MATERIAL_APP.find_site(parent_site_name)

    try:
        parent_site_id = parent_site_obj.id
    except AttributeError:
        parent_site_id = None

    user_obj = MATERIAL_APP.find_user(flask_login.current_user.id)

    if user_obj is None:
        return jsonify({
            "error": f"User \"{user_obj}\" not found."
        }), 404

    ret = MATERIAL_APP.create_site(
        site_id=site_name,
        site_type=site_type,
        user_id=user_obj.id,
        parent_site_ids=[parent_site_id],
        shorthand=shorthand
    )

    return jsonify({
        "message": "Site created successfully!",
        "data": {"id": ret.id}
    }), 200


@app.route('/api/createRole', methods=['POST'])
@permission_required(['edit_role', 'edit_all'])
def api_create_role():
    data = request.get_json()
    site_name = data.get('role_name')

    user_obj = MATERIAL_APP.find_user(flask_login.current_user.id)

    if user_obj is None:
        return jsonify({
            "error": f"User \"{user_obj}\" not found."
        }), 404

    ret = MATERIAL_APP.create_role(
        name=site_name,
        user_id=user_obj.id
    )

    print(ret)

    return jsonify({
        "message": "Role created successfully!",
        "data": {"id": ret.id}
    }), 200


@app.route('/api/addPermission', methods=['PATCH'])
@permission_required(['edit_permission', 'edit_all'])
def api_add_permission():
    data = request.get_json()
    role_id = data.get('role_id')
    permission_title = data.get('permission')

    user_obj = MATERIAL_APP.find_user(flask_login.current_user.id)

    if user_obj is None:
        return jsonify({
            "error": f"User \"{user_obj}\" not found."
        }), 404

    ret = MATERIAL_APP.add_role_permission(
        role_id=role_id,
        permission=permission_title,
        user_id=user_obj.id
    )

    print(ret)

    return jsonify({
        "message": "Role permission added successfully!",
        "data": {"id": ret.id}
    }), 200


@app.route('/api/addUserRole', methods=['PATCH'])
@permission_required(['assign_role', 'edit_all'])
def api_add_role():
    data = request.get_json()
    role_id = data.get('role_id')
    target_user_id = data.get('target_user_id')

    role_obj = MATERIAL_APP.find_role(role_id)

    if role_obj is None:
        return jsonify({
            "error": f"Role \"{role_id}\" not found."
        }), 404

    target_user_obj = MATERIAL_APP.find_user(target_user_id)
    user_obj = MATERIAL_APP.find_user(flask_login.current_user.id)

    if user_obj is None:
        return jsonify({
            "error": f"User \"{flask_login.current_user.id}\" not found."
        }), 404

    ret = MATERIAL_APP.add_user_role(
        role_id=role_obj.id,
        target_user_id=target_user_obj.id,
        user_id=user_obj.id
    )

    print(ret)

    return jsonify({
        "message": "Role added successfully!",
        "data": {"id": ret.id}
    }), 200


@app.route('/api/removeUserRole', methods=['PATCH'])
@permission_required(['assign_role', 'edit_all'])
def api_remove_role():
    data = request.get_json()
    role_id = data.get('role_id')
    target_user_id = data.get('target_user_id')

    role_obj = MATERIAL_APP.find_role(role_id)

    if role_obj is None:
        return jsonify({
            "error": f"Role \"{role_id}\" not found."
        }), 404

    target_user_obj = MATERIAL_APP.find_user(target_user_id)
    user_obj = MATERIAL_APP.find_user(flask_login.current_user.id)

    if user_obj is None:
        return jsonify({
            "error": f"User \"{flask_login.current_user.id}\" not found."
        }), 404

    ret = MATERIAL_APP.remove_user_role(
        role_id=role_obj.id,
        target_user_id=target_user_obj.id,
        user_id=user_obj.id
    )

    print(ret)

    return jsonify({
        "message": "Role removed successfully!",
        "data": {"id": ret.id}
    }), 200


@app.route('/api/removePermission', methods=['PATCH'])
@permission_required(['edit_permission', 'edit_all'])
def remove_add_permission():
    data = request.get_json()
    role_id = data.get('role_id')
    permission_title = data.get('permission')

    user_obj = MATERIAL_APP.find_user(flask_login.current_user.id)

    if user_obj is None:
        return jsonify({
            "error": f"User \"{user_obj}\" not found."
        }), 404

    ret = MATERIAL_APP.remove_role_permission(
        role_id=role_id,
        permission=permission_title,
        user_id=user_obj.id
    )

    print(ret)

    return jsonify({
        "message": "Role permission added successfully!",
        "data": {"id": ret.id}
    }), 200


@app.route('/api/createCatalogueItem', methods=['POST'])
@permission_required(['create_catalogue_item', 'edit_catalogue_item', 'edit_all'])
def api_create_catalogue_item():
    data = request.get_json()
    item_type = data.get('item_type')
    supplier = data.get('supplier')
    provided_item_id = data.get('item_id')
    mpn = data.get('mpn')
    description = data.get('description')
    shorthand = data.get('shorthand')

    user_obj = MATERIAL_APP.find_user(flask_login.current_user.id)

    if user_obj is None:
        return jsonify({
            "error": f"User \"{user_obj}\" not found."
        }), 404

    existing_item = MATERIAL_APP.find_item(provided_item_id)
    if existing_item is not None:
        return jsonify({
            "error": f"Item {existing_item.display_name} already exists."
        }), 409

    ret = MATERIAL_APP.create_item(
        item_id=provided_item_id,
        mpn=mpn,
        description=description,
        shorthand=shorthand,
        item_type=item_type,
        supplier=supplier,
        user=user_obj.id
    )

    return jsonify({
        "message": "Item created successfully!",
        "data": {"id": ret.id}
    }), 200


@app.route('/api/editCatalogueItem', methods=['PATCH'])
@permission_required(['edit_catalogue_item', 'edit_all'])
def api_edit_catalogue_item():
    data = request.get_json()
    item_id = data.get('item_id')
    item_type = data.get('item_type')
    supplier = data.get('supplier')
    provided_item_id = data.get('provided_item_id')
    mpn = data.get('mpn')
    description = data.get('description')
    shorthand = data.get('shorthand')

    user_obj = MATERIAL_APP.find_user(flask_login.current_user.id)

    if user_obj is None:
        return jsonify({
            "error": f"User \"{user_obj}\" not found."
        }), 404

    existing_item = MATERIAL_APP.find_item(item_id)
    if existing_item is None:
        return jsonify({
            "error": f"Item {provided_item_id} could not be found."
        }), 404

    data = {}
    for key, new_value, old_value in (
            ('item_type', item_type, existing_item.item_type),
            ('supplier', supplier, existing_item.supplier),
            ('item_id', provided_item_id, existing_item.item_id),
            ('mpn', mpn, existing_item.mpn),
            ('description', description, existing_item.description),
            ('shorthand', shorthand, existing_item.shorthand),
    ):
        if not new_value:
            continue
        if new_value == old_value:
            print(f"{key}: {new_value} == {old_value}")
            continue
        data[key] = new_value

    ret = MATERIAL_APP.patch_item(
        item_id=item_id,
        user_id=user_obj.id,
        data=data
    )

    return jsonify({
        "message": "Item created successfully!",
        "data": {"id": ret.id}
    }), 200


@app.route('/api/inventoryReport', methods=['GET'])
@permission_required(['read_all', 'edit_all'])
def api_inventory_report():
    # allow tags so we can filter material
    pass


@app.route('/api/pickUpMaterial', methods=['POST'])
def api_pick_up_material():
    data = request.get_json()
    site_id = data.get('site_id')

    user_obj = MATERIAL_APP.find_user(flask_login.current_user.id)

    try:
        ret = MATERIAL_APP.patch_site(
            user_id=user_obj.id,
            site_id=site_id,
            data={'status': 'in_transit'}
        )
    except AttributeError:
        return jsonify({
            "error": f"Value is unchanged in {site_id}."
        }), 422
    except PermissionError:
        return jsonify({
            "error": f"Invalid attribute requested for {site_id}."
        }), 403

    if isinstance(ret, Site):
        return jsonify({
            "message": "Material QOH updated successfully!",
            "data": {"id": ret.id}
        }), 200
    return jsonify({
        "error": f"Unable to edit site {site_id}."
    }), 404


@app.route('/api/completeIntermediateTransfer', methods=['POST'])
def api_complete_intermediate_material():
    data = request.get_json()
    source_id = data.get('source_id')

    source_obj = MATERIAL_APP.find_site(source_id)

    if source_obj.status == 'delivered':
        return jsonify({
            "error": f"No destination site found for {source_id}."
        }), 404

    try:
        target_id = MATERIAL_APP.find_site(source_obj.destination_site).id
    except AttributeError:
        return jsonify({
            "error": f"No destination site found for {source_id}."
        }), 404

    user_obj = MATERIAL_APP.find_user(flask_login.current_user.id)

    MATERIAL_APP.transfer_all_material(
        user_id=user_obj.id,
        source_id=source_obj.id,
        target_id=target_id
    )
    MATERIAL_APP.patch_site(
        user_id=user_obj.id,
        site_id=source_obj.id,
        data={'status': 'delivered'}
    )

    return jsonify({
        "data": {'id': target_id}
    }), 200


@app.route('/api/login', methods=['POST'])
def api_login():
    """

    :return:
    """
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    if email is None:
        return jsonify({
            "error": "No email provided."
        }), 400
    if password is None:
        return jsonify({
            "error": "No password provided."
        }), 400

    user = user_loader(email)
    if user is None:
        return jsonify({
            "error": "Client user creation failed. Please make sure user exists"
        }), 424

    user_obj = MATERIAL_APP.find_user(email)

    # need to check password
    if not user_obj.check_password(password):
        return jsonify({
            "error": "Incorrect password."
        }), 403

    flask_login.login_user(user)
    USERS[user_obj.id] = user
    # if not next_url:
    #     return redirect("sites")
    # return redirect(next_url)
    return jsonify({
        "data": {'id': user_obj.id}
    }), 200


@app.route('/api/dbBackup', methods=['GET'])
def api_db_backup():
    save_name = MATERIAL_APP.make_backup()
    path = f"{MATERIAL_APP.backup_manager.backup_path()}.zip"
    return send_file(
        save_name,
        as_attachment=True,
        download_name=path,
    )


@app.route('/api/setMaintenanceMode', methods=['POST'])
def api_set_maintenance_mode():
    """Sets entire app into Maintenance Mode.

    Restricts access to all endpoints except those pertaining to maintenance setting.
    Specifically to allow backups to have the most up to date data, and to make sure changes aren't made
    while the system is restarting.

    Args:
        table_handle: An open smalltable.Table instance.
        keys: A sequence of strings representing the key of each table
          row to fetch.  String keys will be UTF-8 encoded.
        require_all_keys: If True only rows with values set for all keys will be
          returned.

    Returns:
        {b'Serak': ('Rigel VII', 'Preparer'),
         b'Zim': ('Irk', 'Invader'),
         b'Lrrr': ('Omicron Persei 8', 'Emperor')}

    Raises:
        IOError: An error occurred accessing the smalltable.
    """
    data = request.get_json()
    state = data.get('state')
    # user_obj = MATERIAL_APP.find_user(flask_login.current_user.id)

    if state:
        os.environ['MAINTENANCE_MODE'] = '1'
    else:
        os.environ['MAINTENANCE_MODE'] = '0'

    return jsonify({
        "message": f"Maintenance mode set to {state}",
        "data": {'state': state}
    }), 200


@app.route('/downloads/rustdesk', methods=['GET'])
@permission_required(['download_all'])
def download_rustdesk():
    url = 'https://github.com/rustdesk/rustdesk/releases/download/1.4.4/rustdesk-1.4.4-x86_64.msi'
    return redirect(url)


@app.route('/downloads/bitdefender', methods=['GET'])
@permission_required(['download_all'])
def download_bitdefender():
    url = 'https://cloud.gravityzone.bitdefender.com/Packages/BSTWIN/0/setupdownloader_[aHR0cHM6Ly9jbG91ZC1lY3MuZ3Jhdml0eXpvbmUuYml0ZGVmZW5kZXIuY29tL1BhY2thZ2VzL0JTVFdJTi8wL2k4ckVuVy9pbnN0YWxsZXIueG1sP2xhbmc9ZW4tVVM=].exe'
    return redirect(url)


@app.route('/downloads/rmm', methods=['GET'])
@permission_required(['download_all'])
def download_rmm():
    url = 'https://shared.outlook.inky.com/link?domain=ca.ninjarmm.com&t=h.eJxtj7tywyAQRX_Fozq8BBhw5SRVitjfsIZFJkbII9CkyOTfYzIp0949e-ber2Fb83DYDdfW7vXAmAdaUvmAdZ6pX2YGE5bGUqkNcsaVjWHUXFtJxmgEUU4E4gxwYoWwKpoYESITnHKqjLDs1F3nguS5e8hpe9lSDq9LaSv4lsr0Vjx5h1TOMSb_wLa20Lmm4Wk33Hqvsl36B5sqwies4fgXpOKpBybNRXOBTkqn9jLspYuPSKB2KDQGYMJoJ-w4WtULcSW6GX8XY74HrLejnxr6a1nyMiWsfXVnQmf-OX3_AKBlYQc.MEQCIFpgCRxHezk9Uz4zOBqqtGPSiD9IxP0bwuuDmvF9pt6XAiB7uCDoXTmqYrHXzfodbv0ugwFBSwO1hFOQ9Y7LIHCfBg'
    return redirect(url)


@app.route('/downloads/params', methods=['GET'])
@permission_required(['download_all'])
def download_params():
    return send_file('Parameters.json')


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
