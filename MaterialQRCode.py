from LabelGen import CustomLabel


class MaterialLabel(CustomLabel):
    def __init__(self, item_id):
        super().__init__()
        self.content = "jotform.com"
        self.text = f"Item ID: {item_id}"


if __name__ == '__main__':
    label = MaterialLabel('01NA0001')
    label.save()

