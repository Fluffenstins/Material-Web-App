from datetime import datetime
from dateutil import parser
import random
import string
import bcrypt


ITEM_SPACE = {}


class CoreMaterialObj:
    def __init__(self, name=None, save_data=None):
        self.date_format = '%m/%d/%Y %H:%M:%S'

        if save_data is not None and 'id' in save_data:
            self.id = save_data['id']
        else:
            self.id = self._generate_id()

        ITEM_SPACE[self.id] = self

        self.name = name
        self.type = None
        self.tags = None
        self.comments = []
        self.description = None
        self.associated_people = []
        self.creation_date = None
        self.action_history = []

        self.indexed_values = [
            'name',
            'id',
            'type',
            'action_history',
            'comments',
            'description',
            'associated_people',
            'creation_date'
        ]

    @property
    def display_name(self):
        return self.name

    def _generate_id(self):
        characters = string.ascii_letters + string.digits
        obj_id = ''.join(random.choices(characters, k=12))
        while obj_id in ITEM_SPACE:
            obj_id = ''.join(random.choices(characters, k=12))
        return obj_id

    def json(self):
        ret = {}
        for key in self.indexed_values:
            value = self.__getattribute__(key)
            ret[key] = value
        return ret

    def load_from_json(self, data):
        for key in self.indexed_values:
            if key not in data:
                continue
            self.__setattr__(key, data[key])

    def lookup(self, obj_id):
        return ITEM_SPACE[obj_id]

    def add_action(self, action):
        self.action_history.append(action.id)

    def get_date(self, date_str=None, date_format=None):
        if date_format is None:
            date_format = self.date_format
        if date_str is None:
            date_obj = datetime.now()
        else:
            date_obj = parser.parse(date_str)
        new_date_str = date_obj.strftime(date_format)
        return new_date_str


class Tag(CoreMaterialObj):
    def __init__(self, save_data=None, **kwargs):
        super().__init__(save_data=save_data, **kwargs)
        self.type = 'tag'
        self.value = None
        self.parent_id = None

        self.indexed_values += [
            'value',
            'parent_id'
        ]

        if save_data is not None:
            self.load_from_json(save_data)


class User(CoreMaterialObj):
    def __init__(self, email='', password='', first_name='', last_name='', save_data=None, **kwargs):
        super().__init__(save_data=save_data, **kwargs)
        self.type = 'user'
        self.email = email
        self.password = None
        self.first_name = first_name
        self.last_name = last_name
        self.roles = None
        self.favourites = []
        # I think the person/user separation is going to be removed
        self.person_id = None

        self.indexed_values += [
            'password',
            'person_id',
            'first_name',
            'last_name',
            'email',
            'favourites',
            'roles'
        ]

        if save_data is not None:
            self.load_from_json(save_data)
        else:
            self.password = self.hash_password(password)

    @property
    def display_name(self):
        return self.full_name

    @property
    def person(self):
        return self.lookup(self.person_id)

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    def hash_password(self, password):
        password = password.encode('utf-8')
        password_hash = bcrypt.hashpw(password, bcrypt.gensalt(12))
        password_hash = password_hash.decode('utf-8')
        return password_hash

    def check_password(self, password):
        password_bytes = password.encode('utf-8')
        password_hash = self.password.encode('utf-8')
        ret = bcrypt.checkpw(password_bytes, password_hash)
        return ret


class Role(CoreMaterialObj):
    def __init__(self, name=None, save_data=None, **kwargs):
        super().__init__(save_data=save_data, **kwargs)
        self.type = 'role'
        self.name = name

        self.indexed_values += [
            'name'
        ]

        if save_data is not None:
            self.load_from_json(save_data)


