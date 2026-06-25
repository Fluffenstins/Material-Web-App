import json
from MaterialCore import Action, Material, Site, User, CataloguedItem, ITEM_SPACE
from BackupManager import BackupManager
from copy import deepcopy
import threading
from datetime import datetime


class CoreMaterialManager:
    def __init__(self):
        self.save_loc = "SaveData"
        self.sites = {}
        self.material = {}
        self.users = {}
        self.items = {}
        self.action_history = []
        self.last_action_date = datetime.now()

        self.save_after_action = True

        self.backup_manager = BackupManager()

    def save_json(self):
        print("Saving?")
        self._save_core_dict_json(self.sites, "sites")
        self._save_core_dict_json(self.material, "material")
        self._save_core_dict_json(self.users, "users")
        self._save_core_dict_json(self.items, "items")

        self._save_core_list_json(self.action_history, "action_history")

    def load_json(self):
        self.sites = self._load_core_dict_json('sites', Site)
        self.material = self._load_core_dict_json('material', Material)
        self.users = self._load_core_dict_json('users', User)
        self.items = self._load_core_dict_json('items', CataloguedItem)

        self.action_history = self._load_core_list_json('action_history', Action)

    def async_save(self):
        save_thread = threading.Thread(target=self.save_json)
        save_thread.start()

    def make_backup(self):
        save_name = self.backup_manager.make_backup()
        return save_name

    def load_backup(self):
        self.backup_manager.download_backup()
        self.backup_manager.load_backup()

    def lookup(self, item_id):
        item_obj = ITEM_SPACE[item_id]
        return item_obj

    def _save_core_dict_json(self, core_dict, save_name):
        save_data = {obj_id: obj.json() for obj_id, obj in core_dict.items()}
        with open(f"{self.save_loc}/{save_name}.json", 'w') as file:
            json.dump(save_data, file)

    def _save_core_list_json(self, core_list, save_name):
        save_data = [obj.json() for obj in core_list]
        with open(f"{self.save_loc}/{save_name}.json", 'w') as file:
            json.dump(save_data, file)

    def _load_core_dict_json(self, save_name, core_class):
        try:
            with open(f"{self.save_loc}/{save_name}.json") as file:
                raw_data = json.load(file)
        except FileNotFoundError:
            raw_data = {}
        ret = {key: core_class(save_data=data) for key, data in raw_data.items()}
        return ret

    def _load_core_list_json(self, save_name, core_class):
        try:
            with open(f"{self.save_loc}/{save_name}.json") as file:
                raw_data = json.load(file)
        except FileNotFoundError:
            raw_data = []
        ret = [core_class(save_data=data) for data in raw_data]
        return ret

    def ensure_material(self, site, item_id, user_id=None):
        item_id = item_id.strip()
        material_obj = site.find_material(item_id)
        if material_obj is not None:
            return material_obj
        material_obj = self.create_material(site, item_id, user_id=user_id)
        return material_obj

    def ensure_site(self, site_type, site_id, address=None, user_id=None):
        try:
            site_obj = self.lookup(site_id)
            return site_obj
        except KeyError:
            pass
        for obj_id, site in self.sites.items():
            site_obj = site.find_site(site_id)
            if site_obj is not None:
                return site_obj

        site = self.create_site(site_type=site_type, site_id=site_id, address=address, user_id=user_id)
        return site

    def ensure_item(self, item_id, user_id=None):
        item_id = item_id.strip()
        item = self.find_item(item_id)
        if item is not None:
            return item

        item = self.create_item(item_id=item_id, user=user_id)
        return item

    def find_site(self, site_id):
        try:
            obj = self.lookup(site_id)
            if type(obj) is Site:
                return obj
        except KeyError:
            pass
        if not site_id:
            return None
        for obj_id, site in self.sites.items():
            ret = site.find_site(site_id)
            if ret is not None:
                return ret

    def find_material(self, site, item_id):
        item_id = item_id.strip()
        material_obj = site.find_material(item_id)
        return material_obj

    def find_item(self, item_id):
        try:
            item_obj = self.lookup(item_id)
            return item_obj
        except KeyError:
            pass
        item_id = item_id.strip().lower()
        for obj_id, item in self.items.items():
            if item.item_id.lower() == item_id:
                # call get_item to get the correct item, because there may be duplicates
                return item.get_item()

    def find_user(self, email):
        if email is None:
            return None
        try:
            return self.users[email]
        except KeyError:
            pass
        email = email.lower()
        for obj_id, user in self.users.items():
            if user.email.lower() == email:
                return user
        return None

    def create_site(self, site_id, site_type, status=None, parent_site_ids=(), user_id=None, address=None):
        action = Action(
            'create_site',
            site_type=site_type,
            parent_site_ids=parent_site_ids,
            site_id=site_id,
            user=user_id,
            status=status,
            address=address
        )
        site = self.enact_action(action)
        return site

    def create_material(self, site, item_id, user_id=None):

        action = Action('create_material', site=site.id, item_id=item_id, user=user_id)
        material_obj = self.enact_action(action)
        return material_obj

    def create_item(self, item_id, mpn=None, description=None, user=None):
        action = Action('create_item', item_id=item_id, mpn=mpn, description=description, user=user)
        item = self.enact_action(action)
        return item

    def create_user(self, email, password, first_name, last_name):
        # if the provided password is not already encrypted, Grady, I will lose it on you.
        action = Action('create_user', email=email, password=password, first_name=first_name, last_name=last_name)
        user = self.enact_action(action)
        return user

    def receive(self, user_id, project_id, item_id, qty, location, date_str=None):
        action = Action(
            action_type='receive',
            user=user_id,
            project_id=project_id,
            item_id=item_id,
            qty=qty,
            location=location,
            date_str=date_str
        )
        action.description = "Receive material."
        ret = self.enact_action(action)
        return ret

    def move_out(self, user_id, project_id, item_id, qty, location, date_str=None):
        action = Action(
            action_type='move_out',
            user=user_id,
            project_id=project_id,
            item_id=item_id,
            qty=qty,
            location=location,
            date_str=date_str
        )
        action.description = f"Move out material from {location} to {project_id}."
        ret = self.enact_action(action)
        return ret

    def transfer_material(self, user_id, source_id, target_id, item_id, qty, date_str=None):
        action = Action(
            action_type='transfer_material',
            user=user_id,
            source_id=source_id,
            target_id=target_id,
            item_id=item_id,
            qty=qty,
            date_str=date_str
        )
        action.description = f"Transfer material from {source_id} to {target_id}."
        ret = self.enact_action(action)
        return ret

    def transfer_all_material(self, user_id, source_id, target_id):
        action = Action(
            action_type='transfer_all_material',
            user=user_id,
            source_id=source_id,
            target_id=target_id
        )
        action.description = f"Transfer all material from {source_id} to {target_id}."
        ret = self.enact_action(action)
        return ret

    def set_inventory(self, user_id, site_id, item_id, qty: int):
        action = Action(
            action_type='set_inventory',
            user=user_id,
            site_id=site_id,
            item_id=item_id,
            qty=qty
        )
        ret = self.enact_action(action)
        return ret

    def set_site_parent(self, user_id, site_id, parent_site_id):
        action = Action(
            action_type='set_site_parent',
            user=user_id,
            site_id=site_id,
            parent_site_id=parent_site_id
        )
        action.description = "Parent site set."
        self.enact_action(action)

    def patch_site(self, user_id, site_id, data):
        action = Action(
            action_type='patch_site',
            user=user_id,
            site_id=site_id,
            data=data
        )
        action.description = "Site settings changed."
        ret = self.enact_action(action)
        return ret

    def deprecate_item(self, user_id, item_id, correct_item_id):
        action = Action(
            action_type='deprecate_item',
            user=user_id,
            item_id=item_id,
            correct_item_id=correct_item_id
        )
        action.description = f"Correcting item {item_id} to {correct_item_id}"
        self.enact_action(action)
        return action

    def enact_action(self, action):
        action_dict = {
            'receive': self._receive,
            'create_material': self._create_material,
            'create_site': self._create_site,
            'move_out': self._move_out,
            'create_item': self._create_item,
            'create_user': self._create_user,
            'set_site_parent': self._set_site_parent,
            'transfer_material': self._transfer_material,
            'set_inventory': self._set_inventory,
            'transfer_all_material': self._transfer_all_material,
            'patch_site': self._patch_site,
            'deprecate_item': self._deprecate_item
        }
        ret = None
        try:
            ret = action_dict[action.action_type](action)
            action.processed = True
            try:
                action.user = action.output['user_id']
            except KeyError:
                pass
            # note that the action is not added to history unless it fully goes through
            self.action_history.append(action)
            self.last_action_date = datetime.now()
            if self.save_after_action:
                self.async_save()
        except Exception as e:
            raise e
        return ret

    def _create_material(self, action):

        site_id = action.data['site']
        item_id = action.data['item_id']

        site = self.sites[site_id]

        item_obj = self.ensure_item(item_id)

        material_obj = Material(item_id=item_obj.id, name=item_id)
        material_obj.parent_site = site.id
        self.material[material_obj.id] = material_obj

        site.material_children.append(material_obj.id)

        site.add_action(action)
        material_obj.add_action(action)
        item_obj.add_action(action)

        action.add_output('site_id', site.id)
        action.add_output('material_id', material_obj.id)
        action.add_output('catalogue_item_id', item_obj.id)

        return material_obj

    def _create_item(self, action):

        item_id = action.data['item_id']
        mpn = action.data['mpn']
        description = action.data['description']
        user_id = action.data['user']

        user_obj = self.find_user(user_id)

        item_obj = CataloguedItem(
            item_id=item_id,
            mpn=mpn,
            description=description
        )

        self.items[item_obj.id] = item_obj

        item_obj.add_action(action)
        if user_obj is not None:
            user_obj.add_action(action)
            action.add_output('user_id', user_obj.id)

        action.add_output('catalogued_item_id', item_obj.id)

        return item_obj

    def _create_site(self, action):

        try:
            parent_site_ids = action.data['parent_site_ids']
        except KeyError:
            parent_site_ids = []
        site_type = action.data['site_type']
        status = action.data['status']
        site_id = action.data['site_id'].strip()
        user_id = action.data['user']
        address = action.data['address']

        user_obj = self.find_user(user_id)

        # Create the site
        site_obj = Site(site_type=site_type, site_id=site_id, name=site_id, status=status, address=address)
        self.sites[site_obj.id] = site_obj

        for parent_site_id in parent_site_ids:
            try:
                parent_site = self.sites[parent_site_id]
            except KeyError:
                continue
            site_obj.attach_site_parent(parent_site)

        if user_obj is not None:
            user_obj.add_action(action)
            action.add_output('user_id', user_obj.id)

        site_obj.add_action(action)
        action.add_output('site_id', site_obj.id)

        return site_obj

    def _create_user(self, action):
        email = action.data['email']
        first_name = action.data['first_name']
        last_name = action.data['last_name']
        password = action.data['password']

        existing_user = self.find_user(email)
        if existing_user is not None:
            raise KeyError("Email already exists. Please provide a new email, reset password, or login using previous credentials.")

        new_user = User(
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name
        )

        self.users[new_user.id] = new_user

        new_user.add_action(action)

        action.add_output('user_id', new_user.id)

        return new_user

    def _receive(self, action):
        user_name = action.data['user']
        project_id = action.data['project_id']
        item_id = action.data['item_id']
        qty = action.data['qty']
        location = action.data['location']
        # date_str = action.data['date_str']

        try:
            if type(qty) is str:
                qty = int(qty)
        except ValueError:
            print(f"Bad Qty: {action.json()}")
            qty = 0

        if location is None:
            location = 'Default Location'

        user_obj = self.find_user(user_name)

        catalogue_obj = self.ensure_item(item_id)
        item_id = catalogue_obj.item_id

        location_site = self.ensure_site('location', location)
        location_material_obj = self.ensure_material(location_site, item_id)

        location_material_obj.qty_received += qty
        location_material_obj.qty += qty
        # add user actions
        if user_obj is not None:
            user_obj.add_action(action)
            action.add_output('user_id', user_obj.id)
        # add site actions
        location_site.add_action(action)
        # add material actions
        location_material_obj.add_action(action)
        # add catalogue actions
        catalogue_obj.add_action(action)

        action.add_output('location_id', location_site.id)
        action.add_output('location_material_id', location_material_obj.id)

        if project_id is not None:
            project_site = self.ensure_site('project', project_id)
            project_material_obj = self.ensure_material(project_site, item_id)
            project_material_obj.qty_received += qty
            # add site actions
            project_site.add_action(action)
            # add material actions
            project_material_obj.add_action(action)
            action.add_output('project_id', project_site.id)
            action.add_output('project_material_id', project_material_obj.id)

        return action

    def _move_out(self, action):
        user_name = action.data['user']
        project_id = action.data['project_id']
        item_id = action.data['item_id']
        qty = action.data['qty']
        location = action.data['location']

        try:
            if type(qty) is str:
                qty = int(qty)
        except ValueError:
            print(f"Bad Qty: {action.json()}")
            qty = 0

        if location is None:
            location = 'Default Location'

        location = self.ensure_site('location', location)
        project = self.ensure_site('project', project_id)

        location_material_obj = self.ensure_material(location, item_id)
        project_material_obj = self.ensure_material(project, item_id)

        location_material_obj.qty -= qty
        project_material_obj.qty += qty

        # add site actions
        location.add_action(action)
        project.add_action(action)
        # add material actions
        location_material_obj.add_action(action)
        project_material_obj.add_action(action)
        # add catalogue actions
        location_material_obj.item.add_action(action)

        action.add_output('location_id', location.id)
        action.add_output('project_item_id', location_material_obj.id)
        action.add_output('project_id', project.id)
        action.add_output('project_item_id', project_material_obj.id)

        return action

    def _transfer_material(self, action):
        user_name = action.data['user']
        source_id = action.data['source_id']
        target_id = action.data['target_id']
        item_id = action.data['item_id']
        qty = action.data['qty']

        try:
            if type(qty) is str:
                qty = int(qty)
        except ValueError:
            print(f"Bad Qty: {action.json()}")
            qty = 0

        user_obj = self.find_user(user_name)

        source_obj = self.ensure_site('location', source_id)
        target_obj = self.ensure_site('project', target_id)

        item_obj = self.ensure_item(item_id)
        item_id = item_obj.item_id

        source_material_obj = self.ensure_material(source_obj, item_id)
        target_material_obj = self.ensure_material(target_obj, item_id)

        source_material_obj.qty -= qty
        target_material_obj.qty += qty

        # add user actions
        if user_obj is not None:
            user_obj.add_action(action)
            action.add_output('user_id', user_obj.id)
        # add site actions
        source_obj.add_action(action)
        target_obj.add_action(action)
        # add material actions
        source_material_obj.add_action(action)
        target_material_obj.add_action(action)
        # add catalogue actions
        source_material_obj.item.add_action(action)

        action.add_output('source_id', source_obj.id)
        action.add_output('source_item_id', source_material_obj.id)
        action.add_output('target_id', target_obj.id)
        action.add_output('target_item_id', target_material_obj.id)

        return target_material_obj

    def _transfer_all_material(self, action):
        user_id = action.data['user']
        source_id = action.data['source_id']
        target_id = action.data['target_id']

        user_obj = self.find_user(user_id)

        source_obj = self.ensure_site('location', source_id)
        target_obj = self.ensure_site('project', target_id)

        for material_id in source_obj.material_children:
            source_material_obj = self.lookup(material_id)
            target_material_obj = self.ensure_material(site=target_obj, item_id=source_material_obj.item.id)

            target_material_obj.qty += source_material_obj.qty
            source_material_obj.qty = 0

            # add material actions
            source_material_obj.add_action(action)
            target_material_obj.add_action(action)
            # add catalogue actions
            source_material_obj.item.add_action(action)

        # add user actions
        if user_obj is not None:
            user_obj.add_action(action)
            action.add_output('user_id', user_obj.id)
        # add site actions
        source_obj.add_action(action)
        target_obj.add_action(action)

        # add outputs
        action.add_output('user', user_obj.id)
        action.add_output('source_id', source_obj.id)
        action.add_output('target_id', target_obj.id)

        return target_obj

    def _set_site_parent(self, action):
        user_id = action.data['user']
        site_id = action.data['site_id']
        parent_site_id = action.data['parent_site_id']

        user_obj = self.find_user(user_id)
        parent_site_obj = self.find_site(parent_site_id)
        site_obj = self.find_site(site_id)

        went_through = site_obj.attach_site_parent(parent_site_obj)

        parent_site_obj.add_action(action)
        site_obj.add_action(action)
        user_obj.add_action(action)

        action.add_output('user_id', user_obj.id)

        action.add_output('site_id', site_obj.id)
        action.add_output('parent_site_id', parent_site_obj.id)

        if not went_through:
            raise AttributeError("Unable to assign site parent.")

    def _set_inventory(self, action):
        user_id = action.data['user']
        site_id = action.data['site_id']
        item_id = action.data['item_id']
        qty = action.data['qty']

        # ensures that the qty is actually a qty
        qty = action.str_to_int(qty)

        user_obj = self.find_user(user_id)

        site_obj = self.find_site(site_id)

        catalogue_item_obj = self.ensure_item(item_id)
        material_obj = self.ensure_material(site_obj, catalogue_item_obj.item_id)

        # make note of what the inventory was previously
        action.add_output('previous_qty', material_obj.qty)
        # change the qty
        material_obj.qty = qty

        action.add_output('site_id', site_obj.id)
        action.add_output('material_id', material_obj.id)

        action.add_output('user_id', user_obj.id)

        material_obj.add_action(action=action)
        site_obj.add_action(action=action)
        user_obj.add_action(action=action)

        return material_obj

    def _patch_site(self, action):
        user_id = action.data['user']
        site_id = action.data['site_id']
        data = action.data['data']

        user_obj = self.find_user(user_id)
        site_obj = self.find_site(site_id)

        if site_obj is None:
            raise KeyError(f'Site {site_id} not found.')

        for key, value in data.items():
            if key in site_obj.accessible_attributes(user_obj.id):
                if value == deepcopy(site_obj.__getattribute__(key)):
                    raise AttributeError(f"Value {key} does not differ from existing value")
                action.add_output(f'prev_{key}', deepcopy(site_obj.__getattribute__(key)))
                site_obj.__setattr__(key, value)
            else:
                raise PermissionError(f"Invalid attribute {key}")
                # action.add_output(f'error_{key}', value)

        site_obj.add_action(action)

        if user_obj is not None:
            user_obj.add_action(action)
            action.add_output('user_id', user_obj.id)

        action.add_output('site_id', site_obj.id)

        return site_obj

    def _deprecate_item(self, action):
        user_id = action.data['user']
        item_id = action.data['item_id']
        correct_item_id = action.data['correct_item_id']

        user_obj = self.find_user(user_id)
        if user_obj is None:
            raise KeyError(f"Could not user item {user_id}")

        item_obj = self.find_item(item_id)
        if item_obj is None:
            raise KeyError(f"Could not find item {item_id}")

        correct_item_obj = self.find_item(correct_item_id)
        if item_obj is None:
            raise KeyError(f"Could not find item {correct_item_obj}")

        if item_obj.id in correct_item_obj.deprecated_items:
            raise AttributeError(f"Item {item_obj.id} has already been deprecated in favour of {correct_item_obj.id}")

        item_obj.correct_item = correct_item_obj.id
        correct_item_obj.deprecated_items.append(item_obj.id)

        # add action history
        user_obj.add_action(action)
        item_obj.add_action(action)
        correct_item_obj.add_action(action)

        # add outputs
        action.add_output('deprecated_item_id', item_obj.id)
        action.add_output('correct_item_id', correct_item_obj.id)

        return action

    def connect_northumberland(self):
        northumberland_site = self.find_site('24-176')


