from qdrant_client import QdrantClient
from services.network.embeddings import EmbeddingModelSingleton

client = QdrantClient(host="localhost", port=6333)

embedding_model = EmbeddingModelSingleton()

query = "What are Graph Attention Networks?"

query_vector = embedding_model(query)

results = client.query_points(
    collection_name="embedded_articles",
    query=query_vector,
    limit=5,
)

for point in results.points:
    print("\nScore:", point.score)

    payload = point.payload

    print("Author:", payload.get("author_user_name"))
    print("Link:", payload.get("link"))
    print(payload.get("content", "")[:500])

    print("-" * 80)
