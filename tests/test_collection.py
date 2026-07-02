from qdrant_client import QdrantClient

client = QdrantClient("localhost", port=6333)

points, _ = client.scroll(
    collection_name="embedded_articles",
    limit=1000,
    with_payload=True,
)

authors = sorted(
    {
        p.payload.get("author_user_name")
        for p in points
        if p.payload.get("author_user_name")
    }
)

print(authors)
