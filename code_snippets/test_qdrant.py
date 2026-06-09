from qdrant_client import QdrantClient

client = QdrantClient(host="localhost", port=6333)

records, _ = client.scroll(
    collection_name="embedded_articles",
    limit=3,
    with_payload=True,
    with_vectors=False,
)

for record in records:
    print(record.payload)
    print("-" * 50)
