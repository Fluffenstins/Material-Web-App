
global app_table_count
app_table_count = 0


class AppTableData:
    def __init__(self, table_name, columns=None, data=None):
        if columns is None:
            columns = []
        if data is None:
            data = []

        # global app_table_count
        global app_table_count
        self.table_id = f"table{app_table_count}"
        print(self.table_id)
        app_table_count += 1

        self.table_name = table_name
        self.columns = columns
        self.column_settings = {}
        self.data = data
        self.column_types = [str for _ in self.columns]
        self.row_links = [None for _ in self.data]
        self.cell_links = [[None for _ in self.columns] for _ in self.data]

    def add_row(self, values, row_link=None, cell_links=()):
        self.data.append(values)
        self.row_links.append(row_link)
        if not cell_links:
            cell_links = [None for _ in self.columns]
        self.cell_links.append(cell_links)


class MaterialTableData(AppTableData):
    def __init__(self, material_list):
        table_name = 'Material'
        columns = ('Item ID', 'Qty', 'Shorthand', 'MPN', 'Description')
        super().__init__(table_name=table_name, columns=columns)
        for mat_obj in material_list:
            if mat_obj.item.shorthand is None:
                continue
            row = [mat_obj.item.item_id, mat_obj.qty, mat_obj.item.shorthand, mat_obj.item.mpn, mat_obj.item.description]
            self.add_row(row, row_link=f'/?obj_id={mat_obj.id}')


if __name__ == '__main__':
    pass