class ContinuousMaterialManager(CoreMaterialManager):
    def __init__(self):
        super().__init__()
        self.site_cache = {}

    def load_instructions(self):
        with open("Resources/ReferenceQueue.json") as file:
            ret = json.load(file)
        return ret['instructions']

    def interpret_legacy_instruction(self, instruct):
        instruct_type = instruct[0].lower()

        actions = []

        if len(instruct) < 10:
            instruct = instruct + [None]*(10 - len(instruct))

        def check_cache(text):
            try:
                return self.site_cache[text]
            except KeyError:
                return text

        def cache(raw, obj_id):
            self.site_cache[raw] = obj_id

        ret = None

        if instruct_type.find('clear') != -1:
            return []
        elif instruct_type.find('rogers receive') != -1:
            date_str, project_id, item_id, qty, po, oracle, user, _, yard = instruct[1:10]
            user_id = None
            project_id = check_cache(project_id)
            ret = self.receive(user_id=user_id, project_id=project_id, item_id=item_id, qty=qty, location=yard, date_str=date_str)
            cache(project_id, ret.output['project_id'])
        elif instruct_type.find('receive') != -1:
            date_str, project_id, item_id, qty, po, oracle, user, _, yard = instruct[1:10]
            user_id = None
            project_id = check_cache(project_id)
            ret = self.receive(user_id=user_id, project_id=project_id, item_id=item_id, qty=qty, location=yard, date_str=date_str)
            cache(project_id, ret.output['project_id'])
        elif instruct_type.find('move') != -1:
            date_str, project_id, item_id, qty, user, recipient, contractor, yard = instruct[1:9]
            user_id = None
            project_id = check_cache(project_id)
            ret = self.move_out(user_id=user_id, project_id=project_id, item_id=item_id, qty=qty, location=yard, date_str=date_str)
            cache(project_id, ret.output['project_id'])

        return ret

    def create_action_from_legacy(self):
        # action = Action()
        pass


