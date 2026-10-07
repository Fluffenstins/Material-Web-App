from AppCore import CoreObj


class CataloguedItem(CoreObj):
    def __init__(self, item_id=None, mpn=None, description=None, shorthand=None, nubuild_id=None, supplier=None, item_type=None, tracked=False, save_data=None, **kwargs):
        super().__init__(save_data=save_data, **kwargs)
        self.description = description
        self.item_type = item_type
        self.mpn = mpn
        self.nubuild_id = nubuild_id
        self.item_id = item_id
        self.supplier = supplier
        self.shorthand = shorthand
        self.tracked = tracked
        self.correct_item = None
        self.deprecated_items = []

        self.indexed_values = self.indexed_values | {
            'item_id': {'title': "Item ID", 'permission': 'edit_item', 'type': 'str'},
            'item_type': {'title': "Item Type", 'permission': 'edit_item', 'type': 'str'},
            'mpn': {'title': "MPN", 'permission': 'edit_item', 'type': 'str'},
            'nubuild_id': {'title': "NuBuild ID", 'permission': 'edit_item', 'type': 'str'},
            'supplier': {'title': "Supplier", 'permission': 'edit_item', 'type': 'str'},
            'shorthand': {'title': "Shorthand", 'permission': 'edit_item', 'type': 'str'},
            'correct_item': {'title': "Correct Item", 'permission': 'edit_item', 'type': 'str'},
            'deprecated_items': {'title': "Deprecated Items", 'permission': 'edit_item', 'type': 'list'},
            'tracked': {'title': "Tracked", 'permission': 'edit_item', 'type': 'bool'}
        }
        self.protected_values += [
            'deprecated_items',
            'correct_item'
        ]

        if save_data is not None:
            self.load_from_json(save_data)

    @property
    def display_name(self):
        ret = self.item_id
        if self.nubuild_id is not None:
            ret = self.nubuild_id

        if self.shorthand is not None:
            ret = f"{ret} - {self.shorthand}"

        return ret

    def get_item(self):
        if self.correct_item is not None:
            return self.lookup(self.correct_item).get_item()
        return self

    def item_match(self, text):
        if text == self.id:
            return True

        if text == self.nubuild_id:
            return True

        if text == self.item_id or text == self.mpn:
            return True

        for alias in self.deprecated_items:
            deprecated_item = self.lookup(alias)
            if deprecated_item.item_match(text):
                return True

        return False


class Material(CoreObj):
    def __init__(self, item_id=None, save_data=None, **kwargs):
        super().__init__(save_data=save_data, **kwargs)
        self.type = 'material'
        self.item_id = item_id
        self.parent_site = None
        self.qty = 0
        self.qty_received = 0
        self.unique_id = None
        self.borrows = []

        self.indexed_values = self.indexed_values | {
            'item_id': {'title': "Item ID", 'permission': 'edit_material', 'type': 'str'},
            'parent_site': {'title': "Parent Site", 'permission': 'edit_material', 'type': 'str'},
            'qty': {'title': "Quantity", 'permission': 'edit_material', 'type': 'str'},
            'qty_received': {'title': "Quantity Received", 'permission': 'edit_material', 'type': 'str'},
            'borrows': {'title': "Borrows", 'permission': 'edit_material', 'type': 'list'},
            'unique_id': {'title': "Unique ID", 'permission': 'edit_material', 'type': 'str'},
        }
        self.protected_values += [
            'borrows',
            'unique_id',
            'qty',
            'qty_received',
            'parent_site',
            'item_id',
            'description'
        ]

        if save_data is not None:
            self.load_from_json(save_data)

    @property
    def site(self):
        return self.lookup(self.parent_site)

    @property
    def display_name(self):
        if self.unique_id is not None:
            return self.unique_id
        return f"{self.item.item_id} : {self.item.shorthand}"

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

    def set_parent(self, parent_site_id):
        site = self.site
        new_parent_site = self.lookup(parent_site_id)

        if self.id in new_parent_site.material_children:
            raise IndexError("Material already in target site.")

        try:
            site.material_children.pop(site.material_children.index(self.id))
        except IndexError:
            raise IndexError("Material not found in current site.")

        new_parent_site.material_children.append(self.id)
        self.parent_site = new_parent_site.id


