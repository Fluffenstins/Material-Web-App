import json
from MaterialCore import Action, Material, Site
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
        self.action_history = []

        self.logger = MaterialLogging()

    def save_json(self):
        self._save_core_dict_json(self.sites, "sites")
        self._save_core_dict_json(self.material, "material")
        self._save_core_dict_json(self.people, "people")
        self._save_core_dict_json(self.users, "users")

        self._save_core_list_json(self.action_history, "action_history")

    def _save_core_dict_json(self, core_dict, save_name):
        save_data = {obj_id: obj.json() for obj_id, obj in core_dict.items()}
        with open(f"{self.save_loc}/{save_name}.json", 'w') as file:
            json.dump(save_data, file)

    def _save_core_list_json(self, core_list, save_name):
        save_data = [obj.json() for obj in core_list]
        with open(f"{self.save_loc}/{save_name}", 'w') as file:
            json.dump(save_data, file)

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

        site = self.create_site(site_type)
        return site

    def find_site(self, site_id):
        for obj_id, site in self.sites.items():
            ret = site.find_site(site_id)
            if ret is not None:
                return ret

    def find_material(self, site, item_id):
        material_obj = site.find_material(item_id)
        return material_obj

    def create_site(self, site_type, parent_site_ids=()):
        action = Action('create_site', site_type=site_type, parent_site_ids=parent_site_ids)
        site = self.enact_action(action)
        return site

    def create_material(self, site, item_id):
        action = Action('create_material', site=site.id, item_id=item_id)
        material_obj = self.enact_action(action)
        return material_obj

    def create_person(self):
        pass

    def receive(self, user_id, project_id, item_id, qty, location, date_str=None):
        action = Action(
            'receive',
            user=user_id,
            project_id=project_id,
            item_id=item_id,
            qty=qty,
            location=location,
            date_str=date_str
        )
        action.description = "Receive material."
        self.enact_action(action)

    def enact_action(self, action):
        action_dict = {
            'receive': self._receive,
            'create_material': self._create_material,
            'create_site': self._create_site
        }
        ret = action_dict[action.action_type](action)
        self.action_history.append(action)
        return ret

    def _create_material(self, action):

        site_id = action.data['site']
        item_id = action.data['item_id']

        site = self.sites[site_id]

        material_obj = Material(item_id)
        material_obj.parent_site = site.id
        self.material[material_obj.id] = material_obj

        site.material_children.append(material_obj.id)

        site.add_action(action)
        material_obj.add_action(action)

        return material_obj

    def _create_site(self, action):

        try:
            parent_site_ids = action.data['parent_site_ids']
        except KeyError:
            parent_site_ids = []
        site_type = action.data['site_type']

        site_obj = Site(site_type)
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

        return site_obj

    def _receive(self, action):
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

        location = self.ensure_site('location', location)
        project = self.ensure_site('project', project_id)

        location_material_obj = self.ensure_material(location, item_id)
        project_material_obj = self.ensure_material(project, item_id)

        location_material_obj.qty_received += qty
        location_material_obj.qty += qty

        project_material_obj.qty_received += qty

        location.add_action(action)
        project.add_action(action)
        location_material_obj.add_action(action)
        project_material_obj.add_action(action)

    def _move_out(self, action):
        user_name = action.data['user']
        project_id = action.data['project_id']
        item_id = action.data['item_id']
        qty = action.data['qty']
        location = action.data['location']

        if type(qty) is str:
            qty = int(qty)

        location = self.ensure_site('location', location)
        project = self.ensure_site('project', project_id)

        location_material_obj = self.ensure_material(location, item_id)
        project_material_obj = self.ensure_material(project, item_id)

        location_material_obj.qty -= qty
        project_material_obj.qty += qty

        location.add_action(action)
        project.add_action(action)
        location_material_obj.add_action(action)
        project_material_obj.add_action(action)


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

    def create_action_from_legacy(self):
        # action = Action()
        pass


if __name__ == '__main__':
    manager = ContinuousMaterialManager()
    instructions = manager.load_instructions()
    for instruction in instructions:
        manager.interpret_legacy_instruction(instruction)
    manager.save_json()