class Person(CoreMaterialObj):
    def __init__(self, save_data=None, **kwargs):
        super().__init__(save_data=save_data, **kwargs)
        self.type = 'person'
        self.name = None
        self.role = None
        self.email = None
        self.user_id = None

        self.indexed_values += [
            'name',
            'role',
            'email',
            'user_id'
        ]

        if save_data is not None:
            self.load_from_json(save_data)

    @property
    def user(self):
        return self.lookup(self.user_id)


class CataloguedItem(CoreMaterialObj):
    def __init__(self, item_id=None, mpn=None, description=None, save_data=None, **kwargs):
        super().__init__(save_data=save_data, **kwargs)
        self.description = description
        self.mpn = mpn
        self.item_id = item_id
        self.correct_item = None
        self.deprecated_items = []

        self.indexed_values += [
            'item_id',
            'mpn',
            'description',
            'correct_item',
            'deprecated_items'
        ]

        if save_data is not None:
            self.load_from_json(save_data)

    @property
    def display_name(self):
        return f"{self.item_id}"

    def get_item(self):
        if self.correct_item is not None:
            return self.lookup(self.correct_item).get_item
        return self

    def item_match(self, text):
        if text == self.item_id or text == self.mpn:
            return True

        for alias in self.deprecated_items:
            deprecated_item = self.lookup(alias)
            if deprecated_item.item_match():
                return True

        return False


class Material(CoreMaterialObj):
    def __init__(self, item_id=None, save_data=None, **kwargs):
        super().__init__(save_data=save_data, **kwargs)
        self.type = 'material'
        self.item_id = item_id
        self.parent_site = None
        self.qty = 0
        self.qty_received = 0
        self.borrows = []

        self.indexed_values += [
            'item_id',
            'parent_site',
            'qty',
            'qty_received',
            'borrows'
        ]

        if save_data is not None:
            self.load_from_json(save_data)

    @property
    def site(self):
        return self.lookup(self.parent_site)

    @property
    def display_name(self):
        return f"{self.item.item_id}"

    def item_match(self, text):
        if text == self.id:
            return True
        return self.item.item_match(text)

    @property
    def item(self):
        return self.lookup(self.item_id).get_item()

    @property
    def last_cycle_count(self):
        for action_id in self.action_history[::-1]:
            action = self.lookup(action_id)
            if action.action_type != 'set_inventory':
                continue
            ret = {'qty': action.data['qty'], 'previous_qty': action.output['previous_qty'], 'date': action.get_date(date_format="%Y-%m-%d")}
            print(ret)
            return ret


class Site(CoreMaterialObj):
    def __init__(self, site_id=None, site_type=None, address=None, status='active', save_data=None, **kwargs):
        super().__init__(save_data=save_data, **kwargs)
        self.type = 'site'
        self.site_type = site_type
        self.site_id = site_id
        self.address = address
        self.parent_site_ids = []
        self.status = status  # used for tracking intermediate sites
        self.destination_site = None  # allows bulk transfers to a destination site
        if self.site_type == 'project':
            self.material_counted_in_inventory = False
        else:
            self.material_counted_in_inventory = True
        self.material_children = []
        self.site_children = []

        self.indexed_values += [
            'site_type',
            'site_id',
            'parent_site_ids',
            'material_counted_in_inventory',
            'material_children',
            'site_children',
            'status',
            'destination_site'
        ]

        if save_data is not None:
            self.load_from_json(save_data)

    @property
    def display_name(self):
        return f"{self.site_id}"

    @property
    def site(self):
        return self.lookup(self.site_id)

    def find_site(self, site_id):

        if self.id == site_id:
            return self

        if self.site_id.lower().strip() == site_id.lower().strip():
            return self

        for site in self.site_children:
            ret = self.lookup(site).find_site(site_id)
            if ret is not None:
                return self.lookup(site)

    def find_material(self, item_id):
        for material_id in self.material_children:
            material_obj = self.lookup(material_id)
            if material_obj.item_match(item_id):
                return material_obj

    def attach_site_parent(self, parent_site, main=False):
        if parent_site.id in self.parent_site_ids:
            return False
        if main:
            self.parent_site_ids.insert(0, parent_site.id)
        else:
            self.parent_site_ids.append(parent_site.id)
        parent_site.site_children.append(self.id)
        return True

    def count_material(self, item_id, recursive=True):
        count = 0
        material_obj = self.find_material(item_id)
        if material_obj is not None:
            count += material_obj.qty
        if recursive:
            for site in self.site_children:
                count += site.count_material(item_id, recursive=recursive)

    def list_item_ids(self, recursive=True):
        item_ids = set()
        for material_obj in self.material_children:
            item_ids.add(material_obj.item_id)
        if recursive:
            for site in self.site_children:
                item_ids = item_ids | site.list_item_ids(recursive=True)
        ret = sorted(list(item_ids))
        return ret

    @property
    def path(self):
        path = []
        node = self
        while True:
            path.append(node.site_id)
            if len(node.parent_site_ids) == 0:
                break
            node = node.lookup(node.parent_site_ids[0])
        ret = " / ".join(path[::-1])
        return ret

    @property
    def is_intermediate(self):
        if self.destination_site is not None:
            return True
        return False


