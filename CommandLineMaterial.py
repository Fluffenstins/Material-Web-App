from MaterialContainer import ContinuousMaterialManager
from MaterialCore import ITEM_SPACE
import json
import os


def clear_terminal():
    # Use 'cls' for Windows (os.name is 'nt'), 'clear' for macOS/Linux
    os.system('cls' if os.name == 'nt' else 'clear')


class CommandLineManagerExplorer:
    def __init__(self):
        self.manager = ContinuousMaterialManager()

        self.manager.load_json()

        self.main_loop()

    def main_loop(self):
        while True:
            print("Please enter command:")
            x = input('>:')
            clear_terminal()
            x_split = x.split()
            try:
                command, args = x_split[0].lower(), x_split[1:]
            except IndexError:
                print("No command found in input.")
                continue

            if command == 'sites':
                self.list_sites()
            elif command == 'site':
                try:
                    site_id = args[0]
                except IndexError:
                    print("No site ID provided")
                    continue
                self.display_site(site_id)
            elif command[:3] == 'mat':
                try:
                    print(args)
                    site_id = args[0]
                    item_id = args[1]
                except IndexError:
                    print("No item ID provided")
                    continue
                self.display_material(site_id, item_id)
            elif command[:4] == 'look':
                obj = ITEM_SPACE[args[0]]
                obj_json = self.fill_json(obj.json())
                print(json.dumps(obj_json, indent=2))

    def list_sites(self):
        for obj_id, site in self.manager.sites.items():
            print(f"{obj_id} : {site.site_id} : {site.json()}")

    def display_site(self, site_id):

        print(type(self.manager.sites), f"\"{site_id}\"")
        if site_id in self.manager.sites:
            site = self.manager.sites[site_id]
        else:
            site = self.manager.find_site(site_id)

        if site is None:
            print("No site found.")
            return

        print(f"Site: {site.site_id}")
        obj_json = site.json()
        obj_json = self.fill_json(obj_json)
        print(json.dumps(obj_json, indent=2))

    def display_material(self, site_id, item_id):

        print(type(self.manager.material), f"\"{item_id}\"")
        if site_id in self.manager.sites:
            site = self.manager.sites[site_id]
        else:
            site = self.manager.find_site(site_id)
        if item_id in self.manager.material:
            material_obj = self.manager.material[item_id]
        else:
            material_obj = self.manager.find_material(site, item_id)

        if material_obj is None:
            print("No site found.")
            return

        print(f"Item: {material_obj.item_id}")
        obj_json = material_obj.json()
        obj_json = self.fill_json(obj_json)
        print(json.dumps(obj_json, indent=2))

    def fill_json(self, obj_json):
        for key, val in obj_json.items():
            if key in ['id']:
                continue
            if type(val) != str:
                continue
            try:
                obj_json[key] = ITEM_SPACE[val].json()
            except KeyError:
                pass

        def prune_keys(given_dict, pruned_keys):
            for key in list(given_dict.keys()):
                if key not in pruned_keys:
                    continue
                given_dict[key] = 'PRUNED'
                # del given_dict[key]

            for key, val in given_dict.items():
                if type(val) is dict:
                    prune_keys(val, pruned_keys)
            return given_dict

        prune_keys(obj_json, {'action_history'})

        return obj_json


if __name__ == '__main__':
    explorer = CommandLineManagerExplorer()