class Site(CoreObj):
    def __init__(self, site_id=None, site_type=None, address=None, status='active', save_data=None, shorthand=None, **kwargs):
        super().__init__(save_data=save_data, **kwargs)
        self.type = 'site'
        self.site_type = site_type
        self.shorthand = shorthand
        self.description = None
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

        self.indexed_values = self.indexed_values | {
            'site_type': {'title': "Site Type", 'permission': 'edit_site', 'type': 'str'},
            'shorthand': {'title': "Shorthand", 'permission': 'edit_site', 'type': 'str'},
            'description': {'title': "Description", 'permission': 'edit_site', 'type': 'str'},
            'site_id': {'title': "Site ID", 'permission': 'edit_site', 'type': 'str'},
            'address': {'title': "Address", 'permission': 'edit_site', 'type': 'str'},
            'parent_site_ids': {'title': "Parent Site IDs", 'permission': 'edit_site', 'type': 'list'},
            'material_counted_in_inventory': {'title': "Counted In Inventory", 'permission': 'edit_site', 'type': 'str'},
            'material_children': {'title': "Material Children", 'permission': 'edit_site', 'type': 'list'},
            'site_children': {'title': "Site Children", 'permission': 'edit_site', 'type': 'list'},
            'status': {'title': "Status", 'permission': 'edit_site', 'type': 'str'},
            'destination_site': {'title': "Destination Site", 'permission': 'edit_site', 'type': 'str'},
        }
        self.protected_values += [
            'material_children',
            'site_children',
            'parent_site_ids'
        ]

        if save_data is not None:
            self.load_from_json(save_data)

    @property
    def display_name(self):
        return f"{self.site_id}"

    def subpath(self):
        if self.shorthand is not None:
            return self.shorthand
        return self.site_id

    @property
    def path(self):
        path = []
        node = self
        while True:
            path.append(node.subpath())
            if len(node.parent_site_ids) == 0:
                break
            node = node.lookup(node.parent_site_ids[0])
        ret = " / ".join(path[::-1])
        return ret

    def format_attr(self, val):
        if val is None:
            return None
        status = val.split('_')
        status = ' '.join([i.capitalize() for i in status])
        return status

    @property
    def site(self):
        return self.lookup(self.site_id)

    def find_site(self, site_id):

        if self.id == site_id:
            return self

        if self.site_id.lower().strip() == site_id.lower().strip():
            return self

        if self.path == site_id:
            return self

        for site in self.site_children:
            ret = self.lookup(site).find_site(site_id)
            if ret is not None:
                return ret

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

    def remove_site_parent(self, parent_site):
        if parent_site.id not in self.parent_site_ids:
            return False

        try:
            child_idx = parent_site.site_children.index(self.id)
            parent_idx = self.parent_site_ids.index(parent_site.id)
        except IndexError:
            return False

        self.parent_site_ids.pop(parent_idx)
        parent_site.site_children.pop(child_idx)
        return True

    def count_material(self, item_id, recursive=True):
        count = 0
        material_obj = self.find_material(item_id)
        if material_obj is not None:
            count += material_obj.qty
        if recursive:
            for site_id in self.site_children:
                site_obj = self.lookup(site_id)
                count += site_obj.count_material(item_id, recursive=recursive)
        return count

    def count_received(self, item_id, recursive=True):
        count = 0
        material_obj = self.find_material(item_id)
        if material_obj is not None:
            count += material_obj.qty_received
        if recursive:
            for site_id in self.site_children:
                site_obj = self.lookup(site_id)
                count += site_obj.count_material(item_id, recursive=recursive)
        return count

    def list_item_ids(self, recursive=True):
        item_ids = set()
        for material_id in self.material_children:
            item_ids.add(self.lookup(material_id).item.id)
        if recursive:
            for site_id in self.site_children:
                site_obj = self.lookup(site_id)
                item_ids.update(site_obj.list_item_ids(recursive=True))
        ret = sorted(list(item_ids))
        return ret

    @property
    def is_intermediate(self):
        return self.site_type == 'intermediate'

    @property
    def owner(self):
        for action_id in self.action_history:
            action = self.lookup(action_id)
            if action.action_type != 'create_site':
                continue
            try:
                return self.lookup(action.user)
            except KeyError:
                return None
        return None

