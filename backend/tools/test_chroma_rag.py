import os
import sys

# Get absolute paths to configure environment correctly
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)
project_root = os.path.dirname(backend_dir)

# Add the project root to the python path to allow importing backend modules
sys.pclath.append(project_root)

from dotenv import load_dotenv
import logging

try:
    import chromadb
except ImportError:
    print("Please install chromadb: pip install chromadb")
    sys.exit(1)

from sqlalchemy import select
from backend.database.db import get_db_session
from backend.database.models import Article
from backend.ai_processing.vector_store import generate_embeddings_batch, generate_embedding

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Load local environment variables for the database
load_dotenv(dotenv_path=os.path.join(backend_dir, ".env"))

def main():
    # 1. Fetch articles from your PostgreSQL DB
    logger.info("Fetching articles from the PostgreSQL database...")
    articles_data = []
    
    with get_db_session() as session:
        # Let's get the 50 most recent articles to test with
        stmt = select(Article).order_by(Article.collected_at.desc()).limit(50)
        articles = list(session.scalars(stmt))
        
        for a in articles:
            # Build the text: use title and a snippet of full_text or summary
            parts = [a.title or ""]
            if a.summary:
                parts.append(a.summary[:500])
            elif a.full_text:
                parts.append(a.full_text[:500])
                
            combined_text = " — ".join(p for p in parts if p).strip()
            
            if combined_text:
                articles_data.append({
                    "id": str(a.id),
                    "text": combined_text,
                    "metadata": {
                        "title": a.title,
                        "source": a.source_name,
                        "language": a.language,
                        "url": a.url
                    }
                })

    if not articles_data:
        logger.warning("No articles found in the database. Ensure the db is populated.")
        return

    logger.info(f"Fetched {len(articles_data)} articles from the database.")

    # 2. Embed the articles using your existing MiniLM sentence-transformer
    logger.info("Generating embeddings for the articles (this may take a moment)...")
    texts_to_embed = [item["text"] for item in articles_data]
    
    # We reuse the specific batch embedding function from your pipeline
    embeddings = generate_embeddings_batch(texts_to_embed, batch_size=16)

    # 3. Save them locally in ChromaDB
    chroma_db_dir = os.path.join(backend_dir, "chroma_data")
    logger.info(f"Connecting to local ChromaDB at {chroma_db_dir}...")
    
    # PersistentClient stores db files on disk so they aren't lost
    chroma_client = chromadb.PersistentClient(path=chroma_db_dir)
    
    # Create or get the collection
    collection = chroma_client.get_or_create_collection(name="articles_test")
    
    # Prepare data for Chroma
    ids = [item["id"] for item in articles_data]
    documents = [item["text"] for item in articles_data]
    metadatas = [item["metadata"] for item in articles_data]
    
    logger.info("Upserting articles to ChromaDB...")
    collection.upsert(
        ids=ids,
        embeddings=embeddings,
        documents=documents,
        metadatas=metadatas
    )
    logger.info("Successfully added to ChromaDB!")

    # 4. Test the RAG vector store with a simple query
    test_query = "technology and artificial intelligence"
    logger.info(f"Testing local Chroma DB with query: '{test_query}'")
    
    query_embedding = generate_embedding(test_query)
    
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=3  # Get top 3 closest
    )

    print("\n--- TEST QUERY RESULTS ---")
    for i, meta in enumerate(results["metadatas"][0]):
        dist = results["distances"][0][i]
        title = meta.get("title", "No Title")
        source = meta.get("source", "No Source")
        print(f"{i+1}. [Distance: {dist:.4f}] {title} (Source: {source})")
        
    print("\nTest completed successfully!")

if __name__ == "__main__":
    main()
