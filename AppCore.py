from datetime import datetime
from dateutil import parser
import random
import string
import bcrypt
import json

ITEM_SPACE = {}


class CoreObj:
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
        self.associated_users = []
        self.creation_date = self.get_date()
        self.action_history = []
        self.files = []

        self.indexed_values = {
            'name':                 {'title': "Name",               'permission': 'edit_all', 'type': 'str'},
            'id':                   {'title': "Object ID",          'permission': 'edit_all', 'type': 'str'},
            'type':                 {'title': "Object Type",        'permission': 'edit_all', 'type': 'str'},
            'files':                {'title': "Files",              'permission': 'edit_all', 'type': 'list'},
            'action_history':       {'title': "Action History",     'permission': 'edit_all', 'type': 'list'},
            'comments':             {'title': "Comments",           'permission': 'edit_all', 'type': 'list'},
            'description':          {'title': "Description",        'permission': 'edit_all', 'type': 'str'},
            'associated_users':     {'title': "Associated Users",   'permission': 'edit_all', 'type': 'list'},
            'creation_date':        {'title': "Creation Date",      'permission': 'edit_all', 'type': 'str'}
        }
        self.protected_values = [
            'id',
            'type',
            'files',
            'action_history',
            'comments',
            'associated_users',
            'creation_date'
        ]

    @property
    def display_name(self):
        return self.name

    def _generate_id(self):
        characters = string.ascii_letters + string.digits
        obj_id = ''.join(random.choices(characters, k=12))
        while True:
            try:
                self.lookup(obj_id)
            except KeyError:
                break
            obj_id = ''.join(random.choices(characters, k=12))
        return obj_id

    def json(self):
        ret = {}
        for key in self.indexed_values:
            value = self.__getattribute__(key)
            ret[key] = value
        try:
            json.dumps(ret)
        except:
            print(f"Unable to make json of obj. {self.id} : {ret}")
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

    def add_file(self, file):
        self.files.append(file.id)

    def get_date(self, date_str=None, date_format=None):
        if date_format is None:
            date_format = self.date_format
        if date_str is None:
            date_obj = datetime.now()
        else:
            date_obj = parser.parse(date_str)
        new_date_str = date_obj.strftime(date_format)
        return new_date_str

    def accessible_attributes(self, user_id=None):
        # provides a list of attributes that should be editable/readable by users
        # if user_id is provided, it checks against the privileges of that user
        return [i for i in self.indexed_values if i not in self.protected_values]

    def display_attr(self, attr):
        if attr not in self.indexed_values:
            raise KeyError(f"{attr} not listed as an indexed value.")
        # if attr in self.protected_values:
        #     raise KeyError(f"{attr} is a protected value.")
        ret = self.__getattribute__(attr)
        try:
            ret = self.lookup(ret).display_name
        except KeyError:
            pass
        if ret is None:
            ret = ""
        return ret


class Comment(CoreObj):
    def __init__(self, parent_id=None, text=None, user_id=None, save_data=None, **kwargs):
        super().__init__(save_data=save_data, **kwargs)
        self.type = 'comment'
        self.parent_id = parent_id
        self.text = text
        self.user = user_id

        self.indexed_values = self.indexed_values | {
            'parent_id': {'title': "Parent ID", 'permission': 'edit_comment', 'type': 'str'},
            'text': {'title': "Text", 'permission': 'edit_comment', 'type': 'str'},
            'user': {'title': "User", 'permission': 'edit_comment', 'type': 'str'},
        }

        self.protected_values += [
            'parent_id'
            'user'
        ]

        if save_data is not None:
            self.load_from_json(save_data)


