import json
from MaterialCore import Action, Material, Site, User, Person, CataloguedItem, ITEM_SPACE
import logging
import logging.handlers
import queue
import sys


class MaterialLogging:
    def __init__(self):
        self.log_queue = queue.Queue(-1)

        stream_handler = logging.StreamHandler(stream=sys.stdout)
        file_handler = logging.FileHandler("app.log")

        self.listener = logging.handlers.QueueListener(self.log_queue, stream_handler)
        self.listener.start()
        queue_handler = logging.handlers.QueueHandler(self.log_queue)

        self.logger = logging.getLogger(__name__)
        self.logger.addHandler(queue_handler)

    def stop(self):
        self.listener.stop()


class CoreMaterialManager:
    def __init__(self):
        self.save_loc = "SaveData"
        self.sites = {}
        self.material = {}
        self.people = {}
        self.users = {}
        self.items = {}
        self.action_history = []

        self.logger = MaterialLogging()

    def save_json(self):
        print("This should be saved asynchronously!")
        self._save_core_dict_json(self.sites, "sites")
        self._save_core_dict_json(self.material, "material")
        self._save_core_dict_json(self.people, "people")
        self._save_core_dict_json(self.users, "users")
        self._save_core_dict_json(self.items, "items")

        self._save_core_list_json(self.action_history, "action_history")

    def load_json(self):
        self.sites = self._load_core_dict_json('sites', Site)
        self.material = self._load_core_dict_json('material', Material)
        self.people = self._load_core_dict_json('people', Person)
        self.users = self._load_core_dict_json('users', User)
        self.items = self._load_core_dict_json('items', CataloguedItem)

        self.action_history = self._load_core_list_json('action_history', Action)

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

    def ensure_material(self, site, item_id):
        material_obj = site.find_material(item_id)
        if material_obj is not None:
            return material_obj
        material_obj = self.create_material(site, item_id)
        return material_obj

    def ensure_site(self, site_type, site_id):

        for obj_id, site in self.sites.items():
            site_obj = site.find_site(site_id)
            if site_obj is not None:
                return site_obj

        site = self.create_site(site_type=site_type, site_id=site_id)
        return site

    def ensure_item(self, item_id):
        for obj_id, item in self.items.items():
            if item.item_id.lower() == item_id:
                # call get_item to get the correct item, because there may be duplicates
                return item.get_item()

        item = self.create_item(item_id=item_id)
        return item

    def find_site(self, site_id):
        if not site_id:
            return None
        for obj_id, site in self.sites.items():
            ret = site.find_site(site_id)
            if ret is not None:
                return ret

    def find_material(self, site, item_id):
        material_obj = site.find_material(item_id)
        return material_obj

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

    def create_site(self, site_id, site_type, parent_site_ids=()):
        action = Action('create_site', site_type=site_type, parent_site_ids=parent_site_ids, site_id=site_id)
        site = self.enact_action(action)
        return site

    def create_material(self, site, item_id):
        action = Action('create_material', site=site.id, item_id=item_id)
        material_obj = self.enact_action(action)
        return material_obj

    def create_item(self, item_id, mpn=None, description=None):
        action = Action('create_item', item_id=item_id, mpn=mpn, description=description)
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
        self.enact_action(action)

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
        self.enact_action(action)

    def set_site_parent(self, user_id, site_id, parent_site_id):
        action = Action(
            action_type='set_site_parent',
            user=user_id,
            site_id=site_id,
            parent_site_id=parent_site_id
        )
        action.description = "Parent site set."
        self.enact_action(action)

    def enact_action(self, action):
        action_dict = {
            'receive': self._receive,
            'create_material': self._create_material,
            'create_site': self._create_site,
            'move_out': self._move_out,
            'create_item': self._create_item,
            'create_user': self._create_user,
            'set_site_parent': self._set_site_parent
        }
        try:
            ret = action_dict[action.action_type](action)
            action.processed = True
        except Exception as e:
            raise e
            return e
        self.action_history.append(action)
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

        item_obj = CataloguedItem(
            item_id=item_id,
            mpn=mpn,
            description=description
        )

        self.items[item_obj.id] = item_obj

        item_obj.add_action(action)

        action.add_output('catalogued_item_id', item_obj.id)

        return item_obj

    def _create_site(self, action):

        try:
            parent_site_ids = action.data['parent_site_ids']
        except KeyError:
            parent_site_ids = []
        site_type = action.data['site_type']
        site_id = action.data['site_id'].strip()

        # Create the site
        site_obj = Site(site_type=site_type, site_id=site_id, name=site_id)
        self.sites[site_obj.id] = site_obj

        for parent_site_id in parent_site_ids:
            try:
                parent_site = self.sites[parent_site_id]
            except KeyError:
                self.logger.logger.error("Parent site not found.")
                continue
            parent_site.attach_site_child(site_obj)
            site_obj.attach_site_parent(parent_site)

        site_obj.add_action(action)

        action.add_output('site_id', site_obj.id)

        return site_obj

    def _receive(self, action):
        user_name = action.data['user']
        project_id = action.data['project_id']
        item_id = action.data['item_id']
        qty = action.data['qty']
        location = action.data['location']
        date_str = action.data['date_str']

        try:
            if type(qty) is str:
                qty = int(qty)
        except ValueError:
            print(f"Bad Qty: {action.json()}")
            qty = 0

        if location is None:
            location = 'Default Location'

        location_site = self.ensure_site('location', location)
        location_material_obj = self.ensure_material(location_site, item_id)

        location_material_obj.qty_received += qty
        location_material_obj.qty += qty
        # add site actions
        location_site.add_action(action)
        # add material actions
        location_material_obj.add_action(action)
        location_site.add_action(action)
        # add catalogue actions
        location_material_obj.item.add_action(action)

        action.add_output('location_id', location_site.id)
        action.add_output('location_material_id', location_material_obj.id)

        if project_id is not None:
            project = self.ensure_site('project', project_id)
            project_material_obj = self.ensure_material(project, item_id)
            project_material_obj.qty_received += qty
            # add site actions
            project.add_action(action)
            # add material actions
            project_material_obj.add_action(action)
            action.add_output('project_id', project.id)
            action.add_output('project_material_id', project_material_obj.id)

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

        action.add_output('location_id', new_user.id)

        return new_user

    def _set_site_parent(self, action):
        user_id = action.data['user']
        site_id = action.data['site_id']
        parent_side_id = action.data['parent_site_id']

        user_obj = self.find_user(user_id)
        parent_site_obj = self.find_site(parent_side_id)
        site_obj = self.find_site(site_id)

        went_through = site_obj.attach_site_parent(parent_site_obj)

        print(f"Did it go through? {went_through}")

        parent_site_obj.add_action(action)
        site_obj.add_action(action)
        user_obj.add_action(action)

        action.add_output('site_id', site_obj.id)
        action.add_output('parent_side_id', parent_site_obj.id)

        if not went_through:
            raise AttributeError("Unable to assign site parent.")

    def connect_northumberland(self):
        northumberland_site = self.find_site('24-176')


