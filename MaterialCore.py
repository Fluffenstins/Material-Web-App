

class CoreMaterialObj:
    def __init__(self):
        self.name = None
        self.id = None
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

    def json(self):
        ret = {}
        for key in self.indexed_values:
            value = self.__getattribute__(key)
            ret[key] = value
        return ret


class Tag(CoreMaterialObj):
    def __init__(self):
        super().__init__()
        self.type = 'tag'
        self.value = None

        self.indexed_values += [
            'value'
        ]


class User(CoreMaterialObj):
    def __init__(self):
        super().__init__()
        self.type = 'user'

        self.indexed_values += [
        ]


class Person(CoreMaterialObj):
    def __init__(self):
        super().__init__()
        self.type = 'person'

        self.indexed_values += [
        ]


class Material(CoreMaterialObj):
    def __init__(self):
        super().__init__()
        self.type = 'material'
        self.item_id = None
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


class Site(CoreMaterialObj):
    def __init__(self):
        super().__init__()
        self.type = 'site'
        self.parent_sites = []
        self.site_obj = None
        self.material_counted_in_inventory = True
        self.material_children = []

        self.indexed_values += [
            'parent_sites',
            'site_obj',
            'material_counted_in_inventory',
            'material_children'
        ]


class Location(CoreMaterialObj):
    def __init__(self):
        super().__init__()
        self.type = 'location'

        self.indexed_values += [
        ]


class Project(CoreMaterialObj):
    def __init__(self):
        super().__init__()
        self.type = 'project'
        self.project_id = None

        self.indexed_values += [
            'project_id'
        ]


class Stage(CoreMaterialObj):
    def __init__(self):
        super().__init__()
        self.type = 'stage'

        self.indexed_values += [
        ]


class Action(CoreMaterialObj):
    def __init__(self):
        super().__init__()
        self.type = 'action'

        self.indexed_values += [
        ]


class Comment(CoreMaterialObj):
    def __init__(self):
        super().__init__()
        self.type = 'comment'
        self.parent_id = None
        self.text = None
        self.user = None

