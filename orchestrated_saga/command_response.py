class CommandResponse:
    def __init__(self, name: str, saga_id: str, ok: bool):
        self.name = name
        self.saga_id = saga_id
        self.ok = ok
