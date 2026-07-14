class DocumentStore:

    def __init__(self):
        self.documents = []

    def add_document(self, filename, chunks):

        for index, chunk in enumerate(chunks):

            self.documents.append({
                "document": filename,
                "chunk_id": index,
                "text": chunk
            })

    def get_chunks(self, filename=None):

        if filename is None:
            return [doc["text"] for doc in self.documents]

        return [
            doc["text"]
            for doc in self.documents
            if doc["document"] == filename
        ]
