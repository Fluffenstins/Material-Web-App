from MaterialContainer import ContinuousMaterialManager
from GraphAPI import MSDrive


class MaterialInitializer(ContinuousMaterialManager):
    def __init__(self):
        super().__init__()
        self.save_after_action = False

        self.system_user = self.find_user('administration@nubuildinc.ca')
        if self.system_user is None:
            self.system_user = self.create_user(
                email='administration@nubuildinc.ca',
                password='not applicable',
                first_name='system',
                last_name='administration'
            )

        self.drive = MSDrive(batch=False, meta_remote=True)
        self.drive.getMeta()

    def init_users(self):
        pass

    def init_locations(self):
        pass

    def init_projects(self):
        for nb_id, job in self.drive.meta.items():
            sub_project_ids = []
            for key in ['ADM', 'RPAT', 'customer id']:
                try:
                    sub_project_ids += job[key]
                except KeyError:
                    pass
            address = job['address']

            master_site = self.ensure_site(
                user_id=self.system_user.id,
                site_type='project',
                site_id=nb_id,
                address=address
            )

            for sub_project_id in sub_project_ids:
                if self.find_site(sub_project_id) is not None:
                    continue
                self.create_site(
                    user_id=self.system_user.id,
                    site_type='project',
                    site_id=sub_project_id,
                    address=address,
                    parent_site_ids=[master_site.id]
                )

    def init_items(self):
        # set up item catalogue data
        #   for the moment lets only update existing catalogue items
        #   this reduces the clutter in our system of overlapping items
        bad_item = self.ensure_item('369305000')
        good_item = self.ensure_item('02TW0002')
        self.deprecate_item(self.system_user.id, bad_item.id, good_item.id)

    def run_legacy_instructions(self):
        instructions = self.load_instructions()
        for instruction in instructions:
            self.interpret_legacy_instruction(instruction)

    def routine(self):
        print("Initializing users.")
        self.init_users()
        print("Initializing locations.")
        self.init_locations()
        print("Initializing projects.")
        self.init_projects()
        print("Initializing item catalogue.")
        self.init_items()
        print("Running instructions.")
        self.run_legacy_instructions()

        self.save_json()


if __name__ == '__main__':
    initializer = MaterialInitializer()
    initializer.routine()