class Action(CoreMaterialObj):
    def __init__(self, action_type=None, save_data=None, **data):
        super().__init__(save_data=save_data)
        self.type = 'action'
        self.action_type = action_type
        self.data = data
        self.processed = False
        self.user = None
        self.output = {}

        try:
            self.creation_date = self.get_date(data['date_str'])
        except KeyError:
            self.creation_date = self.get_date()

        self.indexed_values += [
            'action_type',
            'data',
            'processed',
            'user',
            'output'
        ]

        if save_data is not None:
            self.load_from_json(save_data)

    def display_text(self):
        data = {}
        for key, value in self.data.items():
            try:
                data[key] = self.lookup(value).display_name
            except (KeyError, TypeError):
                data[key] = value
        output = {}
        for key, value in self.output.items():
            try:
                output[key] = self.lookup(value).display_name
            except (KeyError, TypeError):
                output[key] = value

        match self.action_type:
            case "create_material":
                return f"Material created in {self.lookup(self.data['site']).site_id}: {data['item_id']}"
            case "create_site":
                return f"Site \"{data['site_id']}\" of type \"{data['site_type']}\" created."
            case "receive":
                return f"{data['qty']} received for {data['item_id']} at {data['location']}"
            case "move_out":
                return f"{data['qty']} moved out to {data['project_id']} for {data['item_id']} from {data['location']}"
            case "set_site_parent":
                return f"Site {self.lookup(self.data['parent_site_id']).site_id} was set as a parent to {self.lookup(self.data['site_id']).site_id}"
            case "create_user":
                return f"User \"{output['user_id']}\" created"
            case "create_item":
                return f"Item \"{output['catalogued_item_id']}\" catalogued"
            case "transfer_material":
                return f"{data['qty']} of {data['item_id']} transferred to {data['target_id']} from {data['source_id']}"
            case "set_inventory":
                return f"Inventory set to {data['qty']} from {output['previous_qty']}"
            case _:
                print(f"no procedure for {self.action_type}")
                print(self.data)
                return self.action_type

    def add_output(self, key, value):
        self.output[key] = value

    def str_to_int(self, text):
        if type(text) is int:
            return text
        try:
            return int(text)
        except TypeError:
            # allows scientific notation which is allowed by html
            # note that floating point approximations apply here. We don't like this
            return int(float(text))


class Comment(CoreMaterialObj):
    def __init__(self, save_data=None, **kwargs):
        super().__init__(save_data=save_data, **kwargs)
        self.type = 'comment'
        self.parent_id = None
        self.text = None
        self.user = None

        self.indexed_values += [
            'parent_id',
            'text',
            'user'
        ]

        if save_data is not None:
            self.load_from_json(save_data)