# def init_routine():
#     from GraphAPI import MSDrive
#
#     drive = MSDrive(batch=False, meta_remote=True)
#     drive.getMeta()
#
#     manager = ContinuousMaterialManager()
#     manager.save_after_action = False
#
#     # set up users
#     print("Setting up users")
#     system_user = manager.create_user(
#         email='administration@nubuildinc.ca',
#         password='not applicable',
#         first_name='system',
#         last_name='administration'
#     )
#
#     # set up location data
#     print("Setting up locations")
#
#     # set up project data
#     #   import project
#     #   attach parent projects
#     print("Setting up projects")
#     count = 0
#     for nb_id, job in drive.meta.items():
#         sub_project_ids = []
#         for key in ['ADM', 'RPAT', 'customer id']:
#             try:
#                 sub_project_ids += job[key]
#             except KeyError:
#                 pass
#         address = job['address']
#
#         master_site = manager.ensure_site(
#             site_type='project',
#             site_id=nb_id,
#             address=address
#         )
#         count += 1
#
#         for sub_project_id in sub_project_ids:
#             if manager.find_site(sub_project_id) is not None:
#                 continue
#             manager.create_site(
#                 site_type='project',
#                 site_id=sub_project_id,
#                 address=address,
#                 parent_site_ids=[master_site.id]
#             )
#             count += 1
#     print(f"Instruction count: {count}")
#
#     # run all previous instructions
#     print("Running instructions")
#     instructions = manager.load_instructions()
#     for instruction in instructions:
#         manager.interpret_legacy_instruction(instruction)
#
#     # set up item catalogue data
#     #   for the moment lets only update existing catalogue items
#     #   this reduces the clutter in our system of overlapping items
#     print("Setting up catalogue items")
#     bad_item = manager.find_item('369305000')
#     good_item = manager.find_item('02TW0002')
#     manager.deprecate_item(system_user.id, bad_item.id, good_item.id)
#
#     # Save init
#     manager.async_save()


if __name__ == '__main__':
    pass