class Action(CoreObj):
    def __init__(self, action_type=None, save_data=None, **data):
        super().__init__(save_data=save_data)
        self.type = 'action'
        self.action_type = action_type
        self.data = data
        self.processed = False
        self.user = None
        self.output = {}
        self.activation_key = None

        try:
            self.creation_date = self.get_date(data['date_str'])
        except KeyError:
            self.creation_date = self.get_date()

        self.indexed_values = self.indexed_values | {
            'action_type': {'title': "Action Type", 'permission': 'edit_action', 'type': 'str'},
            'data': {'title': "Data", 'permission': 'edit_action', 'type': 'dict'},
            'processed': {'title': "Processed", 'permission': 'edit_action', 'type': 'bool'},
            'user': {'title': "User", 'permission': 'edit_action', 'type': 'str'},
            'output': {'title': "Output", 'permission': 'edit_action', 'type': 'dict'},
            'activation_key': {'title': "Activation Key", 'permission': 'edit_action', 'type': 'str'}
        }
        self.protected_values += [
            'activation_key'
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
                return f"Site \"{data['site_id']}\" of type \"{data['site_type']}\" created"
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
            case "patch_site":
                max_word_count = 2
                patched_attributes = [f"{i[5:]}" for i in output if i[:5] == 'prev_']
                if len(patched_attributes) == 0:
                    return f"Site values update attempt"
                if len(patched_attributes) > max_word_count:
                    patched_attributes = patched_attributes[:2]
                    attr_str = ', '.join(patched_attributes)
                    return f"Site values {attr_str}, updated"
                attr_str = patched_attributes[0]
                val = data['data'][attr_str]
                try:
                    val = self.lookup(val).display_name
                except:
                    pass
                return f"Site value {attr_str} updated to {val}"
            case "patch_item":
                max_word_count = 2
                patched_attributes = [f"{i[5:]}" for i in output if i[:5] == 'prev_']
                if len(patched_attributes) == 0:
                    return f"Item values update attempt"
                if len(patched_attributes) > max_word_count:
                    patched_attributes = patched_attributes[:2]
                    attr_str = ', '.join(patched_attributes)
                    return f"Item values {attr_str}, updated"
                attr_str = patched_attributes[0]
                val = data['data'][attr_str]
                try:
                    val = self.lookup(val).display_name
                except:
                    pass
                return f"Item value {attr_str} updated to {val}"
            case "transfer_all_material":
                return f"All material transferred from {output['source_id']} to {output['target_id']}"
            case "deprecate_item":
                return f"Deprecated {output['deprecated_item_id']}. Correct item is now {output['correct_item_id']}"
            case "create_role":
                return f"Created role \"{output['role_id']}\""
            case "add_user_role":
                return f"Added role \"{output['role_id']}\" to user \"{output['target_user_id']}\""
            case "add_role_permission":
                print(output)
                return f"Added permission \"{data['permission']}\" to role \"{output['role_id']}\""
            case "remove_role_permission":
                return f"Removed permission \"{data['permission']}\" from role \"{output['role_id']}\""
            case "remove_site_parent":
                return f"Removed parent site \"{output['parent_site_id']}\""
            case _:
                print(f"no procedure for {self.action_type}")
                print(self.data)
                return self.action_type

    def strip_data(self):
        for key, value in self.data.items():
            if type(value) is not str:
                continue
            self.data[key] = value.strip()

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


class File(CoreObj):
    def __init__(self, parent=None, source=None, file_name=None, extension=None, extension_type=None, file_type=None, save_data=None, **kwargs):
        super().__init__(save_data=save_data)
        self.type = 'file'
        self.parent = parent
        self.source = source
        self.file_name = file_name
        self.file_type = file_type
        self.extension = extension
        self.extension_type = extension_type

        self.indexed_values = self.indexed_values | {
            'source': {'title': "Source", 'permission': 'edit_file', 'type': 'str'},
            'file_name': {'title': "File Name", 'permission': 'edit_file', 'type': 'str'},
            'extension': {'title': "Extension", 'permission': 'edit_file', 'type': 'str'},
            'extension_type': {'title': "Extension Type", 'permission': 'edit_file', 'type': 'str'},
            }
        self.protected_values += [
        ]

        if save_data is not None:
            self.load_from_json(save_data)

    def display_text(self):
        return f"{self.file_name}.{self.extension}"

    def bytes(self):
        pass


class User(CoreObj):
    def __init__(self, email='', password='', first_name='', last_name='', save_data=None, **kwargs):
        super().__init__(save_data=save_data, **kwargs)
        self.type = 'user'
        self.email = email
        self.password = None
        self.first_name = first_name
        self.last_name = last_name
        self.sitetracker_resource_id = None
        self.roles = None
        self.favourites = []

        self.indexed_values = self.indexed_values | {
            'password': {'title': "Password", 'permission': 'edit_user_password', 'type': 'str'},
            'first_name': {'title': "First Name", 'permission': 'edit_user', 'type': 'str'},
            'last_name': {'title': "Last Name", 'permission': 'edit_user', 'type': 'str'},
            'email': {'title': "Email", 'permission': 'edit_user', 'type': 'str'},
            'favourites': {'title': "Favourites", 'permission': 'edit_user', 'type': 'list'},
            'roles': {'title': "Roles", 'permission': 'edit_user', 'type': 'list'},
            'sitetracker_resource_id': {'title': "SiteTracker Resource ID", 'permission': 'edit_user_st', 'type': 'list'},
        }
        self.protected_values += [
            'password',
            'favourites',
            'roles'
        ]

        if save_data is not None:
            self.load_from_json(save_data)
        else:
            self.password = self.hash_password(password)

        if self.roles is None:
            self.roles = []

    @property
    def display_name(self):
        return self.full_name

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

    def add_role(self, role_id):
        if role_id in self.roles:
            print(f"user {self.display_name} already has the role {role_id}")
            return

        role = self.lookup(role_id)
        if type(role) is not Role:
            return

        self.roles.append(role.id)
        role.user_list.append(self.id)

    def remove_role(self, role_id):
        if role_id not in self.roles:
            print(f"user {self.display_name} does not have the role {role_id}")
            return

        role = self.lookup(role_id)
        if type(role) is not Role:
            return

        try:
            role_idx = self.roles.index(role_id)
            self.roles.pop(role_idx)
        except IndexError:
            pass

        try:
            user_idx = role.user_list.index(self.id)
            if user_idx != -1:
                role.user_list.pop(user_idx)
        except IndexError:
            pass

    def check_permission(self, permission):
        for role_id in self.roles:
            role = self.lookup(role_id)
            if role is None:
                continue
            if role.check_permission(permission):
                return True
        return False


class Tag(CoreObj):
    def __init__(self, save_data=None, **kwargs):
        super().__init__(save_data=save_data, **kwargs)
        self.type = 'tag'
        self.value = None
        self.parent_id = None

        self.indexed_values = self.indexed_values | {
            'value': {'title': "Tag Value", 'permission': 'edit_tag', 'type': 'str'},
            'parent_id': {'title': "Parent ID", 'permission': 'edit_tag', 'type': 'str'},
        }

        if save_data is not None:
            self.load_from_json(save_data)


class Role(CoreObj):
    def __init__(self, name=None, save_data=None, **kwargs):
        super().__init__(save_data=save_data, **kwargs)
        self.type = 'role'
        self.allowed_actions = []
        self.user_list = []
        self.name = name

        self.indexed_values = self.indexed_values | {
            'allowed_actions': {'title': "Allowed Actions", 'permission': 'edit_role', 'type': 'list'},
            'user_list': {'title': "User List", 'permission': 'edit_role', 'type': 'list'}
        }

        if save_data is not None:
            self.load_from_json(save_data)

    @property
    def display_name(self):
        return self.name

    def add_permission(self, permission):
        permission = permission.lower()
        if permission in self.allowed_actions:
            return
        self.allowed_actions.append(permission)

    def remove_permission(self, permission):
        permission = permission.lower()
        try:
            permission_idx = self.allowed_actions.index(permission)
            self.allowed_actions.pop(permission_idx)
        except IndexError:
            pass

    def check_permission(self, permission):
        permission = permission.lower()
        for allowed_action in self.allowed_actions:
            if permission == allowed_action.lower():
                return True
        return False


if __name__ == '__main__':
    pass
