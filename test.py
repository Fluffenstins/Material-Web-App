

class TestClass:
    def __init__(self):
        self.data = None
        self.data_dict = {'data': self.data}
        self.data = 'guelph'
        print(self.data_dict)



test = TestClass()