class ContinuousMaterialManager(CoreMaterialManager):
    def __init__(self):
        super().__init__()

    def load_instructions(self):
        with open("Resources/ReferenceQueue.json") as file:
            ret = json.load(file)
        return ret['instructions']

    def interpret_legacy_instruction(self, instruct):
        instruct_type = instruct[0].lower()

        actions = []

        if len(instruct) < 10:
            instruct = instruct + [None]*(10 - len(instruct))

        if instruct_type.find('clear') != -1:
            return []
        elif instruct_type.find('rogers receive') != -1:
            date_str, project_id, item_id, qty, po, oracle, user, _, yard = instruct[1:10]
            user_id = None
            self.receive(user_id=user_id, project_id=project_id, item_id=item_id, qty=qty, location=yard, date_str=date_str)
        elif instruct_type.find('receive') != -1:
            date_str, project_id, item_id, qty, po, oracle, user, _, yard = instruct[1:10]
            user_id = None
            self.receive(user_id=user_id, project_id=project_id, item_id=item_id, qty=qty, location=yard, date_str=date_str)
        elif instruct_type.find('move') != -1:
            date_str, project_id, item_id, qty, user, recipient, contractor, yard = instruct[1:9]
            user_id = None
            self.move_out(user_id=user_id, project_id=project_id, item_id=item_id, qty=qty, location=yard, date_str=date_str)

    def create_action_from_legacy(self):
        # action = Action()
        pass


if __name__ == '__main__':
    manager = ContinuousMaterialManager()
    instructions = manager.load_instructions()
    for instruction in instructions:
        manager.interpret_legacy_instruction(instruction)
    manager.save_json()
