from GraphAPI import MSDrive
import os
import shutil


class BackupManager:
    def __init__(self):
        self.drive = MSDrive(batch=False)
        self.storage_location_id = '01ZWWTLPLOUELMUI5ETRHZCJROLL2W2OU4'
        self.data_dir = "SaveData"
        self.backup_dir = "Backups"
        self.backup_name = 'MaterialDBBackup'
        self.extension = "zip"
        self.save_name = f"{self.backup_name}.{self.extension}"

    def backup_path(self):
        return f"{self.backup_dir}/{self.backup_name}"

    def delete_backup(self):
        try:
            os.remove(f"{self.backup_path()}.zip")
        except FileNotFoundError:
            print("Couldn't Delete")
            pass

    def make_backup(self):
        self.delete_backup()
        save_path = self.backup_name
        extension = self.extension
        save_name = f"{save_path}.{extension}"
        shutil.make_archive(base_name=f"{self.backup_path()}", format=self.extension, root_dir=self.data_dir)
        shutil.copy(src=f"{self.backup_path()}.zip", dst=f"{self.backup_name}.zip")
        return save_name

    def upload_backup(self):
        if self.save_name not in os.listdir(self.backup_dir):
            self.make_backup()
        ret = self.drive.upload(
            path=f"{self.backup_dir}/{self.save_name}",
            pref=self.storage_location_id,
            name=self.save_name
        )
        return ret

    def download_backup(self):
        path = f"{self.backup_dir}/{self.save_name}"
        ret = self.drive.get(f"{self.storage_location_id}:/{self.save_name}:/content")
        with open(path, 'wb') as file:
            file.write(ret)
        return path

    def load_backup(self):
        backup_path = f"{self.backup_dir}/{self.save_name}"
        unload_path = f"{self.backup_dir}/UnloadedBackup"
        try:
            os.mkdir(unload_path)
        except FileExistsError:
            pass
        shutil.unpack_archive(backup_path, unload_path)

        shutil.copytree(unload_path, self.data_dir, dirs_exist_ok=True)


if __name__ == '__main__':
    manager = BackupManager()
