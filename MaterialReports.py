from MaterialContainer import ContinuousMaterialManager


class MaterialReporter:
    def __init__(self, material_app=None):
        if material_app is None:
            material_app = ContinuousMaterialManager()
            material_app.load_json()
        self.mat_app = material_app


if __name__ == '__main__':
    reporter = MaterialReporter()
