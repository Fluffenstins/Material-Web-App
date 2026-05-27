from datetime import datetime
from dateutil import parser
import random
import string



ITEM_SPACE = {}


class CoreMaterialObj:
    def __init__(self):
        self.date_format = '%m/%d/%Y %H:%M:%S'

        self.id = self._generate_id()
        ITEM_SPACE[self.id] = self

        self.name = None
        self.type = None
        self.tags = None
        self.action_history = []
        self.comments = []
        self.description = None
        self.associated_people = []
        self.creation_date = None

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

    def lookup(self, obj_id):
        return ITEM_SPACE[obj_id]

    def add_action(self, action):
        self.action_history.append(action.id)

    def get_date(self, date_str=None):
        if date_str is None:
            date_obj = datetime.now()
        else:
            date_obj = parser.parse(date_str)
        new_date_str = date_obj.strftime(self.date_format)
        return new_date_str


class Tag(CoreMaterialObj):
    def __init__(self):
        super().__init__()
        self.type = 'tag'
        self.value = None
        self.parent_id = None

        self.indexed_values += [
            'value',
            'parent_id'
        ]


class User(CoreMaterialObj):
    def __init__(self):
        super().__init__()
        self.type = 'user'
        self.username = None
        self.password = None
        self.person_id = None
        self.favourites = []

        self.indexed_values += [
            'username',
            'password',
            'person_id',
            'favourites'
        ]

    @property
    def person(self):
        return self.lookup(self.person_id)


class Person(CoreMaterialObj):
    def __init__(self):
        super().__init__()
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

    @property
    def user(self):
        return self.lookup(self.user_id)


class Material(CoreMaterialObj):
    def __init__(self, item_id):
        super().__init__()
        self.type = 'material'
        self.item_id = item_id
        self.parent_site = None
        self.aliases = []
        self.qty = 0
        self.qty_received = 0
        self.borrows = []

        self.indexed_values += [
            'item_id',
            'parent_site',
            'qty',
            'qty_received',
            'borrows',
            'aliases'
        ]

    def item_match(self, text):
        if self.item_id == text:
            return True
        for alias in self.aliases:
            if alias == text:
                return True
        return False


class Site(CoreMaterialObj):
    def __init__(self, site_type):
        super().__init__()
        self.type = 'site'
        self.site_type = site_type
        self.site_id = None
        self.parent_site_ids = []
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
            'site_children'
        ]

    @property
    def site(self):
        return self.lookup(self.site_id)

    def find_site(self, site_id):

        if self.site_id == site_id:
            return self

        for site in self.site_children:
            ret = site.find_site(site_id)
            if ret is not None:
                return site

    def find_material(self, item_id):
        for material_id in self.material_children:
            material_obj = self.lookup(material_id)
            if material_obj.item_match(item_id):
                return material_obj

    def attach_site_child(self, site):
        self.site_children.append(site.id)

    def attach_site_parent(self, site):
        self.site_children.append(site.id)

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


class Stage(CoreMaterialObj):
    def __init__(self):
        super().__init__()
        self.type = 'stage'

        self.indexed_values += [
        ]


class Action(CoreMaterialObj):
    def __init__(self, action_type, date_str=None, **data):
        super().__init__()
        self.type = 'action'
        self.action_type = action_type
        self.data = data

        self.creation_date = self.get_date(date_str)

        self.indexed_values += [
            'action_type',
            'data'
        ]


class Comment(CoreMaterialObj):
    def __init__(self):
        super().__init__()
        self.type = 'comment'
        self.parent_id = None
        self.text = None
        self.user = None

