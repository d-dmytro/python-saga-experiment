class Command:
    def __init__(self, name: str, saga_id: str, payload: dict):
        self.name = name
        self.saga_id = saga_id
        self.payload = payload
