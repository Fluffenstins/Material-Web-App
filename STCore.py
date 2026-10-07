from AppCore import CoreObj


class ExampleObj(CoreObj):
    def __init__(self, save_data=None, **kwargs):
        super().__init__(save_data=save_data, **kwargs)

        self.indexed_values = self.indexed_values | {}
        self.protected_values += []

        if save_data is not None:
            self.load_from_json(save_data)

    @property
    def display_name(self):
        return self.id


class Project(CoreObj):
    def __init__(self, status=None, customer_id=None, nb_id=None, st_id=None, location=None, save_data=None, **kwargs):
        super().__init__(save_data=save_data, **kwargs)

        self.customer_id = customer_id
        self.nb_id = nb_id
        self.st_id = st_id

        self.time_entries = None
        self.parent_project = None
        self.child_projects = []
        self.site = None
        self.status = status
        self.location = location

        self.indexed_values = self.indexed_values | {
            'customer_id': {'title': "Customer ID", 'permission': 'edit_project', 'type': 'str'},
            'nb_id': {'title': "NuBuild ID", 'permission': 'edit_project', 'type': 'str'},
            'st_id': {'title': "SiteTracker ID", 'permission': 'edit_project', 'type': 'str'},
            'status': {'title': "Status", 'permission': 'edit_project', 'type': 'str'},
            'location': {'title': "Location", 'permission': 'edit_project', 'type': 'str'},
            'parent_project': {'title': "Parent Project", 'permission': 'edit_project', 'type': 'str'},
            'child_projects': {'title': "Child Projects", 'permission': 'edit_project', 'type': 'list'},
        }
        self.protected_values += [
            'parent_project',
            'child_projects'
        ]

        if save_data is not None:
            self.load_from_json(save_data)

    @property
    def display_name(self):
        return f"{self.nb_id} : {self.customer_id}"


class TimeEntry(CoreObj):
    def __init__(self,
                 status=None,
                 asset_cost=None,
                 vehicle_cost=None,
                 hourly_rate=None,
                 notes=None,
                 project=None,
                 work_start=None,
                 work_end=None,
                 target=None,
                 save_data=None, **kwargs):
        super().__init__(save_data=save_data, **kwargs)
        self.status = status
        self.target = target
        self.asset_cost = asset_cost
        self.vehicle_cost = vehicle_cost
        self.hourly_rate = hourly_rate
        self.notes = notes
        self.project = project
        self.work_start = work_start
        self.work_end = work_end

        self.indexed_values = self.indexed_values | {
            'status': {'title': "Status", 'permission': 'edit_time_entry', 'type': 'str'},
            'target': {'title': "Target User", 'permission': 'edit_time_entry', 'type': 'str'},
            'asset_cost': {'title': "Associated Asset Cost", 'permission': 'edit_time_entry', 'type': 'int'},
            'vehicle_cost': {'title': "Associated Vehicle Cost", 'permission': 'edit_time_entry', 'type': 'int'},
            'hourly_rate': {'title': "User Hourly Rate", 'permission': 'edit_time_entry', 'type': 'int'},
            'notes': {'title': "Notes", 'permission': 'edit_time_entry', 'type': 'str'},
            'project': {'title': "Project", 'permission': 'edit_time_entry', 'type': 'str'},
            'work_start': {'title': "Work Start Datetime", 'permission': 'edit_time_entry', 'type': 'str'},
            'work_end': {'title': "Work End Datetime", 'permission': 'edit_time_entry', 'type': 'str'}
        }
        self.protected_values += [
            'status',
            'asset_cost',
            'vehicle_cost',
            'hourly_rate',
            'project'
        ]

        if save_data is not None:
            self.load_from_json(save_data)

    @property
    def display_name(self):
        return self.id


if __name__ == '__main__':
    pass
