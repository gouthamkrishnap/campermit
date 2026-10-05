from pathlib import Path


class Sysfs:
    def __init__(self,root:Path=Path("/sys")):
        self.root=root

    def path(self,*parts:str)->Path:
        return self.root.joinpath(*parts)

    def exists(self,*parts:str)->bool:
        return self.path(*parts).exists()

    def read(self,*parts:str)->str:
        return self.path(*parts).read_text().strip()

    def listdir(self,*parts:str)->list[str]:
        return sorted(
            entry.name
            for entry in self.path(*parts).iterdir()
        )

    def children(self,*parts:str)->list[Path]:
        return sorted(
            entry
            for entry in self.path(*parts).iterdir()
            if entry.is_dir()
        )

    def resolve(self,*parts:str)->Path:
        return self.path(*parts).resolve()